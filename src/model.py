import re
import streamlit as st
from openai import OpenAI
from src.constants import (
    MODEL, MODEL_FALLBACK, MODEL_TIMEOUT_SECONDS, MODEL_MAX_RETRIES
)

class ModelUnavailable(Exception):
    """Both the primary model and its fallback failed."""


@st.cache_resource
def get_model_client() -> OpenAI:
    return OpenAI(api_key=st.secrets["api"]["key"], base_url=st.secrets["api"].get("base_url"),
                  timeout=MODEL_TIMEOUT_SECONDS, max_retries=MODEL_MAX_RETRIES)


def call_model(prompt: str, model: str = MODEL, temperature: float | None = None,
                reasoning_effort: str | None = None) -> str:
    def _complete(m: str) -> str:
        kwargs = {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if reasoning_effort is not None:
            kwargs["reasoning_effort"] = reasoning_effort
        response = get_model_client().chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        content = response.choices[0].message.content
        # a safety block or length cut-off comes back as an empty reply, not an error -
        # raise so the fallback model gets its turn
        if not content:
            raise ValueError(f"{m} returned an empty reply")
        return content

    try:
        return _complete(model)
    except Exception:
        try:
            return _complete(MODEL_FALLBACK)
        except Exception as e:
            raise ModelUnavailable(f"{model} and {MODEL_FALLBACK}") from e


def strip_thoughts(text: str) -> str:
    """
    Removes the model's reasoning blocks (<thought>...</thought>, <thinking>...</thinking>)
    so only the final answer is left. Also handles an unclosed opening tag by dropping
    everything up to the last closing tag.
    """
    text = re.sub(r"<(thought|thinking)>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
    tail = re.search(r"(?is).*</(?:thought|thinking)>", text)
    if tail:
        text = text[tail.end():]
    return text.strip()


def extract_sql(text: str) -> str:
    """
    Strips reasoning blocks, code fences and any leading/trailing prose ("Here's the
    query:", etc.) the model tacked on, keeping just the SQL statement. The SQL prompt asks
    for a reasoning pass before the query, so the last fenced block wins, not the first.
    """
    text = strip_thoughts(text)
    # An unclosed <thinking> opener survives strip_thoughts; drop everything up to the last
    # one so a SELECT mentioned inside the reasoning is not mistaken for the query.
    opener = re.search(r"(?is).*<(?:thought|thinking)>", text)
    if opener:
        text = text[opener.end():]
    fenced = re.findall(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced[-1]
    # "" = no query: the model's NO_SQL marker, or prose with no SQL statement in it
    if "NO_SQL" in text:
        return ""
    keyword = r"(SELECT|WITH|INSERT|UPDATE|DELETE)\b.*"
    if fenced:
        statement = re.search(keyword, text, re.DOTALL | re.IGNORECASE)
    else:
        # unfenced replies can carry prose, where "with"/"select" are ordinary English words:
        # prefer an uppercase keyword, else one (any case) that starts a line
        statement = (re.search(keyword, text, re.DOTALL)
                     or re.search(rf"^\s*{keyword}", text, re.DOTALL | re.IGNORECASE | re.MULTILINE))
    return statement.group(0).strip() if statement else ""
