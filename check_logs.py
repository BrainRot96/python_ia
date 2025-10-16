# check_logs.py
from evaluation.logger import read_events, LOG_FILE
from pathlib import Path

p = Path(LOG_FILE)
print("LOG_FILE =", p.resolve())
if not p.exists():
    print("Aucun fichier de log. Lance au moins une génération.")
    raise SystemExit

evts = read_events(limit=5)
print(f"Derniers événements ({len(evts)}) :")
for e in evts:
    rid = e.get("rating", None)
    print("-", e.get("id", "")[:8], "| rating =", rid, "| provider =", e.get("provider"))
    