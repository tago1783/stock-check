"""ページ共通の小物。キャッシュ付き fetch とウォッチリスト state。"""
from __future__ import annotations

import streamlit as st

from stock_data import StockSnapshot, fetch_one


@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch(ticker: str, period: str = "6mo", interval: str = "1d") -> StockSnapshot:
    return fetch_one(ticker, period=period, interval=interval)


# ─── ウォッチリスト: URL の ?w=AAPL,MSFT,7203.T に永続化 ──────
WATCHLIST_KEY = "w"


def get_watchlist() -> list[str]:
    raw = st.query_params.get(WATCHLIST_KEY, "")
    return [t.strip().upper() for t in raw.split(",") if t.strip()]


def set_watchlist(tickers: list[str]) -> None:
    cleaned = [t.strip().upper() for t in tickers if t and t.strip()]
    # 重複除去・順序保持
    seen: set[str] = set()
    unique = [t for t in cleaned if not (t in seen or seen.add(t))]
    if unique:
        st.query_params[WATCHLIST_KEY] = ",".join(unique)
    elif WATCHLIST_KEY in st.query_params:
        del st.query_params[WATCHLIST_KEY]


def add_to_watchlist(ticker: str) -> None:
    current = get_watchlist()
    t = ticker.strip().upper()
    if t and t not in current:
        set_watchlist(current + [t])


def remove_from_watchlist(ticker: str) -> None:
    set_watchlist([t for t in get_watchlist() if t != ticker.strip().upper()])
