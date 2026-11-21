"""Text discovery, tokenizer training, and reusable token-cache creation."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

import numpy as np
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers

ProgressCallback = Callable[[str, int, int], None]
_CACHE_FORMAT_VERSION = 1


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


def _make_cache_key(files: list[Path], tokenizer_identity: str) -> str:
    file_info = []
    for path in files:
        try:
            stat = path.stat()
        except OSError as exc:
            raise RuntimeError(f"Не удалось проверить файл {path.name}: {exc}") from exc
        file_info.append(
            {
                "path": str(path.resolve()),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        )
    signature = {
        "cache_format": _CACHE_FORMAT_VERSION,
        "tokenizer": tokenizer_identity,
        "files": file_info,
    }
    encoded = json.dumps(signature, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_cached_token_data(
    cache_root: Path,
    cache_key: str,
    output_dir: Path,
    progress: ProgressCallback,
    file_count: int,
) -> tuple[Path, Path, int, int] | None:
    cache_dir = cache_root / cache_key
    manifest_path = cache_dir / "manifest.json"
    tokenizer_cache_path = cache_dir / "tokenizer.json"
    token_cache_path = cache_dir / "tokens.bin"
    if not manifest_path.is_file() or not tokenizer_cache_path.is_file() or not token_cache_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        token_count = int(manifest["token_count"])
        vocab_size = int(manifest["vocab_size"])
        if (
            manifest.get("cache_format") != _CACHE_FORMAT_VERSION
            or manifest.get("cache_key") != cache_key
            or token_count < 32
            or vocab_size < 2
        ):
            return None
        if token_cache_path.stat().st_size != token_count * np.dtype(np.uint16).itemsize:
            return None
        output_dir.mkdir(parents=True, exist_ok=True)
        tokenizer_path = output_dir / "tokenizer.json"
        shutil.copy2(tokenizer_cache_path, tokenizer_path)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
    progress(
        f"Использую готовый кэш: {token_count:,} токенов — повторно кодировать тексты не нужно.",
        file_count,
        file_count,
    )
    return tokenizer_path, token_cache_path, token_count, vocab_size


def _write_token_data(
    files: list[Path],
    output_dir: Path,
    tokenizer: Tokenizer,
    progress: ProgressCallback,
    cache_root: Path | None = None,
    cache_key: str | None = None,
) -> tuple[Path, Path, int, int]:
    if not files:
        raise ValueError("В выбранной папке нет непустых файлов .txt.")
    output_dir.mkdir(parents=True, exist_ok=True)

    if cache_root is not None and cache_key is not None:
        cache_root.mkdir(parents=True, exist_ok=True)
        cached = _load_cached_token_data(cache_root, cache_key, output_dir, progress, len(files))
        if cached is not None:
            return cached
        work_dir = Path(tempfile.mkdtemp(prefix=f".{cache_key[:12]}-", dir=cache_root))
        tokenizer_path = work_dir / "tokenizer.json"
        token_cache_path = work_dir / "tokens.bin"
    else:
        work_dir = None
        tokenizer_path = output_dir / "tokenizer.json"
        token_cache_path = output_dir / "tokens.bin"

    try:
        tokenizer.save(str(tokenizer_path))
        eos_id = tokenizer.token_to_id("<eos>")
        if eos_id is None:
            raise RuntimeError("В словаре модели нет токена конца документа.")

        progress("Кодирую тексты…", 0, len(files))
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

        if work_dir is None or cache_root is None or cache_key is None:
            return tokenizer_path, token_cache_path, total_tokens, vocab_size

        manifest = {
            "cache_format": _CACHE_FORMAT_VERSION,
            "cache_key": cache_key,
            "token_count": total_tokens,
            "vocab_size": vocab_size,
        }
        (work_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        final_cache_dir = cache_root / cache_key
        cached = _load_cached_token_data(cache_root, cache_key, output_dir, progress, len(files))
        if cached is not None:
            return cached
        if final_cache_dir.is_dir():
            shutil.rmtree(final_cache_dir)
        elif final_cache_dir.exists():
            final_cache_dir.unlink()
        try:
            work_dir.rename(final_cache_dir)
        except OSError:
            cached = _load_cached_token_data(cache_root, cache_key, output_dir, progress, len(files))
            if cached is not None:
                return cached
            raise
        work_dir = None

        cached_tokenizer_path = final_cache_dir / "tokenizer.json"
        run_tokenizer_path = output_dir / "tokenizer.json"
        shutil.copy2(cached_tokenizer_path, run_tokenizer_path)
        return run_tokenizer_path, final_cache_dir / "tokens.bin", total_tokens, vocab_size
    finally:
        if work_dir is not None and work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)


def prepare_token_data(
    files: list[Path],
    output_dir: Path,
    vocab_size: int,
    progress: ProgressCallback,
    cache_root: Path | None = None,
) -> tuple[Path, Path, int, int]:
    """Train a fresh byte-level BPE tokenizer, reusing a matching persistent cache."""
    if not files:
        raise ValueError("В выбранной папке нет непустых файлов .txt.")
    if vocab_size > 65_000:
        raise ValueError("Для первого прототипа размер словаря должен быть меньше 65 000.")

    cache_key = None
    if cache_root is not None:
        tokenizer_identity = f"byte-level-bpe-v1:vocab={vocab_size}:min_frequency=2"
        cache_key = _make_cache_key(files, tokenizer_identity)
        cached = _load_cached_token_data(cache_root, cache_key, output_dir, progress, len(files))
        if cached is not None:
            return cached

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
    return _write_token_data(files, output_dir, tokenizer, progress, cache_root, cache_key)


def encode_with_existing_tokenizer(
    files: list[Path],
    output_dir: Path,
    tokenizer_path: Path,
    progress: ProgressCallback,
    cache_root: Path | None = None,
) -> tuple[Path, Path, int, int]:
    """Reuse a model's tokenizer and a matching persistent token cache."""
    if not files:
        raise ValueError("В выбранной папке нет непустых файлов .txt.")
    if not tokenizer_path.is_file():
        raise FileNotFoundError(f"Не найден словарь модели: {tokenizer_path}")

    cache_key = None
    if cache_root is not None:
        try:
            tokenizer_hash = hashlib.sha256(tokenizer_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise RuntimeError(f"Не удалось прочитать словарь модели: {exc}") from exc
        cache_key = _make_cache_key(files, f"saved-tokenizer-sha256:{tokenizer_hash}")
        cached = _load_cached_token_data(cache_root, cache_key, output_dir, progress, len(files))
        if cached is not None:
            return cached

    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    return _write_token_data(files, output_dir, tokenizer, progress, cache_root, cache_key)
