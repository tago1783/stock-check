"""ウォッチリスト: 銘柄保存と現在値一覧。社名検索でも追加可能。"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from _lib import (
    add_to_watchlist,
    cached_fetch,
    filter_by_regex,
    get_watchlist,
    has_cjk,
    remove_from_watchlist,
    search_ticker,
)

st.set_page_config(page_title="ウォッチリスト", layout="wide")
st.title("📋 ウォッチリスト")
st.caption(
    "保存銘柄の現在値・騰落率を一覧表示。リストは URL (`?w=AAPL,7203.T`) に保存されるので、"
    "ブックマークすればそのまま再現・共有できます。"
)

current = get_watchlist()

# ─── 銘柄追加 UI ───────────────────────────────────────────
with st.expander("➕ 銘柄を追加", expanded=not current):
    tab_search, tab_direct = st.tabs(["🔍 社名で検索", "✏️ ティッカー直接入力"])

    # ── 社名検索タブ ──────────────────────────────────────
    with tab_search:
        st.caption(
            "💡 **英語/ローマ字で入力してください**。Yahoo Finance の検索 API は日本語（カナ・漢字）を受け付けません。"
            " 例: `トヨタ` → `toyota`、`任天堂` → `nintendo`、`ソニーG` → `sony`"
        )
        with st.form("search_form", clear_on_submit=False):
            cols = st.columns([4, 1])
            query = cols[0].text_input(
                "社名・シンボル",
                placeholder="例: apple, toyota, nintendo, northsand",
                label_visibility="collapsed",
            ).strip()
            submitted = cols[1].form_submit_button("🔍 検索", type="primary")
            use_regex = st.checkbox(
                "結果を正規表現でフィルタ (上級者向け)",
                help="Yahoo の検索結果を更にクライアント側で絞り込む",
            )

        if submitted and query:
            try:
                candidates = search_ticker(query)
            except Exception as exc:  # noqa: BLE001
                st.error(f"検索失敗: {exc}")
                candidates = []

            if use_regex:
                candidates = filter_by_regex(candidates, query)

            if not candidates:
                if has_cjk(query):
                    st.warning(
                        f"日本語の `{query}` では検索 API が反応しません。"
                        " **英語/ローマ字** で入力してください（例: トヨタ → `toyota`、任天堂 → `nintendo`）。"
                        " ローマ字が分からない場合は『✏️ ティッカー直接入力』タブで `7203.T` のように入れてください。"
                    )
                else:
                    st.info(
                        "候補が見つかりませんでした。スペル、または `XXXX.T` (東証) のような市場サフィックスを確認してください。"
                    )
            else:
                st.caption(f"{len(candidates)} 件ヒット")
                already = set(current)
                for c in candidates:
                    cols = st.columns([5, 1])
                    sec = f" · {c['sector']}" if c.get("sector") else ""
                    typ = f" [{c['type']}]" if c.get("type") else ""
                    cols[0].markdown(
                        f"**{c['symbol']}** — {c['name']}  \n"
                        f"<small>{c['exchange']}{sec}{typ}</small>",
                        unsafe_allow_html=True,
                    )
                    if c["symbol"] in already:
                        cols[1].caption("✓ 追加済")
                    elif cols[1].button("➕ 追加", key=f"add_{c['symbol']}"):
                        add_to_watchlist(c["symbol"])
                        st.rerun()

    # ── 直接入力タブ ──────────────────────────────────────
    with tab_direct:
        with st.form("direct_form", clear_on_submit=True):
            cols = st.columns([4, 1])
            new = cols[0].text_input(
                "Ticker",
                placeholder="例: AAPL / 7203.T / 446A.T",
                label_visibility="collapsed",
                help="米国はそのまま、東証は末尾 .T、香港は .HK、ロンドンは .L など",
            ).strip()
            add_btn = cols[1].form_submit_button("➕ 追加", type="primary")
        if add_btn and new:
            add_to_watchlist(new)
            st.rerun()

# ─── 一覧 (空 or 表示) ─────────────────────────────────────
tickers = get_watchlist()
if not tickers:
    st.info(
        """
        **ウォッチリストはまだ空です**。上の「➕ 銘柄を追加」から登録してください:

        - 🔍 **社名で検索** タブ — 例: `apple` / `northsand` / `トヨタ` と入力 → 候補から「➕ 追加」を押す
        - ✏️ **ティッカー直接入力** タブ — `AAPL`、`7203.T`、`446A.T` のようにコードを入れて「➕ 追加」

        追加した銘柄はブラウザの URL (`?w=...`) に保存されるので、ブックマークすれば再訪時も同じリストが復元されます。
        """
    )
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

    st.subheader("🗑️ 削除")
    cols = st.columns(min(len(rows), 5))
    for i, r in enumerate(rows):
        if cols[i % len(cols)].button(f"❌ {r['Ticker']}", key=f"del_{r['Ticker']}"):
            remove_from_watchlist(r["Ticker"])
            st.rerun()

if errors:
    with st.expander(f"⚠️ 取得失敗 ({len(errors)} 件)"):
        for e in errors:
            st.text(e)
