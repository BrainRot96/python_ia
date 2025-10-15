# pipeline/__init__.py

from .pipeline import LLMConfig, PipelineInput, PipelineOutput, Pipeline
from .fake_llm import FakeLLM

# Ollama est optionnel : on protège l'import pour éviter de casser si requests/ollama manquent
try:
    from .providers import OllamaLLM  # défini dans pipeline/providers/__init__.py
except Exception:
    OllamaLLM = None  # L'app gérera le cas où Ollama n'est pas dispo

__all__ = [
    "LLMConfig",
    "PipelineInput",
    "PipelineOutput",
    "Pipeline",
    "FakeLLM",
    "OllamaLLM",
]