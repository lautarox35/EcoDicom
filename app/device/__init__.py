"""Capa de dispositivo (ecógrafo / captura easierCAP)."""

from app.device.capture import (
    CameraDevice,
    capture_frame,
    list_camera_devices,
    list_camera_indices,
    resolve_preferred_camera,
)
from app.device.detector import list_usb_devices
from app.device.easycap import easycap_status_message, find_easycap_devices
from app.device.welld_wed3100 import ConnectionStatus, WellDConnectionResult, connect_wed3100

__all__ = [
    "CameraDevice",
    "capture_frame",
    "list_camera_devices",
    "list_camera_indices",
    "resolve_preferred_camera",
    "list_usb_devices",
    "find_easycap_devices",
    "easycap_status_message",
    "ConnectionStatus",
    "WellDConnectionResult",
    "connect_wed3100",
]
