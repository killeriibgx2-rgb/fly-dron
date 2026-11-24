"""CPU-first LoRA fine-tuning and chat helpers for local Qwen 2.5 models."""

from __future__ import annotations

import gc
import math
import random
import threading
from pathlib import Path
from typing import Callable, Iterator


def validate_model_folder(model_dir: Path) -> None:
    required = ["config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json"]
    missing = [name for name in required if not (model_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(
            "В выбранной папке не хватает файлов: " + ", ".join(missing)
            + ". Скачай их со страницы Qwen и положи все файлы в одну папку."
        )


def _text_files(data_dir: Path) -> list[Path]:
    files = sorted(path for path in data_dir.rglob("*.txt") if path.is_file())
    if not files:
        raise FileNotFoundError("В выбранной папке и подпапках нет .txt-файлов.")
    return files


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Файл не читается как UTF-8: {path}") from exc


def _token_batches(tokenizer, files: list[Path], sequence_length: int) -> Iterator[list[int]]:
    """Yield sequences across document boundaries without dropping short files."""
    eos_id = tokenizer.eos_token_id
    token_buffer: list[int] = []
    for file_path in files:
        text = _read_text(file_path)
        # Tokenize modest pieces rather than accumulating the full corpus in RAM.
        for offset in range(0, len(text), 48_000):
            fragment = text[offset : offset + 48_000]
            ids = tokenizer(fragment, add_special_tokens=False)["input_ids"]
            token_buffer.extend(ids)
            while len(token_buffer) >= sequence_length:
                yield token_buffer[:sequence_length]
                del token_buffer[:sequence_length]
        if eos_id is not None:
            token_buffer.append(eos_id)
        while len(token_buffer) >= sequence_length:
            yield token_buffer[:sequence_length]
            del token_buffer[:sequence_length]
    # Keep the final partial sequence too; variable-length batches are valid at batch size 1.
    if len(token_buffer) >= 2:
        yield token_buffer


def train_lora(
    model_dir: Path,
    data_dir: Path,
    output_dir: Path,
    sequence_length: int,
    epochs: int,
    learning_rate: float,
    lora_rank: int,
    cpu_threads: int,
    forget_dir: Path | None,
    stop_event: threading.Event,
    on_progress: Callable[[dict[str, object]], None],
    on_message: Callable[[str], None],
) -> Path:
    """Fine-tune LoRA adapters on plain Minecraft text, using CPU float32."""
    model_dir = model_dir.expanduser().resolve()
    data_dir = data_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    forget_dir = forget_dir.expanduser().resolve() if forget_dir else None
    validate_model_folder(model_dir)
    files = _text_files(data_dir)
    forget_files = _text_files(forget_dir) if forget_dir else []
    if forget_dir and (forget_dir == data_dir or forget_dir in data_dir.parents or data_dir in forget_dir.parents):
        raise ValueError("Папки для сохранения Minecraft и для забывания должны быть раздельными.")
    if not 32 <= sequence_length <= 2048:
        raise ValueError("Длина примера должна быть от 32 до 2048 токенов.")
    if epochs < 1 or learning_rate <= 0 or lora_rank < 1:
        raise ValueError("Проверь число эпох, скорость обучения и размер LoRA.")
    source_dirs = [model_dir, data_dir] + ([forget_dir] if forget_dir else [])
    if any(output_dir == source or source in output_dir.parents for source in source_dirs):
        raise ValueError("Папка результата должна быть отдельно от модели и обеих папок с текстами.")

    _clear_chat_cache()

    try:
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "Не установлены библиотеки для обучения Qwen. Запусти setup_windows.bat ещё раз, "
            "чтобы установить обновлённые зависимости."
        ) from exc

    torch.set_num_threads(max(1, cpu_threads))
    torch.manual_seed(42)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_dir = output_dir / "qwen_minecraft_lora"
    if run_dir.exists() and any(run_dir.iterdir()):
        from datetime import datetime
        run_dir = output_dir / f"qwen_minecraft_lora_{datetime.now():%Y%m%d_%H%M%S}"
    run_dir.mkdir(parents=True, exist_ok=True)

    on_message(f"Загружаю исходную модель на процессор: {model_dir}")
    on_message("Обучение Qwen выполняется на CPU. DirectML/RX 580 этим режимом не используется.")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(model_dir),
        local_files_only=True,
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
    )
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    lora_config = LoraConfig(
        r=lora_rank,
        lora_alpha=lora_rank * 2,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()
    model.train()
    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not trainable:
        raise RuntimeError("Не удалось найти веса LoRA для обучения.")
    optimizer = torch.optim.AdamW(trainable, lr=learning_rate)
    model.to("cpu")
    on_message(f"Minecraft-текстов: {len(files)}. Обучаемые веса сохраняются отдельным LoRA-адаптером.")
    if forget_files:
        on_message(f"Текстов для экспериментального забывания: {len(forget_files)}. "
                   "Исходный файл Qwen останется нетронутым.")

    # Estimate progress from retained text size; exact token count is avoided to limit RAM use.
    total_chars = sum(path.stat().st_size for path in files)
    estimated_steps = max(1, math.ceil(total_chars / max(1, sequence_length * 3.5)))
    global_step = 0
    last_loss: float | None = None
    stopped = False
    try:
        forget_strength = 0.1
        for epoch in range(1, epochs + 1):
            shuffled_files = files[:]
            random.Random(42 + epoch).shuffle(shuffled_files)
            forget_iterator = iter(_token_batches(tokenizer, forget_files, sequence_length)) if forget_files else None
            next_forget_batch: list[int] | None = None
            if forget_iterator is not None:
                try:
                    next_forget_batch = next(forget_iterator)
                except StopIteration as exc:
                    raise ValueError("В выбранных файлах для забывания слишком мало текста.") from exc

            for ids in _token_batches(tokenizer, shuffled_files, sequence_length):
                if stop_event.is_set():
                    stopped = True
                    break
                keep_inputs = torch.tensor([ids], dtype=torch.long)
                optimizer.zero_grad(set_to_none=True)
                keep_output = model(input_ids=keep_inputs, labels=keep_inputs, use_cache=False)
                total_loss = keep_output.loss
                forget_loss_value: float | None = None
                if next_forget_batch is not None and forget_iterator is not None:
                    forget_inputs = torch.tensor([next_forget_batch], dtype=torch.long)
                    forget_output = model(input_ids=forget_inputs, labels=forget_inputs, use_cache=False)
                    # Minimize loss on Minecraft examples while maximizing it on selected forget examples.
                    total_loss = total_loss - forget_strength * forget_output.loss
                    forget_loss_value = float(forget_output.loss.detach().item())
                    try:
                        next_forget_batch = next(forget_iterator)
                    except StopIteration:
                        forget_iterator = iter(_token_batches(tokenizer, forget_files, sequence_length))
                        try:
                            next_forget_batch = next(forget_iterator)
                        except StopIteration as exc:
                            raise ValueError("В выбранных файлах для забывания слишком мало текста.") from exc
                total_loss.backward()
                torch.nn.utils.clip_grad_norm_(trainable, 1.0)
                optimizer.step()
                last_loss = float(keep_output.loss.detach().item())
                global_step += 1
                if global_step % 5 == 0 or global_step == 1:
                    on_progress({
                        "epoch": epoch,
                        "epochs": epochs,
                        "step": min(global_step, estimated_steps * epochs),
                        "steps_per_epoch": estimated_steps,
                        "percent": min(99, int(global_step * 100 / (estimated_steps * epochs))),
                        "train_loss": last_loss,
                        "forget_loss": forget_loss_value,
                        "message": f"Обучение LoRA · эпоха {epoch}/{epochs}",
                    })
            _save_adapter(model, tokenizer, run_dir, model_dir)
            on_message(f"Сохранён адаптер после эпохи {epoch}/{epochs}.")
            if stop_event.is_set():
                stopped = True
            if stopped:
                break
        if global_step == 0 and not stopped:
            raise ValueError("В текстах не нашлось ни одного полноценного примера для обучения.")
        on_progress({
            "epoch": min(epochs, epoch),
            "epochs": epochs,
            "step": global_step,
            "steps_per_epoch": estimated_steps,
            "percent": 100 if not stopped else min(99, int(global_step * 100 / max(1, estimated_steps * epochs))),
            "train_loss": last_loss,
            "message": "Остановлено" if stopped else "Обучение завершено",
        })
        if stopped:
            on_message("Остановка запрошена. Адаптер сохранён; его можно выбрать для чата.")
        return run_dir
    finally:
        del optimizer, model, tokenizer
        gc.collect()


def _save_adapter(model, tokenizer, run_dir: Path, base_dir: Path) -> None:
    model.save_pretrained(run_dir, safe_serialization=True)
    tokenizer.save_pretrained(run_dir)
    # Store the actual local location for reliable loading even if the adapter is moved.
    config_path = run_dir / "adapter_config.json"
    import json
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["base_model_name_or_path"] = str(base_dir)
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


_CHAT_LOCK = threading.RLock()
_CHAT_CACHE: dict[str, object] = {}


def _clear_chat_cache() -> None:
    with _CHAT_LOCK:
        _CHAT_CACHE.clear()
    gc.collect()


def answer_with_lora(
    model_dir: Path,
    adapter_dir: Path,
    messages: list[dict[str, str]],
    max_new_tokens: int = 256,
    cpu_threads: int = 6,
) -> str:
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("Для чата Qwen не установлены transformers и peft. Запусти setup_windows.bat.") from exc

    model_dir = model_dir.expanduser().resolve()
    adapter_dir = adapter_dir.expanduser().resolve()
    validate_model_folder(model_dir)
    adapter_config = adapter_dir / "adapter_config.json"
    if not adapter_config.is_file() or not (adapter_dir / "adapter_model.safetensors").is_file():
        raise FileNotFoundError("В папке адаптера не найдены adapter_config.json и adapter_model.safetensors.")
    torch.set_num_threads(max(1, cpu_threads))
    key = f"{model_dir}|{adapter_dir}"
    with _CHAT_LOCK:
        if _CHAT_CACHE.get("key") != key:
            _CHAT_CACHE.clear()
            gc.collect()
            tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True, use_fast=True)
            base_model = AutoModelForCausalLM.from_pretrained(
                str(model_dir), local_files_only=True, torch_dtype=torch.float32, low_cpu_mem_usage=True
            )
            model = PeftModel.from_pretrained(base_model, str(adapter_dir), is_trainable=False)
            model.eval()
            model.config.use_cache = True
            _CHAT_CACHE.update({"key": key, "tokenizer": tokenizer, "model": model})
        tokenizer = _CHAT_CACHE["tokenizer"]
        model = _CHAT_CACHE["model"]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        encoded = tokenizer(prompt, return_tensors="pt")
        with torch.inference_mode():
            output = model.generate(
                **encoded,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                repetition_penalty=1.08,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        new_tokens = output[0, encoded["input_ids"].shape[1] :]
        return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
