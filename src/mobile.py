import re
import streamlit as st


def is_mobile() -> bool:
    ua = st.context.headers.get("User-Agent", "")
    return bool(re.search(r"Mobile|Android|iPhone", ua))


def legend(n_series: int) -> dict:
    """Horizontal legend above the chart on desktop; stacked vertical legend below
    the chart on mobile once enough series would wrap/overlap a horizontal one."""
    if is_mobile() and n_series > 4:
        return dict(orientation="v", yanchor="top", y=-0.3, xanchor="left", x=0,
                    font=dict(size=11))
    return dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)


def chart_height(n_series: int, base: int = 600) -> int:
    return base + (70 + n_series * 22 if is_mobile() and n_series > 4 else 0)


def category_ticks(n: int) -> dict:
    if is_mobile() and n > 8:
        return dict(dtick=-(-n // 8), tickangle=90, tickfont=dict(size=11))
    return dict(dtick=max(1, n // 20), tickangle=45, tickfont=dict(size=13))


def map_colorbar(title: str) -> dict:
    """Map colorbar + margin: unchanged (Plotly Express default) on desktop,
    moved horizontal below the map on mobile so it doesn't eat plot width."""
    if is_mobile():
        return dict(coloraxis_colorbar=dict(title=title, orientation="h", y=-0.15,
                                             thickness=12, len=0.9),
                    margin=dict(l=0, r=0, t=10, b=90))
    return dict(coloraxis_colorbar=dict(title=title), margin=dict(l=0, r=0, t=10, b=0))


if __name__ == "__main__":
    import unittest.mock as mock

    with mock.patch(f"{__name__}.is_mobile", return_value=True):
        assert legend(5)["orientation"] == "v"
        assert chart_height(5) == 600 + 70 + 5 * 22
        assert category_ticks(20)["tickangle"] == 90
        assert map_colorbar("x")["margin"]["b"] == 90

    with mock.patch(f"{__name__}.is_mobile", return_value=False):
        assert legend(5)["orientation"] == "h"
        assert chart_height(5) == 600
        assert category_ticks(20) == dict(dtick=1, tickangle=45, tickfont=dict(size=13))
        assert map_colorbar("x")["margin"]["b"] == 0

    print("ok")
