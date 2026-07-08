# TRADEX Crypto Trading Bot

Automated crypto trading bot that pulls OHLCV/orderbook data from Kraken and Binance via `ccxt`, computes technical indicators, and asks Claude to produce a structured BUY/SELL/HOLD trading decision on a fixed interval loop (paper trading by default).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in ANTHROPIC_API_KEY
python main.py
```

## Optional: TradingView Desktop pairing (MCP)

This repo ships a `.mcp.json` that wires up [`tradingview-mcp`](https://github.com/tradesdontlie/tradingview-mcp) for **interactive** use inside Claude Code — it is not called by the automated bot loop (`main.py`), since it requires a real, locally running TradingView Desktop app.

To use it:

1. Install TradingView Desktop and launch it with remote debugging enabled:
   ```bash
   # macOS example
   open -a "TradingView" --args --remote-debugging-port=9222
   ```
2. Open this project in Claude Code — the `tradingview` MCP server (run via `npx -y tradingview-mcp`) starts automatically and connects over Chrome DevTools Protocol on port 9222.
3. Ask Claude things like "switch the chart to BTCUSD 1h" or "read the current RSI/MACD values" while reviewing TRADEX's decisions manually on the chart.

No API keys are needed for the MCP server — everything happens locally on your machine.
