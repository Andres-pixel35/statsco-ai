import json
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.i18n import t, get_lang
from src.constants import MAINLAND_LON_RANGE, MAINLAND_LAT_RANGE
from src.mobile import legend, chart_height, category_ticks, map_colorbar

_X_NAME_RE = re.compile(r"year|anio|año|fecha|date|mes|month|period|day", re.IGNORECASE)
_GREY = "rgba(180,180,180,0.3)"
# shown under a chart and after a prose answer when the result hit SQL_ROW_LIMIT
TRUNCATED_NOTE = "Only the first {n} rows of the result are shown."
_NO_DATA_GREY = "#D3D3D3"


def _separators() -> str:
    """Plotly's decimal + thousands characters: Spanish writes 97,3 and 1.234.567."""
    return ",." if get_lang() == "es" else ".,"

_DEPT_GEOJSON_PATH = Path(__file__).resolve().parent.parent / "data" / "colombia_departments.geojson"
_DEPT_NAME_COL_RE = re.compile(r"depart|dpto", re.IGNORECASE)


@st.cache_data
def _dept_geojson() -> dict:
    return json.loads(_DEPT_GEOJSON_PATH.read_text(encoding="utf-8"))


def _dept_map_figure(df: pd.DataFrame, value_col: str, label: str):
    """Choropleth of value_col by department. Keys on a column of 2-digit DANE
    department codes (the SQL prompt is told to SELECT department_code for map
    questions); returns None if the result has no such column.

    'a column whose values are all 2-digit strings' is the code heuristic;
    a stray unrelated 2-digit column would mis-key - Table view is the safe fallback.
    """
    code_col = next(
        (c for c in df.columns
         if df[c].notna().any()
         and df[c].dropna().astype(str).str.fullmatch(r"\d{2}").all()),
        None)
    if code_col is None:
        return None
    name_col = next((c for c in df.columns
                     if c != code_col and _DEPT_NAME_COL_RE.search(str(c))), None)

    fig = px.choropleth(df, geojson=_dept_geojson(), featureidkey="properties.DPTO",
                        locations=code_col, color=value_col,
                        hover_name=name_col or code_col,
                        color_continuous_scale="Blues")
    fig.update_geos(visible=False, lonaxis_range=MAINLAND_LON_RANGE, lataxis_range=MAINLAND_LAT_RANGE)
    # map has no x/y to hover over, just a location name and its shaded value -
    # replace px's default "value_col=%{z}" (raw column name, unformatted number)
    fig.update_traces(hovertemplate=f"<b>%{{hovertext}}</b><br>{label}: %{{z:,.2f}}<extra></extra>")
    # departments absent from the result still get drawn, in grey (after update_traces so
    # its hovertemplate doesn't overwrite this one); own colorscale keeps it off the colorbar
    present = set(df[code_col].dropna().astype(str))
    missing = [f["properties"] for f in _dept_geojson()["features"] if f["properties"]["DPTO"] not in present]
    if missing:
        fig.add_trace(go.Choropleth(
            geojson=_dept_geojson(), featureidkey="properties.DPTO",
            locations=[p["DPTO"] for p in missing], z=[0] * len(missing),
            text=[p["NOMBRE_DPT"].title() for p in missing],
            colorscale=[[0, _NO_DATA_GREY], [1, _NO_DATA_GREY]], showscale=False,
            hovertemplate=f"<b>%{{text}}</b><br>{t('No data')}<extra></extra>"))
    layout = map_colorbar(label)
    margin = layout.pop("margin")
    fig.update_layout(height=600, margin=margin, paper_bgcolor="rgba(0,0,0,0)", separators=_separators(),
                      geo=dict(bgcolor="rgba(0,0,0,0)"), **layout)
    return fig


def pick_axes(df: pd.DataFrame):
    """Guess (x column, y value columns, series column) for charting a SQL result.

    x is a period-like column by name if present, else the first non-numeric
    column. series_col groups long-format results (one value column plus any
    leftover columns that actually vary, e.g. sex) for pivoting to wide;
    leftover columns that are constant (e.g. a unit column) are ignored, and
    multiple varying columns are combined into one composite series key. No
    numeric column -> nothing to plot, caller falls back to a table.
    """
    # heuristic axis pick; odd SQL shapes may mis-map - Table view is the always-safe fallback
    numeric = list(df.select_dtypes(include="number").columns)
    candidates = [c for c in df.columns if _X_NAME_RE.search(str(c))]
    x = max(candidates, key=lambda c: df[c].nunique(dropna=True)) if candidates else None
    if x is None:
        non_numeric = [c for c in df.columns if c not in numeric]
        x = non_numeric[0] if non_numeric else None
    y_cols = [c for c in numeric if c != x and df[c].nunique(dropna=True) > 1]
    # other date/period-named columns (e.g. a human-readable period_label alongside
    # period_start_date) are redundant with x, not a real grouping dimension - excluding
    # them from series_col keeps a day-by-day result one continuous line, not one line per day
    others = [c for c in df.columns
              if c != x and c not in y_cols and not _X_NAME_RE.search(str(c))]
    varying = [c for c in others if df[c].nunique(dropna=True) > 1]

    if len(y_cols) != 1 or not varying:
        return x, y_cols, None
    if len(varying) == 1:
        return x, y_cols, varying[0]

    # more than one real grouping dimension (e.g. sex + concept) -> combine
    # into a single composite series key so pivot/plot still works
    series_col = " + ".join(varying)
    df[series_col] = df[varying].astype(str).agg(" · ".join, axis=1)
    return x, y_cols, series_col


def _wide(df, x, y_cols, series_col):
    if series_col:
        return df.pivot(index=x, columns=series_col, values=y_cols[0])
    if x is not None:
        return df.set_index(x)[y_cols]
    return df[y_cols]


def _format_numbers(df):
    swap = str.maketrans(".,", _separators())  # identity for English
    out = df.copy()
    for c in out.select_dtypes(include="number").columns:
        col = out[c].dropna()
        decimals = 0 if (col == col.round()).all() else 2
        out[c] = out[c].map(lambda v: v if pd.isna(v) else f"{v:,.{decimals}f}".translate(swap))
    return out


def _humanize(col: str) -> str:
    """Fallback axis/legend label when the LLM-provided label is missing for a
    column (no chart-title response, parse failure, or a column it skipped)."""
    return col.replace("_", " ").strip().title()


def build_figure(df, chart_type, x, y_cols, series_col, labels=None, units=None, highlight=None):
    """A plotly Figure for "Line"/"Bar", or a display-formatted DataFrame for
    "Table" (also the fallback when there is no numeric column to plot)."""
    if chart_type == "Table" or not y_cols:
        return _format_numbers(df)

    labels = labels or {}
    units = units or {}
    label_for = lambda col: labels.get(col) or _humanize(col)

    wide = _wide(df, x, y_cols, series_col)
    if series_col:
        # series values are raw data (e.g. a "metric" column storing "average_life"),
        # not a column name - no LLM label for them, just humanize the slug
        wide = wide.rename(columns={c: _humanize(str(c)) for c in wide.columns})
    else:
        # rename even a single y column: a raw column literally named "value" (common
        # in this app's SQL) collides with plotly express's own reserved melt-column
        # name, which silently renames it to "_value" and breaks the labels lookup below
        wide = wide.rename(columns={c: label_for(c) for c in y_cols})
    x_label = label_for(x) if x is not None else ""
    y_label = (units.get(y_cols[0]) or label_for(y_cols[0])) if y_cols else "Value"
    plot_labels = {wide.index.name or "index": x_label, "value": y_label}

    if chart_type == "Bar":
        fig = px.bar(wide, barmode="group", labels=plot_labels)
        y_grid = False
    else:
        fig = px.line(wide, labels=plot_labels)
        y_grid = True

    n_series = len(wide.columns) if hasattr(wide, "columns") else 1
    fig.update_layout(
        height=chart_height(n_series),
        separators=_separators(),
        margin=dict(l=50, r=20, t=40, b=0),
        legend=legend(n_series),
        legend_title_text="",
        xaxis_title_font=dict(size=15),
        yaxis_title_font=dict(size=15),
    )
    fig.update_yaxes(showgrid=y_grid, gridwidth=0.5, gridcolor="rgba(255,255,255,0.1)",
                     tickfont=dict(size=15), tickformat=",.0f")
    fig.update_xaxes(type="category", showgrid=False, **category_ticks(len(wide)))
    fig.for_each_trace(lambda tr: tr.update(
        hovertemplate=f"<b>%{{fullData.name}}</b><br>{x_label}: %{{x}}<br>"
                      f"{y_label}: %{{y:,.2f}}<extra></extra>"))

    if highlight:
        for tr in fig.data:
            if tr.name != highlight:
                tr.update(marker=dict(color=_GREY)) if chart_type == "Bar" \
                    else tr.update(line=dict(color=_GREY))
    return fig


def render_chart_message(payload: dict, key: str) -> None:
    """Render a chart payload: title, Line/Bar/Table switch, optional highlight,
    then the Source markdown. payload = {rows, title, sources, default_view, labels}."""
    df = pd.DataFrame(payload["rows"])
    labels = payload.get("labels", {})
    units = payload.get("units", {})
    x, y_cols, series_col = pick_axes(df)

    st.markdown(f"#### {payload['title']}")
    if payload.get("truncated"):
        st.caption(t(TRUNCATED_NOTE).format(n=len(df)))

    map_fig = _dept_map_figure(df, y_cols[0], units.get(y_cols[0]) or labels.get(y_cols[0]) or _humanize(y_cols[0])) \
        if y_cols else None
    default = payload.get("default_view", "Line")
    if default == "Map":
        choices = (["Map"] if map_fig is not None else []) + ["Table"]
    else:
        choices = (["Map"] if map_fig is not None else []) + \
                  (["Line", "Bar", "Table"] if y_cols else ["Table"])
    view = st.radio("View", choices, horizontal=True, label_visibility="collapsed",
                    key=f"view_{key}", format_func=t,
                    index=choices.index(default) if default in choices else 0)

    if view == "Map":
        st.plotly_chart(map_fig, width="stretch")
        if len(map_fig.data) > 1:  # the grey no-data trace was added
            st.caption(t("Departments in grey have no data."))
        if payload["sources"]:
            st.markdown(payload["sources"])
        return

    highlight = None
    if view != "Table":
        names = ([_humanize(str(n)) for n in sorted(df[series_col].dropna().unique())]
                  if series_col else [labels.get(c) or _humanize(c) for c in y_cols])
        if len(names) > 1:
            picked = st.selectbox(t("Highlight"), ["(none)", *names], key=f"hl_{key}",
                                  format_func=lambda n: t(n) if n == "(none)" else n)
            highlight = None if picked == "(none)" else picked

    fig = build_figure(df, view, x, y_cols, series_col, labels, units, highlight=highlight)
    if isinstance(fig, pd.DataFrame):
        st.dataframe(fig, width="stretch")
    else:
        st.plotly_chart(fig, width="stretch")

    if payload["sources"]:
        st.markdown(payload["sources"])
