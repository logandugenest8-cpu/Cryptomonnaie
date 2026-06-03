import ccxt
import pandas as pd
from config import OHLCV_TIMEFRAME, OHLCV_LIMIT


def create_exchanges():
    kraken = ccxt.kraken({"enableRateLimit": True})
    binance = ccxt.binance({"enableRateLimit": True})
    return kraken, binance


def fetch_ohlcv(exchange: ccxt.Exchange, symbol: str, timeframe: str = OHLCV_TIMEFRAME, limit: int = OHLCV_LIMIT) -> pd.DataFrame:
    raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


def fetch_ticker(exchange: ccxt.Exchange, symbol: str) -> dict:
    ticker = exchange.fetch_ticker(symbol)
    return {
        "last": ticker.get("last"),
        "bid": ticker.get("bid"),
        "ask": ticker.get("ask"),
        "high": ticker.get("high"),
        "low": ticker.get("low"),
        "volume": ticker.get("baseVolume"),
        "change_pct": ticker.get("percentage"),
    }


def fetch_orderbook(exchange: ccxt.Exchange, symbol: str, limit: int = 10) -> dict:
    ob = exchange.fetch_order_book(symbol, limit=limit)
    return {
        "bids": ob["bids"][:limit],
        "asks": ob["asks"][:limit],
    }


def get_market_data(exchange: ccxt.Exchange, symbol: str) -> dict:
    df = fetch_ohlcv(exchange, symbol)
    ticker = fetch_ticker(exchange, symbol)
    orderbook = fetch_orderbook(exchange, symbol)
    return {"df": df, "ticker": ticker, "orderbook": orderbook}


def format_market_data_for_prompt(symbol: str, ticker: dict, indicators: dict, orderbook: dict) -> str:
    bid_wall = max(orderbook["bids"], key=lambda x: x[1]) if orderbook["bids"] else [0, 0]
    ask_wall = min(orderbook["asks"], key=lambda x: x[1]) if orderbook["asks"] else [0, 0]
    bid_total = sum(b[1] for b in orderbook["bids"])
    ask_total = sum(a[1] for a in orderbook["asks"])
    imbalance = (bid_total - ask_total) / (bid_total + ask_total) * 100 if (bid_total + ask_total) > 0 else 0

    volume_ratio = (
        indicators["volume"] / indicators["volume_sma20"]
        if indicators["volume_sma20"] > 0 else 1.0
    )

    spread = ticker["ask"] - ticker["bid"] if ticker["ask"] and ticker["bid"] else 0
    spread_pct = spread / ticker["last"] * 100 if ticker["last"] else 0

    return f"""=== {symbol} MARKET DATA ===

PRICE ACTION:
  Current Price: {ticker['last']:.4f}
  Bid: {ticker['bid']:.4f} | Ask: {ticker['ask']:.4f}
  Spread: {spread:.4f} ({spread_pct:.3f}%)
  24h High: {indicators['high_24h']:.4f} | 24h Low: {indicators['low_24h']:.4f}
  24h Change: {indicators['price_change_24h']:+.2f}%

TECHNICAL INDICATORS:
  RSI(14): {indicators['rsi_14']:.2f} (prev: {indicators['prev_rsi']:.2f})
  MACD: {indicators['macd']:.4f} | Signal: {indicators['macd_signal']:.4f} | Histogram: {indicators['macd_histogram']:.4f} (prev: {indicators['prev_macd_histogram']:.4f})
  EMA_20: {indicators['ema_20']:.4f}
  EMA_50: {indicators['ema_50']:.4f}
  EMA_200: {indicators['ema_200']:.4f}
  Price vs EMA_20: {((ticker['last'] / indicators['ema_20'] - 1) * 100) if indicators['ema_20'] else 0:+.2f}%
  Price vs EMA_50: {((ticker['last'] / indicators['ema_50'] - 1) * 100) if indicators['ema_50'] else 0:+.2f}%
  Price vs EMA_200: {((ticker['last'] / indicators['ema_200'] - 1) * 100) if indicators['ema_200'] else 0:+.2f}%

VOLUME:
  Current Volume: {indicators['volume']:.2f}
  Volume SMA(20): {indicators['volume_sma20']:.2f}
  Volume Ratio: {volume_ratio:.2f}x average

ORDER BOOK (top 10):
  Bid/Ask Imbalance: {imbalance:+.1f}% ({'buy pressure' if imbalance > 0 else 'sell pressure'})
  Largest Bid Wall: {bid_wall[0]:.4f} ({bid_wall[1]:.4f} units)
  Largest Ask Wall: {ask_wall[0]:.4f} ({ask_wall[1]:.4f} units)
  Top 3 Bids: {', '.join(f"{b[0]:.2f}@{b[1]:.3f}" for b in orderbook['bids'][:3])}
  Top 3 Asks: {', '.join(f"{a[0]:.2f}@{a[1]:.3f}" for a in orderbook['asks'][:3])}
"""
