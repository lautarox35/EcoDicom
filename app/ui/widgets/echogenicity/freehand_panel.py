"""Panel card para ROI libre: superficie + ecogenicidad."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.analysis.calibration.models import ImageCalibration
from app.analysis.roi_freehand.export import export_freehand_roi
from app.analysis.roi_freehand.models import FreehandAnalysisResult


class _DistBar(QWidget):
    def __init__(self, label: str, color: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._label = label
        self._color = QColor(color)
        self._pct = 0.0
        self.setMinimumHeight(18)
        self.setMaximumHeight(20)

    def set_percent(self, pct: float) -> None:
        self._pct = max(0.0, min(100.0, pct))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QColor("#94a3b8"))
        painter.drawText(0, 0, 72, self.height(), Qt.AlignmentFlag.AlignVCenter, self._label)
        track = self.rect().adjusted(76, 4, -48, -4)
        painter.fillRect(track, QColor("#1e293b"))
        fill_w = int(track.width() * self._pct / 100.0)
        if fill_w > 0:
            painter.fillRect(track.x(), track.y(), fill_w, track.height(), self._color)
        painter.setPen(QColor("#e2e8f0"))
        painter.drawText(
            track.right() + 6,
            0,
            42,
            self.height(),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            f"{self._pct:.0f}%",
        )


class FreehandROIPanel(QFrame):
    """Card lateral ROI Libre."""

    threshold_changed = Signal(int)
    closed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._result: Optional[FreehandAnalysisResult] = None
        self._calib: ImageCalibration = ImageCalibration.unknown()
        self.setObjectName("freehandCard")
        self.setStyleSheet(
            """
            QFrame#freehandCard {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QLabel { color: #e2e8f0; }
            QLabel#title {
                color: #14b8a6;
                font-weight: 700;
                font-size: 13px;
                letter-spacing: 1px;
            }
            QLabel#ecoValue {
                color: #5eead4;
                font-size: 26px;
                font-weight: 700;
            }
            QSpinBox {
                background: #1e293b; color: #e2e8f0;
                border: 1px solid #475569; border-radius: 4px; padding: 2px 4px;
            }
            QPushButton {
                background: #1e293b; color: #e2e8f0;
                border: 1px solid #475569; border-radius: 6px; padding: 6px 10px;
            }
            QPushButton:hover { background: #334155; }
            QPushButton#exportBtn {
                background: #0f766e; border-color: #14b8a6; font-weight: 600;
            }
            """
        )
        self.setMinimumWidth(220)
        self.setMaximumWidth(300)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("ROI LIBRE")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch(1)
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedWidth(28)
        self.btn_close.clicked.connect(self.closed.emit)
        header.addWidget(self.btn_close)
        layout.addLayout(header)

        self.lbl_hint = QLabel("Clics o arrastre · doble clic cierra")
        self.lbl_hint.setStyleSheet("color: #94a3b8; font-size: 11px;")
        layout.addWidget(self.lbl_hint)

        self.lbl_calib_warn = QLabel("")
        self.lbl_calib_warn.setWordWrap(True)
        self.lbl_calib_warn.setStyleSheet("color: #fbbf24; font-size: 11px;")
        layout.addWidget(self.lbl_calib_warn)

        thr = QHBoxLayout()
        thr.addWidget(QLabel("Umbral blanco"))
        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(0, 255)
        self.spin_threshold.setValue(180)
        self.spin_threshold.valueChanged.connect(self.threshold_changed.emit)
        thr.addWidget(self.spin_threshold)
        layout.addLayout(thr)

        self.lbl_surface = QLabel("Superficie:\n—")
        self.lbl_area_mm = QLabel("Área:\n—")
        self.lbl_peri = QLabel("Perímetro:\n—")
        self.lbl_bbox = QLabel("Bounding box:\n—")
        self.lbl_centroid = QLabel("Centroide:\n—")
        self.lbl_pixels = QLabel("Píxeles:\n—")
        for w in (
            self.lbl_surface,
            self.lbl_area_mm,
            self.lbl_peri,
            self.lbl_bbox,
            self.lbl_centroid,
            self.lbl_pixels,
        ):
            layout.addWidget(w)

        layout.addWidget(QLabel("Ecogenicidad"))
        self.lbl_eco = QLabel("—")
        self.lbl_eco.setObjectName("ecoValue")
        layout.addWidget(self.lbl_eco)

        self.lbl_mean = QLabel("Promedio: —")
        self.lbl_std = QLabel("Desviación: —")
        layout.addWidget(self.lbl_mean)
        layout.addWidget(self.lbl_std)

        layout.addWidget(QLabel("Distribución"))
        self.bar_black = _DistBar("Negros", "#1e293b")
        self.bar_dark = _DistBar("Oscuros", "#475569")
        self.bar_gray = _DistBar("Grises", "#94a3b8")
        self.bar_light = _DistBar("Claros", "#cbd5e1")
        self.bar_white = _DistBar("Blancos", "#f8fafc")
        for b in (
            self.bar_black,
            self.bar_dark,
            self.bar_gray,
            self.bar_light,
            self.bar_white,
        ):
            layout.addWidget(b)

        self.btn_export = QPushButton("Exportar análisis")
        self.btn_export.setObjectName("exportBtn")
        self.btn_export.clicked.connect(self._on_export)
        layout.addWidget(self.btn_export)
        layout.addStretch(1)
        self.clear_result()
        self.set_calibration(ImageCalibration.unknown())

    def white_threshold(self) -> int:
        return int(self.spin_threshold.value())

    def set_calibration(self, calib: ImageCalibration) -> None:
        """Actualiza aviso según calibración espacial."""
        self._calib = calib
        if calib.calibrated:
            self.lbl_calib_warn.setText(
                f"Calibrado ({calib.source}): medidas en mm."
            )
            self.lbl_calib_warn.setStyleSheet("color: #4ade80; font-size: 11px;")
        else:
            self.lbl_calib_warn.setText(
                "Sin calibración: medidas en píxeles. Use «Calibración»."
            )
            self.lbl_calib_warn.setStyleSheet("color: #fbbf24; font-size: 11px;")
        if self._result is not None:
            self.set_result(self._result)

    def set_result(self, result: Optional[FreehandAnalysisResult]) -> None:
        self._result = result
        if result is None:
            self.clear_result()
            return
        g = result.geometry
        s = result.statistics
        d = result.distribution
        calibrated = g.area_mm2 is not None

        if calibrated:
            self.lbl_surface.setText(f"Superficie:\n{g.area_cm2:.2f} cm²")
            self.lbl_area_mm.setText(f"Área:\n{g.area_mm2:.2f} mm²")
            self.lbl_peri.setText(f"Perímetro:\n{g.perimeter_mm:.1f} mm")
            w_mm = g.bbox_width * (g.col_spacing_mm or 0)
            h_mm = g.bbox_height * (g.row_spacing_mm or 0)
            self.lbl_bbox.setText(f"Bounding box:\n{w_mm:.1f} × {h_mm:.1f} mm")
            cx = g.centroid_x * (g.col_spacing_mm or 1)
            cy = g.centroid_y * (g.row_spacing_mm or 1)
            self.lbl_centroid.setText(f"Centroide:\nX: {cx:.1f} mm\nY: {cy:.1f} mm")
        else:
            self.lbl_surface.setText(
                f"Superficie:\n{g.pixel_area:,.0f} px²".replace(",", ".")
            )
            self.lbl_area_mm.setText("Área:\n(sin calibración)")
            self.lbl_peri.setText(f"Perímetro:\n{g.perimeter_px:.1f} px")
            self.lbl_bbox.setText(
                f"Bounding box:\n{g.bbox_width} × {g.bbox_height} px"
            )
            self.lbl_centroid.setText(
                f"Centroide:\nX: {g.centroid_x:.1f} px\nY: {g.centroid_y:.1f} px"
            )

        self.lbl_pixels.setText(f"Píxeles:\n{s.pixel_count:,}".replace(",", "."))
        self.lbl_eco.setText(f"{result.white_percentage:.1f} %")
        self.lbl_mean.setText(f"Promedio: {s.mean:.0f}")
        self.lbl_std.setText(f"Desviación: {s.std_dev:.1f}")
        self.bar_black.set_percent(d.black)
        self.bar_dark.set_percent(d.dark)
        self.bar_gray.set_percent(d.gray)
        self.bar_light.set_percent(d.light)
        self.bar_white.set_percent(d.white)
        self.btn_export.setEnabled(True)
        self.lbl_hint.setText(result.roi_label)

    def clear_result(self) -> None:
        self._result = None
        self.lbl_surface.setText("Superficie:\n—")
        self.lbl_area_mm.setText("Área:\n—")
        self.lbl_peri.setText("Perímetro:\n—")
        self.lbl_bbox.setText("Bounding box:\n—")
        self.lbl_centroid.setText("Centroide:\n—")
        self.lbl_pixels.setText("Píxeles:\n—")
        self.lbl_eco.setText("—")
        self.lbl_mean.setText("Promedio: —")
        self.lbl_std.setText("Desviación: —")
        for b in (
            self.bar_black,
            self.bar_dark,
            self.bar_gray,
            self.bar_light,
            self.bar_white,
        ):
            b.set_percent(0)
        self.btn_export.setEnabled(False)
        self.lbl_hint.setText("Clics o arrastre · doble clic cierra")

    def _on_export(self) -> None:
        if self._result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar ROI Libre",
            "roi_libre.json",
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            export_freehand_roi(self._result, path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Exportar", str(exc))
            return
        QMessageBox.information(self, "Exportar", f"Guardado en:\n{path}")
