"""
Rapport automatique toutes les 4 heures.
Analyse l'état des trades ouverts, le P&L en cours et envoie
un résumé dans reports/report_4h_YYYYMMDD_HH.json
"""
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

REPORTS_DIR = Path("reports")
STATE_FILE  = Path("agent_state.json")
REPORTS_DIR.mkdir(exist_ok=True)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

REPORTER_PROMPT = """Tu es REPORTER, un agent IA spécialisé dans l'analyse de performance de trading crypto.
Tu reçois l'état actuel des trades ouverts et fermés du bot TRADEX (en euros).

Ta mission :
1. Résumer l'état de chaque position ouverte (P&L latent en €, distance au stop-loss, distance à l'objectif)
2. Lister les trades fermés depuis le dernier rapport (gain ou perte en €)
3. Calculer le P&L total du portefeuille simulé en €
4. Donner un verdict global : SAIN / ATTENTION / ALERTE
5. Recommander des ajustements si nécessaire

Réponds en JSON avec les champs :
- timestamp: string ISO
- verdict: "SAIN" | "ATTENTION" | "ALERTE"
- portfolio_eur: float (valeur totale estimée)
- pnl_4h_eur: float (P&L des 4 dernières heures)
- open_positions: liste de résumés de positions ouvertes
- closed_since_last: liste de trades fermés depuis le dernier rapport
- analysis: string (2-3 phrases d'analyse)
- recommendations: liste de recommandations (max 3)
"""


def generate_4h_report(state: dict, history_file: Path | None = None) -> dict:
    prev_report = {}
    if history_file and history_file.exists():
        try:
            prev_report = json.loads(history_file.read_text())
        except Exception:
            pass

    prompt = f"""Voici l'état actuel du bot TRADEX (toutes valeurs en euros) :

{json.dumps(state, indent=2, default=str)}

Rapport précédent (il y a 4h) :
{json.dumps(prev_report, indent=2, default=str) if prev_report else 'Aucun'}

Génère le rapport de situation des 4 dernières heures."""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=REPORTER_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    try:
        report = json.loads(text)
    except json.JSONDecodeError:
        report = {"raw": text, "timestamp": datetime.now(timezone.utc).isoformat()}

    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["type"] = "4h"
    return report


def run_4h_report():
    if not STATE_FILE.exists():
        print("[REPORTER] Pas encore de données (agent_state.json manquant).")
        return

    state = json.loads(STATE_FILE.read_text())
    now   = datetime.now(timezone.utc)
    fname = f"report_4h_{now.strftime('%Y%m%d_%H')}.json"
    out   = REPORTS_DIR / fname

    # Dernier rapport 4h
    existing = sorted(REPORTS_DIR.glob("report_4h_*.json"))
    last = existing[-1] if existing else None

    print(f"[REPORTER] Génération rapport 4h : {fname}")
    report = generate_4h_report(state, last)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[REPORTER] Rapport sauvegardé : {out}")
    print(f"[REPORTER] Verdict : {report.get('verdict','?')} | P&L 4h : {report.get('pnl_4h_eur', '?')} €")
    return report


if __name__ == "__main__":
    run_4h_report()
