"""Minimal, colorful desktop UI for training and testing a small language model."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import TrainingConfig
from app.system_info import DeviceOption, format_bytes, get_hardware_report
from app.workers import GenerationWorker, TrainingWorker

APP_ROOT = Path(__file__).resolve().parent.parent


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Мастерская модели")
        self.resize(1060, 820)
        self.setMinimumSize(880, 680)
        self.training_worker: TrainingWorker | None = None
        self.generation_worker: GenerationWorker | None = None
        self.hardware = get_hardware_report()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(16)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Мастерская модели")
        title.setObjectName("title")
        subtitle = QLabel("Обучай локально на своих текстах — без отправки данных в интернет")
        subtitle.setObjectName("subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)
        self.refresh_button = QPushButton("Обновить железо")
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.clicked.connect(self.refresh_hardware)
        header.addWidget(self.refresh_button, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(header)

        self.hardware_card = QFrame()
        self.hardware_card.setObjectName("hardwareCard")
        hardware_layout = QGridLayout(self.hardware_card)
        hardware_layout.setContentsMargins(16, 12, 16, 12)
        hardware_layout.setHorizontalSpacing(18)
        self.cpu_label = QLabel()
        self.ram_label = QLabel()
        self.gpu_label = QLabel()
        self.backend_label = QLabel()
        self.backend_label.setObjectName("hint")
        hardware_layout.addWidget(self._field_label("ПРОЦЕССОР"), 0, 0)
        hardware_layout.addWidget(self._field_label("ОПЕРАТИВНАЯ ПАМЯТЬ"), 0, 1)
        hardware_layout.addWidget(self._field_label("ВИДЕОКАРТА"), 0, 2)
        hardware_layout.addWidget(self.cpu_label, 1, 0)
        hardware_layout.addWidget(self.ram_label, 1, 1)
        hardware_layout.addWidget(self.gpu_label, 1, 2)
        hardware_layout.addWidget(self.backend_label, 2, 0, 1, 3)
        root.addWidget(self.hardware_card)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_training_tab(), "Обучение")
        self.tabs.addTab(self._build_generation_tab(), "Проверка текста")
        root.addWidget(self.tabs, 1)
        self.statusBar().showMessage("Готово к работе")
        self.refresh_hardware()
        self._apply_style()

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _build_training_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 14, 8, 8)
        layout.setSpacing(12)

        data_group = QGroupBox("Данные и сохранение")
        data_form = QFormLayout(data_group)
        data_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.data_dir_edit = QLineEdit(str(APP_ROOT / "data" / "texts"))
        self.data_dir_edit.setPlaceholderText("Выбери папку со своими .txt файлами")
        self.data_dir_edit.setReadOnly(True)
        data_row, self.data_browse_button = self._path_row(self.data_dir_edit, "Выбрать папку")
        self.data_browse_button.clicked.connect(self._choose_data_dir)
        data_form.addRow("Папка с .txt", data_row)

        self.output_dir_edit = QLineEdit(str(APP_ROOT / "runs"))
        self.output_dir_edit.setReadOnly(True)
        output_row, self.output_browse_button = self._path_row(self.output_dir_edit, "Куда сохранять")
        self.output_browse_button.clicked.connect(self._choose_output_dir)
        data_form.addRow("Модели и отчёты", output_row)
        layout.addWidget(data_group)

        settings_group = QGroupBox("Параметры обучения")
        grid = QGridLayout(settings_group)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        self.device_combo = QComboBox()
        self.device_combo.addItem("Автоматически", "auto")
        self.device_combo.addItem("CPU", "cpu")
        self._fill_device_options()
        self.device_combo.setToolTip("Авто выбирает доступное ускорение, иначе использует CPU.")

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Маленькая", "Сбалансированная", "Покрупнее"])
        self.preset_combo.setToolTip("Для первого запуска рекомендуется маленькая модель.")

        self.context_combo = QComboBox()
        self.context_combo.addItems(["128", "256", "384", "512"])
        self.context_combo.setCurrentText("128")
        self.batch_combo = QComboBox()
        self.batch_combo.addItems(["2", "4", "8", "16"])
        self.batch_combo.setCurrentText("4")
        self.vocab_combo = QComboBox()
        self.vocab_combo.addItems(["2048", "4096", "8192"])
        self.vocab_combo.setCurrentText("2048")

        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 100)
        self.epochs_spin.setValue(2)
        self.epochs_spin.setSuffix(" эпох")
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, max(1, int(self.hardware.get("logical_cores", 1))))
        self.threads_spin.setValue(min(6, max(1, int(self.hardware.get("logical_cores", 1)))))
        self.threads_spin.setSuffix(" потоков")

        self._add_setting(grid, 0, 0, "Устройство", self.device_combo)
        self._add_setting(grid, 0, 1, "Размер модели", self.preset_combo)
        self._add_setting(grid, 1, 0, "Контекст", self.context_combo)
        self._add_setting(grid, 1, 1, "Пакет примеров", self.batch_combo)
        self._add_setting(grid, 2, 0, "Словарь токенов", self.vocab_combo)
        self._add_setting(grid, 2, 1, "Процессор", self.threads_spin)
        self._add_setting(grid, 3, 0, "Проходы по данным", self.epochs_spin)
        memory_hint = QLabel("Память регулируется размером модели, контекстом и пакетом.")
        memory_hint.setObjectName("hint")
        grid.addWidget(memory_hint, 3, 1)
        layout.addWidget(settings_group)

        info = QLabel(
            "Учебная модель с нуля может генерировать ошибки и повторять текст. "
            "Для начала используй небольшие .txt-файлы и модель «Маленькая»."
        )
        info.setObjectName("notice")
        info.setWordWrap(True)
        layout.addWidget(info)

        progress_group = QGroupBox("Прогресс")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_stage = QLabel("Ожидает запуска")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_details = QLabel("Эпоха — · шаг — · ошибка —")
        self.progress_details.setObjectName("hint")
        progress_layout.addWidget(self.progress_stage)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_details)
        layout.addWidget(progress_group)

        controls = QHBoxLayout()
        self.start_button = QPushButton("Начать обучение")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self.start_training)
        self.stop_button = QPushButton("Остановить и сохранить")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_training)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Здесь появится ход обучения и сообщения программы.")
        self.log_view.setMaximumHeight(150)
        layout.addWidget(self.log_view)
        return page

    def _build_generation_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 14, 8, 8)
        layout.setSpacing(12)

        checkpoint_group = QGroupBox("Обученная модель")
        checkpoint_form = QFormLayout(checkpoint_group)
        self.checkpoint_edit = QLineEdit()
        self.checkpoint_edit.setReadOnly(True)
        self.checkpoint_edit.setPlaceholderText("Здесь появится файл latest.pt после обучения")
        checkpoint_row, self.checkpoint_browse_button = self._path_row(
            self.checkpoint_edit, "Выбрать модель"
        )
        self.checkpoint_browse_button.clicked.connect(self._choose_checkpoint)
        checkpoint_form.addRow("Контрольная точка", checkpoint_row)
        layout.addWidget(checkpoint_group)

        prompt_group = QGroupBox("Проверить генерацию")
        prompt_layout = QVBoxLayout(prompt_group)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Напиши начало текста — модель попробует его продолжить…")
        self.prompt_edit.setFixedHeight(105)
        prompt_layout.addWidget(self.prompt_edit)

        options = QHBoxLayout()
        options.addWidget(QLabel("Новых токенов"))
        self.generation_length = QSpinBox()
        self.generation_length.setRange(8, 512)
        self.generation_length.setValue(96)
        options.addWidget(self.generation_length)
        options.addSpacing(14)
        options.addWidget(QLabel("Случайность"))
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.1, 1.5)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(0.8)
        options.addWidget(self.temperature)
        options.addStretch(1)
        self.generate_button = QPushButton("Сгенерировать")
        self.generate_button.setObjectName("primaryButton")
        self.generate_button.clicked.connect(self.generate_text)
        options.addWidget(self.generate_button)
        prompt_layout.addLayout(options)
        layout.addWidget(prompt_group)

        result_group = QGroupBox("Результат")
        result_layout = QVBoxLayout(result_group)
        self.generated_text = QTextEdit()
        self.generated_text.setReadOnly(True)
        self.generated_text.setPlaceholderText("Ответ модели появится здесь.")
        result_layout.addWidget(self.generated_text)
        layout.addWidget(result_group, 1)
        return page

    @staticmethod
    def _path_row(edit: QLineEdit, button_text: str) -> tuple[QWidget, QPushButton]:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        button = QPushButton(button_text)
        button.setObjectName("secondaryButton")
        layout.addWidget(edit, 1)
        layout.addWidget(button)
        return row, button

    @staticmethod
    def _add_setting(grid: QGridLayout, row: int, column: int, label: str, widget: QWidget) -> None:
        cell = QWidget()
        layout = QVBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        text = QLabel(label)
        text.setObjectName("fieldLabel")
        layout.addWidget(text)
        layout.addWidget(widget)
        grid.addWidget(cell, row, column)

    def _fill_device_options(self) -> None:
        current = self.device_combo.currentData() if hasattr(self, "device_combo") else "auto"
        if not hasattr(self, "device_combo"):
            return
        while self.device_combo.count() > 2:
            self.device_combo.removeItem(2)
        devices = self.hardware.get("devices", [])
        if isinstance(devices, list):
            for option in devices:
                if not isinstance(option, DeviceOption) or option.key == "cpu":
                    continue
                self.device_combo.addItem(f"GPU · {option.label}", option.key)
        index = self.device_combo.findData(current)
        self.device_combo.setCurrentIndex(max(index, 0))

    def refresh_hardware(self) -> None:
        self.hardware = get_hardware_report()
        self.cpu_label.setText(
            f"{self.hardware['cpu_name']} · {self.hardware['physical_cores']} ядра / "
            f"{self.hardware['logical_cores']} пот.")
        self.ram_label.setText(
            f"{format_bytes(self.hardware['available_ram'])} доступно / "
            f"{format_bytes(self.hardware['total_ram'])} всего")
        self.gpu_label.setText("; ".join(self.hardware["gpu_names"]))
        note = str(self.hardware.get("backend_note", ""))
        supported = [
            option.label
            for option in self.hardware.get("devices", [])
            if isinstance(option, DeviceOption) and option.key != "cpu"
        ]
        if supported:
            note = "Доступное ускорение: " + ", ".join(supported)
        elif not note:
            note = "GPU будет доступна только если её поддерживает установленный PyTorch-бэкенд."
        self.backend_label.setText(note)
        if hasattr(self, "device_combo"):
            self._fill_device_options()
        if hasattr(self, "threads_spin"):
            max_threads = max(1, int(self.hardware.get("logical_cores", 1)))
            current_threads = min(self.threads_spin.value(), max_threads)
            self.threads_spin.setMaximum(max_threads)
            self.threads_spin.setValue(max(1, current_threads))

    def _choose_data_dir(self) -> None:
        current = self.data_dir_edit.text()
        directory = QFileDialog.getExistingDirectory(self, "Выбери папку с .txt-файлами", current)
        if directory:
            self.data_dir_edit.setText(directory)

    def _choose_output_dir(self) -> None:
        current = self.output_dir_edit.text()
        directory = QFileDialog.getExistingDirectory(self, "Выбери папку для результатов", current)
        if directory:
            self.output_dir_edit.setText(directory)

    def _choose_checkpoint(self) -> None:
        current = self.checkpoint_edit.text() or str(APP_ROOT / "runs")
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Выбери контрольную точку модели",
            current,
            "Файл модели (*.pt)",
        )
        if filename:
            self.checkpoint_edit.setText(filename)

    def _append_log(self, text: str) -> None:
        self.log_view.append(text)
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def start_training(self) -> None:
        data_dir = Path(self.data_dir_edit.text())
        output_dir = Path(self.output_dir_edit.text())
        if not data_dir.is_dir():
            QMessageBox.warning(self, "Нет папки с текстами", "Выбери существующую папку с .txt-файлами.")
            return
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                QMessageBox.critical(self, "Не удалось создать папку", str(exc))
                return
        data_path = data_dir.resolve()
        output_path = output_dir.resolve()
        if (
            data_path == output_path
            or data_path in output_path.parents
            or output_path in data_path.parents
        ):
            QMessageBox.warning(
                self,
                "Выбери отдельные папки",
                "Папка с текстами и папка результатов не должны совпадать или находиться одна внутри другой.",
            )
            return

        config = TrainingConfig(
            data_dir=data_dir,
            output_dir=output_dir,
            device=str(self.device_combo.currentData()),
            preset=self.preset_combo.currentText(),
            context_length=int(self.context_combo.currentText()),
            batch_size=int(self.batch_combo.currentText()),
            epochs=self.epochs_spin.value(),
            vocab_size=int(self.vocab_combo.currentText()),
            cpu_threads=self.threads_spin.value(),
        )
        self.training_worker = TrainingWorker(config)
        self.training_worker.progress.connect(self._on_training_progress)
        self.training_worker.message.connect(self._append_log)
        self.training_worker.completed.connect(self._on_training_complete)
        self.training_worker.failed.connect(self._on_training_error)
        self.training_worker.finished.connect(self._on_training_thread_finished)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_stage.setText("Подготовка…")
        self.progress_details.setText("Эпоха — · шаг — · ошибка —")
        self._append_log("— Запуск нового обучения —")
        self.statusBar().showMessage("Обучение запущено")
        self.training_worker.start()

    def stop_training(self) -> None:
        if self.training_worker is not None:
            self.training_worker.request_stop()
            self.stop_button.setEnabled(False)
            self.progress_stage.setText("Останавливаю после текущего шага и сохраняю модель…")
            self._append_log("Запрошена остановка. Текущая эпоха будет сохранена.")

    def _on_training_progress(self, data: dict[str, object]) -> None:
        self.progress_stage.setText(str(data.get("message") or data.get("stage", "Обучение")))
        self.progress_bar.setValue(int(data.get("percent", 0)))
        epoch = data.get("epoch", "—")
        epochs = data.get("epochs", "—")
        step = data.get("step", data.get("global_step", "—"))
        steps = data.get("steps_per_epoch", data.get("total_steps", "—"))
        loss = data.get("train_loss")
        loss_text = f"{float(loss):.4f}" if isinstance(loss, (int, float)) else "—"
        self.progress_details.setText(f"Эпоха {epoch}/{epochs} · шаг {step}/{steps} · ошибка {loss_text}")

    def _on_training_complete(self, path: str) -> None:
        self.checkpoint_edit.setText(path)
        stopped = self.progress_stage.text() == "Остановлено"
        if stopped:
            self.statusBar().showMessage("Обучение остановлено; контрольная точка сохранена")
            self._append_log("Сохранённую контрольную точку можно выбрать во вкладке «Проверка текста».")
        else:
            self.progress_bar.setValue(100)
            self.statusBar().showMessage("Обучение завершено; контрольная точка сохранена")
            self._append_log(
                "Модель готова. Перейди во вкладку «Проверка текста», чтобы попробовать генерацию."
            )

    def _on_training_error(self, error: str) -> None:
        self.statusBar().showMessage("Обучение завершилось с ошибкой")
        self._append_log(f"ОШИБКА: {error}")
        QMessageBox.critical(self, "Не удалось обучить модель", error)

    def _on_training_thread_finished(self) -> None:
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.training_worker = None

    def generate_text(self) -> None:
        checkpoint = Path(self.checkpoint_edit.text())
        if not checkpoint.is_file():
            QMessageBox.warning(self, "Нет модели", "Выбери файл latest.pt или сначала обучи модель.")
            return
        prompt = self.prompt_edit.toPlainText()
        if not prompt.strip():
            QMessageBox.warning(self, "Нужен текст", "Напиши начало текста, которое модель должна продолжить.")
            return
        self.generation_worker = GenerationWorker(
            checkpoint_path=checkpoint,
            prompt=prompt,
            device_key=str(self.device_combo.currentData()),
            max_new_tokens=self.generation_length.value(),
            temperature=self.temperature.value(),
        )
        self.generation_worker.completed.connect(self._on_generation_complete)
        self.generation_worker.failed.connect(self._on_generation_error)
        self.generation_worker.finished.connect(self._on_generation_thread_finished)
        self.generate_button.setEnabled(False)
        self.generated_text.setPlainText("Генерирую…")
        self.generation_worker.start()

    def _on_generation_complete(self, text: str) -> None:
        self.generated_text.setPlainText(text)
        self.statusBar().showMessage("Генерация завершена")

    def _on_generation_error(self, error: str) -> None:
        self.generated_text.setPlainText("")
        self.statusBar().showMessage("Не удалось сгенерировать текст")
        QMessageBox.critical(self, "Ошибка генерации", error)

    def _on_generation_thread_finished(self) -> None:
        self.generate_button.setEnabled(True)
        self.generation_worker = None

    def _apply_style(self) -> None:
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #f3f7f5; color: #23352f; }
            QLabel#title { color: #1d4e45; font-size: 25px; font-weight: 700; }
            QLabel#subtitle { color: #687b74; font-size: 12px; }
            QFrame#hardwareCard { background: #e3f0eb; border: 1px solid #c9dfd6; border-radius: 12px; }
            QLabel#fieldLabel { color: #688078; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
            QLabel#hint { color: #687b74; font-size: 11px; }
            QGroupBox { background: #ffffff; border: 1px solid #d8e4df; border-radius: 11px; margin-top: 12px; padding: 12px; font-weight: 600; color: #315d52; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit { background: #fbfdfc; border: 1px solid #d6e2dd; border-radius: 7px; padding: 7px 9px; selection-background-color: #69a994; }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus { border: 1px solid #69a994; }
            QPushButton { background: #e6efeb; color: #31564d; border: 1px solid #cfddd7; border-radius: 8px; padding: 8px 13px; font-weight: 600; }
            QPushButton:hover { background: #dbeae4; }
            QPushButton:disabled { background: #edf1ef; color: #9aa9a3; border-color: #e1e7e4; }
            QPushButton#primaryButton { background: #438c78; color: white; border: none; padding: 10px 18px; }
            QPushButton#primaryButton:hover { background: #367965; }
            QPushButton#stopButton { background: #f5e9e4; color: #9a533f; border: 1px solid #ecd4ca; }
            QPushButton#secondaryButton { background: #edf4f1; }
            QLabel#notice { background: #fff4dc; border: 1px solid #f0dfb6; border-radius: 8px; padding: 9px 12px; color: #775d2e; }
            QProgressBar { border: 1px solid #d5e1dc; border-radius: 7px; background: #edf2ef; height: 20px; text-align: center; color: #284b41; }
            QProgressBar::chunk { background: #69a994; border-radius: 6px; }
            QTabWidget::pane { border: 1px solid #d8e4df; background: #f3f7f5; border-radius: 9px; }
            QTabBar::tab { background: #e6eeea; color: #60756d; padding: 9px 18px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; }
            QTabBar::tab:selected { background: #438c78; color: white; }
            QStatusBar { color: #657970; }
            """
        )


def run_app() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Мастерская модели")
    app.setOrganizationName("FlyDron")
    window = MainWindow()
    window.show()
    return app.exec()
