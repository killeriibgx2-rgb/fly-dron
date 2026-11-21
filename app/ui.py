"""Minimal, colorful desktop UI for training and testing a small language model."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Qt
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
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import TrainingConfig
from app.model import preset_values
from app.system_info import DeviceOption, format_bytes, get_hardware_report
from app.workers import GenerationWorker, ModelControlWorker, TrainingWorker

APP_ROOT = Path(__file__).resolve().parent.parent


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Мастерская модели")
        self.resize(1280, 900)
        self.setMinimumSize(900, 700)
        self.training_worker: TrainingWorker | None = None
        self.generation_worker: GenerationWorker | None = None
        self.model_control_worker: ModelControlWorker | None = None
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
        self.refresh_button = QPushButton("Обновить данные о ПК")
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
        self.tabs.addTab(self._scrollable(self._build_training_tab()), "Обучение")
        self.tabs.addTab(self._scrollable(self._build_generation_tab()), "Попробовать модель")
        root.addWidget(self.tabs, 1)
        self.statusBar().showMessage("Готово к работе")
        self.refresh_hardware()
        self._apply_style()

    @staticmethod
    def _scrollable(page: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setWidget(page)
        return area

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
        data_form.addRow("Папка с текстами", data_row)

        self.output_dir_edit = QLineEdit(str(APP_ROOT / "runs"))
        self.output_dir_edit.setReadOnly(True)
        output_row, self.output_browse_button = self._path_row(self.output_dir_edit, "Куда сохранять")
        self.output_browse_button.clicked.connect(self._choose_output_dir)
        data_form.addRow("Куда сохранять модель", output_row)
        layout.addWidget(data_group)

        continue_group = QGroupBox("Продолжить сохранённую модель")
        continue_form = QFormLayout(continue_group)
        self.model_dir_edit = QLineEdit()
        self.model_dir_edit.setReadOnly(True)
        self.model_dir_edit.setPlaceholderText("Выбери папку запуска из runs")
        model_row, self.model_browse_button = self._path_row(
            self.model_dir_edit, "Выбрать папку модели"
        )
        self.model_browse_button.clicked.connect(self._choose_model_dir)
        continue_form.addRow("Папка модели", model_row)
        continue_hint = QLabel(
            "Архитектура, контекст, dropout и словарь возьмутся из этой модели; настройки этих параметров ниже при продолжении не применяются. "
            "Папка с текстами выше должна содержать старые и новые файлы."
        )
        continue_hint.setObjectName("hint")
        continue_hint.setWordWrap(True)
        continue_form.addRow(continue_hint)
        layout.addWidget(continue_group)

        settings_group = QGroupBox("Параметры обучения")
        grid = QGridLayout(settings_group)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        self.device_combo = QComboBox()
        self.device_combo.addItem("Автоматически", "auto")
        self.device_combo.addItem("CPU", "cpu")
        self._fill_device_options()
        self.device_combo.setToolTip(
            "«Автоматически» использует поддерживаемую видеокарту, если она доступна; иначе работает на CPU."
        )

        self.preset_combo = QComboBox()
        self.preset_combo.addItems(
            [
                "Маленькая",
                "Сбалансированная",
                "Покрупнее",
                "Большая",
                "Очень большая",
                "Максимальная",
                "Своя",
            ]
        )
        self.preset_combo.setToolTip(
            "Выбор пресета выставляет размер трансформера ниже. Варианты «Большая» и выше требуют значительно больше памяти."
        )

        self.embedding_spin = QSpinBox()
        self.embedding_spin.setRange(64, 2048)
        self.embedding_spin.setSingleStep(32)
        self.embedding_spin.setValue(128)
        self.embedding_spin.setToolTip("Ширина скрытых представлений модели. Больше — больше параметров и расход VRAM.")
        self.layers_spin = QSpinBox()
        self.layers_spin.setRange(1, 48)
        self.layers_spin.setValue(2)
        self.layers_spin.setToolTip("Количество блоков трансформера. Больше блоков увеличивает объём вычислений и памяти.")
        self.heads_spin = QSpinBox()
        self.heads_spin.setRange(1, 32)
        self.heads_spin.setValue(4)
        self.heads_spin.setToolTip("Число голов внимания. Размер embedding должен делиться на это число.")

        self.context_spin = QSpinBox()
        self.context_spin.setRange(16, 4096)
        self.context_spin.setSingleStep(16)
        self.context_spin.setValue(128)
        self.context_spin.setToolTip(
            "Максимальная длина контекста. Внимание требует намного больше памяти при увеличении контекста."
        )
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 256)
        self.batch_spin.setValue(4)
        self.batch_spin.setToolTip(
            "Сколько примеров обрабатывать одновременно. Больший пакет может ускорить GPU, но заметно увеличивает расход VRAM."
        )
        self.vocab_spin = QSpinBox()
        self.vocab_spin.setRange(256, 65000)
        self.vocab_spin.setSingleStep(256)
        self.vocab_spin.setValue(2048)
        self.vocab_spin.setToolTip(
            "Максимальный размер словаря токенизатора. Больше — больше токенов различается, но увеличиваются модель и расход памяти."
        )

        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 10_000)
        self.epochs_spin.setValue(2)
        self.epochs_spin.setSuffix(" эпох")
        self.epochs_spin.setToolTip(
            "Одна эпоха — полный проход по обучающим текстам. До 10 000 для долгих запусков; это может занять очень много времени и привести к переобучению."
        )
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, max(1, int(self.hardware.get("logical_cores", 1))))
        self.threads_spin.setValue(min(6, max(1, int(self.hardware.get("logical_cores", 1)))))
        self.threads_spin.setSuffix(" потоков")
        self.threads_spin.setToolTip("Число потоков CPU. Больше не всегда быстрее и может сильнее занять компьютер.")

        self.learning_rate_spin = QDoubleSpinBox()
        self.learning_rate_spin.setDecimals(6)
        self.learning_rate_spin.setRange(0.000001, 0.01)
        self.learning_rate_spin.setSingleStep(0.00005)
        self.learning_rate_spin.setValue(0.0003)
        self.learning_rate_spin.setToolTip(
            "Скорость изменения весов. Слишком высокая может испортить обучение; для дообучения обычно выбирают меньшую."
        )
        self.weight_decay_spin = QDoubleSpinBox()
        self.weight_decay_spin.setDecimals(4)
        self.weight_decay_spin.setRange(0.0, 0.5)
        self.weight_decay_spin.setSingleStep(0.005)
        self.weight_decay_spin.setValue(0.01)
        self.weight_decay_spin.setToolTip("Регуляризация AdamW: помогает сдерживать слишком большие веса.")
        self.dropout_spin = QDoubleSpinBox()
        self.dropout_spin.setDecimals(2)
        self.dropout_spin.setRange(0.0, 0.8)
        self.dropout_spin.setSingleStep(0.05)
        self.dropout_spin.setValue(0.1)
        self.dropout_spin.setToolTip("Доля случайно выключаемых связей при обучении; помогает уменьшить переобучение.")
        self.gradient_clip_spin = QDoubleSpinBox()
        self.gradient_clip_spin.setDecimals(1)
        self.gradient_clip_spin.setRange(0.0, 10.0)
        self.gradient_clip_spin.setSingleStep(0.1)
        self.gradient_clip_spin.setValue(1.0)
        self.gradient_clip_spin.setToolTip("Ограничивает слишком большие градиенты. Ноль выключает ограничение.")
        self.optimizer_combo = QComboBox()
        self.optimizer_combo.addItems(["AdamW", "Adam"])
        self.optimizer_combo.setToolTip("Алгоритм оптимизации. AdamW обычно удобный вариант по умолчанию.")
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 2_147_483_647)
        self.seed_spin.setValue(42)
        self.seed_spin.setToolTip("Начальное случайное число. При одинаковых условиях помогает повторить запуск.")
        self.validation_spin = QSpinBox()
        self.validation_spin.setRange(1, 30)
        self.validation_spin.setValue(5)
        self.validation_spin.setSuffix(" %")
        self.validation_spin.setToolTip("Доля текстов, отложенная для проверки ошибки; она не участвует в обучении.")

        self.preset_combo.currentTextChanged.connect(self._apply_model_preset)
        for control in (self.embedding_spin, self.layers_spin, self.heads_spin):
            control.valueChanged.connect(self._mark_custom_model_preset)
        self._add_setting(grid, 0, 0, "Где считать", self.device_combo)
        self._add_setting(grid, 0, 1, "Готовый размер модели", self.preset_combo)
        self._add_setting(grid, 1, 0, "Ширина модели (embedding)", self.embedding_spin)
        self._add_setting(grid, 1, 1, "Слои трансформера", self.layers_spin)
        self._add_setting(grid, 2, 0, "Головы внимания", self.heads_spin)
        self._add_setting(grid, 2, 1, "Контекст, токенов", self.context_spin)
        self._add_setting(grid, 3, 0, "Примеров за шаг (batch)", self.batch_spin)
        self._add_setting(grid, 3, 1, "Максимум токенов словаря", self.vocab_spin)
        self._add_setting(grid, 4, 0, "Полных проходов по текстам", self.epochs_spin)
        self._add_setting(grid, 4, 1, "Потоков процессора", self.threads_spin)
        self._add_setting(grid, 5, 0, "Скорость обучения", self.learning_rate_spin)
        self._add_setting(grid, 5, 1, "Weight decay", self.weight_decay_spin)
        self._add_setting(grid, 6, 0, "Dropout", self.dropout_spin)
        self._add_setting(grid, 6, 1, "Ограничение градиента", self.gradient_clip_spin)
        self._add_setting(grid, 7, 0, "Случайное зерно (seed)", self.seed_spin)
        self._add_setting(grid, 7, 1, "Оптимизатор", self.optimizer_combo)
        self._add_setting(grid, 8, 0, "Тексты на проверку", self.validation_spin)
        memory_hint = QLabel(
            "Если не хватает памяти, уменьши сначала batch, затем контекст или модель. При продолжении архитектура берётся из checkpoint."
        )
        memory_hint.setObjectName("hint")
        memory_hint.setWordWrap(True)
        grid.addWidget(memory_hint, 8, 1)
        layout.addWidget(settings_group)

        info = QLabel(
            "Для первого запуска выбери модель «Маленькая», контекст 128–256, пакет 2–4 и 2–5 эпох. "
            "Одна эпоха — полный проход по текстам; 10 000 эпох доступны для длинных экспериментов, но могут занять очень долго и привести к переобучению. "
            "Сейчас модель учится продолжать текст, а не понимать команды."
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
        self.progress_details = QLabel("Проход — · шаг — · показатель ошибки —")
        self.progress_details.setObjectName("hint")
        self.progress_details.setToolTip(
            "Показатель ошибки обычно снижается по мере обучения. Сам по себе он не гарантирует, что модель хорошо разговаривает."
        )
        progress_layout.addWidget(self.progress_stage)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_details)
        layout.addWidget(progress_group)

        controls = QHBoxLayout()
        self.start_button = QPushButton("Обучить с нуля")
        self.start_button.setObjectName("secondaryButton")
        self.start_button.clicked.connect(self.start_training)
        self.continue_button = QPushButton("Продолжить обучение")
        self.continue_button.setObjectName("primaryButton")
        self.continue_button.setToolTip(
            "Загрузить сохранённые веса и продолжить на выбранной папке со старыми и новыми текстами."
        )
        self.continue_button.clicked.connect(self.continue_training)
        self.stop_button = QPushButton("Остановить и сохранить")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_training)
        controls.addWidget(self.start_button)
        controls.addWidget(self.continue_button)
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
        checkpoint_form.addRow("Файл модели", checkpoint_row)
        layout.addWidget(checkpoint_group)

        memory_group = QGroupBox("Загрузка модели в память")
        memory_layout = QHBoxLayout(memory_group)
        self.model_memory_status = QLabel("Модель не загружена в память")
        self.model_memory_status.setObjectName("hint")
        self.load_model_button = QPushButton("Загрузить в RAM / VRAM")
        self.load_model_button.setObjectName("primaryButton")
        self.load_model_button.setToolTip(
            "Загружает модель на выбранное устройство: CPU использует системную RAM, GPU — видеопамять."
        )
        self.load_model_button.clicked.connect(self.load_generation_model)
        self.unload_model_button = QPushButton("Выгрузить из памяти")
        self.unload_model_button.setObjectName("secondaryButton")
        self.unload_model_button.clicked.connect(self.unload_generation_model)
        memory_layout.addWidget(self.model_memory_status, 1)
        memory_layout.addWidget(self.load_model_button)
        memory_layout.addWidget(self.unload_model_button)
        layout.addWidget(memory_group)

        prompt_group = QGroupBox("Напиши начало фразы для модели")
        prompt_layout = QVBoxLayout(prompt_group)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Напиши начало текста — модель попробует его продолжить…")
        self.prompt_edit.setFixedHeight(105)
        prompt_layout.addWidget(self.prompt_edit)

        options = QHBoxLayout()
        options.addWidget(QLabel("Длина ответа"))
        self.generation_length = QSpinBox()
        self.generation_length.setRange(8, 512)
        self.generation_length.setValue(96)
        self.generation_length.setToolTip("Сколько частей текста модель добавит к твоему началу фразы.")
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

    def _apply_model_preset(self, preset: str) -> None:
        if preset == "Своя":
            return
        embedding_size, layers, heads = preset_values(preset)
        blockers = [
            QSignalBlocker(self.embedding_spin),
            QSignalBlocker(self.layers_spin),
            QSignalBlocker(self.heads_spin),
        ]
        self.embedding_spin.setValue(embedding_size)
        self.layers_spin.setValue(layers)
        self.heads_spin.setValue(heads)
        del blockers

    def _mark_custom_model_preset(self, _value: int) -> None:
        if self.preset_combo.currentText() != "Своя":
            self.preset_combo.setCurrentText("Своя")

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
        if self.device_combo.count() > 2:
            self.device_combo.setItemText(0, "Автоматически")
        else:
            self.device_combo.setItemText(0, "Автоматически — сейчас CPU")
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
        supported = [
            option.label
            for option in self.hardware.get("devices", [])
            if isinstance(option, DeviceOption) and option.key != "cpu"
        ]
        detected_gpus = self.hardware.get("gpu_names", [])
        directml_devices = [
            option.label
            for option in self.hardware.get("devices", [])
            if isinstance(option, DeviceOption) and option.key.startswith("directml:")
        ]
        if directml_devices:
            note = (
                "DirectML найден: "
                + ", ".join(directml_devices)
                + ". Режим экспериментальный; перед обучением проверим операции."
            )
        elif supported:
            note = "Можно обучать на видеокарте: " + ", ".join(supported)
        elif detected_gpus and detected_gpus[0] != "Видеокарта не обнаружена системой":
            note = "Видеокарта найдена, но ускорение не подключено. Пока можно обучать на процессоре."
        elif self.hardware.get("backend_note"):
            note = "Не удалось проверить видеокарту. Процессор доступен для обучения."
        else:
            note = "Для первого запуска оставь «Автоматически» — программа выберет доступный вариант."
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

    def _choose_model_dir(self) -> None:
        current = self.model_dir_edit.text() or str(APP_ROOT / "runs")
        directory = QFileDialog.getExistingDirectory(
            self, "Выбери папку запуска с latest.pt и tokenizer.json", current
        )
        if directory:
            self.model_dir_edit.setText(directory)

    def _choose_checkpoint(self) -> None:
        current = self.checkpoint_edit.text() or str(APP_ROOT / "runs")
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Выбери файл обученной модели",
            current,
            "Файл модели (*.pt)",
        )
        if filename:
            self.checkpoint_edit.setText(filename)
            self.model_memory_status.setText("Файл выбран; нажми «Загрузить в RAM / VRAM».")

    def _append_log(self, text: str) -> None:
        self.log_view.append(text)
        if text.startswith("Выгрузил модель генерации"):
            self.model_memory_status.setText("Выгружена автоматически перед обучением.")
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def start_training(self) -> None:
        self._launch_training(continue_from=None)

    def continue_training(self) -> None:
        model_dir_text = self.model_dir_edit.text().strip()
        if not model_dir_text:
            QMessageBox.warning(self, "Не выбрана модель", "Сначала выбери папку запуска с сохранённой моделью.")
            return
        self._launch_training(continue_from=Path(model_dir_text))

    def _launch_training(self, continue_from: Path | None) -> None:
        if continue_from is None and self.embedding_spin.value() % self.heads_spin.value() != 0:
            QMessageBox.warning(
                self,
                "Несовместимые размеры модели",
                "Ширина модели должна делиться на число голов внимания. Измени embedding или число голов.",
            )
            return
        if self.epochs_spin.value() >= 1000:
            answer = QMessageBox.question(
                self,
                "Очень долгий запуск",
                f"Выбрано {self.epochs_spin.value():,} эпох. Одна эпоха — полный проход по текстам; запуск может длиться очень долго и переобучить модель. Продолжить?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        data_dir = Path(self.data_dir_edit.text())
        output_dir = Path(self.output_dir_edit.text())
        if not data_dir.is_dir():
            QMessageBox.warning(self, "Нет папки с текстами", "Выбери существующую папку с .txt-файлами.")
            return
        if continue_from is not None:
            if not continue_from.is_dir() or not (continue_from / "latest.pt").is_file():
                QMessageBox.warning(
                    self,
                    "Не найдена модель",
                    "В выбранной папке должен лежать файл latest.pt.",
                )
                return
            if continue_from.resolve() == output_dir.resolve() or continue_from.resolve() in output_dir.resolve().parents:
                QMessageBox.warning(
                    self,
                    "Выбери другую папку для результата",
                    "Новая версия должна сохраняться отдельно от исходной модели. Выбери родительскую папку results или runs.",
                )
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
            context_length=self.context_spin.value(),
            batch_size=self.batch_spin.value(),
            epochs=self.epochs_spin.value(),
            learning_rate=self.learning_rate_spin.value(),
            optimizer=str(self.optimizer_combo.currentText()),
            weight_decay=self.weight_decay_spin.value(),
            gradient_clip=self.gradient_clip_spin.value(),
            dropout=self.dropout_spin.value(),
            embedding_size=self.embedding_spin.value(),
            layers=self.layers_spin.value(),
            heads=self.heads_spin.value(),
            vocab_size=self.vocab_spin.value(),
            validation_percent=self.validation_spin.value(),
            cpu_threads=self.threads_spin.value(),
            seed=self.seed_spin.value(),
            continue_from=continue_from,
        )
        self.training_worker = TrainingWorker(config)
        self.training_worker.progress.connect(self._on_training_progress)
        self.training_worker.message.connect(self._append_log)
        self.training_worker.completed.connect(self._on_training_complete)
        self.training_worker.failed.connect(self._on_training_error)
        self.training_worker.finished.connect(self._on_training_thread_finished)
        self.start_button.setEnabled(False)
        self.continue_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.generate_button.setEnabled(False)
        self.load_model_button.setEnabled(False)
        self.unload_model_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_stage.setText("Подготовка…")
        self.progress_details.setText("Проход — · шаг — · показатель ошибки —")
        self._append_log(
            "— Продолжение обучения с сохранённых весов —" if continue_from else "— Запуск нового обучения —"
        )
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
        self.progress_details.setText(
            f"Проход {epoch}/{epochs} · шаг {step}/{steps} · показатель ошибки {loss_text}"
        )

    def _on_training_complete(self, path: str) -> None:
        self.checkpoint_edit.setText(path)
        self.model_memory_status.setText("Новая модель сохранена; загрузи её в память для генерации.")
        stopped = self.progress_stage.text() == "Остановлено"
        if stopped:
            self.statusBar().showMessage("Обучение остановлено; контрольная точка сохранена")
            self._append_log("Сохранённую модель можно выбрать во вкладке «Попробовать модель».")
        else:
            self.progress_bar.setValue(100)
            self.statusBar().showMessage("Обучение завершено; контрольная точка сохранена")
            self._append_log(
                "Модель готова. Перейди во вкладку «Попробовать модель», чтобы проверить её."
            )

    def _on_training_error(self, error: str) -> None:
        self.statusBar().showMessage("Обучение завершилось с ошибкой")
        self._append_log(f"ОШИБКА: {error}")
        QMessageBox.critical(self, "Не удалось обучить модель", error)

    def _on_training_thread_finished(self) -> None:
        self.training_worker = None
        control_active = self.model_control_worker is not None
        self.start_button.setEnabled(True)
        self.continue_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.generate_button.setEnabled(not control_active)
        self.load_model_button.setEnabled(not control_active)
        self.unload_model_button.setEnabled(not control_active)

    def load_generation_model(self) -> None:
        checkpoint = Path(self.checkpoint_edit.text())
        if not checkpoint.is_file():
            QMessageBox.warning(self, "Нет модели", "Выбери файл latest.pt или сначала обучи модель.")
            return
        if self.model_control_worker is not None:
            return
        self.model_control_worker = ModelControlWorker(
            action="load",
            checkpoint_path=checkpoint,
            device_key=str(self.device_combo.currentData()),
        )
        self.model_control_worker.completed.connect(self._on_model_control_complete)
        self.model_control_worker.failed.connect(self._on_model_control_error)
        self.model_control_worker.finished.connect(self._on_model_control_finished)
        self.load_model_button.setEnabled(False)
        self.unload_model_button.setEnabled(False)
        self.generate_button.setEnabled(False)
        self.model_memory_status.setText("Загружаю модель в память; это может занять время…")
        self.model_control_worker.start()

    def unload_generation_model(self) -> None:
        if self.model_control_worker is not None:
            return
        self.model_control_worker = ModelControlWorker(action="unload")
        self.model_control_worker.completed.connect(self._on_model_control_complete)
        self.model_control_worker.failed.connect(self._on_model_control_error)
        self.model_control_worker.finished.connect(self._on_model_control_finished)
        self.load_model_button.setEnabled(False)
        self.unload_model_button.setEnabled(False)
        self.generate_button.setEnabled(False)
        self.model_memory_status.setText("Выгружаю модель и освобождаю память…")
        self.model_control_worker.start()

    def _on_model_control_complete(self, message: str) -> None:
        self.model_memory_status.setText(message)
        self._append_log(message)
        self.statusBar().showMessage(message)

    def _on_model_control_error(self, error: str) -> None:
        self.model_memory_status.setText("Не удалось выполнить операцию с моделью.")
        self._append_log(f"ОШИБКА загрузки модели: {error}")
        QMessageBox.critical(self, "Ошибка работы с моделью", error)

    def _on_model_control_finished(self) -> None:
        self.model_control_worker = None
        training_active = self.training_worker is not None
        self.load_model_button.setEnabled(not training_active)
        self.unload_model_button.setEnabled(not training_active)
        self.generate_button.setEnabled(not training_active)

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
        self.load_model_button.setEnabled(False)
        self.unload_model_button.setEnabled(False)
        self.generated_text.setPlainText("Генерирую…")
        self.generation_worker.start()

    def _on_generation_complete(self, text: str) -> None:
        self.generated_text.setPlainText(text)
        self.model_memory_status.setText("Модель загружена в память; нажми «Выгрузить» для освобождения RAM / VRAM.")
        self.statusBar().showMessage("Генерация завершена")

    def _on_generation_error(self, error: str) -> None:
        self.generated_text.setPlainText("")
        self.statusBar().showMessage("Не удалось сгенерировать текст")
        QMessageBox.critical(self, "Ошибка генерации", error)

    def _on_generation_thread_finished(self) -> None:
        self.generation_worker = None
        training_active = self.training_worker is not None
        control_active = self.model_control_worker is not None
        self.generate_button.setEnabled(not training_active and not control_active)
        self.load_model_button.setEnabled(not training_active and not control_active)
        self.unload_model_button.setEnabled(not training_active and not control_active)

    def _apply_style(self) -> None:
        self.setFont(QFont("Segoe UI", 11))
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #17171d; color: #eee8e5; }
            QWidget { font-size: 13px; }
            QLabel#title { color: #fff0e8; font-size: 28px; font-weight: 700; }
            QLabel#subtitle { color: #b8aaa8; font-size: 14px; }
            QFrame#hardwareCard { background: #232229; border: 1px solid #44353b; border-radius: 12px; }
            QLabel#fieldLabel { color: #e1a48f; font-size: 12px; font-weight: 700; letter-spacing: 0.5px; }
            QLabel#hint { color: #c1b6b3; font-size: 13px; }
            QGroupBox { background: #1e1d24; border: 1px solid #3a343b; border-radius: 11px; margin-top: 14px; padding: 14px; font-size: 15px; font-weight: 600; color: #f0c1ae; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit { background: #28272f; color: #f3ece9; border: 1px solid #49414a; border-radius: 7px; padding: 8px 10px; min-height: 36px; font-size: 13px; selection-background-color: #bd6e63; }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus { border: 1px solid #d78369; }
            QComboBox QAbstractItemView { background: #28272f; color: #f3ece9; selection-background-color: #744b50; border: 1px solid #49414a; }
            QPushButton { background: #302c34; color: #f2e7e2; border: 1px solid #51444b; border-radius: 8px; padding: 10px 15px; min-height: 38px; font-size: 13px; font-weight: 600; }
            QPushButton:hover { background: #40343a; border-color: #a96861; }
            QPushButton:disabled { background: #242329; color: #777178; border-color: #36333a; }
            QPushButton#primaryButton { background: #bf7059; color: #fff8f5; border: none; padding: 10px 18px; }
            QPushButton#primaryButton:hover { background: #d28266; }
            QPushButton#stopButton { background: #3a292e; color: #efb5aa; border: 1px solid #69434a; }
            QPushButton#secondaryButton { background: #29272f; }
            QLabel#notice { background: #332721; border: 1px solid #705044; border-radius: 8px; padding: 10px 12px; color: #f0c39b; }
            QProgressBar { border: 1px solid #49414a; border-radius: 7px; background: #28272f; height: 22px; text-align: center; color: #fff0e8; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d88759, stop:1 #bd6681); border-radius: 6px; }
            QTabWidget::pane { border: 1px solid #3a343b; background: #17171d; border-radius: 9px; }
            QTabBar::tab { background: #27252d; color: #b8aaa8; padding: 11px 20px; font-size: 14px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; }
            QTabBar::tab:selected { background: #a85e56; color: #fff8f5; }
            QScrollArea { background: #17171d; border: none; }
            QScrollBar:vertical { background: #201f26; width: 14px; margin: 2px; border-radius: 6px; }
            QScrollBar::handle:vertical { background: #625057; min-height: 28px; border-radius: 6px; }
            QScrollBar::handle:vertical:hover { background: #9d665f; }
            QStatusBar { color: #b8aaa8; }
            QToolTip { background: #343039; color: #fff0e8; border: 1px solid #8c5b59; padding: 6px; }
            """
        )


def run_app() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Мастерская модели")
    app.setOrganizationName("FlyDron")
    window = MainWindow()
    window.showMaximized()
    return app.exec()
