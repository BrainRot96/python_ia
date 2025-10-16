# tests/test_logger.py
import os, tempfile, json
from evaluation.logger import log_event, read_events

def test_logger_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "log.jsonl")
        log_event({"provider":"test","model":"m","input":{"query":"q"},"output":{"text":"t"}}, rating=1, log_path=path)
        evts = read_events(limit=None, log_path=path)
        assert len(evts) == 1
        assert evts[0]["rating"] == 1
        assert evts[0]["output"]["text"] == "t"
        # valide JSON
        json.dumps(evts[0], ensure_ascii=False)
        