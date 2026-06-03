import logging
import os
import json
from datetime import datetime, timezone
from config import LOG_DIR, LOG_LEVEL


def setup_logger(name: str = "tradex") -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        console = logging.StreamHandler()
        console.setFormatter(fmt)
        logger.addHandler(console)

        log_file = os.path.join(LOG_DIR, f"tradex_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log")
        fh = logging.FileHandler(log_file)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


logger = setup_logger()


def log_decision(decision: dict) -> None:
    meta = decision.get("_meta", {})
    cache_note = ""
    if meta.get("cache_read_tokens"):
        cache_note = f" [cache hit: {meta['cache_read_tokens']} tokens]"
    elif meta.get("cache_created_tokens"):
        cache_note = f" [cache write: {meta['cache_created_tokens']} tokens]"

    logger.info(
        f"DECISION | {decision['asset']} | {decision['action']} | "
        f"confidence={decision['confidence']:.0%} | regime={decision['market_regime']} | "
        f"risk={decision['risk_level']} | entry={decision['entry_price']:.4f} | "
        f"sl={decision['stop_loss']:.4f} | tp={decision['take_profit']:.4f} | "
        f"size={decision['position_size_pct']:.1f}%{cache_note}"
    )
    logger.info(f"RATIONALE | {decision['asset']} | {decision['rationale']}")
    logger.info(f"SIGNALS   | {decision['asset']} | {' | '.join(decision['key_signals'])}")


class PaperPortfolio:
    def __init__(self, initial_balance: float, max_position_pct: float):
        self.cash = initial_balance
        self.initial_balance = initial_balance
        self.max_position_pct = max_position_pct
        self.positions: dict = {}
        self.trade_history: list = []

    def execute_decision(self, decision: dict, current_price: float) -> dict | None:
        asset = decision["asset"]
        action = decision["action"]

        if action == "BUY":
            if asset in self.positions:
                logger.info(f"PAPER | {asset} | Already in position, skipping BUY")
                return None

            alloc_pct = min(decision["position_size_pct"], self.max_position_pct) / 100
            alloc_usd = self.cash * alloc_pct
            if alloc_usd < 10:
                logger.info(f"PAPER | {asset} | Insufficient cash for BUY")
                return None

            quantity = alloc_usd / current_price
            self.cash -= alloc_usd
            self.positions[asset] = {
                "quantity": quantity,
                "entry_price": current_price,
                "entry_time": datetime.now(timezone.utc).isoformat(),
                "stop_loss": decision["stop_loss"],
                "take_profit": decision["take_profit"],
                "allocated_usd": alloc_usd,
            }
            trade = {
                "time": datetime.now(timezone.utc).isoformat(),
                "asset": asset,
                "action": "BUY",
                "price": current_price,
                "quantity": quantity,
                "value_usd": alloc_usd,
                "portfolio_value": self.total_value({asset: current_price}),
            }
            self.trade_history.append(trade)
            logger.info(
                f"PAPER | BUY  | {asset} | qty={quantity:.6f} | price={current_price:.4f} | "
                f"value=${alloc_usd:.2f} | cash_remaining=${self.cash:.2f}"
            )
            return trade

        elif action == "SELL":
            if asset not in self.positions:
                logger.info(f"PAPER | {asset} | No position to SELL")
                return None

            pos = self.positions.pop(asset)
            proceeds = pos["quantity"] * current_price
            pnl = proceeds - pos["allocated_usd"]
            pnl_pct = pnl / pos["allocated_usd"] * 100
            self.cash += proceeds
            trade = {
                "time": datetime.now(timezone.utc).isoformat(),
                "asset": asset,
                "action": "SELL",
                "price": current_price,
                "quantity": pos["quantity"],
                "value_usd": proceeds,
                "pnl_usd": pnl,
                "pnl_pct": pnl_pct,
                "portfolio_value": self.total_value(),
            }
            self.trade_history.append(trade)
            logger.info(
                f"PAPER | SELL | {asset} | qty={pos['quantity']:.6f} | price={current_price:.4f} | "
                f"pnl=${pnl:+.2f} ({pnl_pct:+.2f}%) | cash=${self.cash:.2f}"
            )
            return trade

        else:
            logger.info(f"PAPER | HOLD | {asset} | No action taken")
            return None

    def total_value(self, current_prices: dict | None = None) -> float:
        position_value = sum(
            pos["quantity"] * (current_prices.get(asset, pos["entry_price"]) if current_prices else pos["entry_price"])
            for asset, pos in self.positions.items()
        )
        return self.cash + position_value

    def summary(self, current_prices: dict | None = None) -> str:
        total = self.total_value(current_prices)
        pnl = total - self.initial_balance
        pnl_pct = pnl / self.initial_balance * 100
        lines = [
            f"Portfolio: ${total:.2f} (PnL: ${pnl:+.2f} / {pnl_pct:+.2f}%)",
            f"Cash: ${self.cash:.2f}",
        ]
        for asset, pos in self.positions.items():
            price = (current_prices or {}).get(asset, pos["entry_price"])
            pos_value = pos["quantity"] * price
            pos_pnl = pos_value - pos["allocated_usd"]
            lines.append(f"  {asset}: qty={pos['quantity']:.6f} @ {pos['entry_price']:.4f} | value=${pos_value:.2f} | pnl=${pos_pnl:+.2f}")
        return " | ".join(lines)
