"""Claude API による3軸投資判断（ファンダメンタル / テクニカル / センチメント）。

⚠️ 教育・試作目的。投資助言ではありません。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import anthropic
import yfinance as yf

from indicators import add_indicators, latest_summary
from stock_data import StockSnapshot

MODEL = "claude-opus-4-7"

SYSTEM_PROMPT = """あなたは経験豊富な金融アナリストです。
渡された個別株のデータをもとに、以下の3つの観点から客観的に評価し、最終的な売買判断を出してください。

# 観点
1. ファンダメンタルズ — バリュエーション (PER/PBR等)、収益性 (ROE/利益率)、成長性、財務指標、配当
2. テクニカル — トレンド (移動平均の関係)、モメンタム (RSI/MACD)、過熱感、ボリンジャー
3. センチメント — 提供された最新ニュースのトーン、市場の関心、懸念材料

# ルール
- 与えられた数値・事実のみから論じ、推測の数値は出さない
- 各観点で「強気要因 (bullish)」と「弱気要因 (bearish)」を箇条書きで列挙し、最後に1〜2文の総括を付ける
- 強気・弱気それぞれ 1〜4 項目。該当がなければ空配列でよい
- 各項目は数値や指標名を引用して具体的に (例: "RSI=31 で売られすぎ圏")
- 総合判断は BUY / HOLD / SELL のいずれか、確信度は Low / Medium / High
- rationale には総合的な論拠と、上振れ/下振れの主要リスクを 3〜5 文で書く
- 投資助言ではない旨に触れる必要はない (UIで明示するため)
- 全ての出力は日本語"""


# JSON Schema (Anthropic structured outputs)
OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "confidence", "fundamentals", "technical", "sentiment", "rationale"],
    "properties": {
        "verdict": {"type": "string", "enum": ["BUY", "HOLD", "SELL"]},
        "confidence": {"type": "string", "enum": ["Low", "Medium", "High"]},
        "fundamentals": {
            "type": "object",
            "additionalProperties": False,
            "required": ["bullish", "bearish", "summary"],
            "properties": {
                "bullish": {"type": "array", "items": {"type": "string"}},
                "bearish": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"},
            },
        },
        "technical": {
            "type": "object",
            "additionalProperties": False,
            "required": ["bullish", "bearish", "summary"],
            "properties": {
                "bullish": {"type": "array", "items": {"type": "string"}},
                "bearish": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"},
            },
        },
        "sentiment": {
            "type": "object",
            "additionalProperties": False,
            "required": ["bullish", "bearish", "summary"],
            "properties": {
                "bullish": {"type": "array", "items": {"type": "string"}},
                "bearish": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"},
            },
        },
        "rationale": {"type": "string"},
    },
}


@dataclass
class Advice:
    verdict: str
    confidence: str
    fundamentals: dict[str, Any]
    technical: dict[str, Any]
    sentiment: dict[str, Any]
    rationale: str
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


# ─── データ収集 ────────────────────────────────────────────
_FUND_KEYS = [
    "marketCap", "trailingPE", "forwardPE", "priceToBook", "trailingEps",
    "beta", "dividendYield", "payoutRatio",
    "totalRevenue", "netIncomeToCommon", "revenueGrowth", "earningsGrowth",
    "returnOnEquity", "returnOnAssets", "grossMargins", "operatingMargins",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "currentPrice",
    "sector", "industry", "fullTimeEmployees", "currency",
]


def _collect_fundamentals(ticker: str) -> dict[str, Any]:
    info = getattr(yf.Ticker(ticker), "info", {}) or {}
    return {k: info.get(k) for k in _FUND_KEYS if info.get(k) is not None}


def _collect_news(ticker: str, limit: int = 8) -> list[dict[str, str]]:
    raw = yf.Ticker(ticker).news or []
    out = []
    for item in raw[:limit]:
        if "content" in item and isinstance(item["content"], dict):
            c = item["content"]
            out.append({
                "title": c.get("title", "") or "",
                "summary": (c.get("summary") or c.get("description") or "")[:400],
                "publisher": (c.get("provider") or {}).get("displayName", "") or "",
                "pub_date": c.get("pubDate", "") or "",
            })
        else:
            ts = item.get("providerPublishTime")
            pub = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else ""
            out.append({
                "title": item.get("title", "") or "",
                "summary": (item.get("summary") or "")[:400],
                "publisher": item.get("publisher", "") or "",
                "pub_date": pub,
            })
    return [n for n in out if n["title"]]


def _build_user_prompt(snapshot: StockSnapshot, news: list[dict], fund: dict) -> str:
    ind = add_indicators(snapshot.history)
    summary = latest_summary(ind)
    tail = ind[["Close", "SMA_20", "SMA_50", "RSI_14", "MACD", "Signal"]].tail(20)
    payload = {
        "ticker": snapshot.ticker,
        "name": snapshot.name,
        "fundamentals": fund,
        "technical_latest": summary,
        "technical_recent_20": [
            {
                "date": str(idx.date()),
                **{k: (None if v != v else round(v, 4)) for k, v in row.items()},
            }
            for idx, row in tail.iterrows()
        ],
        "recent_news": news,
    }
    return (
        "次の銘柄を3軸 (ファンダメンタル/テクニカル/センチメント) でレビューし、"
        "売買判断を JSON で返してください:\n\n"
        f"```json\n{json.dumps(payload, ensure_ascii=False, default=str, indent=2)}\n```"
    )


# ─── メインAPI ────────────────────────────────────────────
def advise(snapshot: StockSnapshot, *, api_key: str | None = None) -> Advice:
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    fund = _collect_fundamentals(snapshot.ticker)
    news = _collect_news(snapshot.ticker)
    user_text = _build_user_prompt(snapshot, news, fund)

    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
        },
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_text}],
    )

    text = next((b.text for b in response.content if b.type == "text"), "")
    data = json.loads(text)
    u = response.usage
    return Advice(
        verdict=data["verdict"],
        confidence=data["confidence"],
        fundamentals=data["fundamentals"],
        technical=data["technical"],
        sentiment=data["sentiment"],
        rationale=data["rationale"],
        cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
        cache_creation_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
        input_tokens=u.input_tokens,
        output_tokens=u.output_tokens,
        raw=data,
    )


def main() -> int:
    import argparse
    from stock_data import fetch_one

    p = argparse.ArgumentParser(description="3-axis AI investment review (BUY/HOLD/SELL).")
    p.add_argument("ticker")
    p.add_argument("--period", default="6mo")
    args = p.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set.")
        return 1

    snap = fetch_one(args.ticker, period=args.period)
    if snap.history.empty:
        print(f"No history for {args.ticker}.")
        return 1

    advice = advise(snap)
    print(f"\n=== {advice.verdict} (confidence: {advice.confidence}) ===\n")
    for axis_name, axis in [
        ("ファンダメンタル", advice.fundamentals),
        ("テクニカル", advice.technical),
        ("センチメント", advice.sentiment),
    ]:
        print(f"## {axis_name}")
        for b in axis.get("bullish", []):
            print(f"  + {b}")
        for b in axis.get("bearish", []):
            print(f"  - {b}")
        print(f"  → {axis.get('summary', '')}\n")
    print("## 総合論拠")
    print(advice.rationale)
    print(
        f"\n[usage] in={advice.input_tokens} out={advice.output_tokens} "
        f"cache_read={advice.cache_read_tokens}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
