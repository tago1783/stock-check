"""ページ共通の小物。キャッシュ付き fetch / ウォッチリスト state / 銘柄検索。"""
from __future__ import annotations

import re

import streamlit as st
import yfinance as yf

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


# ─── 銘柄検索 (社名 → ティッカー) ─────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def search_ticker(query: str, limit: int = 15) -> list[dict]:
    """Yahoo Finance autocomplete で社名/シンボル検索。

    返却: [{symbol, name, exchange, type, sector}, ...]
    """
    if not query.strip():
        return []
    result = yf.Search(query.strip(), max_results=limit)
    out = []
    for q in (result.quotes or [])[:limit]:
        out.append({
            "symbol": q.get("symbol", ""),
            "name": q.get("longname") or q.get("shortname") or q.get("symbol", ""),
            "exchange": q.get("exchDisp") or q.get("exchange", ""),
            "type": q.get("typeDisp") or q.get("quoteType", ""),
            "sector": q.get("sectorDisp") or q.get("sector", ""),
        })
    return out


def filter_by_regex(items: list[dict], pattern: str) -> list[dict]:
    """name または symbol が pattern にマッチするものだけ残す。"""
    if not pattern:
        return items
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error:
        return items
    return [c for c in items if rx.search(c["name"]) or rx.search(c["symbol"])]
