"""業種別ビュー: ウォッチリストの銘柄を業種で分類して比較。"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from _lib import cached_fetch, get_watchlist

st.set_page_config(page_title="業種別", layout="wide")
st.title("🏭 業種別ビュー")
st.caption("ウォッチリストの銘柄を業種で分類し、セクター単位での偏りやパフォーマンスを確認します。")

tickers = get_watchlist()
if not tickers:
    st.info("ウォッチリストが空です。Watchlist ページで銘柄を追加してください。")
    st.stop()

rows = []
errors = []
with st.spinner(f"{len(tickers)} 銘柄を取得中..."):
    for tk in tickers:
        try:
            s = cached_fetch(tk, period="1mo", interval="1d")
            if s.history.empty:
                errors.append(f"{tk}: 履歴なし")
                continue
            last = float(s.history["Close"].iloc[-1])
            first = float(s.history["Close"].iloc[0])
            pct = (last - first) / first * 100
            rows.append({
                "Ticker": tk,
                "Name": (s.name or tk)[:30],
                "Sector": s.sector or "(未分類)",
                "Last": round(last, 2),
                "1ヶ月 %": round(pct, 2),
                "PER": round(s.trailing_pe, 2) if s.trailing_pe else None,
                "時価総額(B)": round(s.market_cap / 1e9, 2) if s.market_cap else None,
                "Currency": s.currency or "",
            })
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{tk}: {exc}")

if not rows:
    st.warning("データを取得できた銘柄がありません。")
    st.stop()

df = pd.DataFrame(rows)

# ─── 業種サマリ ────────────────────────────────────────────
st.subheader("業種サマリ")
sector_summary = (
    df.groupby("Sector")
    .agg(銘柄数=("Ticker", "count"), 平均1ヶ月=("1ヶ月 %", "mean"), 平均PER=("PER", "mean"))
    .round(2)
    .sort_values("平均1ヶ月", ascending=False)
)
st.dataframe(
    sector_summary,
    width="stretch",
    column_config={
        "平均1ヶ月": st.column_config.NumberColumn(format="%.2f%%"),
    },
)

# ─── 業種シェア (銘柄数の構成比) ────────────────────────────
share = df["Sector"].value_counts()
st.subheader("業種別 銘柄数")
st.bar_chart(share)

# ─── 業種別 詳細 ──────────────────────────────────────────
st.subheader("業種別 銘柄詳細")
for sector in sector_summary.index:
    group = df[df["Sector"] == sector].drop(columns=["Sector"])
    avg = group["1ヶ月 %"].mean()
    emoji = "📈" if avg > 0 else "📉" if avg < 0 else "➡️"
    label = f"{emoji} {sector} — {len(group)} 銘柄, 平均 1ヶ月 {avg:+.2f}%"
    with st.expander(label, expanded=len(sector_summary) <= 3):
        st.dataframe(
            group,
            width="stretch",
            hide_index=True,
            column_config={
                "1ヶ月 %": st.column_config.NumberColumn(format="%.2f%%"),
                "PER": st.column_config.NumberColumn(format="%.2f"),
            },
        )

if errors:
    with st.expander(f"⚠️ 取得失敗 ({len(errors)} 件)"):
        for e in errors:
            st.text(e)
