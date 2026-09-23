import re
import unicodedata
import numpy as np
import streamlit as st
from sentence_transformers import SentenceTransformer
from src.catalog import enumerate_values
from src.constants import TITLE_STOPWORDS, LEXICAL_WEIGHT, CHART_KEYWORDS, MAP_KEYWORDS


@st.cache_resource
def load_embedder():
    # pinned to a commit: a changed or hijacked upstream model can't silently swap in, and
    # retrieval's tuning (LEXICAL_WEIGHT, the 0.7 topic weight) stays valid for these weights
    return SentenceTransformer("all-MiniLM-L6-v2", revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41")


def title_words(title: str) -> set[str]:
    """Content words of a table title, for the retrieval lexical bonus below."""
    return {w for w in re.findall(r"[a-zA-Z]+", title.lower()) if w not in TITLE_STOPWORDS}


@st.cache_resource
def build_table_index(_embedder, _catalog: dict) -> dict[str, tuple[np.ndarray, set[str]]]:
    """
    Embeds each table's topic and its column names/meanings separately, then
    combines them with the topic weighted higher. A raw concatenation lets a
    table with many verbose columns dilute its own topic's signal relative to
    a table with few columns, distorting similarity ranking against short questions.

    Each entry also carries the table's title words, for retrieve_relevant_tables'
    lexical bonus: short topic sentences can lose an almost-literal match (e.g.
    "minimum wage" in the question vs. the "Minimum wage" table) to a competing
    table that merely shares an incidental token (a place name, a year).
    """
    DESCRIPTION_WEIGHT = 0.7
    index = {}
    for table_name, entry in _catalog["dataset_catalog"].items():
        columns = _catalog["column_dictionary"].get(table_name, {})
        dim_values = _catalog["dimension_values"].get(table_name, {})
        # 'meta' rows describe a column the fact table no longer carries (a lifted
        # constant, a source URL) — not part of what the table is about. Enumerated
        # values are included so a question naming one (e.g. a president) can match
        # a table whose topic sentence never names it.
        col_text = "; ".join(f"{name}: {col['description'] or ''}"
                             + enumerate_values(col, dim_values.get(name))
                             for name, col in columns.items() if col["role"] != "meta")
        topic = entry["topic"] or f"{entry['title']}. {entry['description']}"
        desc_vec = _embedder.encode(topic)
        col_vec = _embedder.encode(col_text)
        vec = DESCRIPTION_WEIGHT * desc_vec + (1 - DESCRIPTION_WEIGHT) * col_vec
        index[table_name] = (vec, title_words(entry["title"]))
    return index


def retrieve_relevant_tables(question: str, table_index: dict[str, tuple[np.ndarray, set[str]]],
                              embedder, top_k: int = 4) -> list[str]:
    """
    Given a user question, returns the top_k most relevant table names, ranked by
    cosine similarity plus a lexical bonus for questions that nearly name the table.
    Chart/map words are dropped first: they say how to show the data, not which data,
    yet they pull the embedding off-subject - "Graph the annual inflation from 2015 to
    2024" ranked consumer_price_index 5th, the same question without "Graph" 4th.
    """
    question = re.sub(rf"\b({'|'.join(CHART_KEYWORDS + MAP_KEYWORDS)})\w*\b", " ", question,
                      flags=re.IGNORECASE)
    question_vec = embedder.encode(question)
    question_words = title_words(question)

    scores = {}
    for table, (vec, t_words) in table_index.items():
        cos = np.dot(question_vec, vec) / (np.linalg.norm(question_vec) * np.linalg.norm(vec))
        overlap = len(question_words & t_words) / len(t_words) if t_words else 0.0
        scores[table] = cos + LEXICAL_WEIGHT * overlap

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [table for table, _score in ranked[:top_k]]


def _fold(text: str) -> str:
    """Lowercase, accents stripped ("Álvaro" -> "alvaro")."""
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()


def mentions_president(question: str, catalog: dict) -> bool:
    """
    Whether the question refers to a presidency ("under Petro", "Uribe's government").
    `presidential_terms` is a join-only lookup, so embedding retrieval drops it from the
    top-k as soon as the question carries other wording - and without it the SQL prompt
    refuses to guess the term's years (NO_SQL). Names come from the DB itself.
    """
    names = catalog["dimension_values"].get("presidential_terms", {}).get("president_name", [])
    # any name word >= 4 chars counts, so "Santos"/"Valencia" can false-positive;
    # the cost is one small extra table in the prompt
    words = {w for name, _ in names for w in re.findall(r"[a-z]+", _fold(name)) if len(w) >= 4}
    q_words = set(re.findall(r"[a-z]+", _fold(question)))
    return bool(words & q_words) or bool(re.search(r"presiden|government|administration",
                                                   _fold(question)))


def tables_in_sql(sql: str, table_names: list[str]) -> list[str]:
    """
    The retrieved tables the query actually touched. Retrieval hands the SQL prompt
    several candidates so the model can pick; once it has picked, a table the query
    never referenced explains nothing about the rows that came back.
    Falls back to everything if nothing matches, rather than answering with no context.
    """
    used = [t for t in table_names if re.search(rf"\b{re.escape(t)}\b", sql, re.IGNORECASE)]
    return used or table_names
