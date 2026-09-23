from src.constants import CHART_KEYWORDS, MAP_KEYWORDS, RATE_LIMIT_PER_DAY, SQL_ROW_LIMIT

ABOUT_AND_LIMITS = (
    "Conversations here are sent to Google's Gemini API. Google may "
    "retain and use them to train their models.\n\n"
    "StatsCoAI itself does not collect or store any information about "
    "you or your conversation, beyond what Streamlit or Google may "
    "collect on their own.\n\n"
    "The model has no memory between questions, each one is answered "
    "on its own, with no knowledge of what you asked before.\n\n"
    "It performs faster and cheaper, and generally even better, with questions "
    "in English.\n\n"
    "The data will only be updated twice per month. "
    "Last update: {date}.\n\n"
    f"To keep this free for everyone, questions are capped at "
    f"{RATE_LIMIT_PER_DAY} per day, and each answer returns at most "
    f"{SQL_ROW_LIMIT} rows.\n\n"
    "At certain hours you may experience high latency, or the model may fail "
    "to return an answer at all. If that happens, please try again."
)

_CHART_WORDS = ", ".join(f"**{w}**" for w in CHART_KEYWORDS)
_MAP_WORDS = ", ".join(f'"**{w}**"' for w in MAP_KEYWORDS)

CHARTS_INFO = (
    f"A chart replaces the text answer when your question includes one of these "
    f"words: {_CHART_WORDS}.\n\n"
    "The chart type is picked automatically: a **line** chart for results with "
    "more than one row, a **bar** chart for a single row.\n\n"
    f"Ask for something like {_MAP_WORDS} and you'll get a **map** of Colombia "
    "instead.\n\n"
    "A table view of the same data is always available alongside the chart."
)

HOW_IT_WORKS = (
    "**Try asking:**\n"
    "- What was the unemployment rate in Colombia in 2024?\n"
    "- Plot the minimum wage from 2000 to 2026\n"
    "- Population in 2025, department by department\n\n"
    "You ask in plain language. First, the app checks whether its data can answer "
    "the question: if not, it tells you what it can help with; if the question is "
    "vague, it asks you to be more specific.\n\n"
    "Then it finds the most relevant tables among ~30 official datasets (DANE, Banco "
    "de la República, MinHacienda…) and writes a database query to look up the "
    "numbers. If the query fails or returns nothing, it adjusts and tries again.\n\n"
    "Finally, it writes the answer in plain language, or draws a chart or map when "
    "you ask for one. Every answer lists its sources."
)
