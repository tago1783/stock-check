"""配当履歴: 年次配当の棒グラフ + 推移テーブル。"""
from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="配当履歴", layout="wide")
st.title("💰 配当履歴")

with st.sidebar:
    ticker = st.text_input("Ticker", value="AAPL").strip()
    fetch = st.button("取得", type="primary")

if not fetch:
    st.info("サイドバーで銘柄を入力して「取得」を押してください。")
    st.stop()


@st.cache_data(ttl=600, show_spinner=False)
def get_dividends(ticker: str):
    t = yf.Ticker(ticker)
    info = getattr(t, "info", {}) or {}
    return t.dividends, t.splits, info


with st.spinner("取得中..."):
    try:
        divs, splits, info = get_dividends(ticker)
    except Exception as exc:  # noqa: BLE001
        st.error(f"取得失敗: {exc}")
        st.stop()

st.subheader(f"{info.get('longName') or info.get('shortName') or ticker} ({ticker})")

if divs is None or len(divs) == 0:
    st.warning("配当履歴がありません（無配銘柄、または yfinance が取得できないケース）。")
    st.stop()

divs = divs.copy()
divs.index = pd.to_datetime(divs.index).tz_localize(None)

c1, c2, c3 = st.columns(3)
c1.metric("通算支払回数", len(divs))
c2.metric("直近配当", f"{divs.iloc[-1]:.4f}")
yield_pct = info.get("dividendYield")
if yield_pct:
    c3.metric("配当利回り", f"{yield_pct * 100:.2f}%" if yield_pct < 1 else f"{yield_pct:.2f}%")

st.subheader("年次配当合計")
yearly = divs.groupby(divs.index.year).sum()
yearly.index.name = "Year"
st.bar_chart(yearly)

st.subheader("支払履歴")
df = pd.DataFrame({"Date": divs.index.date, "Amount": divs.values}).iloc[::-1]
st.dataframe(df, width="stretch", hide_index=True)

if splits is not None and len(splits) > 0:
    with st.expander(f"株式分割 ({len(splits)} 件)"):
        sp = pd.DataFrame({"Date": pd.to_datetime(splits.index).date, "Ratio": splits.values}).iloc[::-1]
        st.dataframe(sp, width="stretch", hide_index=True)
