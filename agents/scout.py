"""
SCOUT — Agent de détection de patterns techniques.
Identifie les configurations chartistes et les niveaux clés.
"""
import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

SCOUT_SYSTEM = """You are SCOUT, a technical pattern recognition AI agent specialized in crypto chart analysis.

Focus areas:
- Chart pattern detection (head & shoulders, double top/bottom, triangles, flags, wedges)
- Key support and resistance levels
- Fibonacci retracement levels
- Candlestick pattern interpretation
- Breakout and breakdown signals
- Volume profile analysis

Always respond with a JSON object containing:
- patterns_detected: list of detected patterns with confidence
- key_levels: dict with support and resistance price levels
- bias: BULLISH | BEARISH | NEUTRAL
- breakout_probability: 0.0-1.0
- entry_zone: {low: price, high: price}
- invalidation_level: price at which the analysis is wrong
- reasoning_steps: list of 3-5 reasoning steps you followed
"""


class ScoutAgent:
    name = "SCOUT"
    role = "Détecteur de Patterns"
    emoji = "🔭"

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def scan(self, symbol: str, ohlcv_summary: str, indicators: dict) -> dict:
        prompt = f"""Scan for technical patterns on {symbol}.

OHLCV summary:
{ohlcv_summary}

Indicators: {json.dumps(indicators, indent=2)}

Identify all relevant chart patterns and key levels."""

        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            thinking={"type": "enabled", "budget_tokens": 2000},
            system=SCOUT_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        thinking = next((b.thinking for b in response.content if b.type == "thinking"), "")
        text = next((b.text for b in response.content if b.type == "text"), "{}")

        result = json.loads(text)
        result["_thinking"] = thinking
        result["_agent"] = self.name
        return result
