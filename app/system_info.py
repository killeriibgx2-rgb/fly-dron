"""Hardware discovery with safe fallbacks for Windows and CPU-only installs."""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceOption:
    key: str
    label: str
    usable: bool


def _memory_info() -> tuple[int | None, int | None]:
    try:
        import psutil

        memory = psutil.virtual_memory()
        return int(memory.total), int(memory.available)
    except Exception:
        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes

                class MemoryStatus(ctypes.Structure):
                    _fields_ = [
                        ("length", wintypes.DWORD),
                        ("memory_load", wintypes.DWORD),
                        ("total_phys", ctypes.c_ulonglong),
                        ("avail_phys", ctypes.c_ulonglong),
                        ("total_page_file", ctypes.c_ulonglong),
                        ("avail_page_file", ctypes.c_ulonglong),
                        ("total_virtual", ctypes.c_ulonglong),
                        ("avail_virtual", ctypes.c_ulonglong),
                        ("avail_extended_virtual", ctypes.c_ulonglong),
                    ]

                status = MemoryStatus()
                status.length = ctypes.sizeof(status)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                    return int(status.total_phys), int(status.avail_phys)
            except Exception:
                pass
        return None, None


def _windows_cpu_name() -> str | None:
    if os.name != "nt":
        return None
    command = "Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name"
    try:
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            creationflags=creation_flags,
        )
        name = next((line.strip() for line in result.stdout.splitlines() if line.strip()), None)
        return name
    except Exception:
        return None


def _windows_gpu_names() -> list[str]:
    if os.name != "nt":
        return []
    command = (
        "Get-CimInstance Win32_VideoController | "
        "ForEach-Object { if ($_.Name) { $_.Name } }"
    )
    try:
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            creationflags=creation_flags,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def _torch_devices() -> tuple[list[DeviceOption], str]:
    options = [DeviceOption("cpu", "CPU", True)]
    notes: list[str] = []
    try:
        import torch
    except Exception as exc:
        return options, f"PyTorch не загружен: {exc}"

    try:
        if torch.cuda.is_available():
            for index in range(torch.cuda.device_count()):
                try:
                    name = torch.cuda.get_device_name(index)
                except Exception:
                    name = f"GPU {index}"
                options.append(DeviceOption(f"cuda:{index}", name, True))
    except Exception as exc:
        notes.append(f"CUDA/ROCm недоступен: {exc}")

    try:
        import torch_directml  # type: ignore[import-not-found]

        count_function = getattr(torch_directml, "device_count", None)
        name_function = getattr(torch_directml, "device_name", None)
        count = int(count_function()) if callable(count_function) else 1
        for index in range(max(0, count)):
            try:
                name = str(name_function(index)) if callable(name_function) else f"DirectML GPU {index}"
            except Exception:
                name = f"DirectML GPU {index}"
            options.append(DeviceOption(f"directml:{index}", name, True))
    except ImportError:
        pass
    except Exception as exc:
        notes.append(f"DirectML не удалось проверить: {exc}")

    return options, "; ".join(notes)


def get_hardware_report() -> dict[str, object]:
    total_ram, available_ram = _memory_info()
    cpu_name = _windows_cpu_name() or platform.processor().strip() or platform.machine()
    logical = os.cpu_count() or 1
    try:
        import psutil

        physical = psutil.cpu_count(logical=False) or logical
    except Exception:
        physical = logical

    devices, backend_note = _torch_devices()
    gpu_names = _windows_gpu_names()
    if not gpu_names:
        gpu_names = [option.label for option in devices if option.key != "cpu"]
    if not gpu_names:
        gpu_names = ["Видеокарта не обнаружена системой"]

    return {
        "cpu_name": cpu_name,
        "logical_cores": logical,
        "physical_cores": physical,
        "total_ram": total_ram,
        "available_ram": available_ram,
        "gpu_names": gpu_names,
        "devices": devices,
        "backend_note": backend_note,
    }


def format_bytes(value: int | None) -> str:
    if value is None:
        return "не определено"
    gib = value / (1024**3)
    return f"{gib:.1f} ГБ"
