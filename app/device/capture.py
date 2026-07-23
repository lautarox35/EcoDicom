"""Captura de frames con OpenCV (easierCAP / webcam USB)."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from app.config import (
    CAPTURE_HEIGHT,
    CAPTURE_RESOLUTION_CANDIDATES,
    CAPTURE_WARMUP_FRAMES,
    CAPTURE_WIDTH,
    DEFAULT_CAMERA_INDEX,
    SAMPLE_IMAGES_DIR,
    ensure_directories,
)
from app.device.easycap import camera_name_looks_like_easycap
from app.device.enhance import EnhanceSettings, enhance_frame


@dataclass
class CameraDevice:
    """Dispositivo de video enumerable por OpenCV."""

    index: int
    name: str
    backend: int
    vid: Optional[int] = None
    pid: Optional[int] = None
    is_easycap: bool = False

    @property
    def label(self) -> str:
        tag = " [easierCAP]" if self.is_easycap else ""
        return f"{self.index}: {self.name}{tag}"


def _camera_backends() -> list[int]:
    """Backends preferidos por plataforma (orden de intento)."""
    system = platform.system()
    if system == "Windows":
        # DirectShow suele ir mejor con capturadoras USB genéricas (MS210x)
        return [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    if system == "Darwin":
        backends = [cv2.CAP_ANY]
        if hasattr(cv2, "CAP_AVFOUNDATION"):
            backends.insert(0, cv2.CAP_AVFOUNDATION)
        return backends
    return [cv2.CAP_V4L2, cv2.CAP_ANY] if hasattr(cv2, "CAP_V4L2") else [cv2.CAP_ANY]


def _is_easycap_camera(name: str, vid: Optional[int], pid: Optional[int]) -> bool:
    if camera_name_looks_like_easycap(name):
        return True
    if vid is None or pid is None:
        return False
    from app.device.easycap import EASIERCAP_VID_PIDS, _norm_hex

    pair = (_norm_hex(f"{int(vid):04X}"), _norm_hex(f"{int(pid):04X}"))
    return pair in EASIERCAP_VID_PIDS


def _enumerate_with_cv2_package(max_index: int) -> list[CameraDevice]:
    """Usa cv2_enumerate_cameras si está instalado (nombres + VID/PID)."""
    try:
        from cv2_enumerate_cameras import enumerate_cameras  # type: ignore
    except ImportError:
        return []

    devices: list[CameraDevice] = []
    seen: set[tuple[int, int]] = set()
    for backend in _camera_backends():
        try:
            infos = list(enumerate_cameras(backend))
        except Exception:  # noqa: BLE001
            continue
        for info in infos:
            raw_index = int(getattr(info, "index", -1))
            if raw_index < 0:
                continue
            # Índice “lógico” 0..N (si el backend va codificado en dígitos altos)
            logical = raw_index % 100 if raw_index >= 100 else raw_index
            if logical >= max_index:
                continue
            be = int(getattr(info, "backend", backend))
            key = (raw_index, be)
            if key in seen:
                continue
            seen.add(key)
            name = str(getattr(info, "name", None) or f"Cámara {logical}")
            vid = getattr(info, "vid", None)
            pid = getattr(info, "pid", None)
            vid_i = int(vid) if vid is not None else None
            pid_i = int(pid) if pid is not None else None
            devices.append(
                CameraDevice(
                    index=raw_index,
                    name=name,
                    backend=be,
                    vid=vid_i,
                    pid=pid_i,
                    is_easycap=_is_easycap_camera(name, vid_i, pid_i),
                )
            )
        if devices:
            break
    return devices


def _probe_indices(max_index: int) -> list[CameraDevice]:
    """Fallback: prueba índices 0..max_index-1."""
    devices: list[CameraDevice] = []
    for i in range(max_index):
        cap = _open_capture(i)
        if cap.isOpened():
            # Algunos backends exponen el nombre vía CAP_PROP_BACKEND o similar; usamos genérico
            name = f"Dispositivo de video {i}"
            devices.append(
                CameraDevice(
                    index=i,
                    name=name,
                    backend=_camera_backends()[0],
                    is_easycap=False,
                )
            )
            cap.release()
        else:
            cap.release()
    return devices


def list_camera_devices(max_index: int = 8) -> list[CameraDevice]:
    """Lista cámaras/capturadoras disponibles, priorizando nombres reales."""
    devices = _enumerate_with_cv2_package(max_index)
    if not devices:
        devices = _probe_indices(max_index)

    # Si hay easierCAP en USB pero ningún nombre lo marcó, marcar el índice preferido
    from app.device.easycap import find_easycap_devices

    if find_easycap_devices() and devices and not any(d.is_easycap for d in devices):
        # Con una sola cámara y easierCAP USB presente, es casi seguro esa
        if len(devices) == 1:
            devices[0].is_easycap = True
            if "video" not in devices[0].name.lower():
                devices[0].name = f"{devices[0].name} (easierCAP)"
    return devices


def list_camera_indices(max_index: int = 5) -> list[int]:
    return [d.index for d in list_camera_devices(max_index)]


def resolve_preferred_camera(
    preferred_index: Optional[int] = None,
    max_index: int = 8,
) -> CameraDevice:
    """
    Elige la capturadora a usar.
    Prioridad: índice pedido → easierCAP → DEFAULT_CAMERA_INDEX → primera disponible.
    """
    devices = list_camera_devices(max_index)
    if not devices:
        raise RuntimeError(
            "No se encontró ninguna cámara ni capturadora USB. "
            "Conecte la easierCAP (cable USB) y verifique el cable Video/SVGA del ecógrafo. "
            "En macOS, conceda permiso de Cámara a EcoDICOM."
        )

    if preferred_index is not None:
        for d in devices:
            if d.index == preferred_index:
                return d

    for d in devices:
        if d.is_easycap:
            return d

    for d in devices:
        if d.index == DEFAULT_CAMERA_INDEX:
            return d

    return devices[0]


def _open_capture(camera_index: int, backend: Optional[int] = None) -> cv2.VideoCapture:
    preferred = [backend] if backend is not None else []
    backends: list[int] = []
    for be in preferred + _camera_backends():
        if be is None:
            continue
        if be not in backends:
            backends.append(be)

    last: Optional[cv2.VideoCapture] = None
    for be in backends:
        cap = cv2.VideoCapture(camera_index, be)
        if cap.isOpened():
            # Verificar que realmente entrega frames (MSMF a veces “abre” sin leer)
            ok, _frame = cap.read()
            if ok:
                return cap
            cap.release()
            continue
        cap.release()
        last = cap
    return last if last is not None else cv2.VideoCapture(camera_index)


def _configure_capture(cap: cv2.VideoCapture, for_easycap: bool = False) -> None:
    """Ajusta resolución/formato típicos de grabbers UVC (MS210x / easierCAP)."""
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:  # noqa: BLE001
        pass

    # Probar resoluciones de mayor a menor; quedarse con la primera aceptada
    applied = False
    for width, height in CAPTURE_RESOLUTION_CANDIDATES:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        got_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        got_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if got_w >= width * 0.9 and got_h >= height * 0.9:
            applied = True
            break
    if not applied:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)


def capture_frame(
    camera_index: Optional[int] = None,
    output_dir: Optional[Path] = None,
    backend: Optional[int] = None,
    prefer_easycap: bool = True,
    enhance: bool | EnhanceSettings = True,
) -> Path:
    """
    Captura un frame de la easierCAP / cámara y lo guarda como PNG.
    Lanza RuntimeError si no hay dispositivo disponible.
    """
    ensure_directories()
    out_dir = Path(output_dir) if output_dir else SAMPLE_IMAGES_DIR / "captures"
    out_dir.mkdir(parents=True, exist_ok=True)

    device: Optional[CameraDevice] = None
    index = camera_index if camera_index is not None else DEFAULT_CAMERA_INDEX
    be = backend

    if prefer_easycap or camera_index is None:
        try:
            device = resolve_preferred_camera(preferred_index=camera_index)
            index = device.index
            be = device.backend
        except RuntimeError:
            if camera_index is None:
                raise
            device = None

    for_easycap = bool(device.is_easycap) if device else True
    cap = _open_capture(index, backend=be)
    if not cap.isOpened():
        raise RuntimeError(
            f"No se pudo abrir la capturadora en el índice {index}. "
            "Conecte la easierCAP por USB, encienda el ecógrafo y use el puerto Video/SVGA. "
            "También puede usar Importar imagen. "
            "En macOS, conceda permiso de Cámara a EcoDICOM en Ajustes del Sistema."
        )

    _configure_capture(cap, for_easycap=for_easycap)

    frame: Optional[np.ndarray] = None
    for _ in range(max(CAPTURE_WARMUP_FRAMES, 5)):
        ok, candidate = cap.read()
        if ok and candidate is not None:
            frame = candidate
    cap.release()

    if frame is None:
        raise RuntimeError(
            "La capturadora está abierta pero no devolvió imagen. "
            "Revise el cable Video/SVGA → easierCAP y la entrada (CVBS/composite)."
        )

    return save_bgr_frame(frame, out_dir, enhance=enhance)


def save_bgr_frame(
    frame: np.ndarray,
    output_dir: Optional[Path] = None,
    enhance: bool | EnhanceSettings = True,
) -> Path:
    """Guarda un frame BGR (p. ej. el de la vista en vivo) como PNG."""
    ensure_directories()
    out_dir = Path(output_dir) if output_dir else SAMPLE_IMAGES_DIR / "captures"
    out_dir.mkdir(parents=True, exist_ok=True)

    if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
        raise RuntimeError("No hay frame para guardar.")

    if float(np.mean(frame)) < 2.0:
        raise RuntimeError(
            "Se obtuvo un frame negro: no hay señal de video. "
            "Verifique el cable del ecógrafo a la easierCAP y que el ecógrafo esté encendido."
        )

    to_save = frame
    if enhance is True:
        to_save = enhance_frame(frame)
    elif isinstance(enhance, EnhanceSettings):
        to_save = enhance_frame(frame, enhance)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"capture_{stamp}.png"
    # PNG sin pérdida
    if not cv2.imwrite(str(out_path), to_save, [cv2.IMWRITE_PNG_COMPRESSION, 3]):
        raise RuntimeError(f"No se pudo guardar la captura en {out_path}")
    return out_path
