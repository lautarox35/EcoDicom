"""Detección genérica de dispositivos USB (Windows y macOS)."""

from __future__ import annotations

import json
import platform
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class UsbDeviceInfo:
    name: str
    device_id: str
    vid: Optional[str] = None
    pid: Optional[str] = None


def _parse_vid_pid(device_id: str) -> tuple[Optional[str], Optional[str]]:
    vid = pid = None
    upper = device_id.upper()
    if "VID_" in upper:
        try:
            vid = upper.split("VID_")[1][:4]
        except (IndexError, ValueError):
            pass
    if "PID_" in upper:
        try:
            pid = upper.split("PID_")[1][:4]
        except (IndexError, ValueError):
            pass
    # macOS hex forms: 0x1234 or vendor_id
    if vid is None:
        m = re.search(r"VID[_\s:=]*0?x?([0-9A-F]{4})", upper)
        if m:
            vid = m.group(1)
    if pid is None:
        m = re.search(r"PID[_\s:=]*0?x?([0-9A-F]{4})", upper)
        if m:
            pid = m.group(1)
    return vid, pid


def _list_usb_windows() -> list[UsbDeviceInfo]:
    ps = (
        "Get-PnpDevice -PresentOnly | "
        "Where-Object { $_.InstanceId -like 'USB*' } | "
        "Select-Object -Property FriendlyName, InstanceId | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []

    devices: list[UsbDeviceInfo] = []
    lines = result.stdout.strip().splitlines()
    for line in lines[1:]:
        parts = [p.strip().strip('"') for p in line.split('","')]
        if len(parts) < 2:
            continue
        name = parts[0].lstrip('"')
        device_id = parts[1].rstrip('"')
        vid, pid = _parse_vid_pid(device_id)
        devices.append(
            UsbDeviceInfo(name=name or "USB Device", device_id=device_id, vid=vid, pid=pid)
        )
    return devices


def _walk_usb_tree(node: Any, devices: list[UsbDeviceInfo]) -> None:
    if isinstance(node, list):
        for item in node:
            _walk_usb_tree(item, devices)
        return
    if not isinstance(node, dict):
        return

    vendor = node.get("vendor_id")
    product = node.get("product_id")
    name = str(node.get("_name") or "").strip()

    if vendor is not None or product is not None:
        vid = pid = None
        try:
            if vendor is not None:
                vid = (
                    vendor[2:].upper().zfill(4)[-4:]
                    if isinstance(vendor, str) and vendor.lower().startswith("0x")
                    else f"{int(str(vendor), 0):04X}"
                )
        except (TypeError, ValueError):
            vid = str(vendor) if vendor is not None else None
        try:
            if product is not None:
                pid = (
                    product[2:].upper().zfill(4)[-4:]
                    if isinstance(product, str) and product.lower().startswith("0x")
                    else f"{int(str(product), 0):04X}"
                )
        except (TypeError, ValueError):
            pid = str(product) if product is not None else None

        serial = str(node.get("serial_num") or "")
        device_id = f"USB\\VID_{vid or '????'}&PID_{pid or '????'}\\{serial}".rstrip("\\")
        devices.append(
            UsbDeviceInfo(name=name or "USB Device", device_id=device_id, vid=vid, pid=pid)
        )

    items = node.get("_items")
    if items is not None:
        _walk_usb_tree(items, devices)


def _list_usb_macos() -> list[UsbDeviceInfo]:
    try:
        result = subprocess.run(
            ["system_profiler", "SPUSBDataType", "-json"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    devices: list[UsbDeviceInfo] = []
    _walk_usb_tree(data.get("SPUSBDataType", data), devices)

    # Deduplicar por device_id + name
    unique: dict[str, UsbDeviceInfo] = {}
    for d in devices:
        key = f"{d.name}|{d.vid}|{d.pid}|{d.device_id}"
        unique[key] = d
    return list(unique.values())


def list_usb_devices() -> list[UsbDeviceInfo]:
    """Lista dispositivos USB según el sistema operativo."""
    system = platform.system()
    if system == "Windows":
        return _list_usb_windows()
    if system == "Darwin":
        return _list_usb_macos()
    return []


def find_devices_by_keywords(keywords: list[str]) -> list[UsbDeviceInfo]:
    keys = [k.lower() for k in keywords]
    found: list[UsbDeviceInfo] = []
    for dev in list_usb_devices():
        hay = f"{dev.name} {dev.device_id}".lower()
        if any(k in hay for k in keys):
            found.append(dev)
    return found
