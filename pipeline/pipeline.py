# pipeline/pipeline.py
from dataclasses import dataclass
from typing import Any, Dict, Optional
from .fake_llm import FakeLLM

@dataclass
class LLMConfig:
    max_tokens: int = 256
    temperature: float = 0.2

# ⬇️ PipelineInput maintenant attend query + context (optionnel)
@dataclass
class PipelineInput:
    query: str
    context: Optional[str] = None

@dataclass
class PipelineOutput:
    text: str
    usage: Dict[str, int]

class Pipeline:
    def __init__(self, llm: FakeLLM | None = None, cfg: LLMConfig | None = None):
        self.llm = llm or FakeLLM(seed=42)
        self.cfg = cfg or LLMConfig()

    def run(self, inp: PipelineInput) -> PipelineOutput:
        # Construit le prompt final à partir de query + context
        if inp.context:
            prompt = (
                "Contexte:\n"
                f"{inp.context}\n\n"
                "Tâche: Réponds de façon concise et utile en t'appuyant sur le contexte.\n"
                f"Question: {inp.query}"
            )
        else:
            prompt = inp.query

        result = self.llm.generate(
            prompt,
            max_tokens=self.cfg.max_tokens,
            temperature=self.cfg.temperature,
        )
        return PipelineOutput(text=result["text"], usage=result["usage"])
    