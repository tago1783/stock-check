"""yfinanceから株価データを取得するモック。

使い方:
    python fetch_stock.py 7203.T          # トヨタ (東証)
    python fetch_stock.py AAPL            # Apple (米国)
    python fetch_stock.py 7203.T --period 1mo --interval 1d
"""
import argparse
import sys

import yfinance as yf


def fetch(ticker: str, period: str, interval: str) -> None:
    t = yf.Ticker(ticker)

    print(f"=== {ticker} ===")

    info = getattr(t, "info", {}) or {}
    name = info.get("longName") or info.get("shortName") or "(name unavailable)"
    currency = info.get("currency", "")
    market_cap = info.get("marketCap")
    pe = info.get("trailingPE")
    sector = info.get("sector")

    print(f"Name        : {name}")
    if sector:
        print(f"Sector      : {sector}")
    if market_cap:
        print(f"Market Cap  : {market_cap:,} {currency}")
    if pe:
        print(f"Trailing PE : {pe:.2f}")

    hist = t.history(period=period, interval=interval).dropna(subset=["Close"])
    if hist.empty:
        print("No price history returned.")
        return

    print(f"\nPrice history (period={period}, interval={interval}):")
    print(hist.tail(10).to_string())

    last = hist.iloc[-1]
    first = hist.iloc[0]
    change = (last["Close"] - first["Close"]) / first["Close"] * 100
    print(
        f"\nLatest close: {last['Close']:.2f} {currency}"
        f"  |  Change over period: {change:+.2f}%"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch stock data via yfinance.")
    parser.add_argument("ticker", help="Ticker symbol, e.g. 7203.T or AAPL")
    parser.add_argument("--period", default="1mo",
                        help="1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max (default: 1mo)")
    parser.add_argument("--interval", default="1d",
                        help="1m,5m,15m,30m,60m,1h,1d,1wk,1mo (default: 1d)")
    args = parser.parse_args()

    try:
        fetch(args.ticker, args.period, args.interval)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
