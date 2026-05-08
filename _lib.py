"""ページ共通の小物。キャッシュ付き fetch / ウォッチリスト state / 銘柄検索。"""
from __future__ import annotations

import re

import streamlit as st
import yfinance as yf

from stock_data import StockSnapshot, fetch_one


@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch(ticker: str, period: str = "6mo", interval: str = "1d") -> StockSnapshot:
    return fetch_one(ticker, period=period, interval=interval)


# ─── ウォッチリスト: session_state を主、URL を副 (シェア用) ─────
# session_state はページ遷移で保持される。URL クエリパラメータは Streamlit の
# 内部ナビでクリアされる場合があるため、session_state を信頼源とする。
WATCHLIST_KEY = "w"
_STATE_KEY = "_watchlist"


def _hydrate_from_url_once() -> None:
    """初回アクセス時のみ URL ?w=... を session_state に取り込む。"""
    if _STATE_KEY in st.session_state:
        return
    raw = st.query_params.get(WATCHLIST_KEY, "")
    st.session_state[_STATE_KEY] = [
        t.strip().upper() for t in raw.split(",") if t.strip()
    ]


def get_watchlist() -> list[str]:
    _hydrate_from_url_once()
    return list(st.session_state.get(_STATE_KEY, []))


def set_watchlist(tickers: list[str]) -> None:
    cleaned = [t.strip().upper() for t in tickers if t and t.strip()]
    seen: set[str] = set()
    unique = [t for t in cleaned if not (t in seen or seen.add(t))]
    st.session_state[_STATE_KEY] = unique
    # URL にも反映 (ブックマーク・共有用)
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


def has_cjk(s: str) -> bool:
    """日本語/中国語の漢字・かな・全角文字が含まれるか。

    Yahoo Finance autocomplete は CJK で投げると 0 件を返すため、
    UI 側で英語/ローマ字入力を促すために使う。
    """
    return any(
        0x3040 <= ord(c) <= 0x9FFF or 0xFF00 <= ord(c) <= 0xFFEF
        for c in s
    )
