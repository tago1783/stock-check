"""yfinanceから株価データを取得する共通レイヤー。

CLI:
    python stock_data.py 7203.T AAPL MSFT --period 6mo --out prices.csv
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import yfinance as yf


@dataclass
class StockSnapshot:
    ticker: str
    name: str
    sector: Optional[str]
    currency: str
    market_cap: Optional[float]
    trailing_pe: Optional[float]
    history: pd.DataFrame  # OHLCV indexed by Date


def fetch_one(ticker: str, period: str = "6mo", interval: str = "1d") -> StockSnapshot:
    t = yf.Ticker(ticker)
    info = getattr(t, "info", {}) or {}
    hist = t.history(period=period, interval=interval).dropna(subset=["Close"])
    return StockSnapshot(
        ticker=ticker,
        name=info.get("longName") or info.get("shortName") or ticker,
        sector=info.get("sector"),
        currency=info.get("currency", ""),
        market_cap=info.get("marketCap"),
        trailing_pe=info.get("trailingPE"),
        history=hist,
    )


def fetch_many(tickers: list[str], period: str = "6mo", interval: str = "1d") -> dict[str, StockSnapshot]:
    out: dict[str, StockSnapshot] = {}
    for tk in tickers:
        try:
            out[tk] = fetch_one(tk, period=period, interval=interval)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] {tk}: {exc}", file=sys.stderr)
    return out


def to_long_dataframe(snapshots: dict[str, StockSnapshot]) -> pd.DataFrame:
    """全銘柄の履歴を ticker 列付きの long-format に結合。"""
    frames = []
    for tk, snap in snapshots.items():
        df = snap.history.copy()
        df.insert(0, "Ticker", tk)
        df.index.name = "Date"
        frames.append(df.reset_index())
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def main() -> int:
    p = argparse.ArgumentParser(description="Fetch multiple tickers via yfinance.")
    p.add_argument("tickers", nargs="+")
    p.add_argument("--period", default="6mo")
    p.add_argument("--interval", default="1d")
    p.add_argument("--out", help="Output CSV path (long format)")
    args = p.parse_args()

    snaps = fetch_many(args.tickers, period=args.period, interval=args.interval)

    print(f"{'Ticker':<10}{'Name':<35}{'Last Close':>12}{'Period %':>10}")
    print("-" * 67)
    for tk, s in snaps.items():
        if s.history.empty:
            print(f"{tk:<10}{(s.name or '')[:34]:<35}{'n/a':>12}{'n/a':>10}")
            continue
        last = s.history["Close"].iloc[-1]
        first = s.history["Close"].iloc[0]
        pct = (last - first) / first * 100
        print(f"{tk:<10}{s.name[:34]:<35}{last:>12.2f}{pct:>9.2f}%")

    if args.out:
        df = to_long_dataframe(snaps)
        df.to_csv(args.out, index=False)
        print(f"\nWrote {len(df)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
