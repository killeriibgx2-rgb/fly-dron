"""Text discovery, tokenizer training, and token-cache creation."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

ProgressCallback = Callable[[str, int, int], None]


def discover_text_files(input_dir: Path, excluded_dir: Path | None = None) -> list[Path]:
    input_dir = input_dir.expanduser().resolve()
    if not input_dir.is_dir():
        raise ValueError("Выбранная папка с текстами не существует.")
    excluded = excluded_dir.expanduser().resolve() if excluded_dir else None
    files: list[Path] = []
    for path in sorted(input_dir.rglob("*.txt")):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if excluded is not None:
            try:
                resolved.relative_to(excluded)
                continue
            except ValueError:
                pass
        try:
            if path.stat().st_size > 0:
                files.append(path)
        except OSError:
            continue
    return files


def _lines_from_files(files: list[Path]):
    for path in files:
        try:
            with path.open("r", encoding="utf-8", errors="replace") as source:
                yield from source
        except OSError as exc:
            raise RuntimeError(f"Не удалось прочитать файл {path.name}: {exc}") from exc


def _write_token_data(
    files: list[Path],
    output_dir: Path,
    tokenizer: Tokenizer,
    progress: ProgressCallback,
) -> tuple[Path, Path, int, int]:
    if not files:
        raise ValueError("В выбранной папке нет непустых файлов .txt.")
    output_dir.mkdir(parents=True, exist_ok=True)
    tokenizer_path = output_dir / "tokenizer.json"
    token_cache_path = output_dir / "tokens.bin"
    tokenizer.save(str(tokenizer_path))

    eos_id = tokenizer.token_to_id("<eos>")
    if eos_id is None:
        raise RuntimeError("В словаре модели нет токена конца документа.")

    progress("Кодирую тексты прежним словарём…", 0, len(files))
    total_tokens = 0
    with token_cache_path.open("wb") as cache:
        for file_index, path in enumerate(files, start=1):
            try:
                with path.open("r", encoding="utf-8", errors="replace") as source:
                    for line in source:
                        if not line:
                            continue
                        ids = tokenizer.encode(line, add_special_tokens=False).ids
                        if ids:
                            np.asarray(ids, dtype=np.uint16).tofile(cache)
                            total_tokens += len(ids)
                np.asarray([eos_id], dtype=np.uint16).tofile(cache)
                total_tokens += 1
            except OSError as exc:
                raise RuntimeError(f"Не удалось прочитать файл {path.name}: {exc}") from exc
            progress(f"Кодирую: {path.name}", file_index, len(files))

    vocab_size = tokenizer.get_vocab_size(with_added_tokens=True)
    if total_tokens < 32:
        raise ValueError("В текстах слишком мало содержимого для обучения (нужно хотя бы 32 токена).")
    return tokenizer_path, token_cache_path, total_tokens, vocab_size


def prepare_token_data(
    files: list[Path],
    output_dir: Path,
    vocab_size: int,
    progress: ProgressCallback,
) -> tuple[Path, Path, int, int]:
    """Train a fresh byte-level BPE tokenizer and write token IDs."""
    if not files:
        raise ValueError("В выбранной папке нет непустых файлов .txt.")
    if vocab_size > 65_000:
        raise ValueError("Для первого прототипа размер словаря должен быть меньше 65 000.")

    progress("Обучаю новый словарь на текстах…", 0, 0)
    tokenizer = Tokenizer(models.BPE(unk_token="<unk>"))
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tokenizer.decoder = decoders.ByteLevel()
    special_tokens = ["<unk>", "<eos>"]
    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        min_frequency=2,
        special_tokens=special_tokens,
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        show_progress=False,
    )
    tokenizer.train_from_iterator(_lines_from_files(files), trainer=trainer)
    return _write_token_data(files, output_dir, tokenizer, progress)


def encode_with_existing_tokenizer(
    files: list[Path],
    output_dir: Path,
    tokenizer_path: Path,
    progress: ProgressCallback,
) -> tuple[Path, Path, int, int]:
    """Reuse a model's saved tokenizer when preparing fine-tuning text."""
    if not tokenizer_path.is_file():
        raise FileNotFoundError(f"Не найден словарь модели: {tokenizer_path}")
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    return _write_token_data(files, output_dir, tokenizer, progress)
