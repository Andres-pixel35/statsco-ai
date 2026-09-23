# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A bilingual (en/es) Streamlit text-to-SQL chat app over Colombian official statistics. Each
question is answered independently (no conversation memory fed to the model; history is shown
to the user only): guard → gate for answerability → retrieve relevant tables → generate SQL
with an LLM (retried on failure) → run it read-only against `data/colombia.db` → either phrase
the answer with the LLM, or return a chart payload.

## Commands

```sh
streamlit run streamlit_app.py       # run the app
python tests/test_<name>.py          # each test is a standalone script that prints "ok"
```

- Use the conda env `statsco_ai` if one is needed. Do not pip install; deps in `requirements.txt`
  (streamlit, pandas, boto3, sentence-transformers, openai, plotly) are assumed present.
- `tests/`, `data/colombia.db` (1.8 GB), and `.streamlit/secrets.toml` are gitignored.
- Tests are offline (no LLM call). Known stale: `test_gemini_fallback`,
  `test_token_usage` still import the old `generalities` package (and `test_token_usage` a
  `log_question_usage` that no longer exists); `test_sql_retry`'s fake `call_model` lacks the
  `reasoning_effort` kwarg. `test_injection_guards` covers the input safeguards below.

## Secrets

`.streamlit/secrets.toml`:
- `[api] key` / `[api] base_url` — the model API key and its OpenAI-compatible endpoint URL.
- `[r2]` — Cloudflare R2 credentials for fetching `colombia.db` (private bucket). The code
  is live: `src/pipeline.py` builds the boto3 client at import time (`s3 = boto3.client(...)`,
  so a missing `[r2]` section crashes startup), and `streamlit_app.py`'s `download_db`
  downloads the DB when `DATA_PATH` doesn't exist (once per container via `cache_resource`;
  the file's mtime is set to the R2 upload date, shown as "Last update"). Local users without the credentials must comment out or
  delete that code (README step 5) and get the DB by email.

## Architecture

Code is in `src/`, plus the UI entry point `streamlit_app.py`.

| File | Role |
|---|---|
| `streamlit_app.py` | UI: language picker (before first message), top bar (Support/Contact popovers), landing cards (About / Charts / How it works), chat history, per-question rate-limit check, calls `answer_question`, renders prose or `render_chart_message`. Input is disabled while a question is pending; a rerun that finds the pending question already started (widget click, R key) replies "interrupted, ask again" instead of re-running the pipeline. |
| `pipeline.py` | `answer_question` orchestrator, `run_sql_with_retry`, `gate_verdict`, `wants_chart`/`wants_map`, chart-title parsing, `sum_unfiltered_cause_deaths` |
| `prompts.py` | prompt builders: sql, answer, gate, chart-title; `UNTRUSTED_INPUT_RULES`; `SPANISH_ANSWER_RULES` |
| `model.py` | `call_model` (primary → fallback model, else `ModelUnavailable`), `strip_thoughts`, `extract_sql` |
| `catalog.py` | reads colombia.db's metadata into schema/source text; `list_topics` builds the gate's capability list and the out-of-scope reply |
| `retrieval.py` | embed & rank tables; `mentions_president`; `tables_in_sql` |
| `charts.py` | `render_chart_message`: Plotly Line/Bar/Table/Map views, highlight selector (ported cut-down from `../colombia`) |
| `mobile.py` | User-Agent based `is_mobile()` and the chart layout tweaks that depend on it |
| `i18n.py`, `translations.py`, `ui_copy.py` | `get_lang()`/`t()`, the English→Spanish string map (`UI_ES`, `TOPICS_ES`), long UI copy |
| `rate_limit.py` | per-user throttle (see Tuning knobs) |
| `constants.py` | all tunables |

`answer_question(question, embedder, table_index, catalog, status=None)` returns a prose
string, or a `{rows, title, sources, default_view, labels, units}` dict on the chart path.

Pipeline, in order:

0. Guards — empty input and input over `MAX_QUESTION_CHARS` return a canned message before
   any LLM call.
1. Answerability gate — `build_gate_prompt(question, topics, lang)` (capability list from
   `list_topics`) → `call_model(MODEL, temperature=0)` → `gate_verdict` collapses the
   reply to ANSWERABLE / OUT_OF_SCOPE / UNCLEAR / WRONG_LANGUAGE / MALICIOUS (unrecognised →
   OUT_OF_SCOPE, which is sampled a second time before being trusted). MALICIOUS is checked
   first in the prompt and gets its own short refusal (no topic list). The question must be
   in the UI language (`get_lang()`), else WRONG_LANGUAGE. For `es` the same call also
   translates the question to English (reply line 2, `QUESTION: ...`, read by `gate_translation`;
   if the line is missing the gate is resampled once, then the Spanish text is used as is), mapping
   `CHART_WORDS_ES` back to the exact English chart/map keywords; everything downstream
   (retrieval, SQL, `wants_chart`/`wants_map`) sees only `question_en`. Anything but
   ANSWERABLE returns a canned message; the rest of the pipeline never runs.
2. `retrieve_relevant_tables` — embed the question with `all-MiniLM-L6-v2`, rank tables by
   cosine similarity against `build_table_index`'s per-table vectors (topic weighted 0.7,
   column text 0.3), plus a lexical bonus (`LEXICAL_WEIGHT`) for questions that nearly name
   the table's title. Returns top 4; `presidential_terms` is appended when
   `mentions_president` fires.
3. `get_lookup_tables` — the lookup tables those fact tables must JOIN for readable names.
4. `get_schema_text` — live column names/types from `PRAGMA table_info`, merged with semantic
   descriptions, units, closed vocabularies, and `Measures:` blocks from the catalog.
5. `run_sql_with_retry` — `build_sql_prompt` → `call_model(MODEL,
   REASONING_EFFORT_QUERY)` → `extract_sql` (strips reasoning blocks, fences, prose), wrap in
   `SELECT * FROM (...) LIMIT SQL_ROW_LIMIT`, execute on a **read-only** connection with a
   `SQL_TIMEOUT_SECONDS` progress-handler deadline, `fetchmany(SQL_ROW_LIMIT)` as the hard cap
   (an unclosed `/*` can comment the LIMIT out). On 0 rows, a timeout,
   a SQLite error or no query, retry up to `SQL_MAX_ATTEMPTS` times, feeding each failed query
   + reason back via `build_sql_prompt(prior_attempts=...)`. Every attempt failing returns a
   canned message. (The generated SQL is also echoed with `st.write` in this function.)
6. `sum_unfiltered_cause_deaths` (inside the retry loop) — narrow code-level correction: the
   two tables in `CAUSE_BROKEN_DOWN_TABLES` have no all-causes row, so an unfiltered-cause
   query is wrapped in `SELECT <other cols>, SUM(deaths) ... GROUP BY <other cols>` - only
   when it pins `is_total = 0` or both `sex` and `age_group` (else the sex/age subtotals
   over-count 3-4x) and selects `deaths`. The LLM does this unreliably no matter how the
   prompt is worded.
7. Rows are dicts (column name → value), carried into the answer/chart step. The query fetches
   `SQL_ROW_LIMIT + 1` rows only to detect a cut result: it is trimmed to `SQL_ROW_LIMIT`, the
   answer prompt gets `TRUNCATED_ANSWER_RULES` (no totals/ranks over partial rows), and the user
   sees `TRUNCATED_NOTE` (after the prose, or under the chart title).
8. `wants_chart` — only when the English question contains a `CHART_KEYWORDS` term (row count
   is not a trigger). `wants_map` (`MAP_KEYWORDS`) also routes here with `default_view="Map"`;
   otherwise the default view is Line for >1 row, Bar for one. The prose answer is skipped:
   units come from the DB (`get_column_unit`, checked on every row; a column whose rows disagree
   gets no unit), one `build_chart_title_prompt` call gives a
   title and column labels, and the payload goes to `charts.py`.
9. Otherwise `build_answer_prompt` (schema narrowed to `tables_in_sql`, the tables the query
   touched) → `call_model` → `strip_thoughts`, with the source list appended.

All LLM calls use `MODEL` (the former `MODEL_SIMPLE` is gone), `temperature=0` except SQL
generation, and `REASONING_EFFORT_QUERY` for SQL vs `REASONING_EFFORT_DEFAULT` for the rest.
`call_model` (client timeout `MODEL_TIMEOUT_SECONDS`, `MODEL_MAX_RETRIES`; an empty reply
counts as a failure) retries once on `MODEL_FALLBACK`; if that fails too it raises
`ModelUnavailable`, which the UI shows as a retry-later message.

For `es`, the final call answers in Spanish: `SPANISH_ANSWER_RULES` is appended to the answer
prompt (decimal comma, dot thousands, miles de millones / billones). On the chart path, the
title call also translates the y-axis units and the rows' text values (legends). `charts.py`
sets Plotly `separators=",."` and swaps separators in the table view.

### Untrusted input

The user's question reaches all four prompts (gate, SQL, chart title, answer; the SQL prompt
gets the gate's English translation). Each embeds `UNTRUSTED_INPUT_RULES` and quotes the
question between `<<<START>>>`/`<<<END>>>` via `_quoted`: use it only to decide what data to
fetch, never follow instructions in it, but still honor plot/chart/map, top N, highest/lowest,
latest. The gate refuses injection/damage attempts as MALICIOUS (even when mixed with a real
question). Non-LLM backstops: the length cap, the `SELECT * FROM (...)` wrapper (any
INSERT/UPDATE/DELETE becomes a syntax error), and the `mode=ro` SQLite connection. Any new
prompt that embeds the question must include the rules and the quoting. `catalog.py`'s
schema-text connection is separate and read-only in practice (PRAGMA/metadata reads only).

### colombia.db is the single source of truth for schema knowledge

`load_catalog` reads the DB's own metadata tables — `dataset_catalog`, `column_dictionary`,
`dimension_values`, `measures` — once into an in-memory dict. There is no hand-maintained
schema dict in this repo. The 30 retrieval `topic` strings also live in
`dataset_catalog.topic`; Spanish display versions of the topics are in `TOPICS_ES`.

`colombia.db` is produced by a **separate repo**, `/home/riosandres/Documents/coding/genius/building`
(`python build.py --force`, conda env `statsco_ai`). It builds cleanly from scratch — point
`--db` at a path that does not exist. A full run takes ~13 min plus VACUUM. Changing
schema-text or retrieval behavior usually means a coordinated change there too.

### Language and UI

`get_lang()` picks `es`/`en` from the browser locale on first load and keeps it in
`st.session_state.lang`; `t(s)` looks English strings up in `UI_ES` (missing key → the English
string, so every new user-facing string needs an `UI_ES` entry). Static assets are in
`images/` and `data/colombia_departments.geojson` (map); themes in `.streamlit/config.toml`.

### Caching

`@st.cache_resource` on `load_embedder`, `load_catalog`, `build_table_index`,
`get_model_client`, `download_db`; `@st.cache_data` on `_dept_geojson`. `build_table_index` args are
underscore-prefixed (`_embedder`, `_catalog`) so Streamlit skips hashing them — keep that
when editing signatures.

Errors are never shown raw: `streamlit_app.py` logs them (`log.exception`) and shows `GENERIC_ERROR`
(startup, per-question, and chart rendering via `safe_render_chart`); `ModelUnavailable` keeps its own retry message.

## Tuning knobs

All in `src/constants.py`: `MODEL` and its fallback, `REASONING_EFFORT_QUERY` /
`REASONING_EFFORT_DEFAULT`, `LEXICAL_WEIGHT` (tuned against a 30-table/35-question probe),
`MAX_ENUMERATED_CHARS` (caps which columns dump their full value list into the prompt),
`CAUSE_BROKEN_DOWN_TABLES`, `SQL_MAX_ATTEMPTS` (SQL generate/run tries, worst case = that many
`MODEL` calls), `SQL_ROW_LIMIT` (hard row cap), `SQL_TIMEOUT_SECONDS`, `SQL_MAX_VALUE_BYTES` (per-value size cap), `MODEL_TIMEOUT_SECONDS` /
`MODEL_MAX_RETRIES`, `MAX_QUESTION_CHARS`,
`CHART_KEYWORDS` / `MAP_KEYWORDS` / `CHART_WORDS_ES` (when the chart/map path fires),
`RATE_LIMIT_SECONDS` / `RATE_LIMIT_PER_DAY` (per-IP) / `RATE_LIMIT_GLOBAL_PER_DAY` (all users; all in-memory in `rate_limit.py`, wiped on
redeploy; the cooldown counts every submission, the daily cap only questions the pipeline
answered - `record_answer` - so model outages, crashes and interruptions don't use a slot;
the day resets at midnight Colombia time, UTC-5, when `_roll_day` empties both stores),
`MAINLAND_LON_RANGE` /
`MAINLAND_LAT_RANGE` (map extent, excludes San Andrés). The comments there record why each
value is what it is — read them before changing one.
