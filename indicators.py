import numpy as np
import pandas as pd


def safe_float(value, default=0.0):
    try:
        f = float(value)
        return default if np.isnan(f) else f
    except (TypeError, ValueError):
        return default


def calculate_indicators(df: pd.DataFrame) -> dict:
    df = df.copy()

    df.ta.rsi(length=14, append=True)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    df.ta.ema(length=20, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.ema(length=200, append=True)
    df.ta.sma(length=20, close="volume", prefix="VOL", append=True)

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last

    return {
        "rsi_14": safe_float(last.get("RSI_14")),
        "prev_rsi": safe_float(prev.get("RSI_14")),
        "macd": safe_float(last.get("MACD_12_26_9")),
        "macd_signal": safe_float(last.get("MACDs_12_26_9")),
        "macd_histogram": safe_float(last.get("MACDh_12_26_9")),
        "prev_macd_histogram": safe_float(prev.get("MACDh_12_26_9")),
        "ema_20": safe_float(last.get("EMA_20")),
        "ema_50": safe_float(last.get("EMA_50")),
        "ema_200": safe_float(last.get("EMA_200")),
        "volume": safe_float(last.get("volume")),
        "volume_sma20": safe_float(last.get("VOL_SMA_20")),
        "close": safe_float(last.get("close")),
        "high_24h": safe_float(df["high"].tail(24).max()),
        "low_24h": safe_float(df["low"].tail(24).min()),
        "price_change_24h": safe_float(
            (last["close"] - df.iloc[-24]["close"]) / df.iloc[-24]["close"] * 100
            if len(df) >= 24 else 0.0
        ),
    }
