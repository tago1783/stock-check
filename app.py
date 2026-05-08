"""Streamlit UI: 銘柄入力 → 価格チャート + 指標 + AI投資判断ドラフト。

起動:
    streamlit run app.py
"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from indicators import add_indicators, latest_summary
from stock_data import fetch_one


st.set_page_config(page_title="Stock Check", layout="wide")
st.title("Stock Check — yfinance + Claude")
st.caption("⚠️ 教育・試作目的。実際の投資判断は本人の責任で行ってください。")

# ─── サイドバー ────────────────────────────────────────────
AI_ENABLED = os.environ.get("ENABLE_AI") == "1"

with st.sidebar:
    st.header("入力")
    ticker = st.text_input("Ticker", value="7203.T", help="例: 7203.T (トヨタ), AAPL, MSFT").strip()
    period = st.selectbox("期間", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2)
    interval = st.selectbox("足", ["1d", "1wk", "1mo"], index=0)
    if AI_ENABLED:
        run_ai = st.checkbox(
            "Claudeで投資判断ドラフトを生成",
            value=False,
            help="ANTHROPIC_API_KEY 環境変数が必要",
        )
    else:
        run_ai = False
    fetch_btn = st.button("取得", type="primary")

if not fetch_btn:
    st.info("左サイドバーで銘柄を入力して「取得」を押してください。")
    st.stop()

# ─── データ取得 ────────────────────────────────────────────
with st.spinner(f"{ticker} を取得中..."):
    try:
        snap = fetch_one(ticker, period=period, interval=interval)
    except Exception as exc:  # noqa: BLE001
        st.error(f"取得失敗: {exc}")
        st.stop()

if snap.history.empty:
    st.warning("価格履歴が取得できませんでした。ティッカーを確認してください。")
    st.stop()

ind = add_indicators(snap.history)
summary = latest_summary(ind)

# ─── ヘッダーメトリクス ────────────────────────────────────
st.subheader(f"{snap.name} ({snap.ticker})")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("最新終値", f"{summary['close']:.2f} {snap.currency}")
period_change = (snap.history["Close"].iloc[-1] / snap.history["Close"].iloc[0] - 1) * 100
c2.metric("期間騰落", f"{period_change:+.2f}%")
if summary.get("rsi_14") is not None:
    c3.metric("RSI(14)", f"{summary['rsi_14']:.1f}")
if snap.market_cap:
    c4.metric("時価総額", f"{snap.market_cap/1e9:,.1f} B {snap.currency}")
if snap.trailing_pe:
    c5.metric("Trailing PE", f"{snap.trailing_pe:.2f}")

if summary.get("signals"):
    st.write("シグナル:", " · ".join(f"`{s}`" for s in summary["signals"]))

# ─── チャート ─────────────────────────────────────────────
tab_price, tab_rsi, tab_macd, tab_table = st.tabs(["価格 + SMA", "RSI", "MACD", "データ"])

with tab_price:
    chart_df = ind[["Close", "SMA_20", "SMA_50", "BB_Upper", "BB_Lower"]].copy()
    chart_df.index = pd.to_datetime(chart_df.index).tz_localize(None)
    st.line_chart(chart_df)

with tab_rsi:
    rsi_df = ind[["RSI_14"]].copy()
    rsi_df.index = pd.to_datetime(rsi_df.index).tz_localize(None)
    st.line_chart(rsi_df)
    st.caption("70 以上で買われすぎ、30 以下で売られすぎの目安")

with tab_macd:
    macd_df = ind[["MACD", "Signal", "Hist"]].copy()
    macd_df.index = pd.to_datetime(macd_df.index).tz_localize(None)
    st.line_chart(macd_df)

with tab_table:
    st.dataframe(
        ind[["Close", "SMA_20", "SMA_50", "RSI_14", "MACD", "Signal", "Hist"]].tail(60),
        width="stretch",
    )

# ─── AI 投資判断ドラフト ──────────────────────────────────
if run_ai:
    st.divider()
    st.subheader("Claude 投資判断ドラフト")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY が環境変数に設定されていません。")
    else:
        with st.spinner("Claude Opus 4.7 で判断中..."):
            try:
                from ai_advisor import advise
                advice = advise(snap)
                st.markdown(advice.text)
                with st.expander("API 使用量"):
                    st.json({
                        "input_tokens": advice.input_tokens,
                        "output_tokens": advice.output_tokens,
                        "cache_read_input_tokens": advice.cache_read_tokens,
                        "cache_creation_input_tokens": advice.cache_creation_tokens,
                    })
            except Exception as exc:  # noqa: BLE001
                st.error(f"AI判断生成失敗: {exc}")
