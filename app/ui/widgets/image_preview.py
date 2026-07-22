"""Vista previa de imágenes importadas/capturadas."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.image import CapturedImage


class ImagePreview(QWidget):
    selection_changed = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._images: list[CapturedImage] = []
        self._build()

    def _build(self) -> None:
        group = QGroupBox("Vista previa de imágenes")
        layout = QHBoxLayout(group)

        self.list_widget = QListWidget()
        self.list_widget.setMaximumWidth(180)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)

        self.preview_label = QLabel("Sin imágenes")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(320, 280)
        self.preview_label.setStyleSheet(
            "QLabel { background: #1a1a1a; color: #aaa; border: 1px solid #444; }"
        )
        self.preview_label.setScaledContents(False)

        layout.addWidget(self.list_widget)
        layout.addWidget(self.preview_label, stretch=1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(group)

    def images(self) -> list[CapturedImage]:
        return list(self._images)

    def add_image(self, image: CapturedImage) -> None:
        self._images.append(image)
        item = QListWidgetItem(f"{image.filename} ({image.source})")
        self.list_widget.addItem(item)
        self.list_widget.setCurrentRow(len(self._images) - 1)

    def clear(self) -> None:
        self._images.clear()
        self.list_widget.clear()
        self.preview_label.setText("Sin imágenes")
        self.preview_label.setPixmap(QPixmap())

    def _on_row_changed(self, row: int) -> None:
        self.selection_changed.emit(row)
        if row < 0 or row >= len(self._images):
            self.preview_label.setText("Sin imágenes")
            self.preview_label.setPixmap(QPixmap())
            return
        path = self._images[row].path
        self._show_path(path)

    def _show_path(self, path: Path) -> None:
        pix = QPixmap(str(path))
        if pix.isNull():
            self.preview_label.setText(f"No se pudo cargar:\n{path.name}")
            return
        scaled = pix.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        row = self.list_widget.currentRow()
        if 0 <= row < len(self._images):
            self._show_path(self._images[row].path)
