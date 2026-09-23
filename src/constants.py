DATA_PATH = "./data/colombia.db"

MODEL = "gemini-3.5-flash-lite"
MODEL_FALLBACK = "gemini-3.1-flash-lite"

REASONING_EFFORT_QUERY = "high"     # SQL generation only
REASONING_EFFORT_DEFAULT = "medium" # gate, chart title, final answer

# Per-request timeout and the SDK's own retries, before call_model moves on to
# MODEL_FALLBACK. The SDK default (600s, 2 retries) could hold one question for an hour
# on a hung provider; a single call was measured at 0.8s-40s of queueing.
MODEL_TIMEOUT_SECONDS = 90
MODEL_MAX_RETRIES = 1

# `gdp_quarterly.concept` alone is 140 national-accounts line items, ~9.7k characters — the
# old 5000 cap dropped it entirely (retrieval AND the SQL prompt lost every line-item name,
# e.g. 'Health'), silently breaking both table retrieval and exact-match filtering for
# anything not in the topic text. 12000 covers it with headroom; nothing else in the catalog
# is close to this size, so raising it doesn't dilute any other table's prompt/embedding.
MAX_ENUMERATED_CHARS = 12000

TITLE_STOPWORDS = {"the", "a", "an", "of", "in", "for", "and", "by", "to", "is", "are", "at"}

# Weight of the title-overlap bonus relative to cosine similarity (both roughly
# 0-1 scale). Tuned against a 30-table/35-question probe: 0.05-0.15 all fixed the
# same misranks with no regressions; 0.10 is the stable middle of that band.
LEXICAL_WEIGHT = 0.10

# These two tables have no all-causes aggregate row - is_total only ever aggregates
# sex/age/geography, never cause. A question that never names a cause has no single row
# to land on, so the model must SUM over cause_code itself; it does this unreliably no
# matter how the prompt is worded (tested), so unfiltered-cause queries against exactly
# these two tables are summed in code instead. See sum_unfiltered_cause_deaths().
CAUSE_BROKEN_DOWN_TABLES = ("deaths_by_municipality_and_cause", "deaths_by_department_and_cause")

# SQL generation gets this many attempts total: the first try plus retries that feed the
# previous query and its failure (0 rows, or a SQLite error) back to the model. 3 keeps
# the worst case at 3 MODEL calls per question.
SQL_MAX_ATTEMPTS = 3

# Every generated query is capped at this many rows, enforced in code by wrapping the query
# in run_sql_with_retry (not asked of the model - the wrap makes that redundant). Keeps a
# runaway result from bloating the Streamlit session/cache.
SQL_ROW_LIMIT = 200

# A generated query still running after this many seconds is cancelled and fed back to the
# model as a failed attempt - a runaway recursive CTE or cartesian join would otherwise pin
# a CPU core and the user's session forever.
SQL_TIMEOUT_SECONDS = 30

# Largest single string/blob a generated query may produce (SQLite's SQLITE_LIMIT_LENGTH).
# SQL_ROW_LIMIT caps rows, not their size: without this, one injected randomblob()/zeroblob()
# query can allocate GBs and take the container down for everyone. Real values here are
# short labels and numbers; 100 kB leaves wide headroom. Too big -> "string or blob too big",
# which run_sql_with_retry treats as a failed attempt.
SQL_MAX_VALUE_BYTES = 100_000

# A chart replaces the prose answer only when the question contains one of CHART_KEYWORDS
# (row count is deliberately not a trigger - many multi-row answers, e.g. productivity or
# causes of death for one year, read better as prose). MAP_KEYWORDS additionally routes to
# the department choropleth view. On the chart path the final-answer LLM call is skipped
# entirely - only a one-line title call is made.
CHART_KEYWORDS = (
    "plot", "chart", "graph",
)
MAP_KEYWORDS = ("department by department",)
# Spanish equivalents of CHART_KEYWORDS + MAP_KEYWORDS. The gate translates a Spanish
# question to English and must map these back to the exact English keyword (and use an
# English keyword only when its Spanish one was asked), so wants_chart/wants_map keep
# working on the English question. Also the word list in the Spanish "Charts" popover.
CHART_WORDS_ES = {"chart": "gráfico", "graph": "gráfica", "plot": "graficar",
                  "department by department": "departamento por departamento"}

# Longer questions are refused before any LLM call: long inputs are the usual carrier for
# injected instructions, and no real statistics question needs more.
MAX_QUESTION_CHARS = 500

# Per-user throttling, keyed by IP (see rate_limit.py): one question submitted per minute, and
# no more than 3 answered per calendar day in Colombia time (UTC-5) - each question triggers a
# chain of LLM calls, so this caps API spend per user without a login system. A question that
# fails because the model can't be reached (or crashes, or is interrupted) doesn't use a daily
# slot; the per-minute cooldown still applies to it.
RATE_LIMIT_SECONDS = 60
RATE_LIMIT_PER_DAY = 3

# Answered questions per day across ALL users - a hard spend ceiling that doesn't depend on
# telling users apart (st.context.ip_address can be spoofed, IPv6 users can rotate addresses).
# Same in-memory, per-process store and midnight reset as the per-user cap.
RATE_LIMIT_GLOBAL_PER_DAY = 200

# Mainland Colombia's lon/lat extent. The San Andrés y Providencia archipelago sits
# ~700km off in the Caribbean; fitbounds("locations") stretches the view to include it,
# shrinking the mainland shape everyone actually looks at.
MAINLAND_LON_RANGE = [-79.5, -66.5]
MAINLAND_LAT_RANGE = [-4.6, 12.8]
