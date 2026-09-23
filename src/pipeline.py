import json
import re
import sqlite3
import time
import boto3
import streamlit as st
from src.constants import (
    MODEL,  DATA_PATH, CAUSE_BROKEN_DOWN_TABLES, SQL_MAX_ATTEMPTS,
    CHART_KEYWORDS, MAP_KEYWORDS, SQL_ROW_LIMIT, MAX_QUESTION_CHARS, REASONING_EFFORT_QUERY, REASONING_EFFORT_DEFAULT,
    SQL_TIMEOUT_SECONDS, SQL_MAX_VALUE_BYTES,
)
from src.catalog import (
    get_schema_text, get_lookup_tables, format_sources, list_topics, get_column_unit,
)
from src.charts import TRUNCATED_NOTE
from src.retrieval import retrieve_relevant_tables, tables_in_sql, mentions_president
from src.i18n import t, get_lang
from src.model import call_model, extract_sql, strip_thoughts
from src.prompts import (
    build_sql_prompt, build_answer_prompt, build_gate_prompt, build_chart_title_prompt,
    SPANISH_ANSWER_RULES, TRUNCATED_ANSWER_RULES,
)

s3 = boto3.client(
    "s3",
    endpoint_url=st.secrets["r2"]["endpoint_url"],
    aws_access_key_id=st.secrets["r2"]["access_key_id"],
    aws_secret_access_key=st.secrets["r2"]["secret_access_key"],
    region_name="auto",
)


def sum_unfiltered_cause_deaths(sql: str, conn: sqlite3.Connection) -> str:
    """
    See CAUSE_BROKEN_DOWN_TABLES: these two tables have no all-causes row, so a query that
    never filters cause leaves one row per cause instead of a grand total. Scoped tightly -
    only fires when the SQL touches one of those exact tables, never mentions "cause"
    anywhere (the model always does, whether filtering `cause_code =` or `... cause LIKE`),
    and isn't already aggregating or ranking (SUM / GROUP BY / ORDER BY) - so a query
    that already filters or sums a cause, or ranks causes as detail rows, is untouched.
    It also only sums rows that don't overlap - detail rows (`is_total = 0`), or one pinned
    sex and age band; `is_total = 1` alone still returns the sex/age subtotals, and summing
    them over-counted 3-4x. The query's other selected columns (year, department, ...) are
    kept as GROUP BY keys, so a multi-year result stays one row per year.
    """
    if not any(re.search(rf"\b{t}\b", sql, re.IGNORECASE) for t in CAUSE_BROKEN_DOWN_TABLES):
        return sql
    where = re.split(r"\bWHERE\b", sql, maxsplit=1, flags=re.IGNORECASE)
    condition = where[1] if len(where) > 1 else ""
    if re.search(r"cause", condition, re.IGNORECASE):
        return sql
    if re.search(r"\bSUM\s*\(|\bGROUP BY\b|\bORDER BY\b", sql, re.IGNORECASE):
        return sql
    detail = re.search(r"\bis_total\s*=\s*0\b", condition, re.IGNORECASE)
    pinned = all(re.search(rf"\b{col}\b", condition, re.IGNORECASE) for col in ("sex", "age_group"))
    if not (detail or pinned):
        return sql
    inner = sql.rstrip().rstrip(";")
    columns = [d[0] for d in conn.execute(f"SELECT * FROM ({inner}) LIMIT 0").description]
    if "deaths" not in columns:
        return sql
    # per-cause columns (cause names, rates) can't be summed or kept as group keys
    keys = ['"{}"'.format(c.replace('"', '""')) for c in columns
            if c != "deaths" and not re.search(r"cause|(^|_)rate(_|$)", c, re.IGNORECASE)]
    group_by = f" GROUP BY {', '.join(keys)}" if keys else ""
    return f"SELECT {', '.join([*keys, 'SUM(x.deaths) AS deaths'])} FROM ({inner}) AS x{group_by}"


def run_sql_with_retry(question_en: str, schema_text: str, stage) -> tuple[str, list[dict] | None]:
    """Generate SQL, run it, and on 0 rows, a SQLite error or no query at all retry up
    to SQL_MAX_ATTEMPTS times, feeding the failed query and reason back to the model.
    Returns (sql, rows) on the first attempt that yields rows - up to SQL_ROW_LIMIT + 1 of
    them, the extra one only telling answer_question the result was cut. If every attempt
    failed, returns (last sql, None), where "" means the last reply had no SQL query."""
    prior_attempts: list[tuple[str, str]] = []
    for _ in range(SQL_MAX_ATTEMPTS):
        stage(t("Writing the SQL query…" if not prior_attempts else "Adjusting the SQL query…"))
        sql_query = extract_sql(call_model(
            build_sql_prompt(question_en, schema_text, prior_attempts,
                             wants_map=wants_map(question_en)), model=MODEL,
            reasoning_effort=REASONING_EFFORT_QUERY))
        if not sql_query:
            prior_attempts.append(("(no query)", "did not return a SQL query"))
            continue
        stage(t("Running the query…"))
        conn = sqlite3.connect(f"file:{DATA_PATH}?mode=ro", uri=True)  # read-only: generated SQL can never write
        deadline = time.monotonic() + SQL_TIMEOUT_SECONDS
        conn.set_progress_handler(lambda: time.monotonic() > deadline, 10_000)  # truthy = abort
        # the progress handler can't interrupt one huge value (randomblob(1e8) x 20 rows = 2 GB
        # in 4s, measured) - cap every string/blob so a result can't exhaust RAM or the prompt
        conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, SQL_MAX_VALUE_BYTES)
        try:
            sql_query = sum_unfiltered_cause_deaths(sql_query, conn)
            # Row cap (+1 to detect a cut result): the LIMIT lets SQLite stop early; fetchmany
            # is the hard cap, since a trailing unclosed /* in the generated SQL comments the
            # LIMIT out
            sql_query = f"SELECT * FROM ({sql_query.strip().rstrip(';')}) LIMIT {SQL_ROW_LIMIT + 1}"
            # Rows carry their column names into the answer prompt: a bare tuple leaves the
            # model to infer from the SELECT list which number is the value and which is a rate.
            cursor = conn.cursor().execute(sql_query)
            columns = [d[0] for d in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchmany(SQL_ROW_LIMIT + 1)]
            reason = "returned 0 rows" if not rows else None
        except sqlite3.Error as e:
            rows = None
            reason = (f"timed out after {SQL_TIMEOUT_SECONDS}s" if str(e) == "interrupted"
                      else f"failed with error: {e}")
        finally:
            conn.close()

        if reason is None:
            return sql_query, rows
        prior_attempts.append((sql_query, reason))
    return sql_query, None


def _json_line(raw: str, name: str) -> dict:
    """The JSON object on the `NAME: {...}` line of a model reply, {} if missing/broken."""
    match = re.search(rf"^\s*{name}:\s*(\{{.*\}})\s*$", raw, re.MULTILINE)
    try:
        return json.loads(match.group(1)) if match else {}
    except json.JSONDecodeError:
        return {}


def parse_chart_title(raw: str, question: str) -> dict:
    """Pull title, column->label, and (Spanish only) column->unit and data value
    translation maps out of build_chart_title_prompt's reply. Falls back to the
    question / empty maps if the model drops the format - a bad chart title/label
    is cosmetic, never worth failing the chart over."""
    title_match = re.search(r"TITLE:\s*(.+)", raw)
    title = title_match.group(1).strip().strip('"') if title_match else ""
    return {"title": title or question, "labels": _json_line(raw, "LABELS"),
            "units": _json_line(raw, "UNITS"), "values": _json_line(raw, "VALUES")}


def chart_values_to_translate(rows: list[dict]) -> list[str]:
    """Distinct text data values that can end up as legend/axis entries. 2-digit
    strings are skipped: they are the department codes the map keys on."""
    values = {v for row in rows for v in row.values()
              if isinstance(v, str) and not re.fullmatch(r"\d{2}", v)}
    # over 100 distinct values (e.g. every municipality) the result is left
    # untranslated - raise the cap if long category lists need Spanish too
    return sorted(values) if len(values) <= 100 else []


def gate_verdict(raw: str) -> str:
    """Collapse the answerability gate's reply to one of three tokens, keyed off the
    first word of the first line. Anything that isn't clearly ANSWERABLE, UNCLEAR or WRONG_LANGUAGE
    is treated as OUT_OF_SCOPE — the gate refuses rather than let a question it
    couldn't classify through to the pipeline."""
    words = re.findall(r"[A-Z_]+", (raw.strip().splitlines() or [""])[0].upper())
    head = words[0] if words else ""
    if head == "ANSWERABLE":
        return "ANSWERABLE"
    if head in ("UNCLEAR", "WRONG_LANGUAGE", "MALICIOUS"):
        return head
    return "OUT_OF_SCOPE"


def gate_translation(raw: str) -> str:
    """The English translation on the gate's `QUESTION: ...` line (es only), "" if the
    line is missing. Markdown bold around the label is tolerated."""
    match = re.search(r"^[\s*]*QUESTION[\s*]*:[\s*]*(.+)", raw, re.MULTILINE)
    return match.group(1).strip(" *") if match else ""


def wants_chart(question: str) -> bool:
    """Chart the result instead of writing a prose answer when the question asks
    for a chart by keyword."""
    q = question.lower()
    return any(k in q for k in CHART_KEYWORDS)


def wants_map(question: str) -> bool:
    """Route to the department choropleth view when the question asks for it."""
    q = question.lower()
    return any(k in q for k in MAP_KEYWORDS)


def answer_question(question: str, embedder, table_index, catalog, status=None) -> str | dict:
    """Full text-to-SQL pipeline for one question. Takes only the current
    question.

    `status` is the caller's st.status handle, relabelled as each stage starts. The
    per-stage wait is dominated by model queueing variance (0.8s-40s for the same
    prompt, measured), so which stage is waiting is the only useful thing to show.
    """
    def stage(label: str) -> None:
        if status:
            status.update(label=label)

    if not question.strip():
        return t("Please provide a question and I'll look it up in the data.")

    if len(question) > MAX_QUESTION_CHARS:
        return t("That question is too long. Please keep it under {n} characters.").format(
            n=MAX_QUESTION_CHARS)

    lang = get_lang()
    stage(t("Checking the question…"))
    gate_prompt = build_gate_prompt(question, list_topics(catalog), lang)
    gate_reply = strip_thoughts(call_model(gate_prompt, model=MODEL, temperature=0,
                                            reasoning_effort=REASONING_EFFORT_DEFAULT))
    verdict = gate_verdict(gate_reply)
    if verdict == "OUT_OF_SCOPE":
        # the gate is a single-word classification and occasionally misfires even at
        # temperature=0 (backend non-determinism) - a second sample avoids rejecting a
        # genuinely in-scope question on a fluke
        gate_reply = strip_thoughts(call_model(gate_prompt, model=MODEL, temperature=0,
                                                reasoning_effort=REASONING_EFFORT_DEFAULT))
        verdict = gate_verdict(gate_reply)
    if verdict == "WRONG_LANGUAGE":
        return t("This chat is set to English. Please ask your question in English, or reload "
                 "the page to change the language.")
    if verdict == "MALICIOUS":
        return t("I can only answer questions about Colombian statistics.")
    if verdict == "UNCLEAR":
        return t("I'm not sure what you're asking. Could you rephrase with the specific "
                 "indicator, place and time period you have in mind?")
    if verdict != "ANSWERABLE":
        return (t("Sorry, I can't answer that with the data I currently have. "
                  "Here's what I can help with:\n\n") + list_topics(catalog, lang))

    # Retrieval, schema and SQL only ever see English; for es the gate translated it.
    question_en = question
    if lang == "es":
        # the gate occasionally drops its QUESTION: line - resample once, else carry on with
        # the Spanish text (retrieval and chart keywords work worse on it; SQL still copes)
        question_en = (gate_translation(gate_reply)
                       or gate_translation(strip_thoughts(call_model(
                           gate_prompt, model=MODEL, temperature=0,
                           reasoning_effort=REASONING_EFFORT_DEFAULT)))
                       or question)

    stage(t("Finding relevant tables…"))
    relevant_tables = retrieve_relevant_tables(question_en, table_index, embedder)
    if mentions_president(question_en, catalog) and "presidential_terms" not in relevant_tables:
        relevant_tables.append("presidential_terms")

    lookup_tables = get_lookup_tables(relevant_tables, catalog)

    all_tables = relevant_tables + [t for t in lookup_tables if t not in relevant_tables]

    schema_text = get_schema_text(DATA_PATH, all_tables, catalog)

    sql_query, rows = run_sql_with_retry(question_en, schema_text, stage)
    if rows is None:
        if not sql_query:
            return t("Sorry, we couldn't answer your question this time. Please try again "
                     "or rephrase it.")
        return t('We couldn\'t find data for your question: "{question}". Could you try '
                 "being more specific about the indicator, place and time period?").format(question=question)

    truncated = len(rows) > SQL_ROW_LIMIT
    rows = rows[:SQL_ROW_LIMIT]

    answer_tables = tables_in_sql(sql_query, all_tables)
    sources = format_sources(answer_tables, catalog)

    if wants_chart(question_en) or wants_map(question_en):
        # the DB's own unit (from column_dictionary/measures) is authoritative -
        # the y-axis shows this directly rather than trusting the LLM to guess/include one
        # every row is checked: a long table's `value` column can hold several measures, and
        # one y-axis unit is only right when all rows agree on it (else none is shown)
        units = {}
        for col in rows[0].keys():
            found = {next((u for t in answer_tables
                           if (u := get_column_unit(t, col, row, catalog, sql_query))), None)
                     for row in rows}
            if len(found) == 1 and (unit := found.pop()):
                units[col] = unit
        stage(t("Titling the chart…"))
        to_translate = ({"units": units, "values": chart_values_to_translate(rows)}
                        if lang == "es" else None)
        chart = parse_chart_title(strip_thoughts(call_model(
            build_chart_title_prompt(question, list(rows[0].keys()), lang, to_translate),
            model=MODEL, temperature=0, reasoning_effort=REASONING_EFFORT_DEFAULT)), question)
        if lang == "es":
            units = {col: chart["units"].get(col) or unit for col, unit in units.items()}
            values = chart["values"]
            rows = [{k: values.get(v, v) if isinstance(v, str) else v for k, v in row.items()}
                    for row in rows]
        default_view = "Map" if wants_map(question_en) else ("Line" if len(rows) > 1 else "Bar")
        return {"rows": rows, "title": chart["title"], "sources": sources,
                "default_view": default_view, "labels": chart["labels"], "units": units,
                "truncated": truncated}

    answer_schema = get_schema_text(DATA_PATH, answer_tables, catalog, query_hint=False)

    stage(t("Writing the answer…"))
    answer_prompt = build_answer_prompt(question, sql_query, rows, answer_schema)
    if truncated:
        answer_prompt += TRUNCATED_ANSWER_RULES.format(n=SQL_ROW_LIMIT)
    if lang == "es":
        answer_prompt += SPANISH_ANSWER_RULES
    answer = strip_thoughts(call_model(answer_prompt, model=MODEL, temperature=0,
                                        reasoning_effort=REASONING_EFFORT_DEFAULT))
    note = f"\n\n*{t(TRUNCATED_NOTE).format(n=SQL_ROW_LIMIT)}*" if truncated else ""
    return answer + note + sources
