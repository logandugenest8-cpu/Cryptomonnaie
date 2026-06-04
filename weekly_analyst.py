"""
Analyste hebdomadaire.
- Génère un rapport complet gains/pertes de la semaine en euros
- Analyse pourquoi le bot a perdu de l'argent
- Propose des ajustements de paramètres et les applique si validés
"""
import json
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

REPORTS_DIR  = Path("reports")
STATE_FILE   = Path("agent_state.json")
CONFIG_FILE  = Path("config.py")
REPORTS_DIR.mkdir(exist_ok=True)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

WEEKLY_PROMPT = """Tu es WEEKLY_ANALYST, un agent IA expert en optimisation de bots de trading crypto.
Tu analyses les performances hebdomadaires du bot TRADEX (en euros).

Tes missions :
1. BILAN : Calculer le gain/perte net de la semaine en € et en %
2. ANALYSE DES PERTES : Pour chaque trade perdant, expliquer POURQUOI (mauvais signal RSI ? MACD trompeur ? Stop trop serré ? Marché volatile ?)
3. ANALYSE DES GAINS : Quels signaux ont bien fonctionné cette semaine ?
4. OPTIMISATION : Proposer des ajustements précis aux paramètres du bot (ex: RSI seuil, MACD period, stop-loss %, position size)
5. AJUSTEMENTS CONFIG : Lister les changements de config.py recommandés au format JSON

Réponds en JSON avec :
- period: string ("YYYY-Wxx")
- pnl_week_eur: float
- pnl_week_pct: float
- total_trades: int
- winning_trades: int
- losing_trades: int
- win_rate_pct: float
- best_trade: {asset, pnl_eur, reason}
- worst_trade: {asset, pnl_eur, reason}
- loss_analysis: liste de {trade_id, asset, loss_eur, root_cause, prevention}
- gain_analysis: liste de {asset, gain_eur, what_worked}
- verdict: "EXCELLENT" | "BON" | "MOYEN" | "MAUVAIS" | "CRITIQUE"
- config_adjustments: liste de {param, current_value, recommended_value, reason}
- apply_adjustments: bool (true si les pertes sont > 5% du portefeuille)
- weekly_summary: string (3-4 phrases de résumé)
"""

CRITIQUE_PROMPT = """Tu es CRITIQUE, un agent IA qui analyse en profondeur pourquoi un bot de trading a échoué.
Donne une analyse honnête et détaillée des erreurs commises.
Identifie les patterns de pertes récurrents et propose des corrections précises.

Réponds en JSON avec :
- main_failure_mode: string (le problème principal)
- failure_patterns: liste de patterns d'échec
- corrective_actions: liste d'actions correctives avec impact estimé
- revised_strategy: string (comment le bot devrait trader différemment)
"""


def collect_weekly_data() -> dict:
    """Collecte tous les rapports 4h de la semaine passée."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    reports = []
    for f in sorted(REPORTS_DIR.glob("report_4h_*.json")):
        try:
            r = json.loads(f.read_text())
            ts = datetime.fromisoformat(r.get("generated_at", "2000-01-01"))
            if ts.replace(tzinfo=timezone.utc) >= cutoff:
                reports.append(r)
        except Exception:
            pass

    state = {}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())

    return {"reports_4h": reports, "current_state": state, "period_start": cutoff.isoformat()}


def apply_config_adjustments(adjustments: list) -> bool:
    """Applique les ajustements recommandés dans config.py."""
    if not CONFIG_FILE.exists() or not adjustments:
        return False

    content = CONFIG_FILE.read_text()
    changed = False
    change_log = []

    for adj in adjustments:
        param  = adj.get("param", "")
        newval = adj.get("recommended_value")
        reason = adj.get("reason", "")
        if not param or newval is None:
            continue
        # Cherche la ligne du paramètre et la remplace
        pattern = re.compile(rf'^({re.escape(param)}\s*=\s*)(.+)$', re.MULTILINE)
        if isinstance(newval, str):
            replacement = f'{param} = "{newval}"'
        else:
            replacement = f'{param} = {newval}'
        new_content, n = pattern.subn(lambda m: replacement, content)
        if n > 0:
            content = new_content
            changed = True
            change_log.append(f"  {param}: {adj.get('current_value')} → {newval} ({reason})")

    if changed:
        # Sauvegarde de l'ancienne version
        backup = CONFIG_FILE.with_suffix(".py.bak")
        backup.write_text(CONFIG_FILE.read_text())
        CONFIG_FILE.write_text(content)
        print("[WEEKLY] Ajustements appliqués :")
        for line in change_log:
            print(line)

    return changed


def run_weekly_analysis():
    print("[WEEKLY] Collecte des données de la semaine...")
    data = collect_weekly_data()

    now   = datetime.now(timezone.utc)
    week  = now.strftime("%Y-W%V")
    fname = f"report_weekly_{week}.json"
    out   = REPORTS_DIR / fname

    print("[WEEKLY] Analyse hebdomadaire en cours...")
    prompt = f"""Analyse les performances de la semaine {week} du bot TRADEX (toutes valeurs en euros) :

{json.dumps(data, indent=2, default=str)}

Génère le rapport hebdomadaire complet."""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        thinking={"type": "enabled", "budget_tokens": 8000},
        system=WEEKLY_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    thinking = next((b.thinking for b in response.content if b.type == "thinking"), "")
    text     = next((b.text for b in response.content if b.type == "text"), "{}")

    try:
        report = json.loads(text)
    except json.JSONDecodeError:
        report = {"raw": text}

    report["generated_at"] = now.isoformat()
    report["type"]         = "weekly"
    report["_thinking"]    = thinking

    # Analyse des pertes si verdict mauvais
    verdict = report.get("verdict", "BON")
    if verdict in ("MAUVAIS", "CRITIQUE"):
        print("[WEEKLY] Verdict critique — analyse des échecs en cours...")
        critique_prompt = f"""Le bot TRADEX a eu un verdict {verdict} cette semaine.

Rapport hebdomadaire :
{json.dumps(report, indent=2, default=str)}

Fais une analyse critique approfondie des raisons d'échec."""
        crit_resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            thinking={"type": "enabled", "budget_tokens": 4000},
            system=CRITIQUE_PROMPT,
            messages=[{"role": "user", "content": critique_prompt}],
        )
        crit_text = next((b.text for b in crit_resp.content if b.type == "text"), "{}")
        try:
            report["critique"] = json.loads(crit_text)
        except Exception:
            report["critique"] = {"raw": crit_text}

    # Application des ajustements si nécessaire
    apply = report.get("apply_adjustments", False)
    adjustments = report.get("config_adjustments", [])
    if apply and adjustments:
        print("[WEEKLY] Application des ajustements de configuration...")
        changed = apply_config_adjustments(adjustments)
        report["adjustments_applied"] = changed
    else:
        report["adjustments_applied"] = False
        print("[WEEKLY] Aucun ajustement nécessaire cette semaine.")

    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[WEEKLY] Rapport sauvegardé : {out}")
    print(f"[WEEKLY] Verdict : {verdict} | P&L semaine : {report.get('pnl_week_eur', '?')} €")
    if report.get("adjustments_applied"):
        print("[WEEKLY] ✅ config.py mis à jour automatiquement.")
    return report


if __name__ == "__main__":
    run_weekly_analysis()
