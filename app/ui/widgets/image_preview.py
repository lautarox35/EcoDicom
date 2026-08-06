"""Vista previa de imágenes importadas/capturadas con anotación Paint."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.analysis.calibration.models import ImageCalibration
from app.analysis.calibration.reader import load_image_calibration, log_calibration
from app.analysis.calibration.store import save_manual_calibration
from app.analysis.echogenicity.grayscale import load_gray_from_path
from app.models.image import CapturedImage
from app.ui.widgets.echogenicity.eco_canvas_host import EcoCanvasHost
from app.ui.widgets.echogenicity.freehand_session import FreehandROISession
from app.ui.widgets.echogenicity.session import EcogenicitySession


class ImagePreview(QWidget):
    selection_changed = Signal(int)

    COLORS = {
        "Rojo": QColor(255, 40, 40),
        "Amarillo": QColor(255, 220, 0),
        "Verde": QColor(40, 200, 80),
        "Blanco": QColor(255, 255, 255),
        "Cian": QColor(0, 220, 255),
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._images: list[CapturedImage] = []
        self._current_path: Optional[Path] = None
        self._calibration: ImageCalibration = ImageCalibration.unknown()
        self._eco_session: Optional[EcogenicitySession] = None
        self._freehand_session: Optional[FreehandROISession] = None
        self._build()

    def _build(self) -> None:
        group = QGroupBox("Capturas / Importadas (anotar con el mouse)")
        layout = QVBoxLayout(group)

        tools = QHBoxLayout()
        tools.addWidget(QLabel("Color"))
        self.combo_color = QComboBox()
        self.combo_color.addItems(list(self.COLORS.keys()))
        tools.addWidget(self.combo_color)

        tools.addWidget(QLabel("Grosor"))
        self.slider_width = QSlider(Qt.Orientation.Horizontal)
        self.slider_width.setRange(1, 20)
        self.slider_width.setValue(4)
        self.slider_width.setFixedWidth(100)
        self.slider_width.setMaximumHeight(22)
        self.slider_width.setStyleSheet(
            """
            QSlider::groove:horizontal {
                border: none; height: 4px; background: #9e9e9e; border-radius: 2px;
            }
            QSlider::sub-page:horizontal { background: #1976d2; border-radius: 2px; }
            QSlider::add-page:horizontal { background: #cfcfcf; border-radius: 2px; }
            QSlider::handle:horizontal {
                background: #fff; border: 2px solid #1976d2;
                width: 14px; height: 14px; margin: -6px 0; border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #e3f2fd;
                border: 2px solid #0d47a1;
            }
            """
        )
        tools.addWidget(self.slider_width)

        self.lbl_thick = QLabel("━")
        self.lbl_thick.setToolTip("Trazo grueso")
        tools.addWidget(self.lbl_thick)

        self.lbl_width_value = QLabel("4 px")
        self.lbl_width_value.setMinimumWidth(40)
        self.lbl_width_value.setStyleSheet("color: #444; font-weight: 600;")
        tools.addWidget(self.lbl_width_value)

        self.btn_pen = QPushButton("Lápiz")
        self.btn_eraser = QPushButton("Borrar trazo")
        self.btn_undo = QPushButton("Deshacer")
        self.btn_clear = QPushButton("Limpiar dibujo")
        self.btn_save_draw = QPushButton("Guardar anotación")
        self.btn_ecogenicity = QPushButton("Análisis de Ecogenicidad")
        self.btn_ecogenicity.setCheckable(True)
        self.btn_ecogenicity.setToolTip(
            "ROI rectangular sobre los píxeles originales del archivo."
        )
        self.btn_freehand = QPushButton("ROI Libre")
        self.btn_freehand.setCheckable(True)
        self.btn_freehand.setToolTip(
            "Polígono libre: clics o arrastre; doble clic cierra el contorno."
        )
        self.btn_calibration = QPushButton("Calibración")
        self.btn_calibration.setCheckable(True)
        self.btn_calibration.setToolTip(
            "Calibración espacial (PixelSpacing / PhysicalDelta / manual)."
        )
        for btn in (
            self.btn_pen,
            self.btn_eraser,
            self.btn_undo,
            self.btn_clear,
            self.btn_save_draw,
            self.btn_ecogenicity,
            self.btn_freehand,
            self.btn_calibration,
        ):
            tools.addWidget(btn)
        tools.addStretch(1)
        layout.addLayout(tools)

        body = QHBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.setMaximumWidth(180)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)

        self._eco_host = EcoCanvasHost()
        self.canvas = self._eco_host.canvas
        self.eco_panel = self._eco_host.eco_panel
        self.freehand_panel = self._eco_host.freehand_panel
        self.calib_panel = self._eco_host.calib_panel
        body.addWidget(self.list_widget)
        body.addWidget(self._eco_host, stretch=1)
        layout.addLayout(body, stretch=1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

        self._eco_session = EcogenicitySession(self.canvas, self.eco_panel, parent=self)
        self._freehand_session = FreehandROISession(
            self.canvas, self.freehand_panel, parent=self
        )

        self.combo_color.currentTextChanged.connect(self._on_color)
        self.slider_width.valueChanged.connect(self._on_width_changed)
        self.btn_pen.clicked.connect(self._on_paint_tool)
        self.btn_eraser.clicked.connect(self._on_eraser_tool)
        self.btn_undo.clicked.connect(self.canvas.undo)
        self.btn_clear.clicked.connect(self.canvas.clear_drawings)
        self.btn_save_draw.clicked.connect(lambda: self.save_current_annotation(False))
        self.btn_ecogenicity.toggled.connect(self._on_ecogenicity_toggled)
        self.btn_freehand.toggled.connect(self._on_freehand_toggled)
        self.btn_calibration.toggled.connect(self._on_calibration_toggled)
        self.eco_panel.closed.connect(lambda: self.btn_ecogenicity.setChecked(False))
        self.freehand_panel.closed.connect(lambda: self.btn_freehand.setChecked(False))
        self.calib_panel.closed.connect(lambda: self.btn_calibration.setChecked(False))
        self.calib_panel.calibrate_requested.connect(self._start_manual_calibrate)
        self.canvas.calibrate_line_done.connect(self._on_calibrate_line_done)
        self._on_color(self.combo_color.currentText())
        self._on_width_changed(self.slider_width.value())

    def _apply_calibration(self, calib: ImageCalibration) -> None:
        self._calibration = calib
        self.calib_panel.set_calibration(calib)
        if self._freehand_session is not None:
            self._freehand_session.set_calibration(calib)
        if self._eco_session is not None:
            self._eco_session.set_calibration(calib)

    def _reload_calibration(self, path: Optional[Path]) -> None:
        if path is None:
            self._apply_calibration(ImageCalibration.unknown())
            return
        self._apply_calibration(load_image_calibration(path))

    def _on_paint_tool(self) -> None:
        self._deactivate_analysis_tools()
        self.canvas.set_eraser(False)

    def _on_eraser_tool(self) -> None:
        self._deactivate_analysis_tools()
        self.canvas.set_eraser(True)

    def _deactivate_analysis_tools(self) -> None:
        if self.btn_ecogenicity.isChecked():
            self.btn_ecogenicity.setChecked(False)
        if self.btn_freehand.isChecked():
            self.btn_freehand.setChecked(False)
        if self.btn_calibration.isChecked():
            self.btn_calibration.setChecked(False)

    def _on_ecogenicity_toggled(self, checked: bool) -> None:
        if self._eco_session is None:
            return
        if checked:
            if self.btn_freehand.isChecked():
                self.btn_freehand.blockSignals(True)
                self.btn_freehand.setChecked(False)
                self.btn_freehand.blockSignals(False)
                if self._freehand_session is not None:
                    self._freehand_session.deactivate()
                self._eco_host.show_freehand_panel(False)
            if self.btn_calibration.isChecked():
                self.btn_calibration.blockSignals(True)
                self.btn_calibration.setChecked(False)
                self.btn_calibration.blockSignals(False)
                self.canvas.clear_calibrate()
                self._eco_host.show_calibration_panel(False)
            if not self.canvas.has_image():
                self.btn_ecogenicity.blockSignals(True)
                self.btn_ecogenicity.setChecked(False)
                self.btn_ecogenicity.blockSignals(False)
                QMessageBox.information(
                    self,
                    "Ecogenicidad",
                    "Capture o importe una imagen antes de analizar.",
                )
                return
            self._eco_session.activate()
            self._eco_host.show_panel(True)
            self._set_paint_tools_enabled(False)
        else:
            self._eco_session.deactivate()
            self._eco_host.show_panel(False)
            if not self.btn_freehand.isChecked() and not self.btn_calibration.isChecked():
                self._set_paint_tools_enabled(True)

    def _on_freehand_toggled(self, checked: bool) -> None:
        if self._freehand_session is None:
            return
        if checked:
            if self.btn_ecogenicity.isChecked():
                self.btn_ecogenicity.blockSignals(True)
                self.btn_ecogenicity.setChecked(False)
                self.btn_ecogenicity.blockSignals(False)
                if self._eco_session is not None:
                    self._eco_session.deactivate()
                self._eco_host.show_panel(False)
            if self.btn_calibration.isChecked():
                self.btn_calibration.blockSignals(True)
                self.btn_calibration.setChecked(False)
                self.btn_calibration.blockSignals(False)
                self.canvas.clear_calibrate()
                self._eco_host.show_calibration_panel(False)
            if not self.canvas.has_image():
                self.btn_freehand.blockSignals(True)
                self.btn_freehand.setChecked(False)
                self.btn_freehand.blockSignals(False)
                QMessageBox.information(
                    self,
                    "ROI Libre",
                    "Capture o importe una imagen antes de analizar.",
                )
                return
            self._freehand_session.activate()
            self._eco_host.show_freehand_panel(True)
            self._set_paint_tools_enabled(False)
        else:
            self._freehand_session.deactivate()
            self._eco_host.show_freehand_panel(False)
            if not self.btn_ecogenicity.isChecked() and not self.btn_calibration.isChecked():
                self._set_paint_tools_enabled(True)

    def _on_calibration_toggled(self, checked: bool) -> None:
        if checked:
            if self.btn_ecogenicity.isChecked():
                self.btn_ecogenicity.blockSignals(True)
                self.btn_ecogenicity.setChecked(False)
                self.btn_ecogenicity.blockSignals(False)
                if self._eco_session is not None:
                    self._eco_session.deactivate()
                self._eco_host.show_panel(False)
            if self.btn_freehand.isChecked():
                self.btn_freehand.blockSignals(True)
                self.btn_freehand.setChecked(False)
                self.btn_freehand.blockSignals(False)
                if self._freehand_session is not None:
                    self._freehand_session.deactivate()
                self._eco_host.show_freehand_panel(False)
            if not self.canvas.has_image():
                self.btn_calibration.blockSignals(True)
                self.btn_calibration.setChecked(False)
                self.btn_calibration.blockSignals(False)
                QMessageBox.information(
                    self,
                    "Calibración",
                    "Capture o importe una imagen antes de calibrar.",
                )
                return
            self.calib_panel.set_calibration(self._calibration)
            self._eco_host.show_calibration_panel(True)
            self.canvas.set_mode("paint")
            self._set_paint_tools_enabled(False)
        else:
            self.canvas.clear_calibrate()
            if self.canvas.mode() == "calibrate":
                self.canvas.set_mode("paint")
            self._eco_host.show_calibration_panel(False)
            if not self.btn_ecogenicity.isChecked() and not self.btn_freehand.isChecked():
                self._set_paint_tools_enabled(True)

    def _start_manual_calibrate(self) -> None:
        if not self.canvas.has_image():
            QMessageBox.information(
                self, "Calibración", "No hay imagen cargada."
            )
            return
        if not self.btn_calibration.isChecked():
            self.btn_calibration.setChecked(True)
        self.canvas.clear_calibrate()
        self.canvas.set_mode("calibrate")
        QMessageBox.information(
            self,
            "Calibrar imagen",
            "Haga dos clics sobre la imagen para dibujar una línea de "
            "referencia con longitud conocida.",
        )

    def _on_calibrate_line_done(self, length_px: float) -> None:
        if self._current_path is None or length_px <= 0:
            return
        mm, ok = QInputDialog.getDouble(
            self,
            "Calibrar imagen",
            f"Longitud de la línea ({length_px:.1f} px).\n"
            "Ingrese la distancia real en milímetros:",
            10.0,
            0.01,
            10000.0,
            2,
        )
        self.canvas.clear_calibrate()
        self.canvas.set_mode("paint")
        if not ok or mm <= 0:
            return
        calib = ImageCalibration.manual(mm / length_px)
        try:
            save_manual_calibration(self._current_path, calib)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Calibración", f"No se pudo guardar:\n{exc}")
            return
        log_calibration(calib)
        self._apply_calibration(calib)
        QMessageBox.information(
            self,
            "Calibración",
            f"Calibración manual guardada.\n"
            f"Pixel X/Y: {calib.pixel_spacing_x:.4f} mm/px",
        )

    def _set_paint_tools_enabled(self, enabled: bool) -> None:
        for w in (
            self.combo_color,
            self.slider_width,
            self.btn_pen,
            self.btn_eraser,
            self.btn_undo,
            self.btn_clear,
        ):
            w.setEnabled(enabled)

    def _on_width_changed(self, value: int) -> None:
        self.canvas.set_pen_width(value)
        self.lbl_width_value.setText(f"{value} px")

    def images(self) -> list[CapturedImage]:
        return list(self._images)

    def add_image(self, image: CapturedImage) -> None:
        self.save_current_annotation(silent=True)
        self._images.append(image)
        item = QListWidgetItem(f"{image.filename} ({image.source})")
        self.list_widget.addItem(item)
        self.list_widget.setCurrentRow(len(self._images) - 1)

    def clear(self) -> None:
        self.save_current_annotation(silent=True)
        self._images.clear()
        self.list_widget.clear()
        self._current_path = None
        self.canvas.clear_canvas()
        self._apply_calibration(ImageCalibration.unknown())
        if self._eco_session is not None:
            self._eco_session.set_gray_source(None)
        if self._freehand_session is not None:
            self._freehand_session.set_gray_source(None)

    def save_current_annotation(self, silent: bool = False) -> bool:
        if self._current_path is None or not self.canvas.has_image():
            return False
        ok = self.canvas.save_to_path(self._current_path)
        if ok and not silent:
            self.canvas.load_path(self._current_path)
            gray = load_gray_from_path(self._current_path)
            if self._eco_session is not None:
                self._eco_session.set_gray_source(gray)
            if self._freehand_session is not None:
                self._freehand_session.set_gray_source(
                    gray, calibration=self._calibration
                )
        return ok

    def _on_color(self, name: str) -> None:
        self.canvas.set_pen_color(self.COLORS.get(name, QColor(255, 40, 40)))

    def _on_row_changed(self, row: int) -> None:
        self.save_current_annotation(silent=True)
        self.selection_changed.emit(row)
        if row < 0 or row >= len(self._images):
            self._current_path = None
            self.canvas.clear_canvas()
            self._apply_calibration(ImageCalibration.unknown())
            if self._eco_session is not None:
                self._eco_session.set_gray_source(None)
            if self._freehand_session is not None:
                self._freehand_session.set_gray_source(None)
            return
        path = self._images[row].path
        self._current_path = path
        self.canvas.load_path(path)
        self._reload_calibration(path)
        gray = load_gray_from_path(path)
        if self._eco_session is not None:
            self._eco_session.set_gray_source(gray)
        if self._freehand_session is not None:
            self._freehand_session.set_gray_source(
                gray, calibration=self._calibration
            )
