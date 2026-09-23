import streamlit as st
import logging
import os
import time
from datetime import date
from src.pipeline import answer_question, s3
from src.charts import render_chart_message
from src.model import ModelUnavailable
from src.catalog import load_catalog, list_topics
from src.retrieval import load_embedder, build_table_index
from src.constants import DATA_PATH
from src.ui_copy import ABOUT_AND_LIMITS, CHARTS_INFO, HOW_IT_WORKS
from src.i18n import t, get_lang, format_date
from src.rate_limit import check_and_record, get_user_key, record_answer
from src.mobile import is_mobile
from src.components import copy_button

log = logging.getLogger(__name__)
GENERIC_ERROR = "Something went wrong on our side. Please try again in a moment."


st.set_page_config(page_title=t("Colombia statistics chat"), page_icon=":material/query_stats:",
                   layout="wide")


# The language radio is only rendered before the first message; re-saving its key
# every run stops Streamlit's widget clean-up from dropping the user's pick after that.
st.session_state.lang = get_lang()

st.logo("images/brand/sc-mark.svg", size="large")

# st.context.theme.type can lag one rerun behind an actual theme switch (documented
# Streamlit quirk) - force the extra rerun so the lockup image picks up the new theme.
if st.session_state.get("_theme_type") != st.context.theme.type:
    st.session_state["_theme_type"] = st.context.theme.type
    st.rerun()

def safe_render_chart(chart, key):
    try:
        render_chart_message(chart, key=key)
    except Exception:
        log.exception("chart rendering failed")
        st.markdown(t(GENERIC_ERROR))


def render_top_bar():
    # width sets the button's own width (per st.popover docs), not just the panel it
    # opens - on mobile let each button size to its label ("content") so 3 fit in one
    # row; the fixed desktop pixel widths are unchanged.
    mobile = is_mobile()
    lang_w, panel_w = ("content", "content") if mobile else (110, 150)
    with st.container(horizontal=True, horizontal_alignment="right"):
        if not st.session_state.messages:
            with st.popover(get_lang().upper(), icon=":material/language:", width=lang_w,
                             wrap=mobile or None):
                st.radio("Language / Idioma", ["es", "en"], key="lang",
                          format_func=lambda code: "Español" if code == "es" else "English")
        with st.popover(t("Support"), icon=":material/favorite:", width=panel_w, wrap=mobile or None):
            logo_col, action_col = st.columns([1, 3], vertical_alignment="center")
            with logo_col:
                st.image("images/payment/paypal.svg", width=26)
            with action_col:
                st.link_button(t("Donate"), "https://www.paypal.com/donate/?hosted_button_id=94RJ3NMC9QF7A")
            logo_col, action_col = st.columns([1, 3], vertical_alignment="center")
            with logo_col:
                st.image("images/payment/bre-b.svg", width=60)
            with action_col:
                copy_button(t("Copy key"), "riosandres294@proton.me", key="copy-bre-b-key")
            logo_col, action_col = st.columns([1, 3], vertical_alignment="center")
            with logo_col:
                st.image("images/payment/patreon.svg", width=26)
            with action_col:
                st.link_button(t("Support"), "https://www.patreon.com/cw/StatisticsColombia")
        with st.popover(t("Contact"), icon=":material/mail:", width=panel_w, wrap=mobile or None):
            st.write(t("Bugs, suggestions or questions? Do not hesitate to contact me at:"))
            copy_button(t("Copy email"), "statistics-colombia@proton.me", key="copy-contact-email")


@st.cache_resource(show_spinner=False)
def download_db():
    """Fetches colombia.db from R2 when it isn't on disk. cache_resource runs it once per
    container - sessions that start during the 1.8 GB download wait instead of starting
    their own. boto3 doesn't keep the object's date, so the file's mtime is set to the
    upload date by hand: the About popover shows it as the last data update."""
    if os.path.exists(DATA_PATH):
        return
    obj = s3.head_object(Bucket="colombia-data", Key="colombia-data/colombia.db")
    s3.download_file("colombia-data", "colombia-data/colombia.db", DATA_PATH)
    uploaded = obj["LastModified"].timestamp()
    os.utime(DATA_PATH, (uploaded, uploaded))


try:
    os.makedirs("data", exist_ok=True)
    download_db()

    embedder = load_embedder()
    catalog = load_catalog(DATA_PATH)
    table_index = build_table_index(embedder, catalog)

    # Read only now that the DB is known to be on disk; its mtime is when it was last updated.
    db_last_updated = format_date(date.fromtimestamp(os.path.getmtime(DATA_PATH)))
except Exception:
    log.exception("startup failed")
    st.error(t(GENERIC_ERROR))
    st.stop()

st.session_state.setdefault("messages", [])

# A question is pending (awaiting its answer) once appended but before the assistant
# reply lands - disable input then so a second submission can't interrupt the script run
# that's still computing the first answer.
pending = bool(st.session_state.messages) and st.session_state.messages[-1]["role"] == "user"

render_top_bar()

# Centered input on an empty screen; pinned to the bottom once used.
if st.session_state.messages:
    # Preserved history - shown to the user only, never fed back to the model.
    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            avatar = "images/icons/user.svg"
        elif msg.get("error"):
            avatar = "images/icons/ai-error.svg"
        else:
            avatar = "images/icons/ai-neutral.svg"
        with st.chat_message(msg["role"], avatar=avatar):
            if msg.get("chart"):
                safe_render_chart(msg["chart"], key=f"chart_{i}")
            else:
                st.markdown(msg["content"])
            if msg["elapsed"] is not None:
                st.caption(t("Thought for {s:.1f}s").format(s=msg["elapsed"]))

    if not pending:
        st.caption(t("*StatsCo AI can make mistakes. Always verify important information.*"))
    question = st.chat_input(t("Ask a question"), disabled=pending)
else:
    mobile = is_mobile()
    st.container(height=40 if mobile else 80, border=False)
    with st.container(horizontal_alignment="center"):
        with st.container(width="stretch" if mobile else 640, horizontal_alignment="center"):
            lockup = "images/brand/statsco-lockup-dark.svg"
            st.image(lockup, width=180 if mobile else 280)
            if mobile:
                st.subheader(t("Colombia statistics chat"), text_alignment="center")
            else:
                st.header(t("Colombia statistics chat"), text_alignment="center")
            question = st.chat_input(t("Ask a question"), disabled=pending)

            if mobile:
                # st.columns stacks vertically below a 640px viewport regardless of
                # content width; a horizontal container wraps only if content needs
                # to. width defaults to "content" so each button is only as wide as
                # its label, maximizing the chance all 3 stay on one row.
                with st.container(horizontal=True, horizontal_alignment="distribute"):
                    with st.popover(t("About"), wrap=True):
                        st.write(t(ABOUT_AND_LIMITS).format(date=db_last_updated))
                        st.link_button(t("Want to use your own API key or a higher limit? Run it locally"),
                                       "https://github.com/Andres-pixel35/statsco-ai")
                        st.write(t("**Topics it can help with:**"))
                        st.write(list_topics(catalog, get_lang()))
                    with st.popover(t("Charts"), wrap=True):
                        st.write(t(CHARTS_INFO))
                    with st.popover(t("How it works"), wrap=True):
                        st.write(t(HOW_IT_WORKS))
                        st.image(f"images/how-it-works/{get_lang()}.svg", width="stretch")
            else:
                card_cols = st.columns(3)
                with card_cols[0]:
                    with st.popover(t("About"), width="stretch"):
                        st.write(t(ABOUT_AND_LIMITS).format(date=db_last_updated))
                        st.link_button(t("Want to use your own API key or a higher limit? Run it locally"),
                                       "https://github.com/Andres-pixel35/statsco-ai")
                        st.write(t("**Topics it can help with:**"))
                        st.write(list_topics(catalog, get_lang()))
                with card_cols[1]:
                    with st.popover(t("Charts"), width="stretch"):
                        st.write(t(CHARTS_INFO))
                with card_cols[2]:
                    with st.popover(t("How it works"), width="stretch"):
                        st.write(t(HOW_IT_WORKS))
                        st.image(f"images/how-it-works/{get_lang()}.svg", width="stretch")

            st.caption(t("*StatsCo AI can make mistakes. Always verify important information.*"),
                        text_alignment="center")

# Record the question and rerun first, so the input immediately re-renders
# pinned to the bottom instead of only after the answer is ready.
if question:
    st.session_state.messages.append({"role": "user", "content": question, "elapsed": None})
    block_reason = check_and_record(get_user_key())
    if block_reason:
        st.session_state.messages.append(
            {"role": "assistant", "content": block_reason, "elapsed": None}
        )
    st.rerun()

# Answer a pending question left by that rerun.
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    if st.session_state.messages[-1].get("started"):
        # A rerun (a widget click, the R key) cut the previous run short. Answering again
        # would re-bill every model call without a new rate-limit check, so ask for a resubmit.
        st.session_state.messages.append(
            {"role": "assistant", "elapsed": None, "error": True,
             "content": t("Your question was interrupted before it was answered. "
                          "Please ask it again.")})
        st.rerun()
    st.session_state.messages[-1]["started"] = True
    question = st.session_state.messages[-1]["content"]
    with st.chat_message("assistant", avatar="images/icons/ai-thinking.svg"):
        status = st.status(t("Thinking…"), expanded=False)
        start = time.perf_counter()
        is_error = False
        try:
            answer = answer_question(question, embedder, table_index, catalog, status)
            record_answer(get_user_key())
            elapsed = time.perf_counter() - start
            status.update(label=t("Thought for {s:.1f}s").format(s=elapsed), state="complete")
        except ModelUnavailable:
            log.exception("model unavailable")
            elapsed = time.perf_counter() - start
            status.update(label=t("Failed after {s:.1f}s").format(s=elapsed), state="error")
            answer = t("I couldn't get a response from the AI model (it may be overloaded "
                       "or rate-limited). Please retry in a minute.")
            is_error = True
        except Exception:
            log.exception("answer_question failed")
            elapsed = time.perf_counter() - start
            status.update(label=t("Failed after {s:.1f}s").format(s=elapsed), state="error")
            answer = t(GENERIC_ERROR)
            is_error = True
        if isinstance(answer, dict):
            safe_render_chart(answer, key=f"chart_{len(st.session_state.messages)}")
        else:
            st.markdown(answer)
        st.caption(t("Thought for {s:.1f}s").format(s=elapsed))
    msg = {"role": "assistant", "content": "", "elapsed": elapsed, "error": is_error}
    msg["chart" if isinstance(answer, dict) else "content"] = answer
    st.session_state.messages.append(msg)
    st.rerun()
