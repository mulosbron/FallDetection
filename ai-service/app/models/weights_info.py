from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelWeightsInfo:
    model_path: str
    exists: bool
    size_bytes: int


def get_model_weights_info(model_path: str) -> ModelWeightsInfo:
    path = Path(model_path)
    if not path.exists():
        return ModelWeightsInfo(model_path=model_path, exists=False, size_bytes=0)
    return ModelWeightsInfo(model_path=model_path, exists=True, size_bytes=path.stat().st_size)
