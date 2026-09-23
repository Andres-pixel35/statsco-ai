import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

import streamlit as st

from src.constants import RATE_LIMIT_SECONDS, RATE_LIMIT_PER_DAY, RATE_LIMIT_GLOBAL_PER_DAY
from src.i18n import t

COLOMBIA_TZ = timezone(timedelta(hours=-5))

# process-global in-memory store, wiped on redeploy/sleep and emptied every midnight
# (_roll_day). Fine here since Streamlit Community Cloud containers are themselves ephemeral
_lock = threading.Lock()
_day = None                         # the Colombia date the two stores below belong to
_last_asked: dict[str, float] = {}  # last submission, for the cooldown
_answered: dict[str, int] = {}      # questions answered today, for the daily cap


def _roll_day() -> None:
    """Empties both stores on the first call after midnight, Colombia time: a new day
    resets every cap, and keys never seen again would otherwise pile up. Call under _lock."""
    global _day
    today = datetime.now(COLOMBIA_TZ).date()
    if today != _day:
        _day = today
        _last_asked.clear()
        _answered.clear()


def get_user_key() -> str:
    """Best-effort per-user identity: IP address, falling back to a per-session id."""
    ip = st.context.ip_address
    if ip:
        return ip
    if "_rate_limit_fallback_id" not in st.session_state:
        st.session_state["_rate_limit_fallback_id"] = str(uuid.uuid4())
    return st.session_state["_rate_limit_fallback_id"]


def check_and_record(user_key: str) -> str | None:
    """Returns a block reason if the user is over a cap, else records the submission for
    the cooldown and returns None. The daily cap counts answered questions only - see
    record_answer."""
    now = time.time()
    with _lock:
        _roll_day()
        if now - _last_asked.get(user_key, 0) < RATE_LIMIT_SECONDS:
            return t("Please wait a moment before asking another question.")

        if _answered.get(user_key, 0) >= RATE_LIMIT_PER_DAY:
            return t("You've reached today's limit of {limit} questions. "
                     "Try again after midnight (Colombia time).").format(limit=RATE_LIMIT_PER_DAY)

        if sum(_answered.values()) >= RATE_LIMIT_GLOBAL_PER_DAY:
            return t("The app has reached its daily limit of questions for everyone. "
                     "Try again after midnight (Colombia time).")

        _last_asked[user_key] = now
        return None


def record_answer(user_key: str) -> None:
    """Counts a question toward the daily cap once the pipeline returned a reply - any
    reply, including "no data" or out-of-scope. A model outage, crash or interrupted run
    never gets here."""
    with _lock:
        _roll_day()
        _answered[user_key] = _answered.get(user_key, 0) + 1
