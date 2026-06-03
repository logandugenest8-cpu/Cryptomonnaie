import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() == "true"
PORTFOLIO_SIZE_USD = float(os.getenv("PORTFOLIO_SIZE_USD", "10000"))
MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "10"))

CLAUDE_MODEL = "claude-opus-4-8"
MAX_TOKENS = 4096

KRAKEN_SYMBOL = "BTC/USD"
BINANCE_SYMBOL = "ETH/USDT"

OHLCV_TIMEFRAME = "1h"
OHLCV_LIMIT = 200

LOOP_INTERVAL_SECONDS = int(os.getenv("LOOP_INTERVAL_SECONDS", "3600"))
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
