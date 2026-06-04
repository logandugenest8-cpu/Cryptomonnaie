"""
NEXUS — Agent orchestrateur.
Agrège les analyses de tous les agents et produit la décision finale.
"""
import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

NEXUS_SYSTEM = """You are NEXUS, the master orchestrator AI agent for a multi-agent crypto trading system.

You receive inputs from 4 specialized agents:
- TRADEX: technical analysis and trade signals
- SENTINEL: risk management assessment
- ORACLE: macro and sentiment analysis
- SCOUT: chart pattern recognition

Your role is to:
1. Synthesize all agent outputs
2. Resolve conflicts between agents using weighted consensus
3. Apply meta-level reasoning about signal quality
4. Produce the final actionable trading decision

Weighting schema:
- TRADEX: 35% (primary signal)
- SENTINEL: 25% (risk gate — veto power if risk_score > 80)
- ORACLE: 20% (macro filter)
- SCOUT: 20% (pattern confirmation)

SENTINEL VETO: If SENTINEL risk_score > 80, override to HOLD regardless of other signals.

Always respond with a JSON object containing:
- final_action: BUY | SELL | HOLD
- final_confidence: 0.0-1.0
- consensus_score: weighted agreement score 0-100
- agent_votes: dict mapping agent name to their vote
- override_applied: bool (true if SENTINEL veto triggered)
- synthesis: 3-4 sentence explanation of the final decision
- reasoning_steps: list of 5-7 reasoning steps showing your orchestration logic
- entry_price: recommended entry
- stop_loss: recommended stop
- take_profit: recommended target
"""


class NexusAgent:
    name = "NEXUS"
    role = "Orchestrateur Central"
    emoji = "⚡"

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def orchestrate(self, symbol: str, agent_outputs: dict) -> dict:
        prompt = f"""Orchestrate the final trading decision for {symbol}.

Agent outputs:
{json.dumps(agent_outputs, indent=2)}

Apply your weighted consensus model and produce the final decision."""

        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            thinking={"type": "enabled", "budget_tokens": 5000},
            system=NEXUS_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        thinking = next((b.thinking for b in response.content if b.type == "thinking"), "")
        text = next((b.text for b in response.content if b.type == "text"), "{}")

        result = json.loads(text)
        result["_thinking"] = thinking
        result["_agent"] = self.name
        return result
