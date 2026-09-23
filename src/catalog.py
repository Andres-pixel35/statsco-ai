import re
import sqlite3
import streamlit as st
from src.constants import MAX_ENUMERATED_CHARS
from src.i18n import t
from src.translations import TOPICS_ES


@st.cache_resource
def load_catalog(db_path: str) -> dict:
    """
    Reads colombia.db's metadata tables — the single source of truth for what each
    table holds — into one in-memory dict, so per-question schema work is a dict
    slice instead of a query storm.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)  # ro: never creates an empty DB
    try:
        dataset_catalog = {
            name: {"title": title, "description": desc, "grain": grain,
                   "query_hint": hint, "topic": topic,
                   "source_name": source_name, "source_url": source_url}
            for name, title, desc, grain, hint, topic, source_name, source_url in conn.execute(
                "SELECT table_name, title, description, grain, query_hint, topic, "
                "source_name, source_url "
                "FROM dataset_catalog WHERE builder_script IS NOT NULL")}

        column_dictionary = {}
        for table, col, desc, unit, allowed, lookup, role in conn.execute(
                "SELECT table_name, column_name, description, unit, allowed_values, "
                "lookup_table, role FROM column_dictionary"):
            column_dictionary.setdefault(table, {})[col] = {
                "description": desc, "unit": unit, "allowed_values": allowed,
                "lookup_table": lookup, "role": role}

        measures = {}
        for table, key_col, key_val, unit, basis, derivation in conn.execute(
                "SELECT table_name, key_column, key_value, unit, unit_basis, derivation "
                "FROM measures ORDER BY table_name, key_column, key_value"):
            measures.setdefault(table, []).append((key_col, key_val, unit, basis, derivation))

        dimension_values = {}
        for table, col, value, is_total in conn.execute(
                "SELECT table_name, column_name, value, is_total FROM dimension_values "
                "ORDER BY table_name, column_name, sort_order"):
            dimension_values.setdefault(table, {}).setdefault(col, []).append((value, is_total))
    finally:
        conn.close()

    return {"dataset_catalog": dataset_catalog, "column_dictionary": column_dictionary,
            "measures": measures, "dimension_values": dimension_values}


def list_topics(catalog: dict, lang: str = "en") -> str:
    """One markdown line per dataset — its title and the curated topic sentence.
    Used both as the answerability gate's capability list and as the body of the
    out-of-scope reply shown to the user. `presidential_terms` is a join-only lookup
    table (year -> president), not a topic of its own, so it's left out here.
    lang="es" swaps in TOPICS_ES for display; the gate always gets English."""
    es = TOPICS_ES if lang == "es" else {}
    return "\n".join("- {}: {}".format(*es.get(name, (m['title'], m['topic'])))
                     for name, m in catalog["dataset_catalog"].items()
                     if name != "presidential_terms")


def enumerate_values(column: dict, values: list[tuple[str, int]] | None) -> str:
    """
    A column's closed vocabulary, phrased the way the SQL prompt's exact-match rule
    expects to find it. `allowed_values` is the builder's own declared list;
    `dimension_values` is what the table actually holds (as (value, is_total)
    pairs), and covers the columns the builder never declared one for. Values that
    are a pre-computed aggregate over the column's other values are marked so the
    SQL prompt knows not to sum them with their siblings.
    """
    agg = {v for v, is_total in (values or []) if is_total}
    listed = (column["allowed_values"].split(",") if column.get("allowed_values")
              else [v for v, _ in (values or [])])
    if not listed:
        return ""
    text = "; ".join(f"'{v}' (aggregate)" if v in agg else f"'{v}'" for v in listed)
    return f" Values: {text}." if len(text) <= MAX_ENUMERATED_CHARS else ""


def get_column_unit(table: str, col: str, row: dict, catalog: dict, sql: str = "") -> str | None:
    """The unit for a chart-result column: from column_dictionary directly, or -
    for long/tidy tables that store several measures in one `value` column - from
    the measures table, keyed by the row's own measure-key column value. The SQL
    text is a fallback for the key column's value: the query almost always pins
    it in a WHERE clause (e.g. `LOWER(TRIM(measure)) = 'level'`) without
    SELECTing it, so it's rarely present in `row` itself."""
    col_meta = catalog["column_dictionary"].get(table, {}).get(col, {})
    if col_meta.get("unit"):
        return col_meta["unit"]
    if col_meta.get("role") != "value":
        return None
    for key_col, key_val, m_unit, _basis, _derivation in catalog["measures"].get(table, []):
        if not m_unit:
            continue
        if key_col in row:
            if row[key_col] == key_val:
                return m_unit
        elif re.search(rf"{re.escape(key_col)}.{{0,15}}=\s*'{re.escape(key_val)}'",
                       sql, re.IGNORECASE):
            return m_unit
    return None


def get_schema_text(db_path: str, table_names: list[str], catalog: dict,
                    query_hint: bool = True) -> str:
    """
    Builds schema text by combining:
      - actual column names/types from SQLite (PRAGMA table_info)
      - the semantic descriptions the build wrote into the catalog

    Lookup tables have no catalog entry, so they contribute their column list only.

    `query_hint` is the per-table "Before aggregating: pin exactly one value of ..."
    line. It is advice for *writing* a query, so the answer step - which runs after the
    SQL is already written and executed - passes False. Everything else, closed
    vocabularies included, is kept for both steps.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)  # ro: never creates an empty DB
    cursor = conn.cursor()

    schema_blocks = []
    for table in table_names:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()

        meta = catalog["dataset_catalog"].get(table)
        table_desc = (f"{meta['description']} Grain: {meta['grain']}."
                      + (f" {meta['query_hint']}" if query_hint else "")
                      if meta else "")
        col_meta = catalog["column_dictionary"].get(table, {})
        col_values = catalog["dimension_values"].get(table, {})

        col_lines = []
        for _, col_name, col_type, *_ in columns:
            col = col_meta.get(col_name, {})
            col_desc = col.get("description") or ""
            col_desc += enumerate_values(col, col_values.get(col_name))
            if col.get("unit"):
                col_desc += f" Unit: {col['unit']}."
            role, lookup = col.get("role"), col.get("lookup_table")
            if role == "code" and lookup and lookup != "measures":
                tag = f" [{role} -> {lookup}]"
            elif role:
                tag = f" [{role}]"
            else:
                tag = ""
            col_lines.append(f"  - {col_name} ({col_type}){tag}: {col_desc}")

        block = f"Table: {table}\nDescription: {table_desc}\nColumns:\n" + "\n".join(col_lines)
        # A measure's unit and formula are keyed by a column value, not by a column, so
        # they cannot be stated on the column line they qualify.
        if catalog["measures"].get(table):
            block += "\nMeasures:\n" + "\n".join(
                f"  - {key_col} = '{key_val}': " + " ".join(
                    p for p in (unit, f"of {basis}" if basis else None,
                                f"— {derivation}" if derivation else None) if p)
                for key_col, key_val, unit, basis, derivation in catalog["measures"][table])
        schema_blocks.append(block)

    conn.close()
    return "\n\n".join(schema_blocks)


def get_lookup_tables(table_names: list[str], catalog: dict) -> list[str]:
    """
    Returns the lookup tables (e.g. departments, causes) that the given fact
    tables need to JOIN against for readable names, per the column dictionary.
    `measures` is not one of them: it is a metadata table, already inlined into
    the schema text.
    """
    lookups = set()
    for table in table_names:
        for col in catalog["column_dictionary"].get(table, {}).values():
            if col["lookup_table"] and col["lookup_table"] != "measures":
                lookups.add(col["lookup_table"])
    return sorted(lookups)


def format_sources(table_names: list[str], catalog: dict) -> str:
    """
    Markdown 'Source' footer for the tables the query actually touched (pass
    tables_in_sql's result). Lookup tables have no catalog entry and are skipped;
    tables sharing a source URL are listed once.
    """
    seen, lines = set(), []
    for table in table_names:
        meta = catalog["dataset_catalog"].get(table)
        if not meta or not meta.get("source_url"):
            continue
        # source_url can hold several comma-separated URLs (a table built from
        # more than one dataset) — one bullet each.
        for url in meta["source_url"].split(","):
            url = url.strip()
            if not url or url in seen:
                continue
            seen.add(url)
            lines.append(f"- {meta['source_name']}: {url}")
    return f"\n\n{t('**Source:**')}\n" + "\n".join(lines) if lines else ""
