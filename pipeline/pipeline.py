# pipeline/pipeline.py (extrait)
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class LLMConfig:
    temperature: float = 0.2
    max_tokens: int = 300

@dataclass
class PipelineInput:
    query: str
    context: str = ""

@dataclass
class PipelineOutput:
    text: str
    usage: Dict[str, Any]

class Pipeline:
    def __init__(self, llm, cfg: LLMConfig):
        self.llm = llm
        self.cfg = cfg

    def run(self, inp: PipelineInput) -> PipelineOutput:
        try:
            res = self.llm.generate(
                inp.query,
                max_tokens=self.cfg.max_tokens,
                temperature=self.cfg.temperature,
                context=inp.context,
            )
            return PipelineOutput(text=res.get("text", ""), usage=res.get("usage", {}))
        except Exception as e:
            # On remonte une sortie “propre”
            return PipelineOutput(
                text=f"⚠️ Erreur pendant l'appel LLM : {e}",
                usage={"total_tokens": 0}
            )