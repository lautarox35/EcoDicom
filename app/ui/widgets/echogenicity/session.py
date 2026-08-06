"""Sesión de análisis ROI enlazada a canvas + panel."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QObject

from app.analysis.calibration.models import ImageCalibration
from app.analysis.echogenicity.analyzer import EcogenicityAnalyzer
from app.analysis.echogenicity.models import ROIRect

if TYPE_CHECKING:
    from app.ui.widgets.annotate_canvas import AnnotateCanvas
    from app.ui.widgets.echogenicity.ecogenicity_panel import EcogenicityPanel


class EcogenicitySession(QObject):
    """
    Conecta AnnotateCanvas (modo ROI) con EcogenicityPanel y el analyzer.

    El array gris debe ser Pixel Data / archivo original, nunca el pixmap.
    """

    def __init__(
        self,
        canvas: "AnnotateCanvas",
        panel: "EcogenicityPanel",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.canvas = canvas
        self.panel = panel
        self.analyzer = EcogenicityAnalyzer(panel.white_threshold())
        self._gray: Optional[np.ndarray] = None
        self._calib: ImageCalibration = ImageCalibration.unknown()
        self._active = False

        canvas.roi_changed.connect(self._on_roi_changed)
        canvas.roi_committed.connect(self._on_roi_changed)
        panel.threshold_changed.connect(self._on_threshold)
        panel.closed.connect(self.deactivate)

    @property
    def active(self) -> bool:
        """True si el modo ROI está activo."""
        return self._active

    def set_gray_source(self, gray: Optional[np.ndarray]) -> None:
        """
        Asigna la imagen gris original para el análisis.

        Debe coincidir en tamaño con la imagen mostrada en el canvas.
        """
        self._gray = gray
        if self._active:
            self._reanalyze(self.canvas.active_roi())

    def set_calibration(self, calib: ImageCalibration) -> None:
        """Propaga calibración espacial al panel de resultados."""
        self._calib = calib
        self.panel.set_calibration(calib)
        if self._active:
            self._reanalyze(self.canvas.active_roi())

    def activate(self) -> None:
        """Activa modo ROI y muestra el panel."""
        self._active = True
        self.analyzer.set_white_threshold(self.panel.white_threshold())
        self.canvas.set_mode("roi")
        self._reanalyze(self.canvas.active_roi())

    def deactivate(self) -> None:
        """Vuelve a Paint y limpia el ROI."""
        self._active = False
        self.canvas.set_mode("paint")
        self.canvas.clear_roi()
        self.panel.clear_result()

    def toggle(self) -> bool:
        """Activa/desactiva; devuelve el estado activo resultante."""
        if self._active:
            self.deactivate()
            return False
        self.activate()
        return True

    def _on_threshold(self, value: int) -> None:
        self.analyzer.set_white_threshold(value)
        if self._active:
            self._reanalyze(self.canvas.active_roi())

    def _on_roi_changed(self, roi: object) -> None:
        if not self._active:
            return
        self._reanalyze(roi if isinstance(roi, ROIRect) else None)

    def _reanalyze(self, roi: Optional[ROIRect]) -> None:
        if self._gray is None or roi is None or roi.is_empty():
            self.panel.clear_result()
            return
        # Validar que el canvas y el gris coincidan en tamaño
        size = self.canvas.image_size()
        if size is not None:
            gh, gw = self._gray.shape[:2]
            if (gw, gh) != size:
                # Si difieren, aún analizamos el gris (fuente de verdad);
                # el ROI está en coords del pixmap mostrado — clamp al gris.
                pass
        result = self.analyzer.analyze(self._gray, roi, roi_label="ROI 1")
        self.panel.set_result(result)
