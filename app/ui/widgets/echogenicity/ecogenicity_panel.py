"""Panel tipo card con resultados de análisis de ecogenicidad."""

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

from app.analysis.calibration.measure import area_mm2
from app.analysis.calibration.models import ImageCalibration
from app.analysis.echogenicity.export import export_roi_analysis
from app.analysis.echogenicity.models import EcogenicityResult


class _HistogramWidget(QWidget):
    """Histograma de barras 0–255 dibujado con QPainter."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._counts: tuple[int, ...] = tuple()
        self.setMinimumHeight(72)
        self.setMaximumHeight(90)

    def set_histogram(self, counts: tuple[int, ...]) -> None:
        self._counts = counts
        self.update()

    def clear(self) -> None:
        self._counts = tuple()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0f172a"))
        if not self._counts:
            painter.setPen(QColor("#64748b"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Histograma")
            return
        peak = max(self._counts) or 1
        w = self.width()
        h = self.height()
        n = len(self._counts)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#14b8a6"))
        for i, c in enumerate(self._counts):
            bar_h = int((c / peak) * (h - 4))
            x = int(i * w / n)
            bw = max(1, int(w / n) + 1)
            painter.drawRect(x, h - bar_h - 2, bw, bar_h)


class _DistBar(QWidget):
    """Barra horizontal de porcentaje para una categoría."""

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


class EcogenicityPanel(QFrame):
    """
    Card lateral ANÁLISIS ROI.

    Señales
    -------
    threshold_changed:
        Nuevo umbral de blanco (0–255).
    closed:
        El usuario cerró / desactivó el panel.
    """

    threshold_changed = Signal(int)
    closed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._result: Optional[EcogenicityResult] = None
        self._calib: ImageCalibration = ImageCalibration.unknown()
        self.setObjectName("ecogenicityCard")
        self.setStyleSheet(
            """
            QFrame#ecogenicityCard {
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
                font-size: 28px;
                font-weight: 700;
            }
            QSpinBox {
                background: #1e293b;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 2px 4px;
            }
            QPushButton {
                background: #1e293b;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QPushButton:hover { background: #334155; }
            QPushButton#exportBtn {
                background: #0f766e;
                border-color: #14b8a6;
                font-weight: 600;
            }
            """
        )
        self.setMinimumWidth(240)
        self.setMaximumWidth(300)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("ANÁLISIS ROI")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch(1)
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedWidth(28)
        self.btn_close.setToolTip("Cerrar análisis")
        self.btn_close.clicked.connect(self.closed.emit)
        header.addWidget(self.btn_close)
        layout.addLayout(header)

        thr_row = QHBoxLayout()
        thr_row.addWidget(QLabel("Umbral blanco"))
        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(0, 255)
        self.spin_threshold.setValue(180)
        self.spin_threshold.setToolTip(
            "Píxeles ≥ umbral cuentan para Ecogenicidad (%). "
            "Las bandas Blancos de distribución usan 181–255."
        )
        self.spin_threshold.valueChanged.connect(self.threshold_changed.emit)
        thr_row.addWidget(self.spin_threshold)
        layout.addLayout(thr_row)

        self.lbl_area = QLabel("Área: —")
        self.lbl_mean = QLabel("Promedio: —")
        self.lbl_min = QLabel("Mínimo: —")
        self.lbl_max = QLabel("Máximo: —")
        self.lbl_std = QLabel("Desviación: —")
        self.lbl_median = QLabel("Mediana: —")
        for w in (
            self.lbl_area,
            self.lbl_mean,
            self.lbl_min,
            self.lbl_max,
            self.lbl_std,
            self.lbl_median,
        ):
            layout.addWidget(w)

        layout.addWidget(QLabel("Ecogenicidad"))
        self.lbl_eco = QLabel("—")
        self.lbl_eco.setObjectName("ecoValue")
        self.lbl_eco.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.lbl_eco)

        layout.addWidget(QLabel("Distribución"))
        self.bar_black = _DistBar("Negros", "#1e293b")
        self.bar_dark = _DistBar("Oscuros", "#475569")
        self.bar_gray = _DistBar("Grises", "#94a3b8")
        self.bar_light = _DistBar("Claros", "#cbd5e1")
        self.bar_white = _DistBar("Blancos", "#f8fafc")
        for bar in (
            self.bar_black,
            self.bar_dark,
            self.bar_gray,
            self.bar_light,
            self.bar_white,
        ):
            # Fondo visible para negros
            layout.addWidget(bar)
        self.bar_black.setStyleSheet("background: transparent;")

        layout.addWidget(QLabel("Histograma (0–255)"))
        self.histogram = _HistogramWidget()
        layout.addWidget(self.histogram)

        self.btn_export = QPushButton("Exportar análisis")
        self.btn_export.setObjectName("exportBtn")
        self.btn_export.clicked.connect(self._on_export)
        layout.addWidget(self.btn_export)
        layout.addStretch(1)

        self.clear_result()

    def white_threshold(self) -> int:
        """Umbral de blanco actual del panel."""
        return int(self.spin_threshold.value())

    def set_calibration(self, calib: ImageCalibration) -> None:
        """Actualiza calibración usada para mostrar área en mm²."""
        self._calib = calib
        if self._result is not None:
            self.set_result(self._result)

    def set_result(self, result: Optional[EcogenicityResult]) -> None:
        """Actualiza la card con un nuevo resultado (o vacío)."""
        self._result = result
        if result is None:
            self.clear_result()
            return
        s = result.statistics
        d = result.distribution
        mm2 = area_mm2(float(s.pixel_count), self._calib)
        if mm2 is not None:
            self.lbl_area.setText(
                f"Área:\n{mm2:.2f} mm²\n({s.pixel_count:,} px)".replace(",", ".")
            )
        else:
            self.lbl_area.setText(
                f"Área:\n{s.pixel_count:,} píxeles\n(sin calibración)".replace(",", ".")
            )
        self.lbl_mean.setText(f"Promedio:\n{s.mean:.0f}")
        self.lbl_min.setText(f"Mínimo:\n{s.min_intensity}")
        self.lbl_max.setText(f"Máximo:\n{s.max_intensity}")
        self.lbl_std.setText(f"Desviación:\n{s.std_dev:.1f}")
        self.lbl_median.setText(f"Mediana:\n{s.median:.0f}")
        self.lbl_eco.setText(f"{result.white_percentage:.1f} %")
        self.bar_black.set_percent(d.black)
        self.bar_dark.set_percent(d.dark)
        self.bar_gray.set_percent(d.gray)
        self.bar_light.set_percent(d.light)
        self.bar_white.set_percent(d.white)
        self.histogram.set_histogram(result.histogram)
        self.btn_export.setEnabled(True)

    def clear_result(self) -> None:
        """Estado vacío: sin ROI válido."""
        self._result = None
        self.lbl_area.setText("Área:\n—")
        self.lbl_mean.setText("Promedio:\n—")
        self.lbl_min.setText("Mínimo:\n—")
        self.lbl_max.setText("Máximo:\n—")
        self.lbl_std.setText("Desviación:\n—")
        self.lbl_median.setText("Mediana:\n—")
        self.lbl_eco.setText("—")
        for bar in (
            self.bar_black,
            self.bar_dark,
            self.bar_gray,
            self.bar_light,
            self.bar_white,
        ):
            bar.set_percent(0)
        self.histogram.clear()
        self.btn_export.setEnabled(False)

    def _on_export(self) -> None:
        if self._result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar análisis ROI",
            "ecogenicidad_roi.json",
            "JSON (*.json)",
        )
        if not path:
            return
        try:
            export_roi_analysis(self._result, path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Exportar", str(exc))
            return
        QMessageBox.information(self, "Exportar", f"Análisis guardado en:\n{path}")
