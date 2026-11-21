"""Background training routine for the local desktop application."""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from app.config import TrainingConfig
from app.data import discover_text_files, prepare_token_data
from app.model import ModelConfig, TinyLanguageModel

ProgressCallback = Callable[[dict[str, object]], None]
MessageCallback = Callable[[str], None]


def resolve_device(device_key: str) -> torch.device:
    if device_key in ("", "auto"):
        if torch.cuda.is_available():
            return torch.device("cuda:0")
        try:
            import torch_directml  # type: ignore[import-not-found]

            return torch_directml.device(0)
        except Exception:
            return torch.device("cpu")
    if device_key.startswith("directml:"):
        import torch_directml  # type: ignore[import-not-found]

        index = int(device_key.split(":", 1)[1])
        return torch_directml.device(index)
    return torch.device(device_key)


def _probe_training_ops(model_config: ModelConfig, device: torch.device) -> None:
    """Run one tiny forward/backward/optimizer step before choosing DirectML."""
    probe_model = None
    optimizer = None
    try:
        probe_model = TinyLanguageModel(model_config).to(device)
        optimizer = torch.optim.AdamW(probe_model.parameters(), lr=1e-4)
        length = min(16, model_config.context_length)
        input_ids = torch.randint(0, model_config.vocab_size, (2, length), dtype=torch.long)
        target_ids = torch.randint(0, model_config.vocab_size, (2, length), dtype=torch.long)
        input_ids = input_ids.to(device)
        target_ids = target_ids.to(device)
        logits = probe_model(input_ids)
        loss = F.cross_entropy(logits.reshape(-1, model_config.vocab_size), target_ids.reshape(-1))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(probe_model.parameters(), 1.0)
        optimizer.step()
        float(loss.item())
    finally:
        del optimizer
        del probe_model
        import gc

        gc.collect()


def _make_starts(length: int, block_size: int) -> np.ndarray:
    count = length - block_size
    if count <= 0:
        return np.empty(0, dtype=np.int64)
    return np.arange(0, count, block_size, dtype=np.int64)


def _batch_from_starts(tokens: np.memmap, starts: np.ndarray, block_size: int) -> np.ndarray:
    return np.stack(
        [np.asarray(tokens[int(start) : int(start) + block_size + 1], dtype=np.int64) for start in starts],
        axis=0,
    )


def _save_checkpoint(
    path: Path,
    model: TinyLanguageModel,
    model_config: ModelConfig,
    training_config: TrainingConfig,
    tokenizer_path: Path,
    epoch: int,
    loss: float | None,
) -> None:
    state = {key: value.detach().cpu() for key, value in model.state_dict().items()}
    payload = {
        "format_version": 1,
        "model_config": model_config.to_dict(),
        "training_config": training_config.to_dict(),
        "tokenizer_path": str(tokenizer_path),
        "epoch": epoch,
        "loss": loss,
        "model_state": state,
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temporary)
    temporary.replace(path)


def _evaluate(
    model: TinyLanguageModel,
    tokens: np.memmap,
    start: int,
    length: int,
    block_size: int,
    batch_size: int,
    device: torch.device,
) -> float | None:
    starts = _make_starts(length, block_size)
    if len(starts) == 0:
        return None
    model.eval()
    losses: list[float] = []
    with torch.no_grad():
        for offset in range(0, min(len(starts), batch_size * 8), batch_size):
            chosen = starts[offset : offset + batch_size] + start
            batch = _batch_from_starts(tokens, chosen, block_size)
            inputs = torch.from_numpy(batch[:, :-1].copy()).to(device=device, dtype=torch.long)
            targets = torch.from_numpy(batch[:, 1:].copy()).to(device=device, dtype=torch.long)
            logits = model(inputs)
            loss = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), targets.reshape(-1))
            losses.append(float(loss.item()))
    model.train()
    return sum(losses) / len(losses) if losses else None


def train_model(
    config: TrainingConfig,
    stop_event: threading.Event,
    on_progress: ProgressCallback,
    on_message: MessageCallback,
) -> Path:
    if config.epochs < 1:
        raise ValueError("Число эпох должно быть не меньше 1.")
    if config.batch_size < 1:
        raise ValueError("Размер батча должен быть не меньше 1.")
    if config.context_length < 16:
        raise ValueError("Контекст должен быть не меньше 16 токенов.")

    try:
        torch.set_num_threads(max(1, int(config.cpu_threads)))
    except Exception:
        pass
    torch.manual_seed(config.seed)
    np.random.seed(config.seed)

    run_name = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    run_dir = config.output_dir.expanduser().resolve() / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    on_message(f"Создана папка запуска: {run_dir}")

    files = discover_text_files(config.data_dir, config.output_dir)
    if not files:
        raise ValueError("В выбранной папке не найдено непустых файлов .txt.")
    total_bytes = sum(path.stat().st_size for path in files)
    on_message(f"Найдено файлов: {len(files)}; размер текста: {total_bytes / (1024 * 1024):.1f} МБ.")

    tokenizer_path, token_cache_path, token_count, vocab_size = prepare_token_data(
        files,
        run_dir,
        config.vocab_size,
        lambda text, current, total: on_progress(
            {
                "stage": "Подготовка текста",
                "message": text,
                "stage_current": current,
                "stage_total": total,
                "percent": 0,
            }
        ),
    )
    if token_count < 2 * config.context_length + 2:
        raise ValueError(
            f"После токенизации получилось только {token_count} токенов. "
            f"Для контекста {config.context_length} нужно больше текста; добавь файлы или уменьши контекст."
        )
    on_message(f"Подготовлено токенов: {token_count:,}; размер словаря: {vocab_size:,}.")

    tokens = np.memmap(token_cache_path, dtype=np.uint16, mode="r")
    split = int(token_count * 0.95)
    split = min(max(split, config.context_length + 1), token_count - config.context_length - 1)
    train_length = split
    validation_start = split
    validation_length = token_count - split
    if validation_length <= config.context_length:
        validation_start = 0
        validation_length = train_length
        on_message("Текста для отдельной проверки мало: временно проверяю на обучающей части.")

    block_size = min(config.context_length, train_length - 1)
    model_config = config.model_config(vocab_size)
    if block_size < 16:
        raise ValueError("Недостаточно текста для обучения; добавь больше .txt-файлов.")
    device = resolve_device(config.device)
    is_directml = device.type == "privateuseone" or config.device.startswith("directml:")
    if is_directml:
        on_message("Проверяю DirectML на коротком шаге обучения…")
        try:
            _probe_training_ops(model_config, device)
            on_message("Проверка DirectML прошла. Начинаю обучение на видеокарте.")
        except Exception as exc:
            on_message(
                f"DirectML не прошёл проверку ({exc}). Переключаю обучение на CPU; "
                "текущая установка останется рабочей."
            )
            device = torch.device("cpu")
    on_message(f"Устройство обучения: {device}.")
    model = TinyLanguageModel(model_config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate)

    starts = _make_starts(train_length, block_size)
    if len(starts) == 0:
        raise ValueError("Не получилось составить обучающие последовательности.")
    steps_per_epoch = max(1, math.ceil(len(starts) / config.batch_size))
    total_steps = steps_per_epoch * config.epochs
    global_step = 0
    last_loss: float | None = None
    checkpoint_path = run_dir / "latest.pt"
    started = time.time()
    completed_epochs = 0

    for epoch in range(1, config.epochs + 1):
        if stop_event.is_set():
            break
        model.train()
        epoch_starts = starts.copy()
        np.random.shuffle(epoch_starts)
        epoch_losses: list[float] = []

        for offset in range(0, len(epoch_starts), config.batch_size):
            if stop_event.is_set():
                break
            batch_starts = epoch_starts[offset : offset + config.batch_size]
            batch = _batch_from_starts(tokens, batch_starts, block_size)
            inputs = torch.from_numpy(batch[:, :-1].copy()).to(device=device, dtype=torch.long)
            targets = torch.from_numpy(batch[:, 1:].copy()).to(device=device, dtype=torch.long)

            optimizer.zero_grad(set_to_none=True)
            logits = model(inputs)
            loss = F.cross_entropy(logits.reshape(-1, vocab_size), targets.reshape(-1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            last_loss = float(loss.item())
            epoch_losses.append(last_loss)
            global_step += 1
            elapsed = max(time.time() - started, 0.001)
            percent = int((global_step / max(total_steps, 1)) * 100)
            on_progress(
                {
                    "stage": "Обучение",
                    "epoch": epoch,
                    "epochs": config.epochs,
                    "step": offset // config.batch_size + 1,
                    "steps_per_epoch": steps_per_epoch,
                    "global_step": global_step,
                    "total_steps": total_steps,
                    "train_loss": last_loss,
                    "elapsed_seconds": elapsed,
                    "percent": min(percent, 99),
                }
            )

        if epoch_losses:
            last_loss = sum(epoch_losses) / len(epoch_losses)
        validation_loss = _evaluate(
            model,
            tokens,
            validation_start,
            validation_length,
            block_size,
            config.batch_size,
            device,
        )
        completed_epochs = epoch if epoch_losses else completed_epochs
        _save_checkpoint(
            checkpoint_path,
            model,
            model_config,
            config,
            tokenizer_path,
            completed_epochs,
            last_loss,
        )
        on_message(
            f"Эпоха {epoch}/{config.epochs}: train loss {last_loss:.4f}"
            + (f", проверка {validation_loss:.4f}" if validation_loss is not None else "")
            + ". Контрольная точка сохранена."
        )
        if stop_event.is_set():
            break

    if completed_epochs == 0:
        _save_checkpoint(checkpoint_path, model, model_config, config, tokenizer_path, 0, last_loss)
    was_stopped = stop_event.is_set()
    final_percent = int((global_step / max(total_steps, 1)) * 100) if was_stopped else 100
    on_progress(
        {
            "stage": "Остановлено" if was_stopped else "Готово",
            "epoch": completed_epochs,
            "epochs": config.epochs,
            "global_step": global_step,
            "total_steps": total_steps,
            "train_loss": last_loss,
            "percent": final_percent,
        }
    )
    on_message(
        ("Обучение остановлено. " if stop_event.is_set() else "Обучение завершено. ")
        + f"Файл модели: {checkpoint_path}"
    )
    return checkpoint_path
