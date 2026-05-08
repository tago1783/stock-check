"""銘柄比較: 始点を100に揃えた正規化チャート。"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from _lib import cached_fetch, get_watchlist

st.set_page_config(page_title="銘柄比較", layout="wide")
st.title("📊 銘柄比較")
st.caption("始点を 100 に揃えた相対パフォーマンス比較。")

with st.sidebar:
    st.header("設定")
    raw = st.text_area(
        "Tickers (カンマ or 改行区切り)",
        value=", ".join(get_watchlist()) or "AAPL, MSFT, GOOGL",
    )
    period = st.selectbox("期間", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    interval = st.selectbox("足", ["1d", "1wk", "1mo"], index=0)
    run = st.button("比較", type="primary")

tickers = [t.strip().upper() for t in raw.replace("\n", ",").split(",") if t.strip()]
if not run:
    st.info(f"対象: {', '.join(tickers) if tickers else '(なし)'} — サイドバーで「比較」を押してください。")
    st.stop()
if len(tickers) < 2:
    st.warning("2銘柄以上を入力してください。")
    st.stop()

closes: dict[str, pd.Series] = {}
errors = []
with st.spinner("取得中..."):
    for tk in tickers:
        try:
            s = cached_fetch(tk, period=period, interval=interval)
            if not s.history.empty:
                series = s.history["Close"].copy()
                series.index = pd.to_datetime(series.index).tz_localize(None)
                closes[tk] = series
            else:
                errors.append(f"{tk}: 履歴なし")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{tk}: {exc}")

if not closes:
    st.error("どの銘柄も取得できませんでした。")
    st.stop()

df = pd.DataFrame(closes).dropna()
if df.empty:
    st.warning("共通する取引日がありません。期間を伸ばすか銘柄を見直してください。")
    st.stop()

normalized = df.div(df.iloc[0]) * 100

st.subheader("正規化チャート (始点 = 100)")
st.line_chart(normalized)

st.subheader("リターン サマリ")
last = normalized.iloc[-1] - 100
summary = pd.DataFrame({
    "期間騰落 %": last.round(2),
    "始値": df.iloc[0].round(2),
    "終値": df.iloc[-1].round(2),
})
st.dataframe(summary, width="stretch")

if errors:
    with st.expander(f"⚠️ 取得失敗 ({len(errors)} 件)"):
        for e in errors:
            st.text(e)
