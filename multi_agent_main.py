"""
Point d'entrée du système multi-agents TRADEX.
Orchestre 5 agents spécialisés pour chaque cycle d'analyse.
"""
import json
import time
import signal
from datetime import datetime, timezone
from pathlib import Path

from config import KRAKEN_SYMBOL, BINANCE_SYMBOL, LOOP_INTERVAL_SECONDS, PAPER_TRADING, PORTFOLIO_SIZE_USD, MAX_POSITION_PCT
from market_data import create_exchanges, get_market_data, format_market_data_for_prompt
from indicators import calculate_indicators
from analyzer import analyze_market
from logger import logger, PaperPortfolio
from agents import SentinelAgent, OracleAgent, ScoutAgent, NexusAgent

_running = True
OUTPUT_FILE = Path("agent_state.json")


def _handle_signal(signum, frame):
    global _running
    _running = False


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


def run_multi_agent_cycle(exchange, symbol: str, portfolio: PaperPortfolio, agents: dict) -> dict:
    logger.info(f"[MULTI-AGENT] Starting cycle for {symbol}")

    data = get_market_data(exchange, symbol)
    indicators = calculate_indicators(data["df"])
    summary = format_market_data_for_prompt(symbol, data["ticker"], indicators, data["orderbook"])

    # TRADEX — analyse technique principale
    logger.info(f"[TRADEX] Analyzing {symbol}...")
    tradex_result = analyze_market(symbol, summary)

    # SENTINEL — évaluation du risque
    logger.info(f"[SENTINEL] Evaluating risk for {symbol}...")
    portfolio_state = {
        "total_usd": PORTFOLIO_SIZE_USD,
        "positions": portfolio.positions,
        "cash": portfolio.cash,
    }
    sentinel_result = agents["sentinel"].evaluate(
        {"symbol": symbol, "price": data["ticker"]["last"], "volatility": "medium"},
        portfolio_state,
    )

    # ORACLE — sentiment macro
    logger.info(f"[ORACLE] Reading macro signals...")
    oracle_result = agents["oracle"].analyze(summary)

    # SCOUT — détection de patterns
    logger.info(f"[SCOUT] Scanning patterns for {symbol}...")
    ohlcv_rows = data["df"].tail(20).to_string()
    scout_result = agents["scout"].scan(symbol, ohlcv_rows, {
        "rsi": float(indicators.get("rsi", 50)),
        "macd": float(indicators.get("macd", 0)),
        "ema_20": float(indicators.get("ema_20", 0)),
        "ema_50": float(indicators.get("ema_50", 0)),
    })

    # NEXUS — orchestration finale
    logger.info(f"[NEXUS] Orchestrating final decision...")
    nexus_result = agents["nexus"].orchestrate(symbol, {
        "TRADEX": tradex_result,
        "SENTINEL": sentinel_result,
        "ORACLE": oracle_result,
        "SCOUT": scout_result,
    })

    cycle_output = {
        "symbol": symbol,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "price": data["ticker"]["last"],
        "agents": {
            "TRADEX": tradex_result,
            "SENTINEL": sentinel_result,
            "ORACLE": oracle_result,
            "SCOUT": scout_result,
            "NEXUS": nexus_result,
        },
    }

    # Sauvegarde pour le dashboard
    state = {}
    if OUTPUT_FILE.exists():
        state = json.loads(OUTPUT_FILE.read_text())
    state[symbol] = cycle_output
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    OUTPUT_FILE.write_text(json.dumps(state, indent=2, default=str))

    logger.info(f"[NEXUS] Final: {nexus_result.get('final_action')} | Confidence: {nexus_result.get('final_confidence', 0):.0%}")
    return cycle_output


def run():
    logger.info("=" * 60)
    logger.info("TRADEX Multi-Agent System starting")
    logger.info("Agents: TRADEX · SENTINEL · ORACLE · SCOUT · NEXUS")
    logger.info("=" * 60)

    kraken, binance = create_exchanges()
    portfolio = PaperPortfolio(PORTFOLIO_SIZE_USD, MAX_POSITION_PCT)

    agents = {
        "sentinel": SentinelAgent(),
        "oracle": OracleAgent(),
        "scout": ScoutAgent(),
        "nexus": NexusAgent(),
    }

    assets = [(kraken, KRAKEN_SYMBOL), (binance, BINANCE_SYMBOL)]

    while _running:
        cycle_start = datetime.now(timezone.utc)
        logger.info(f"--- Cycle {cycle_start.strftime('%Y-%m-%d %H:%M:%S UTC')} ---")

        for exchange, symbol in assets:
            if not _running:
                break
            try:
                run_multi_agent_cycle(exchange, symbol, portfolio, agents)
            except Exception as e:
                logger.error(f"Error in multi-agent cycle for {symbol}: {e}", exc_info=True)

        elapsed = (datetime.now(timezone.utc) - cycle_start).total_seconds()
        sleep_secs = max(0, LOOP_INTERVAL_SECONDS - elapsed)
        logger.info(f"Cycle done in {elapsed:.1f}s. Next in {sleep_secs:.0f}s.")

        deadline = time.time() + sleep_secs
        while _running and time.time() < deadline:
            time.sleep(min(5, deadline - time.time()))

    logger.info("Multi-agent system shutdown.")


if __name__ == "__main__":
    run()
