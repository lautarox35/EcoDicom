"""Contenedor: canvas de captura + panel de análisis al costado (herramienta)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.annotate_canvas import AnnotateCanvas
from app.ui.widgets.echogenicity.calibration_panel import CalibrationPanel
from app.ui.widgets.echogenicity.ecogenicity_panel import EcogenicityPanel
from app.ui.widgets.echogenicity.freehand_panel import FreehandROIPanel


class EcoCanvasHost(QWidget):
    """
    Visor de captura a la izquierda; panel de ecogenicidad / ROI libre /
    calibración a la derecha como columna de herramienta (no encima de la imagen).
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.canvas = AnnotateCanvas(self)
        self.canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.eco_panel = EcogenicityPanel()
        self.freehand_panel = FreehandROIPanel()
        self.calib_panel = CalibrationPanel()
        for panel in (self.eco_panel, self.freehand_panel, self.calib_panel):
            panel.setMaximumWidth(16777215)
            panel.setMinimumWidth(220)

        self._tool_scroll = QScrollArea()
        self._tool_scroll.setWidgetResizable(True)
        self._tool_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._tool_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._tool_scroll.setMinimumWidth(250)
        self._tool_scroll.setMaximumWidth(320)
        self._tool_scroll.hide()

        self._tool_inner = QWidget()
        self._tool_layout = QVBoxLayout(self._tool_inner)
        self._tool_layout.setContentsMargins(0, 0, 0, 0)
        self._tool_layout.setSpacing(0)
        self._tool_layout.addWidget(self.eco_panel)
        self._tool_layout.addWidget(self.freehand_panel)
        self._tool_layout.addWidget(self.calib_panel)
        self._tool_layout.addStretch(1)
        self._tool_scroll.setWidget(self._tool_inner)

        self.eco_panel.hide()
        self.freehand_panel.hide()
        self.calib_panel.hide()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)
        root.addWidget(self.canvas, stretch=1)
        root.addWidget(self._tool_scroll, stretch=0)

        self._active_panel: Optional[QFrame] = None

    def _show_only(self, panel: QFrame) -> None:
        self.eco_panel.hide()
        self.freehand_panel.hide()
        self.calib_panel.hide()
        panel.show()
        self._active_panel = panel
        self._tool_scroll.show()

    def _hide_if_active(self, panel: QFrame) -> None:
        panel.hide()
        if self._active_panel is panel:
            self._active_panel = None
        if (
            not self.eco_panel.isVisible()
            and not self.freehand_panel.isVisible()
            and not self.calib_panel.isVisible()
        ):
            self._tool_scroll.hide()

    def show_panel(self, visible: bool = True) -> None:
        """Muestra/oculta el panel rectangular de ecogenicidad al costado."""
        if visible:
            self._show_only(self.eco_panel)
        else:
            self._hide_if_active(self.eco_panel)

    def show_freehand_panel(self, visible: bool = True) -> None:
        """Muestra/oculta el panel de ROI libre al costado."""
        if visible:
            self._show_only(self.freehand_panel)
        else:
            self._hide_if_active(self.freehand_panel)

    def show_calibration_panel(self, visible: bool = True) -> None:
        """Muestra/oculta el panel de calibración espacial."""
        if visible:
            self._show_only(self.calib_panel)
        else:
            self._hide_if_active(self.calib_panel)
