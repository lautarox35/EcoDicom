"""Vista previa en vivo de la easierCAP / capturadora USB."""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QWidget

from app.device.capture import _configure_capture, _open_capture
from app.device.enhance import EnhanceSettings, enhance_frame

# Realce liviano solo para pantalla (sin upscale, para no perder FPS)
_LIVE_ENHANCE = EnhanceSettings(
    enabled=True,
    clahe_clip=2.0,
    denoise=3,
    sharpen=0.45,
    upscale=1.0,
)


class _CameraWorker(QThread):
    frame_ready = Signal(object)  # np.ndarray BGR
    status = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        camera_index: int,
        backend: Optional[int] = None,
        for_easycap: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._index = camera_index
        self._backend = backend
        self._for_easycap = for_easycap
        self._running = True
        self._latest: Optional[np.ndarray] = None

    def stop(self) -> None:
        self._running = False

    def latest_frame(self) -> Optional[np.ndarray]:
        if self._latest is None:
            return None
        return self._latest.copy()

    def run(self) -> None:
        cap = _open_capture(self._index, backend=self._backend)
        if not cap.isOpened():
            self.failed.emit(
                f"No se pudo abrir el índice {self._index}. "
                "Elija AV TO USB2.0 [easierCAP] y actualice dispositivos."
            )
            return

        _configure_capture(cap, for_easycap=self._for_easycap)
        self.status.emit("Transmitiendo…")

        # Descartar frames iniciales inestables
        for _ in range(8):
            if not self._running:
                break
            cap.read()

        black_streak = 0
        while self._running:
            ok, frame = cap.read()
            if not ok or frame is None:
                self.msleep(30)
                continue

            mean = float(np.mean(frame))
            if mean < 2.0:
                black_streak += 1
                if black_streak == 15:
                    self.status.emit(
                        "Sin señal de video — revise cable Video/SVGA → easierCAP "
                        "y que el ecógrafo esté encendido."
                    )
            else:
                if black_streak >= 15:
                    self.status.emit("Señal OK")
                black_streak = 0

            self._latest = frame
            self.frame_ready.emit(frame)
            self.msleep(33)  # ~30 fps

        cap.release()


class LivePreview(QWidget):
    """Muestra el video en vivo de la capturadora seleccionada."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._worker: Optional[_CameraWorker] = None
        self._build()

    def _build(self) -> None:
        group = QGroupBox("Vista en vivo (easierCAP)")
        layout = QVBoxLayout(group)

        self.video_label = QLabel(
            "Sin vista previa\n\nSeleccione la capturadora easierCAP"
        )
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(320, 240)
        self.video_label.setStyleSheet(
            "QLabel { background: #111; color: #aaa; border: 1px solid #444; }"
        )

        self.hint_label = QLabel("")
        self.hint_label.setStyleSheet("color: #888;")
        self.hint_label.setWordWrap(True)

        layout.addWidget(self.video_label, stretch=1)
        layout.addWidget(self.hint_label)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

    def start(
        self,
        camera_index: int,
        backend: Optional[int] = None,
        for_easycap: bool = True,
    ) -> None:
        self.stop()
        self.video_label.setText("Abriendo capturadora…")
        self.hint_label.setText("")
        self._worker = _CameraWorker(
            camera_index=camera_index,
            backend=backend,
            for_easycap=for_easycap,
            parent=self,
        )
        self._worker.frame_ready.connect(self._on_frame)
        self._worker.status.connect(self._on_status)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def stop(self) -> None:
        if self._worker is None:
            return
        self._worker.stop()
        self._worker.wait(3000)
        self._worker = None

    def is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def latest_frame(self) -> Optional[np.ndarray]:
        if self._worker is None:
            return None
        return self._worker.latest_frame()

    @Slot(object)
    def _on_frame(self, frame: object) -> None:
        if not isinstance(frame, np.ndarray):
            return
        display = enhance_frame(frame, _LIVE_ENHANCE)
        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
        pix = QPixmap.fromImage(image)
        scaled = pix.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.video_label.setPixmap(scaled)

    @Slot(str)
    def _on_status(self, message: str) -> None:
        self.hint_label.setText(message)
        if message.startswith("Sin señal"):
            self.hint_label.setStyleSheet("color: #c62828;")
        else:
            self.hint_label.setStyleSheet("color: #2e7d32;")

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        self.video_label.setText(message)
        self.hint_label.setText(message)
        self.hint_label.setStyleSheet("color: #c62828;")

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        frame = self.latest_frame()
        if frame is not None:
            self._on_frame(frame)
