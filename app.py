"""Streamlit UI: 銘柄詳細 + AI 3軸レビュー (ファンダ/テクニカル/センチメント)。

起動:
    python -m streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from _lib import cached_fetch, has_cjk, render_api_key_input, search_ticker
from indicators import add_indicators, latest_summary


st.set_page_config(page_title="Stock Check", layout="wide")
st.title("Stock Check — yfinance + Claude")
st.caption("⚠️ 教育・試作目的。実際の投資判断は本人の責任で行ってください。")
st.info(
    "👈 サイドバー上部のナビから他の機能にも移動できます："
    " **Watchlist** / **Compare** (銘柄比較) / **Dividends** (配当) / "
    "**News** / **Company** (企業情報) / **Sector** (業種別)"
)

# ─── サイドバー ────────────────────────────────────────────
with st.sidebar:
    st.header("銘柄")

    # 社名検索 (任意)
    with st.expander("🔍 社名で検索"):
        st.caption("英語/ローマ字で入力 (例: トヨタ → `toyota`)")
        with st.form("home_search_form"):
            sq = st.text_input(
                "社名・シンボル",
                placeholder="例: apple, toyota, nintendo",
                label_visibility="collapsed",
            ).strip()
            search_btn = st.form_submit_button("検索", type="primary")
        if search_btn and sq:
            try:
                cands = search_ticker(sq, limit=8)
            except Exception as exc:  # noqa: BLE001
                st.error(f"検索失敗: {exc}")
                cands = []
            if not cands:
                if has_cjk(sq):
                    st.warning("日本語不可。英語/ローマ字で再試行してください。")
                else:
                    st.info("候補なし")
            else:
                st.caption(f"{len(cands)} 件 — クリックで Ticker 欄に反映")
                for c in cands:
                    label = f"**{c['symbol']}** {c['name'][:24]}"
                    if st.button(label, key=f"home_pick_{c['symbol']}"):
                        st.session_state["ticker_input"] = c["symbol"]
                        st.rerun()

    # Ticker (session_state経由で検索結果を反映可)
    if "ticker_input" not in st.session_state:
        st.session_state["ticker_input"] = "7203.T"
    ticker = st.text_input(
        "Ticker",
        key="ticker_input",
        help="例: 7203.T (トヨタ), AAPL, MSFT, 446A.T (ノースサンド)",
    ).strip()
    period = st.selectbox("期間", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2)
    interval = st.selectbox("足", ["1d", "1wk", "1mo"], index=0)
    fetch_btn = st.button("取得", type="primary")

    st.divider()
    st.header("🤖 AI 予想 (任意)")
    st.caption(
        "Claude Opus 4.7 でファンダ・テクニカル・センチメントの3軸レビューを生成。"
        "[API キー取得](https://console.anthropic.com/)。"
        "キーはブラウザのこのタブのメモリのみに保持されます。"
    )
    api_key = render_api_key_input()
    run_ai = st.button("🔮 AI 予想を実行", disabled=not api_key, type="secondary")

if not fetch_btn and not run_ai:
    st.info("左サイドバーで銘柄を入力して「取得」を押してください。")
    st.stop()

# ─── データ取得 ────────────────────────────────────────────
with st.spinner(f"{ticker} を取得中..."):
    try:
        snap = cached_fetch(ticker, period=period, interval=interval)
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

# ─── AI 3軸レビュー ───────────────────────────────────────
def _verdict_badge(verdict: str, confidence: str) -> None:
    # Softened palette — muted, not saturated (no pure RGB primaries)
    color = {
        "BUY": "#4A8A5C",   # muted forest
        "HOLD": "#C4924A",  # warm amber
        "SELL": "#B85048",  # muted brick
    }.get(verdict, "#7A7770")
    label = {"BUY": "買い", "HOLD": "様子見", "SELL": "売り"}.get(verdict, verdict)
    st.markdown(
        f"""
        <div style="padding:18px 28px; border-radius:14px; background:{color};
                    color:#F8F6F0; font-weight:600; font-size:22px; text-align:center;
                    margin: 12px 0 18px 0; letter-spacing: 0.02em;
                    box-shadow: 0 1px 4px rgba(45, 44, 40, 0.10);">
            判断: {label} ({verdict})  ／  確信度: {confidence}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_axis(title: str, axis: dict) -> None:
    st.markdown(f"#### {title}")
    bull = axis.get("bullish") or []
    bear = axis.get("bearish") or []
    if bull:
        st.markdown("**強気要因**")
        for b in bull:
            st.markdown(f"- ✅ {b}")
    if bear:
        st.markdown("**弱気要因**")
        for b in bear:
            st.markdown(f"- ⚠️ {b}")
    if not bull and not bear:
        st.caption("該当する要因なし")
    if axis.get("summary"):
        st.markdown(f"_{axis['summary']}_")


if run_ai:
    st.divider()
    st.subheader("🤖 Claude 3軸レビュー")

    with st.spinner("Claude Opus 4.7 で判断中... (ファンダ + テクニカル + ニュース 解析、20-40秒)"):
        try:
            from ai_advisor import advise
            advice = advise(snap, api_key=api_key)
        except Exception as exc:  # noqa: BLE001
            st.error(f"AI判断生成失敗: {exc}")
            st.stop()

    _verdict_badge(advice.verdict, advice.confidence)

    cols = st.columns(3)
    with cols[0]:
        _render_axis("📊 ファンダメンタル", advice.fundamentals)
    with cols[1]:
        _render_axis("📈 テクニカル", advice.technical)
    with cols[2]:
        _render_axis("📰 センチメント", advice.sentiment)

    st.markdown("#### 🧭 総合論拠")
    st.info(advice.rationale)

    st.caption(
        "⚠️ AI による分析ドラフトです。投資助言ではなく、最終判断はご自身で行ってください。"
    )
    with st.expander("API 使用量"):
        st.json({
            "input_tokens": advice.input_tokens,
            "output_tokens": advice.output_tokens,
            "cache_read_input_tokens": advice.cache_read_tokens,
            "cache_creation_input_tokens": advice.cache_creation_tokens,
        })
