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
    optimizer: str = "AdamW"
    weight_decay: float = 0.01
    gradient_clip: float = 1.0
    dropout: float = 0.1
    embedding_size: int | None = None
    layers: int | None = None
    heads: int | None = None
    vocab_size: int = 4096
    validation_percent: int = 5
    cpu_threads: int = 6
    seed: int = 42
    continue_from: Path | None = None

    def model_config(self, vocab_size: int) -> ModelConfig:
        preset_embedding, preset_layers, preset_heads = preset_values(self.preset)
        return ModelConfig(
            vocab_size=vocab_size,
            context_length=self.context_length,
            embedding_size=self.embedding_size or preset_embedding,
            layers=self.layers or preset_layers,
            heads=self.heads or preset_heads,
            dropout=self.dropout,
        )

    def to_dict(self) -> dict[str, object]:
        values = asdict(self)
        values["data_dir"] = str(self.data_dir)
        values["output_dir"] = str(self.output_dir)
        values["continue_from"] = str(self.continue_from) if self.continue_from else None
        return values
