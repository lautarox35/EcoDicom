"""Stub de conexión con Well-D WED-3100."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.device.detector import UsbDeviceInfo, find_devices_by_keywords, list_usb_devices


class ConnectionStatus(str, Enum):
    DISCONNECTED = "Desconectado"
    DETECTED = "Detectado (USB)"
    UNSUPPORTED = "Detectado — protocolo no soportado aún"
    ERROR = "Error de detección"


@dataclass
class WellDConnectionResult:
    status: ConnectionStatus
    message: str
    device: Optional[UsbDeviceInfo] = None
    usb_count: int = 0


# Keywords heurísticos; el VID/PID real se confirma con el equipo físico
WELLD_KEYWORDS = ["welld", "well.d", "well-d", "wed-3100", "wed3100", "ultrasound"]


def connect_wed3100() -> WellDConnectionResult:
    """
    Intenta detectar un WED-3100 en el bus USB.

    El equipo usa USB 2.0 propietario para 'real-time picture uploading'
    y NO expone DICOM nativo ni mass storage documentado. Hasta tener
    el VID/PID y/o el software de estación Well.d, devolvemos estado
    informativo y pedimos importación/captura manual.
    """
    try:
        all_usb = list_usb_devices()
        matches = find_devices_by_keywords(WELLD_KEYWORDS)

        if matches:
            dev = matches[0]
            return WellDConnectionResult(
                status=ConnectionStatus.UNSUPPORTED,
                message=(
                    f"Se encontró un dispositivo USB compatible por nombre: "
                    f"{dev.name} (VID={dev.vid}, PID={dev.pid}). "
                    "El protocolo Well.d aún no está implementado. "
                    "Use Capturar imagen con la easierCAP (puerto Video/SVGA) "
                    "o Importar imagen."
                ),
                device=dev,
                usb_count=len(all_usb),
            )

        return WellDConnectionResult(
            status=ConnectionStatus.DISCONNECTED,
            message=(
                f"No se detectó un Well-D WED-3100 ({len(all_usb)} dispositivos USB presentes). "
                "Use la easierCAP: Video/SVGA del ecógrafo → easierCAP → USB al PC, "
                "luego Capturar imagen; o Importar imagen (JPG/PNG)."
            ),
            usb_count=len(all_usb),
        )
    except Exception as exc:  # noqa: BLE001
        return WellDConnectionResult(
            status=ConnectionStatus.ERROR,
            message=f"Error al inspeccionar USB: {exc}",
        )
