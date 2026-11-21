"""Qt workers for local Qwen fine-tuning and chat."""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.qwen_finetune import answer_with_lora, train_lora


class QwenTrainingWorker(QThread):
    progress = Signal(dict)
    message = Signal(str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        model_dir: Path,
        data_dir: Path,
        output_dir: Path,
        sequence_length: int,
        epochs: int,
        learning_rate: float,
        lora_rank: int,
        cpu_threads: int,
    ) -> None:
        super().__init__()
        self.args = (
            model_dir, data_dir, output_dir, sequence_length, epochs,
            learning_rate, lora_rank, cpu_threads,
        )
        self.stop_event = threading.Event()

    def request_stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        try:
            model_dir, data_dir, output_dir, sequence_length, epochs, learning_rate, lora_rank, cpu_threads = self.args
            result = train_lora(
                model_dir, data_dir, output_dir, sequence_length, epochs,
                learning_rate, lora_rank, cpu_threads, self.stop_event,
                self.progress.emit, self.message.emit,
            )
            self.completed.emit(str(result))
        except Exception as exc:
            self.failed.emit(str(exc))


class QwenChatWorker(QThread):
    completed = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        model_dir: Path,
        adapter_dir: Path,
        messages: list[dict[str, str]],
        max_new_tokens: int = 256,
        cpu_threads: int = 6,
    ) -> None:
        super().__init__()
        self.model_dir = model_dir
        self.adapter_dir = adapter_dir
        self.messages = messages
        self.max_new_tokens = max_new_tokens
        self.cpu_threads = cpu_threads

    def run(self) -> None:
        try:
            answer = answer_with_lora(
                self.model_dir,
                self.adapter_dir,
                self.messages,
                self.max_new_tokens,
                self.cpu_threads,
            )
            self.completed.emit(answer)
        except Exception as exc:
            self.failed.emit(str(exc))
