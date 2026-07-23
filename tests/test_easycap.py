"""Tests de detección heurística easierCAP (sin hardware)."""

from app.device.detector import UsbDeviceInfo
from app.device.easycap import (
    camera_name_looks_like_easycap,
    is_easycap_usb,
)


def test_vid_pid_macrosilicon() -> None:
    dev = UsbDeviceInfo(
        name="USB Video Device",
        device_id=r"USB\VID_534D&PID_0021\6&123",
        vid="534D",
        pid="0021",
    )
    assert is_easycap_usb(dev) == "vid_pid"


def test_keyword_av_to_usb() -> None:
    dev = UsbDeviceInfo(
        name="AV to USB2",
        device_id=r"USB\VID_FFFF&PID_FFFF\1",
        vid="FFFF",
        pid="FFFF",
    )
    assert is_easycap_usb(dev) == "keyword"


def test_not_easycap() -> None:
    dev = UsbDeviceInfo(
        name="Logitech Webcam",
        device_id=r"USB\VID_046D&PID_0825\1",
        vid="046D",
        pid="0825",
    )
    assert is_easycap_usb(dev) is None


def test_camera_name_heuristics() -> None:
    assert camera_name_looks_like_easycap("USB Video Device MS210x")
    assert camera_name_looks_like_easycap("easierCAP")
    assert not camera_name_looks_like_easycap("Integrated Camera")
