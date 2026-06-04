"""
ORACLE — Agent d'analyse macro et sentiment.
Surveille les tendances macro, la peur/cupidité et les narratifs du marché.
"""
import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

ORACLE_SYSTEM = """You are ORACLE, a crypto macro and sentiment analysis AI agent.
You interpret broader market conditions, news sentiment, and on-chain signals.

Focus areas:
- Market fear/greed index interpretation
- Macro economic environment (rates, USD strength, risk-on/off)
- Crypto-specific narratives (halving cycles, regulatory news, institutional flows)
- On-chain metrics (exchange inflows/outflows, whale movements)
- Social sentiment and funding rates

Always respond with a JSON object containing:
- sentiment: EXTREME_FEAR | FEAR | NEUTRAL | GREED | EXTREME_GREED
- macro_bias: BULLISH | NEUTRAL | BEARISH
- key_narratives: list of 3 active market narratives
- market_phase: ACCUMULATION | MARKUP | DISTRIBUTION | MARKDOWN
- confidence: 0.0-1.0
- reasoning_steps: list of 3-5 reasoning steps you followed
"""


class OracleAgent:
    name = "ORACLE"
    role = "Analyste Macro & Sentiment"
    emoji = "🔮"

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def analyze(self, market_context: str) -> dict:
        prompt = f"""Analyze the macro sentiment for the current crypto market.

Market context:
{market_context}

Provide your macro and sentiment assessment."""

        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            thinking={"type": "enabled", "budget_tokens": 2000},
            system=ORACLE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        thinking = next((b.thinking for b in response.content if b.type == "thinking"), "")
        text = next((b.text for b in response.content if b.type == "text"), "{}")

        result = json.loads(text)
        result["_thinking"] = thinking
        result["_agent"] = self.name
        return result
