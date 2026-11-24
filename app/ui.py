"""Simple Qwen fine-tuning and chat desktop interface."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.qwen_finetune import validate_model_folder, _text_files
from app.qwen_workers import QwenChatWorker, QwenTrainingWorker

APP_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_DIR = APP_ROOT / "models" / "Qwen2.5-1.5B-Instruct"
DEFAULT_DATA_DIR = APP_ROOT / "data" / "minecraft"
DEFAULT_OUTPUT_DIR = APP_ROOT / "runs" / "qwen"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Мастерская Minecraft-модели")
        self.resize(1050, 850)
        self.setMinimumSize(820, 680)
        self.training_worker: QwenTrainingWorker | None = None
        self.chat_worker: QwenChatWorker | None = None
        self.messages: list[dict[str, str]] = []

        root_widget = QWidget()
        self.setCentralWidget(root_widget)
        root = QVBoxLayout(root_widget)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        title = QLabel("Дообучение Qwen для Minecraft")
        title.setObjectName("title")
        root.addWidget(title)
        intro = QLabel(
            "Укажи, где лежат скачанные файлы Qwen и твои Minecraft-тексты. "
            "Программа сохранит отдельную дообученную добавку (LoRA), а затем даст пообщаться с моделью."
        )
        intro.setObjectName("notice")
        intro.setWordWrap(True)
        root.addWidget(intro)

        paths = QGroupBox("1. Выбери папки")
        form = QFormLayout(paths)
        self.model_dir_edit = self._path_field(DEFAULT_MODEL_DIR)
        self.data_dir_edit = self._path_field(DEFAULT_DATA_DIR)
        self.output_dir_edit = self._path_field(DEFAULT_OUTPUT_DIR)
        self._add_folder_row(form, "Папка с Qwen-файлами", self.model_dir_edit, "Выбрать папку модели")
        self._add_folder_row(form, "Папка с Minecraft .txt", self.data_dir_edit, "Выбрать папку текстов")
        self._add_folder_row(form, "Куда сохранять результат", self.output_dir_edit, "Выбрать папку результата")
        root.addWidget(paths)

        settings = QGroupBox("2. Настройки обучения")
        settings_form = QFormLayout(settings)
        self.context_spin = QSpinBox()
        self.context_spin.setRange(32, 1024)
        self.context_spin.setSingleStep(32)
        self.context_spin.setValue(256)
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 20)
        self.epochs_spin.setValue(1)
        self.learning_rate_spin = QDoubleSpinBox()
        self.learning_rate_spin.setDecimals(6)
        self.learning_rate_spin.setRange(0.000001, 0.01)
        self.learning_rate_spin.setSingleStep(0.00005)
        self.learning_rate_spin.setValue(0.0001)
        self.rank_spin = QSpinBox()
        self.rank_spin.setRange(4, 32)
        self.rank_spin.setSingleStep(4)
        self.rank_spin.setValue(8)
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, max(1, os.cpu_count() or 1))
        self.threads_spin.setValue(min(6, max(1, os.cpu_count() or 1)))
        settings_form.addRow("Длина примера, токенов", self.context_spin)
        settings_form.addRow("Проходов по текстам", self.epochs_spin)
        settings_form.addRow("Скорость обучения", self.learning_rate_spin)
        settings_form.addRow("Размер LoRA", self.rank_spin)
        settings_form.addRow("Потоков процессора", self.threads_spin)
        self.avoid_topics_edit = QTextEdit()
        self.avoid_topics_edit.setMaximumHeight(68)
        self.avoid_topics_edit.setPlaceholderText("Добавь по одной теме на строку")
        self.avoid_topics_edit.setPlainText("Наполеон")
        settings_form.addRow("Темы, которые обходить (по одной в строке)", self.avoid_topics_edit)
        focus_note = QLabel(
            "Для каждой темы программа добавит примеры, где модель просто переводит разговор на Minecraft — без явного отказа. "
            "Это меняет ответы, но не стирает знание из модели полностью."
        )
        focus_note.setObjectName("hint")
        focus_note.setWordWrap(True)
        settings_form.addRow(focus_note)
        cpu_note = QLabel(
            "Для первого раза оставь значения как есть. Обучение идёт на процессоре: RX 580 не используется, "
            "поэтому процесс может быть долгим. Исходные веса Qwen не меняются."
        )
        cpu_note.setObjectName("hint")
        cpu_note.setWordWrap(True)
        settings_form.addRow(cpu_note)
        root.addWidget(settings)

        self.progress_label = QLabel("Готово к обучению")
        self.progress_label.setObjectName("hint")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFormat("%p%")
        root.addWidget(self.progress_label)
        root.addWidget(self.progress)

        buttons = QHBoxLayout()
        self.train_button = QPushButton("3. Дообучить Qwen")
        self.train_button.setObjectName("primaryButton")
        self.train_button.clicked.connect(self.start_training)
        self.stop_button = QPushButton("Остановить и сохранить")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_training)
        buttons.addWidget(self.train_button)
        buttons.addWidget(self.stop_button)
        buttons.addStretch(1)
        root.addLayout(buttons)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(115)
        self.log.setPlaceholderText("Здесь будет ход обучения.")
        root.addWidget(self.log)

        chat_group = QGroupBox("4. Пообщайся с дообученной моделью")
        chat_layout = QVBoxLayout(chat_group)
        adapter_row = QHBoxLayout()
        self.adapter_edit = QLineEdit()
        self.adapter_edit.setPlaceholderText("После обучения выберется автоматически")
        adapter_row.addWidget(self.adapter_edit, 1)
        self.adapter_button = QPushButton("Выбрать адаптер")
        self.adapter_button.setObjectName("secondaryButton")
        self.adapter_button.clicked.connect(self.choose_adapter)
        adapter_row.addWidget(self.adapter_button)
        chat_layout.addLayout(adapter_row)

        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setMinimumHeight(140)
        self.chat_view.setPlaceholderText("Например: как найти крепость в Нижнем мире?")
        chat_layout.addWidget(self.chat_view)
        chat_input_row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Напиши вопрос о Minecraft")
        self.chat_input.returnPressed.connect(self.send_message)
        chat_input_row.addWidget(self.chat_input, 1)
        self.send_button = QPushButton("Отправить")
        self.send_button.setObjectName("primaryButton")
        self.send_button.clicked.connect(self.send_message)
        chat_input_row.addWidget(self.send_button)
        self.clear_chat_button = QPushButton("Очистить чат")
        self.clear_chat_button.setObjectName("secondaryButton")
        self.clear_chat_button.clicked.connect(self.clear_chat)
        chat_input_row.addWidget(self.clear_chat_button)
        chat_layout.addLayout(chat_input_row)
        root.addWidget(chat_group, 1)

        self.statusBar().showMessage("Готово")
        self._apply_style()

    @staticmethod
    def _path_field(path: Path) -> QLineEdit:
        edit = QLineEdit(str(path))
        edit.setReadOnly(True)
        return edit

    def _add_folder_row(self, form: QFormLayout, label: str, edit: QLineEdit, button_text: str) -> None:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        button = QPushButton(button_text)
        button.setObjectName("secondaryButton")
        button.clicked.connect(lambda: self.choose_folder(edit, label))
        layout.addWidget(edit, 1)
        layout.addWidget(button)
        form.addRow(label, row)

    def choose_folder(self, edit: QLineEdit, title: str) -> None:
        selected = QFileDialog.getExistingDirectory(self, title, edit.text())
        if selected:
            edit.setText(selected)

    def _avoid_topics(self) -> list[str]:
        lines = [line.strip()[:80] for line in self.avoid_topics_edit.toPlainText().splitlines() if line.strip()]
        unique: list[str] = []
        seen: set[str] = set()
        for topic in lines:
            key = topic.casefold()
            if key not in seen:
                seen.add(key)
                unique.append(topic)
        return unique[:20]

    def start_training(self) -> None:
        if self.training_worker is not None or self.chat_worker is not None:
            return
        model_dir = Path(self.model_dir_edit.text()).expanduser()
        data_dir = Path(self.data_dir_edit.text()).expanduser()
        output_dir = Path(self.output_dir_edit.text()).expanduser()
        try:
            validate_model_folder(model_dir)
            if not data_dir.is_dir():
                raise FileNotFoundError("Не найдена папка с Minecraft-текстами.")
            text_files = _text_files(data_dir)
            if model_dir.resolve() == output_dir.resolve() or model_dir.resolve() in output_dir.resolve().parents:
                raise ValueError("Папку результата выбери отдельно от папки Qwen.")
            if data_dir.resolve() == output_dir.resolve() or data_dir.resolve() in output_dir.resolve().parents:
                raise ValueError("Папку результата выбери отдельно от папки текстов.")
        except Exception as exc:
            QMessageBox.warning(self, "Проверь папки", str(exc))
            return

        size_mb = sum(path.stat().st_size for path in text_files) / (1024 * 1024)
        confirmation = QMessageBox.question(
            self,
            "Начать дообучение?",
            f"Найдено файлов: {len(text_files)} ({size_mb:.1f} МБ). Обучение идёт на CPU и может занять много времени. Продолжить?",
        )
        if confirmation != QMessageBox.StandardButton.Yes:
            return

        self.training_worker = QwenTrainingWorker(
            model_dir=model_dir,
            data_dir=data_dir,
            output_dir=output_dir,
            sequence_length=self.context_spin.value(),
            epochs=self.epochs_spin.value(),
            learning_rate=self.learning_rate_spin.value(),
            lora_rank=self.rank_spin.value(),
            cpu_threads=self.threads_spin.value(),
            avoid_topics=self._avoid_topics(),
        )
        self.training_worker.progress.connect(self.on_training_progress)
        self.training_worker.message.connect(self.append_log)
        self.training_worker.completed.connect(self.on_training_complete)
        self.training_worker.failed.connect(self.on_training_error)
        self.training_worker.finished.connect(self.on_training_finished)
        self.train_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.send_button.setEnabled(False)
        self.progress.setValue(0)
        self.progress_label.setText("Загружаю исходную модель…")
        self.append_log("Запускаю дообучение Minecraft-текстами.")
        self.training_worker.start()

    def stop_training(self) -> None:
        if self.training_worker is not None:
            self.training_worker.request_stop()
            self.stop_button.setEnabled(False)
            self.progress_label.setText("Останавливаю и сохраняю LoRA-адаптер…")

    def append_log(self, text: str) -> None:
        self.log.append(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def on_training_progress(self, data: dict[str, object]) -> None:
        self.progress.setValue(int(data.get("percent", 0)))
        label = str(data.get("message", "Обучение Qwen"))
        loss = data.get("train_loss")
        if isinstance(loss, (int, float)):
            label += f" · ошибка {float(loss):.4f} · шаг {data.get('step', 0)}"
        self.progress_label.setText(label)

    def on_training_complete(self, adapter_dir: str) -> None:
        self.adapter_edit.setText(adapter_dir)
        stopped = "Остановлено" in self.progress_label.text()
        self.progress.setValue(100 if not stopped else self.progress.value())
        self.progress_label.setText("Остановлено, адаптер сохранён." if stopped else "Дообучение завершено.")
        self.append_log(f"Адаптер сохранён: {adapter_dir}")
        self.messages.clear()
        self.chat_view.clear()

    def on_training_error(self, error: str) -> None:
        self.progress_label.setText("Не удалось дообучить Qwen.")
        self.append_log(f"ОШИБКА: {error}")
        QMessageBox.critical(self, "Ошибка обучения", error)

    def on_training_finished(self) -> None:
        self.training_worker = None
        self.train_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.send_button.setEnabled(True)

    def choose_adapter(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, "Выбери папку с LoRA-адаптером", self.output_dir_edit.text()
        )
        if selected:
            self.adapter_edit.setText(selected)
            self.messages.clear()
            self.chat_view.clear()

    def send_message(self) -> None:
        if self.chat_worker is not None or self.training_worker is not None:
            return
        model_dir = Path(self.model_dir_edit.text()).expanduser()
        adapter_dir = Path(self.adapter_edit.text()).expanduser()
        question = self.chat_input.text().strip()
        if not question:
            return
        if not adapter_dir.is_dir():
            QMessageBox.information(self, "Сначала обучи Qwen", "Сначала нажми «Дообучить Qwen» или выбери папку адаптера.")
            return
        if not self.messages:
            system_prompt = (
                "Ты дружелюбный русскоязычный помощник по Minecraft. Отвечай ясно и по существу. "
                "Если не уверен или важна версия игры, скажи об этом и уточни версию. "
                "Если вопрос не о Minecraft, не обсуждай исходную тему и не отказывай; естественно переведи разговор на Minecraft."
            )
            topics = self._avoid_topics()
            if topics:
                system_prompt += " Не углубляйся в эти темы: " + ", ".join(topics) + "."
            self.messages.append({"role": "system", "content": system_prompt})
        self.messages.append({"role": "user", "content": question})
        self.chat_view.append(f"Ты: {question}")
        self.chat_input.clear()
        self.send_button.setEnabled(False)
        self.train_button.setEnabled(False)
        history = [self.messages[0]] + [
            item for item in self.messages[1:] if item.get("role") in {"user", "assistant"}
        ][-12:]
        self.chat_worker = QwenChatWorker(
            model_dir=model_dir,
            adapter_dir=adapter_dir,
            messages=history,
            max_new_tokens=256,
            cpu_threads=self.threads_spin.value(),
        )
        self.chat_worker.completed.connect(self.on_chat_complete)
        self.chat_worker.failed.connect(self.on_chat_error)
        self.chat_worker.finished.connect(self.on_chat_finished)
        self.chat_worker.start()

    def on_chat_complete(self, answer: str) -> None:
        self.messages.append({"role": "assistant", "content": answer})
        self.chat_view.append(f"Qwen: {answer}\n")
        self.statusBar().showMessage("Ответ готов")

    def on_chat_error(self, error: str) -> None:
        if self.messages and self.messages[-1].get("role") == "user":
            self.messages.pop()
        self.append_log(f"Ошибка чата: {error}")
        QMessageBox.critical(self, "Ошибка чата", error)

    def on_chat_finished(self) -> None:
        self.chat_worker = None
        self.send_button.setEnabled(True)
        self.train_button.setEnabled(True)

    def clear_chat(self) -> None:
        self.messages.clear()
        self.chat_view.clear()

    def _apply_style(self) -> None:
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #17171d; color: #eee8e5; }
            QWidget { font-size: 13px; }
            QLabel#title { color: #fff0e8; font-size: 25px; font-weight: 700; }
            QLabel#notice { background: #332721; border: 1px solid #705044; border-radius: 8px; padding: 10px; color: #f0c39b; }
            QLabel#hint { color: #c1b6b3; }
            QGroupBox { background: #1e1d24; border: 1px solid #3a343b; border-radius: 10px; margin-top: 12px; padding: 12px; font-size: 14px; font-weight: 600; color: #f0c1ae; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; }
            QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit { background: #28272f; color: #f3ece9; border: 1px solid #49414a; border-radius: 6px; padding: 7px; min-height: 30px; selection-background-color: #bd6e63; }
            QPushButton { background: #302c34; color: #f2e7e2; border: 1px solid #51444b; border-radius: 7px; padding: 9px 12px; min-height: 32px; font-weight: 600; }
            QPushButton:hover { background: #40343a; }
            QPushButton:disabled { color: #777178; }
            QPushButton#primaryButton { background: #bf7059; color: white; border: none; }
            QPushButton#stopButton { background: #3a292e; color: #efb5aa; }
            QProgressBar { border: 1px solid #49414a; border-radius: 6px; background: #28272f; height: 20px; text-align: center; }
            QProgressBar::chunk { background: #c87761; border-radius: 5px; }
            QStatusBar { color: #b8aaa8; }
            """
        )


def run_app() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Мастерская Minecraft-модели")
    window = MainWindow()
    window.show()
    return app.exec()
