"""Qt workers keep training and text generation off the UI thread."""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.config import TrainingConfig
from app.model import ModelConfig, TinyLanguageModel
from app.training import resolve_device, train_model


class TrainingWorker(QThread):
    progress = Signal(dict)
    message = Signal(str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, config: TrainingConfig) -> None:
        super().__init__()
        self.config = config
        self.stop_event = threading.Event()

    def request_stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        try:
            path = train_model(
                self.config,
                self.stop_event,
                self.progress.emit,
                self.message.emit,
            )
            self.completed.emit(str(path))
        except Exception as exc:
            self.failed.emit(str(exc))


class GenerationWorker(QThread):
    completed = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        checkpoint_path: Path,
        prompt: str,
        device_key: str,
        max_new_tokens: int,
        temperature: float,
    ) -> None:
        super().__init__()
        self.checkpoint_path = checkpoint_path
        self.prompt = prompt
        self.device_key = device_key
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature

    def run(self) -> None:
        try:
            import torch
            from tokenizers import Tokenizer

            device = resolve_device(self.device_key)
            checkpoint = torch.load(
                self.checkpoint_path,
                map_location="cpu",
                weights_only=False,
            )
            tokenizer_path = self.checkpoint_path.parent / "tokenizer.json"
            if not tokenizer_path.is_file():
                tokenizer_path = Path(checkpoint["tokenizer_path"])
            if not tokenizer_path.is_file():
                raise FileNotFoundError("Рядом с моделью не найден tokenizer.json.")

            config = ModelConfig(**checkpoint["model_config"])
            tokenizer = Tokenizer.from_file(str(tokenizer_path))
            model = TinyLanguageModel(config)
            model.load_state_dict(checkpoint["model_state"])
            model.to(device)
            model.eval()

            encoded = tokenizer.encode(self.prompt, add_special_tokens=False).ids
            if not encoded:
                encoded = [tokenizer.token_to_id("<eos>") or 0]
            input_ids = torch.tensor([encoded], dtype=torch.long, device=device)
            end_id = tokenizer.token_to_id("<eos>")
            output_ids = model.generate(
                input_ids,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                top_k=min(40, config.vocab_size - 1),
                end_token_id=end_id,
            )[0].detach().cpu().tolist()
            result = tokenizer.decode(output_ids, skip_special_tokens=True)
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
