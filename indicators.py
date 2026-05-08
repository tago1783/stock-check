"""シンプルなテクニカル指標。SMA / EMA / RSI / MACD / Bollinger。"""
from __future__ import annotations

import pandas as pd


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window=window, min_periods=window).mean()


def ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"MACD": macd_line, "Signal": signal_line, "Hist": hist})


def bollinger(close: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    mid = sma(close, window)
    std = close.rolling(window=window, min_periods=window).std()
    return pd.DataFrame({
        "BB_Mid": mid,
        "BB_Upper": mid + num_std * std,
        "BB_Lower": mid - num_std * std,
    })


def add_indicators(history: pd.DataFrame) -> pd.DataFrame:
    """OHLCV DataFrame に主要指標列を付加。"""
    if history.empty:
        return history.copy()
    close = history["Close"]
    out = history.copy()
    out["SMA_20"] = sma(close, 20)
    out["SMA_50"] = sma(close, 50)
    out["EMA_12"] = ema(close, 12)
    out["EMA_26"] = ema(close, 26)
    out["RSI_14"] = rsi(close, 14)
    out = out.join(macd(close))
    out = out.join(bollinger(close))
    return out


def latest_summary(history_with_ind: pd.DataFrame) -> dict:
    """最終行から見やすい辞書を作る。"""
    if history_with_ind.empty:
        return {}
    last = history_with_ind.iloc[-1]
    close = last["Close"]
    sma20, sma50 = last.get("SMA_20"), last.get("SMA_50")
    rsi14 = last.get("RSI_14")
    macd_v, sig_v = last.get("MACD"), last.get("Signal")

    trend_signals = []
    if pd.notna(sma20) and pd.notna(sma50):
        trend_signals.append("uptrend" if sma20 > sma50 else "downtrend")
    if pd.notna(rsi14):
        if rsi14 >= 70:
            trend_signals.append("overbought")
        elif rsi14 <= 30:
            trend_signals.append("oversold")
    if pd.notna(macd_v) and pd.notna(sig_v):
        trend_signals.append("macd_bullish" if macd_v > sig_v else "macd_bearish")

    return {
        "close": float(close),
        "sma_20": None if pd.isna(sma20) else float(sma20),
        "sma_50": None if pd.isna(sma50) else float(sma50),
        "rsi_14": None if pd.isna(rsi14) else float(rsi14),
        "macd": None if pd.isna(macd_v) else float(macd_v),
        "macd_signal": None if pd.isna(sig_v) else float(sig_v),
        "signals": trend_signals,
    }
