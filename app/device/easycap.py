"""Detección y preferencia de capturadoras USB tipo easierCAP / EasyCAP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.device.detector import UsbDeviceInfo, find_devices_by_keywords, list_usb_devices

# MacroSilicon MS210x (easierCAP / EasyCAP genéricos más comunes)
EASIERCAP_VID_PIDS: set[tuple[str, str]] = {
    ("534D", "0021"),  # MS210x Video Grabber [EasierCAP]
    ("534D", "2109"),  # Variante MS2109
    ("1B71", "3002"),  # Empia EM2860 (EasyCAP DC60+)
    ("EB1A", "2870"),  # Empia (algunos EasyCAP)
}

EASIERCAP_KEYWORDS = [
    "easycap",
    "easiercap",
    "easier cap",
    "macrosilicon",
    "ms210",
    "ms210x",
    "av to usb",
    "av to ubs",  # typo frecuente en drivers Windows
    "usb video",
    "usb capture",
    "video grabber",
    "composite",
]


@dataclass
class EasyCapInfo:
    """Dispositivo USB identificado como capturadora de video."""

    usb: UsbDeviceInfo
    matched_by: str  # "vid_pid" | "keyword"


def _norm_hex(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip().upper().removeprefix("0X")
    if len(cleaned) < 4:
        cleaned = cleaned.zfill(4)
    return cleaned[-4:]


def is_easycap_usb(device: UsbDeviceInfo) -> Optional[str]:
    """Devuelve el criterio de match o None si no parece capturadora EasyCAP."""
    vid = _norm_hex(device.vid)
    pid = _norm_hex(device.pid)
    if vid and pid and (vid, pid) in EASIERCAP_VID_PIDS:
        return "vid_pid"

    hay = f"{device.name} {device.device_id}".lower()
    for key in EASIERCAP_KEYWORDS:
        if key in hay:
            return "keyword"
    return None


def find_easycap_devices() -> list[EasyCapInfo]:
    """Lista capturadoras USB tipo easierCAP conectadas."""
    found: list[EasyCapInfo] = []
    seen: set[str] = set()
    for dev in list_usb_devices():
        match = is_easycap_usb(dev)
        if not match:
            continue
        key = f"{dev.vid}|{dev.pid}|{dev.device_id}|{dev.name}"
        if key in seen:
            continue
        seen.add(key)
        found.append(EasyCapInfo(usb=dev, matched_by=match))
    return found


def easycap_status_message() -> tuple[bool, str]:
    """
    Mensaje corto para la UI.
    Returns: (detectado, mensaje)
    """
    devices = find_easycap_devices()
    if not devices:
        # Fallback por keywords globales (por si el nombre no entró en is_easycap)
        loose = find_devices_by_keywords(EASIERCAP_KEYWORDS)
        if not loose:
            return (
                False,
                "easierCAP no detectada. Conecte la capturadora USB y el cable "
                "Video/SVGA del ecógrafo.",
            )
        devices = [EasyCapInfo(usb=d, matched_by="keyword") for d in loose]

    primary = devices[0].usb
    extra = f" (+{len(devices) - 1} más)" if len(devices) > 1 else ""
    return (
        True,
        f"easierCAP detectada: {primary.name} "
        f"(VID={primary.vid}, PID={primary.pid}){extra}",
    )


def camera_name_looks_like_easycap(name: str) -> bool:
    """Heurística sobre el nombre de dispositivo de video (DirectShow / AVFoundation)."""
    lower = name.lower()
    return any(k in lower for k in EASIERCAP_KEYWORDS)
