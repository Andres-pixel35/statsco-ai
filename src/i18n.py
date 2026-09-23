import streamlit as st
from src.translations import UI_ES


def get_lang() -> str:
    if "lang" not in st.session_state:
        loc = st.context.locale or ""
        st.session_state["lang"] = "es" if loc.lower().startswith("es") else "en"
    return st.session_state["lang"]


def t(s):
    if get_lang() == "en" or not isinstance(s, str):
        return s
    return UI_ES.get(s, s)


MONTHS_ES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def format_date(d) -> str:
    if get_lang() == "es":
        return f"{d.day} de {MONTHS_ES[d.month - 1]} de {d.year}"
    return f"{d:%B} {d.day}, {d.year}"
