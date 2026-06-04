"""
SENTINEL — Agent de gestion du risque.
Analyse l'exposition du portefeuille, les drawdowns et la volatilité
pour imposer des limites de position strictes.
"""
import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

SENTINEL_SYSTEM = """You are SENTINEL, a crypto risk management AI agent.
Your sole purpose is to evaluate portfolio risk and position safety.

Focus areas:
- Portfolio exposure and concentration risk
- Drawdown limits (max 15% portfolio drawdown)
- Volatility-adjusted position sizing
- Correlation risk between held assets
- Liquidation risk for leveraged positions

Always respond with a JSON object containing:
- risk_score: 0-100 (0=no risk, 100=extreme risk)
- max_position_pct: recommended maximum position size (0-100)
- warnings: list of active risk warnings
- recommendation: REDUCE | HOLD | INCREASE
- reasoning_steps: list of 3-5 reasoning steps you followed
"""


class SentinelAgent:
    name = "SENTINEL"
    role = "Gestionnaire du Risque"
    emoji = "🛡️"

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def evaluate(self, market_data: dict, portfolio: dict) -> dict:
        prompt = f"""Evaluate risk for this portfolio state:

Portfolio: {json.dumps(portfolio, indent=2)}
Market data summary: {json.dumps(market_data, indent=2)}

Provide your risk assessment."""

        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            thinking={"type": "enabled", "budget_tokens": 2000},
            system=SENTINEL_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        thinking = next((b.thinking for b in response.content if b.type == "thinking"), "")
        text = next((b.text for b in response.content if b.type == "text"), "{}")

        result = json.loads(text)
        result["_thinking"] = thinking
        result["_agent"] = self.name
        return result
