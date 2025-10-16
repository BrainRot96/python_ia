# evaluation/__init__.py

from .logger import LOG_FILE, log_event, read_events, to_dataframe

try:
    from .metrics import basic_kpis, tokens_by_provider, runs_over_time
except Exception:
    basic_kpis = None
    tokens_by_provider = None
    runs_over_time = None

__all__ = [
    "LOG_FILE",
    "log_event",
    "read_events",
    "to_dataframe",
    "basic_kpis",
    "tokens_by_provider",
    "runs_over_time",
]