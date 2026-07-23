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
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.models.image import CapturedImage
from app.ui.widgets.annotate_canvas import AnnotateCanvas


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
        self._build()

    def _build(self) -> None:
        group = QGroupBox("Imágenes capturadas — dibuje con el mouse (Paint)")
        layout = QVBoxLayout(group)

        tools = QHBoxLayout()
        tools.addWidget(QLabel("Color:"))
        self.combo_color = QComboBox()
        for name in self.COLORS:
            self.combo_color.addItem(name)
        tools.addWidget(self.combo_color)

        tools.addWidget(QLabel("Grosor:"))
        self.slider_width = QSlider(Qt.Orientation.Horizontal)
        self.slider_width.setRange(1, 24)
        self.slider_width.setValue(4)
        self.slider_width.setMaximumWidth(120)
        tools.addWidget(self.slider_width)

        self.btn_pen = QPushButton("Lápiz")
        self.btn_eraser = QPushButton("Borrar trazo")
        self.btn_undo = QPushButton("Deshacer")
        self.btn_clear = QPushButton("Limpiar dibujo")
        self.btn_save_draw = QPushButton("Guardar anotación")
        for btn in (
            self.btn_pen,
            self.btn_eraser,
            self.btn_undo,
            self.btn_clear,
            self.btn_save_draw,
        ):
            tools.addWidget(btn)
        tools.addStretch(1)
        layout.addLayout(tools)

        body = QHBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.setMaximumWidth(180)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)

        self.canvas = AnnotateCanvas()
        body.addWidget(self.list_widget)
        body.addWidget(self.canvas, stretch=1)
        layout.addLayout(body, stretch=1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

        self.combo_color.currentTextChanged.connect(self._on_color)
        self.slider_width.valueChanged.connect(self.canvas.set_pen_width)
        self.btn_pen.clicked.connect(lambda: self.canvas.set_eraser(False))
        self.btn_eraser.clicked.connect(lambda: self.canvas.set_eraser(True))
        self.btn_undo.clicked.connect(self.canvas.undo)
        self.btn_clear.clicked.connect(self.canvas.clear_drawings)
        self.btn_save_draw.clicked.connect(lambda: self.save_current_annotation(False))
        self._on_color(self.combo_color.currentText())

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

    def save_current_annotation(self, silent: bool = False) -> bool:
        if self._current_path is None or not self.canvas.has_image():
            return False
        ok = self.canvas.save_to_path(self._current_path)
        if ok and not silent:
            self.canvas.load_path(self._current_path)
        return ok

    def _on_color(self, name: str) -> None:
        self.canvas.set_pen_color(self.COLORS.get(name, QColor(255, 40, 40)))

    def _on_row_changed(self, row: int) -> None:
        self.save_current_annotation(silent=True)
        self.selection_changed.emit(row)
        if row < 0 or row >= len(self._images):
            self._current_path = None
            self.canvas.clear_canvas()
            return
        path = self._images[row].path
        self._current_path = path
        self.canvas.load_path(path)
