"""Panel de estado de calibración espacial."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.analysis.calibration.models import ImageCalibration


class CalibrationPanel(QFrame):
    """Muestra fuente, spacing y estado; botón Calibrar imagen."""

    calibrate_requested = Signal()
    closed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("calibCard")
        self.setStyleSheet(
            """
            QFrame#calibCard {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QLabel { color: #e2e8f0; }
            QLabel#title {
                color: #38bdf8;
                font-weight: 700;
                font-size: 13px;
                letter-spacing: 1px;
            }
            QPushButton {
                background: #1e293b; color: #e2e8f0;
                border: 1px solid #475569; border-radius: 6px; padding: 6px 10px;
            }
            QPushButton:hover { background: #334155; }
            QPushButton#calibBtn {
                background: #0369a1; border-color: #38bdf8; font-weight: 600;
            }
            """
        )
        self.setMinimumWidth(220)
        self._build()
        self.set_calibration(ImageCalibration.unknown())

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("CALIBRACIÓN")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch(1)
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedWidth(28)
        self.btn_close.clicked.connect(self.closed.emit)
        header.addWidget(self.btn_close)
        layout.addLayout(header)

        self.lbl_source = QLabel("Fuente:\n—")
        self.lbl_px = QLabel("Pixel X:\n—")
        self.lbl_py = QLabel("Pixel Y:\n—")
        self.lbl_status = QLabel("Estado:\n—")
        for w in (self.lbl_source, self.lbl_px, self.lbl_py, self.lbl_status):
            layout.addWidget(w)

        self.btn_calibrate = QPushButton("Calibrar imagen")
        self.btn_calibrate.setObjectName("calibBtn")
        self.btn_calibrate.setToolTip(
            "Dibuje una línea de referencia e indique su longitud real en mm."
        )
        self.btn_calibrate.clicked.connect(self.calibrate_requested.emit)
        layout.addWidget(self.btn_calibrate)

        self.lbl_hint = QLabel(
            "Sin calibración DICOM: las medidas se muestran en píxeles."
        )
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.lbl_hint)
        layout.addStretch(1)

    def set_calibration(self, calib: ImageCalibration) -> None:
        """Actualiza el panel con la calibración actual."""
        source_label = {
            "PixelSpacing": "PixelSpacing",
            "ImagerPixelSpacing": "ImagerPixelSpacing",
            "NominalScannedPixelSpacing": "NominalScannedPixelSpacing",
            "PhysicalDelta": "PhysicalDelta",
            "Manual": "Manual",
            "Unknown": "Sin calibración",
        }.get(calib.source, calib.source)
        self.lbl_source.setText(f"Fuente:\n{source_label}")
        if calib.calibrated and calib.pixel_spacing_x is not None:
            self.lbl_px.setText(f"Pixel X:\n{calib.pixel_spacing_x:.4f} mm")
            self.lbl_py.setText(f"Pixel Y:\n{calib.pixel_spacing_y:.4f} mm")
            self.lbl_status.setText("Estado:\n🟢 Calibrado")
            self.lbl_status.setStyleSheet("color: #4ade80; font-weight: 600;")
            self.lbl_hint.setText("Mediciones en mm / cm².")
        else:
            self.lbl_px.setText("Pixel X:\n—")
            self.lbl_py.setText("Pixel Y:\n—")
            self.lbl_status.setText("Estado:\n🔴 Sin calibración")
            self.lbl_status.setStyleSheet("color: #f87171; font-weight: 600;")
            self.lbl_hint.setText(
                "Imagen no calibrada: medidas en píxeles. "
                "Use «Calibrar imagen» o abra un DICOM con PixelSpacing."
            )
