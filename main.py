import signal
import sys
import time
from datetime import datetime, timezone

from config import (
    KRAKEN_SYMBOL, BINANCE_SYMBOL, LOOP_INTERVAL_SECONDS,
    PAPER_TRADING, PORTFOLIO_SIZE_USD, MAX_POSITION_PCT,
)
from market_data import create_exchanges, get_market_data, format_market_data_for_prompt
from indicators import calculate_indicators
from analyzer import analyze_market
from logger import logger, log_decision, PaperPortfolio

_running = True


def _handle_signal(signum, frame):
    global _running
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    _running = False


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


def analyze_asset(exchange, symbol: str, portfolio: PaperPortfolio) -> dict | None:
    logger.info(f"Fetching market data for {symbol}...")
    data = get_market_data(exchange, symbol)
    indicators = calculate_indicators(data["df"])
    summary = format_market_data_for_prompt(symbol, data["ticker"], indicators, data["orderbook"])

    logger.info(f"Sending {symbol} data to TRADEX for analysis...")
    decision = analyze_market(symbol, summary)
    log_decision(decision)

    if PAPER_TRADING:
        current_price = data["ticker"]["last"]
        portfolio.execute_decision(decision, current_price)

    return decision


def run():
    logger.info("=" * 60)
    logger.info("TRADEX Crypto Trading Bot starting up")
    logger.info(f"Mode: {'PAPER TRADING' if PAPER_TRADING else 'LIVE TRADING'}")
    logger.info(f"Assets: {KRAKEN_SYMBOL} (Kraken), {BINANCE_SYMBOL} (Binance)")
    logger.info(f"Loop interval: {LOOP_INTERVAL_SECONDS}s")
    logger.info("=" * 60)

    kraken, binance = create_exchanges()
    portfolio = PaperPortfolio(PORTFOLIO_SIZE_USD, MAX_POSITION_PCT)

    assets = [
        (kraken, KRAKEN_SYMBOL),
        (binance, BINANCE_SYMBOL),
    ]

    while _running:
        cycle_start = datetime.now(timezone.utc)
        logger.info(f"--- Analysis cycle starting at {cycle_start.strftime('%Y-%m-%d %H:%M:%S UTC')} ---")

        current_prices = {}
        for exchange, symbol in assets:
            if not _running:
                break
            try:
                decision = analyze_asset(exchange, symbol, portfolio)
                if decision:
                    current_prices[symbol] = decision["entry_price"]
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)

        if PAPER_TRADING and current_prices:
            logger.info(f"PORTFOLIO | {portfolio.summary(current_prices)}")

        if not _running:
            break

        elapsed = (datetime.now(timezone.utc) - cycle_start).total_seconds()
        sleep_secs = max(0, LOOP_INTERVAL_SECONDS - elapsed)
        logger.info(f"Cycle complete in {elapsed:.1f}s. Next cycle in {sleep_secs:.0f}s.")

        deadline = time.time() + sleep_secs
        while _running and time.time() < deadline:
            time.sleep(min(5, deadline - time.time()))

    logger.info("TRADEX shutdown complete.")


if __name__ == "__main__":
    run()
