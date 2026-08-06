"""Sesión ROI libre: canvas + panel + analyzer + calibración."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QObject

from app.analysis.calibration.models import ImageCalibration
from app.analysis.roi_freehand.analyzer import FreehandROIAnalyzer
from app.analysis.roi_freehand.models import PolygonROI

if TYPE_CHECKING:
    from app.ui.widgets.annotate_canvas import AnnotateCanvas
    from app.ui.widgets.echogenicity.freehand_panel import FreehandROIPanel


class FreehandROISession(QObject):
    """Conecta modo freehand del canvas con el panel de análisis."""

    def __init__(
        self,
        canvas: "AnnotateCanvas",
        panel: "FreehandROIPanel",
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.canvas = canvas
        self.panel = panel
        self.analyzer = FreehandROIAnalyzer(panel.white_threshold())
        self._gray: Optional[np.ndarray] = None
        self._calib: ImageCalibration = ImageCalibration.unknown()
        self._active = False

        canvas.freehand_changed.connect(self._on_poly_changed)
        canvas.freehand_committed.connect(self._on_poly_changed)
        panel.threshold_changed.connect(self._on_threshold)
        panel.closed.connect(self.deactivate)

    @property
    def active(self) -> bool:
        return self._active

    def set_gray_source(
        self,
        gray: Optional[np.ndarray],
        spacing_mm: Optional[tuple[float, float]] = None,
        calibration: Optional[ImageCalibration] = None,
    ) -> None:
        """Fuente de píxeles + calibración espacial."""
        self._gray = gray
        if calibration is not None:
            self._calib = calibration
        elif spacing_mm is not None:
            row_s, col_s = spacing_mm
            self._calib = ImageCalibration(
                source="PixelSpacing",
                pixel_spacing_x=float(col_s),
                pixel_spacing_y=float(row_s),
                calibrated=True,
            )
        self.panel.set_calibration(self._calib)
        if self._active:
            self._reanalyze(self.canvas.active_freehand())

    def set_calibration(self, calib: ImageCalibration) -> None:
        self._calib = calib
        self.panel.set_calibration(calib)
        if self._active:
            self._reanalyze(self.canvas.active_freehand())

    def activate(self) -> None:
        self._active = True
        self.analyzer.set_white_threshold(self.panel.white_threshold())
        self.canvas.set_mode("freehand")
        self._reanalyze(self.canvas.active_freehand())

    def deactivate(self) -> None:
        self._active = False
        self.canvas.set_mode("paint")
        self.canvas.clear_freehand()
        self.panel.clear_result()

    def _on_threshold(self, value: int) -> None:
        self.analyzer.set_white_threshold(value)
        if self._active:
            self._reanalyze(self.canvas.active_freehand())

    def _on_poly_changed(self, poly: object) -> None:
        if not self._active:
            return
        self._reanalyze(poly if isinstance(poly, PolygonROI) else None)

    def _reanalyze(self, poly: Optional[PolygonROI]) -> None:
        if self._gray is None or poly is None or not poly.closed:
            self.panel.clear_result()
            return
        result = self.analyzer.analyze(
            self._gray,
            poly,
            spacing_mm=self._calib.spacing_row_col,
            roi_label=poly.roi_id or "ROI 1",
        )
        self.panel.set_result(result)
