"""Claude API による投資判断ドラフト生成。

⚠️ 教育・試作目的。実際の投資判断は本人の責任で行ってください。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

import anthropic

from indicators import add_indicators, latest_summary
from stock_data import StockSnapshot

MODEL = "claude-opus-4-7"

SYSTEM_PROMPT = """あなたは経験豊富な金融アナリストのアシスタントです。
ユーザーから渡される個別株の価格履歴とテクニカル指標を読み取り、
日本語で以下の構造の投資判断ドラフトを返してください。

# 判断: <BUY / HOLD / SELL のいずれか>
# 確信度: <Low / Medium / High>

## 短期トレンド (1–4週)
- ...

## 中期トレンド (1–6ヶ月)
- ...

## テクニカル根拠
- 移動平均 (SMA20/SMA50)、RSI、MACD のうち主要な3点に絞る
- 数値は具体的に引用 (例: RSI=31.5)

## リスク・反対材料
- ...

## 注意事項
- このドラフトは参考情報であり投資助言ではない旨を最後に1行で明記する

Markdown で簡潔に。各セクション3〜5行以内。憶測の数値は出さず、与えられた情報のみから語ること。"""


@dataclass
class Advice:
    text: str
    cache_read_tokens: int
    cache_creation_tokens: int
    input_tokens: int
    output_tokens: int


def _build_user_prompt(snapshot: StockSnapshot) -> str:
    ind = add_indicators(snapshot.history)
    summary = latest_summary(ind)
    tail = ind[["Close", "SMA_20", "SMA_50", "RSI_14", "MACD", "Signal"]].tail(20)
    payload = {
        "ticker": snapshot.ticker,
        "name": snapshot.name,
        "sector": snapshot.sector,
        "currency": snapshot.currency,
        "market_cap": snapshot.market_cap,
        "trailing_pe": snapshot.trailing_pe,
        "latest": summary,
        "recent_20_rows": [
            {"date": str(idx.date()), **{k: (None if v != v else round(v, 4)) for k, v in row.items()}}
            for idx, row in tail.iterrows()
        ],
    }
    return (
        "次の銘柄について投資判断ドラフトを書いてください:\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, default=str, indent=2)}\n```"
    )


def advise(snapshot: StockSnapshot, *, client: anthropic.Anthropic | None = None) -> Advice:
    if client is None:
        client = anthropic.Anthropic()

    user_text = _build_user_prompt(snapshot)

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_text}],
    )

    text = "".join(b.text for b in response.content if b.type == "text")
    u = response.usage
    return Advice(
        text=text,
        cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
        cache_creation_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
        input_tokens=u.input_tokens,
        output_tokens=u.output_tokens,
    )


def main() -> int:
    import argparse
    from stock_data import fetch_one

    p = argparse.ArgumentParser(description="Generate AI investment advice draft.")
    p.add_argument("ticker")
    p.add_argument("--period", default="6mo")
    args = p.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Set it before running this command.")
        return 1

    snap = fetch_one(args.ticker, period=args.period)
    if snap.history.empty:
        print(f"No history for {args.ticker}.")
        return 1

    advice = advise(snap)
    print(advice.text)
    print()
    print(
        f"[usage] in={advice.input_tokens} out={advice.output_tokens} "
        f"cache_read={advice.cache_read_tokens} cache_write={advice.cache_creation_tokens}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
