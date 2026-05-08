"""ニュース: yfinance.Ticker.news からの最新記事一覧。"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st
import yfinance as yf

st.set_page_config(page_title="ニュース", layout="wide")
st.title("📰 ニュース")

with st.sidebar:
    ticker = st.text_input("Ticker", value="AAPL").strip()
    fetch = st.button("取得", type="primary")

if not fetch:
    st.info("サイドバーで銘柄を入力して「取得」を押してください。")
    st.stop()


@st.cache_data(ttl=300, show_spinner=False)
def get_news(ticker: str):
    return yf.Ticker(ticker).news or []


def normalize_item(item: dict) -> dict:
    """yfinance バージョン差を吸収。新形式は item['content'] にネスト。"""
    if "content" in item and isinstance(item["content"], dict):
        c = item["content"]
        return {
            "title": c.get("title", ""),
            "summary": c.get("summary") or c.get("description", ""),
            "publisher": (c.get("provider") or {}).get("displayName", ""),
            "link": (c.get("canonicalUrl") or c.get("clickThroughUrl") or {}).get("url", ""),
            "pub_date": c.get("pubDate"),
        }
    pub_ts = item.get("providerPublishTime")
    pub_date = (
        datetime.fromtimestamp(pub_ts, tz=timezone.utc).isoformat() if pub_ts else None
    )
    return {
        "title": item.get("title", ""),
        "summary": item.get("summary", ""),
        "publisher": item.get("publisher", ""),
        "link": item.get("link", ""),
        "pub_date": pub_date,
    }


with st.spinner("取得中..."):
    try:
        items = get_news(ticker)
    except Exception as exc:  # noqa: BLE001
        st.error(f"取得失敗: {exc}")
        st.stop()

if not items:
    st.warning("該当ニュースが見つかりませんでした。")
    st.stop()

st.caption(f"{len(items)} 件のニュース")
for raw in items:
    n = normalize_item(raw)
    if not n["title"]:
        continue
    with st.container(border=True):
        st.markdown(f"### [{n['title']}]({n['link']})" if n["link"] else f"### {n['title']}")
        meta = " · ".join(filter(None, [n["publisher"], n["pub_date"]]))
        if meta:
            st.caption(meta)
        if n["summary"]:
            st.write(n["summary"])
