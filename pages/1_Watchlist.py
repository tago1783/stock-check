"""ウォッチリスト: 保存銘柄の一覧。URL の ?w=AAPL,MSFT,7203.T で共有可能。"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from _lib import add_to_watchlist, cached_fetch, get_watchlist, remove_from_watchlist

st.set_page_config(page_title="ウォッチリスト", layout="wide")
st.title("📋 ウォッチリスト")
st.caption("保存銘柄の現在値と騰落率。URL に保存されるのでブックマーク・共有可能です。")

with st.sidebar:
    st.header("追加")
    new = st.text_input("Ticker", placeholder="例: AAPL, 7203.T").strip()
    if st.button("追加", type="primary", disabled=not new):
        add_to_watchlist(new)
        st.rerun()

tickers = get_watchlist()
if not tickers:
    st.info("ウォッチリストは空です。サイドバーから銘柄を追加してください。")
    st.stop()

rows = []
errors = []
for tk in tickers:
    try:
        s = cached_fetch(tk, period="1mo", interval="1d")
        if s.history.empty:
            errors.append(f"{tk}: 履歴なし")
            continue
        last = s.history["Close"].iloc[-1]
        prev = s.history["Close"].iloc[-2] if len(s.history) >= 2 else last
        first = s.history["Close"].iloc[0]
        rows.append({
            "Ticker": tk,
            "Name": s.name[:30],
            "Last": round(float(last), 2),
            "1日 %": round(float((last - prev) / prev * 100), 2),
            "1ヶ月 %": round(float((last - first) / first * 100), 2),
            "Currency": s.currency or "",
        })
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{tk}: {exc}")

if rows:
    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config={
            "1日 %": st.column_config.NumberColumn(format="%.2f%%"),
            "1ヶ月 %": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

    st.subheader("削除")
    cols = st.columns(min(len(rows), 5))
    for i, r in enumerate(rows):
        if cols[i % len(cols)].button(f"❌ {r['Ticker']}", key=f"del_{r['Ticker']}"):
            remove_from_watchlist(r["Ticker"])
            st.rerun()

if errors:
    with st.expander(f"⚠️ 取得失敗 ({len(errors)} 件)"):
        for e in errors:
            st.text(e)
