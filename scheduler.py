"""
Orchestration des tâches planifiées :
- Rapport 4h : toutes les 4 heures
- Rapport hebdomadaire : tous les lundis à 08h00
- Bot principal : toutes les heures

Lancez ce fichier à la place de main.py pour tout avoir ensemble :
  python scheduler.py
"""
import time
import signal
import threading
from datetime import datetime, timezone
from logger import logger
from reporter import run_4h_report
from weekly_analyst import run_weekly_analysis

_running = True


def _stop(sig, frame):
    global _running
    _running = False


signal.signal(signal.SIGINT, _stop)
signal.signal(signal.SIGTERM, _stop)


def run_bot_loop():
    """Boucle principale du bot multi-agents."""
    from multi_agent_main import run
    run()


def schedule_loop():
    last_4h   = None  # datetime du dernier rapport 4h
    last_week = None  # datetime du dernier rapport hebdo

    while _running:
        now = datetime.now(timezone.utc)

        # --- Rapport 4h ---
        if last_4h is None or (now - last_4h).total_seconds() >= 4 * 3600:
            try:
                logger.info("[SCHEDULER] Lancement rapport 4h...")
                run_4h_report()
                last_4h = now
            except Exception as e:
                logger.error(f"[SCHEDULER] Erreur rapport 4h : {e}", exc_info=True)

        # --- Rapport hebdomadaire (lundi 08h UTC) ---
        is_monday_8h = (now.weekday() == 0 and now.hour == 8)
        if is_monday_8h and (last_week is None or (now - last_week).total_seconds() > 3600):
            try:
                logger.info("[SCHEDULER] Lancement analyse hebdomadaire...")
                run_weekly_analysis()
                last_week = now
            except Exception as e:
                logger.error(f"[SCHEDULER] Erreur rapport hebdo : {e}", exc_info=True)

        time.sleep(60)  # vérifie toutes les minutes


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("TRADEX Scheduler démarré")
    logger.info("Rapport 4h : toutes les 4 heures")
    logger.info("Rapport hebdo : lundi 08h00 UTC")
    logger.info("=" * 60)

    # Bot en thread séparé
    bot_thread = threading.Thread(target=run_bot_loop, daemon=True)
    bot_thread.start()

    # Scheduler dans le thread principal
    schedule_loop()

    logger.info("TRADEX Scheduler arrêté.")
