"""Serializable training settings shared by the UI and worker."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from app.model import ModelConfig, preset_values


@dataclass(frozen=True)
class TrainingConfig:
    data_dir: Path
    output_dir: Path
    device: str = "auto"
    preset: str = "Маленькая"
    context_length: int = 256
    batch_size: int = 8
    epochs: int = 2
    learning_rate: float = 0.0003
    vocab_size: int = 4096
    cpu_threads: int = 6
    seed: int = 42

    def model_config(self, vocab_size: int) -> ModelConfig:
        embedding_size, layers, heads = preset_values(self.preset)
        return ModelConfig(
            vocab_size=vocab_size,
            context_length=self.context_length,
            embedding_size=embedding_size,
            layers=layers,
            heads=heads,
        )

    def to_dict(self) -> dict[str, object]:
        values = asdict(self)
        values["data_dir"] = str(self.data_dir)
        values["output_dir"] = str(self.output_dir)
        return values
