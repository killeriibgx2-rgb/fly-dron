"""Qt workers keep training and text generation off the UI thread."""

from __future__ import annotations

import gc
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.config import TrainingConfig
from app.model import ModelConfig, TinyLanguageModel
from app.training import resolve_device, train_model

_MODEL_CACHE: dict[str, object] | None = None
_MODEL_CACHE_LOCK = threading.RLock()


def _release_model_locked() -> bool:
    global _MODEL_CACHE
    was_loaded = _MODEL_CACHE is not None
    _MODEL_CACHE = None
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    return was_loaded


def unload_model_from_memory() -> bool:
    """Release the cached generation model and ask the backend to free memory."""
    with _MODEL_CACHE_LOCK:
        return _release_model_locked()


def release_unused_backend_memory() -> None:
    """Collect freed tensors and release CUDA's unused allocator cache when available."""
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def _load_model_locked(checkpoint_path: Path, device_key: str) -> str:
    """Load or replace the generation model. Caller must hold the cache lock."""
    global _MODEL_CACHE
    import torch
    from tokenizers import Tokenizer

    checkpoint_path = checkpoint_path.expanduser().resolve()
    key_path = str(checkpoint_path)
    if (
        _MODEL_CACHE is not None
        and _MODEL_CACHE.get("checkpoint_path") == key_path
        and _MODEL_CACHE.get("device_key") == device_key
    ):
        return "Модель уже загружена в память."

    _release_model_locked()
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"Файл модели не найден: {checkpoint_path}")
    try:
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    except Exception as exc:
        raise RuntimeError(f"Не удалось открыть файл модели: {exc}") from exc
    if not isinstance(checkpoint, dict):
        raise ValueError("Файл модели имеет неподдерживаемый формат.")

    tokenizer_path = checkpoint_path.parent / "tokenizer.json"
    if not tokenizer_path.is_file():
        stored_path = checkpoint.get("tokenizer_path")
        if isinstance(stored_path, str):
            tokenizer_path = Path(stored_path)
    if not tokenizer_path.is_file():
        raise FileNotFoundError("Рядом с моделью не найден tokenizer.json.")

    config_data = checkpoint.get("model_config")
    state = checkpoint.get("model_state")
    if not isinstance(config_data, dict) or not isinstance(state, dict):
        raise ValueError("В файле модели не найдены настройки или веса.")
    config = ModelConfig(**config_data)
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    device = resolve_device(device_key)
    model = TinyLanguageModel(config)
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    _MODEL_CACHE = {
        "checkpoint_path": key_path,
        "device_key": device_key,
        "model": model,
        "tokenizer": tokenizer,
        "config": config,
    }
    return f"Модель загружена в память: {checkpoint_path.name} · {device}."


def load_model_into_memory(checkpoint_path: Path, device_key: str) -> str:
    with _MODEL_CACHE_LOCK:
        return _load_model_locked(checkpoint_path, device_key)


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
            if unload_model_from_memory():
                self.message.emit("Выгрузил модель генерации из памяти перед обучением.")
            path = train_model(
                self.config,
                self.stop_event,
                self.progress.emit,
                self.message.emit,
            )
            self.completed.emit(str(path))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            release_unused_backend_memory()


class ModelControlWorker(QThread):
    completed = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        action: str,
        checkpoint_path: Path | None = None,
        device_key: str = "auto",
    ) -> None:
        super().__init__()
        self.action = action
        self.checkpoint_path = checkpoint_path
        self.device_key = device_key

    def run(self) -> None:
        try:
            if self.action == "load":
                if self.checkpoint_path is None:
                    raise ValueError("Сначала выбери файл модели.")
                message = load_model_into_memory(self.checkpoint_path, self.device_key)
            elif self.action == "unload":
                released = unload_model_from_memory()
                message = (
                    "Модель выгружена из приложения; драйвер может показать освобождение памяти не сразу."
                    if released
                    else "Загруженной модели не было."
                )
            else:
                raise ValueError("Неизвестное действие с моделью.")
            self.completed.emit(message)
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

            with _MODEL_CACHE_LOCK:
                _load_model_locked(self.checkpoint_path, self.device_key)
                assert _MODEL_CACHE is not None
                model = _MODEL_CACHE["model"]
                tokenizer = _MODEL_CACHE["tokenizer"]
                config = _MODEL_CACHE["config"]
                assert isinstance(model, TinyLanguageModel)
                assert isinstance(config, ModelConfig)

                encoded = tokenizer.encode(self.prompt, add_special_tokens=False).ids
                if not encoded:
                    encoded = [tokenizer.token_to_id("<eos>") or 0]
                device = resolve_device(self.device_key)
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
