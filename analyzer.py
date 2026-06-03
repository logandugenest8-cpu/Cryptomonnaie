import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_TOKENS
from prompts import TRADEX_SYSTEM_PROMPT, TRADE_DECISION_SCHEMA

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def analyze_market(symbol: str, market_summary: str) -> dict:
    user_message = f"""Please analyze the following market data and provide a trading decision for {symbol}.

{market_summary}

Generate a precise trading decision based on your TRADEX analysis framework. Consider all indicators holistically and ensure your stop-loss and take-profit levels are derived from the technical structure."""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": TRADEX_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": TRADE_DECISION_SCHEMA,
            }
        },
    )

    usage = response.usage
    cache_created = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

    text = next(b.text for b in response.content if b.type == "text")
    decision = json.loads(text)

    decision["_meta"] = {
        "model": response.model,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_created_tokens": cache_created,
        "cache_read_tokens": cache_read,
    }

    return decision
