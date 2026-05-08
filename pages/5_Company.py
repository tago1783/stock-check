"""企業情報: 52週レンジ、ファンダメンタル指標、事業概要。"""
from __future__ import annotations

import streamlit as st
import yfinance as yf

st.set_page_config(page_title="企業情報", layout="wide")
st.title("🏢 企業情報 / ファンダメンタルズ")

with st.sidebar:
    ticker = st.text_input("Ticker", value="AAPL").strip()
    fetch = st.button("取得", type="primary")

if not fetch:
    st.info("サイドバーで銘柄を入力して「取得」を押してください。")
    st.stop()


@st.cache_data(ttl=600, show_spinner=False)
def get_info(ticker: str) -> dict:
    return getattr(yf.Ticker(ticker), "info", {}) or {}


with st.spinner("取得中..."):
    try:
        info = get_info(ticker)
    except Exception as exc:  # noqa: BLE001
        st.error(f"取得失敗: {exc}")
        st.stop()

if not info:
    st.warning("情報が取得できませんでした。")
    st.stop()

name = info.get("longName") or info.get("shortName") or ticker
st.subheader(f"{name} ({ticker})")
website = info.get("website")
if website:
    st.markdown(f"🔗 [{website}]({website})")

# ── 52週レンジ + ヘッダー指標 ─────────────────────────
c1, c2, c3, c4 = st.columns(4)
price = info.get("currentPrice") or info.get("regularMarketPrice")
high52 = info.get("fiftyTwoWeekHigh")
low52 = info.get("fiftyTwoWeekLow")
currency = info.get("currency", "")

if price:
    c1.metric("現在値", f"{price:.2f} {currency}")
if high52:
    c2.metric("52週高値", f"{high52:.2f}")
if low52:
    c3.metric("52週安値", f"{low52:.2f}")
if price and high52 and low52 and high52 > low52:
    pos = (price - low52) / (high52 - low52) * 100
    c4.metric("52週レンジ位置", f"{pos:.0f}%", help="0%=安値, 100%=高値")

# ── ファンダメンタル ─────────────────────────────────
st.subheader("バリュエーション")
val_keys = [
    ("時価総額", "marketCap", lambda v: f"{v/1e9:,.2f} B {currency}"),
    ("Trailing PER", "trailingPE", lambda v: f"{v:.2f}"),
    ("Forward PER", "forwardPE", lambda v: f"{v:.2f}"),
    ("PBR", "priceToBook", lambda v: f"{v:.2f}"),
    ("EPS (TTM)", "trailingEps", lambda v: f"{v:.2f}"),
    ("Beta", "beta", lambda v: f"{v:.2f}"),
    ("配当利回り", "dividendYield", lambda v: f"{v*100:.2f}%" if v < 1 else f"{v:.2f}%"),
    ("配当性向", "payoutRatio", lambda v: f"{v*100:.2f}%"),
]
cols = st.columns(4)
for i, (label, key, fmt) in enumerate(val_keys):
    v = info.get(key)
    if v is not None:
        try:
            cols[i % 4].metric(label, fmt(v))
        except Exception:  # noqa: BLE001
            cols[i % 4].metric(label, str(v))

# ── 業績 ─────────────────────────────────────────
st.subheader("業績")
biz_keys = [
    ("売上 (TTM)", "totalRevenue", lambda v: f"{v/1e9:,.2f} B {currency}"),
    ("純利益 (TTM)", "netIncomeToCommon", lambda v: f"{v/1e9:,.2f} B {currency}"),
    ("売上成長率", "revenueGrowth", lambda v: f"{v*100:.2f}%"),
    ("利益成長率", "earningsGrowth", lambda v: f"{v*100:.2f}%"),
    ("ROE", "returnOnEquity", lambda v: f"{v*100:.2f}%"),
    ("ROA", "returnOnAssets", lambda v: f"{v*100:.2f}%"),
    ("粗利益率", "grossMargins", lambda v: f"{v*100:.2f}%"),
    ("営業利益率", "operatingMargins", lambda v: f"{v*100:.2f}%"),
]
cols = st.columns(4)
for i, (label, key, fmt) in enumerate(biz_keys):
    v = info.get(key)
    if v is not None:
        try:
            cols[i % 4].metric(label, fmt(v))
        except Exception:  # noqa: BLE001
            cols[i % 4].metric(label, str(v))

# ── 概要 ─────────────────────────────────────────
st.subheader("基本情報")
basic = {
    "セクター": info.get("sector"),
    "業種": info.get("industry"),
    "本社": ", ".join(filter(None, [info.get("city"), info.get("state"), info.get("country")])),
    "従業員数": info.get("fullTimeEmployees"),
    "上場市場": info.get("exchange"),
}
for k, v in basic.items():
    if v:
        st.text(f"{k}: {v:,}" if isinstance(v, int) else f"{k}: {v}")

summary = info.get("longBusinessSummary")
if summary:
    with st.expander("事業概要"):
        st.write(summary)
