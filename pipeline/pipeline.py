# pipeline/pipeline.py
from dataclasses import dataclass
from typing import Optional, Dict, Any

from .fake_llm import FakeLLM  # défaut si aucun provider n'est passé

@dataclass
class LLMConfig:
    max_tokens: int = 300
    temperature: float = 0.2

@dataclass
class PipelineInput:
    query: str
    context: str = ""

@dataclass
class PipelineOutput:
    text: str
    usage: Dict[str, Any]

class Pipeline:
    """
    Pipeline minimal :
    - prend un 'llm' ayant une méthode .generate(prompt, max_tokens=, temperature=, context=)
    - si llm est None → utilise FakeLLM
    """
    def __init__(self, cfg: Optional[LLMConfig] = None, llm=None):
        self.cfg = cfg or LLMConfig()
        self.llm = llm or FakeLLM()

    def run(self, inp: PipelineInput) -> PipelineOutput:
        resp = self.llm.generate(
            prompt=inp.query,
            max_tokens=self.cfg.max_tokens,
            temperature=self.cfg.temperature,
            context=inp.context,
        )
        text = resp.get("text", "")
        usage = resp.get("usage", {})
        return PipelineOutput(text=text, usage=usage)
    