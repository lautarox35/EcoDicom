"""Lógica de selección / movimiento / redimensionado de ROI."""

from __future__ import annotations

from enum import Enum, auto
from typing import Optional

from app.analysis.echogenicity.models import ROIRect

HANDLE_HIT = 12  # píxeles en espacio de imagen


class RoiHandle(Enum):
    """Esquinas redimensionables del ROI."""

    NONE = auto()
    NW = auto()
    NE = auto()
    SW = auto()
    SE = auto()
    BODY = auto()


class ROISelectionTool:
    """
    Gestiona el estado de uno o más ROI en coordenadas de imagen.

    v1 usa un solo ROI activo; la lista interna permite expandir a N.
    """

    def __init__(self) -> None:
        self._rois: list[ROIRect] = []
        self._active_index: int = 0
        self._drag_mode: RoiHandle = RoiHandle.NONE
        self._drag_origin_img: tuple[int, int] = (0, 0)
        self._drag_start_roi: Optional[ROIRect] = None
        self._creating = False

    @property
    def rois(self) -> list[ROIRect]:
        """Lista de ROI (copia superficial)."""
        return list(self._rois)

    @property
    def active_roi(self) -> Optional[ROIRect]:
        """ROI activo o None."""
        if not self._rois:
            return None
        idx = max(0, min(self._active_index, len(self._rois) - 1))
        return self._rois[idx]

    def clear(self) -> None:
        """Elimina todos los ROI."""
        self._rois.clear()
        self._active_index = 0
        self._drag_mode = RoiHandle.NONE
        self._creating = False
        self._drag_start_roi = None

    def set_active_roi(self, roi: Optional[ROIRect], *, allow_empty: bool = False) -> None:
        """Reemplaza el ROI activo (v1: un solo ROI)."""
        if roi is None:
            self._rois.clear()
            return
        normalized = roi.normalized()
        if normalized.is_empty() and not allow_empty:
            self._rois.clear()
            return
        if self._rois:
            self._rois[self._active_index] = normalized
        else:
            self._rois.append(normalized)
            self._active_index = 0

    def hit_test(self, ix: int, iy: int) -> RoiHandle:
        """Detecta si el punto cae en un handle, el cuerpo o nada."""
        roi = self.active_roi
        if roi is None or roi.is_empty():
            return RoiHandle.NONE
        x0, y0 = roi.x, roi.y
        x1, y1 = roi.x + roi.width, roi.y + roi.height
        corners = {
            RoiHandle.NW: (x0, y0),
            RoiHandle.NE: (x1, y0),
            RoiHandle.SW: (x0, y1),
            RoiHandle.SE: (x1, y1),
        }
        for handle, (cx, cy) in corners.items():
            if abs(ix - cx) <= HANDLE_HIT and abs(iy - cy) <= HANDLE_HIT:
                return handle
        if x0 <= ix <= x1 and y0 <= iy <= y1:
            return RoiHandle.BODY
        return RoiHandle.NONE

    def begin_press(self, ix: int, iy: int) -> None:
        """Inicia creación, movimiento o resize según hit-test."""
        hit = self.hit_test(ix, iy)
        self._drag_origin_img = (ix, iy)
        if hit == RoiHandle.NONE:
            self._creating = True
            self._drag_mode = RoiHandle.SE
            # Guardar origen explícito (no usar set_active_roi vacío: lo descartaba).
            start = ROIRect(ix, iy, 0, 0, "ROI 1")
            self._drag_start_roi = start
            self.set_active_roi(start, allow_empty=True)
            return
        self._creating = False
        self._drag_mode = hit
        self._drag_start_roi = self.active_roi

    def update_drag(self, ix: int, iy: int, img_w: int, img_h: int) -> Optional[ROIRect]:
        """Actualiza el ROI durante el arrastre; devuelve el ROI clampado."""
        if self._drag_mode == RoiHandle.NONE or self._drag_start_roi is None:
            return self.active_roi

        ox, oy = self._drag_origin_img
        start = self._drag_start_roi
        dx, dy = ix - ox, iy - oy

        if self._creating:
            rect = ROIRect(start.x, start.y, ix - start.x, iy - start.y, start.roi_id)
            rect = rect.normalized().clamped(img_w, img_h)
            self.set_active_roi(rect, allow_empty=True)
            return rect

        x, y, w, h = start.x, start.y, start.width, start.height
        mode = self._drag_mode

        if mode == RoiHandle.BODY:
            x, y = start.x + dx, start.y + dy
        elif mode == RoiHandle.NW:
            x, y = start.x + dx, start.y + dy
            w, h = start.width - dx, start.height - dy
        elif mode == RoiHandle.NE:
            y = start.y + dy
            w, h = start.width + dx, start.height - dy
        elif mode == RoiHandle.SW:
            x = start.x + dx
            w, h = start.width - dx, start.height + dy
        elif mode == RoiHandle.SE:
            w, h = start.width + dx, start.height + dy

        rect = ROIRect(x, y, w, h, start.roi_id).normalized().clamped(img_w, img_h)
        if rect.width < 2:
            rect = ROIRect(rect.x, rect.y, 2, max(2, rect.height), rect.roi_id)
        if rect.height < 2:
            rect = ROIRect(rect.x, rect.y, max(2, rect.width), 2, rect.roi_id)
        rect = rect.clamped(img_w, img_h)
        self.set_active_roi(rect)
        return rect

    def end_drag(self) -> Optional[ROIRect]:
        """Finaliza la interacción; descarta ROI degenerados."""
        self._drag_mode = RoiHandle.NONE
        self._creating = False
        self._drag_start_roi = None
        roi = self.active_roi
        if roi is None or roi.width < 2 or roi.height < 2:
            self.clear()
            return None
        return roi

    def cursor_for_pos(self, ix: int, iy: int) -> str:
        """Nombre de cursor sugerido según hit-test."""
        hit = self.hit_test(ix, iy)
        mapping = {
            RoiHandle.NONE: "cross",
            RoiHandle.BODY: "size_all",
            RoiHandle.NW: "size_fdiag",
            RoiHandle.SE: "size_fdiag",
            RoiHandle.NE: "size_bdiag",
            RoiHandle.SW: "size_bdiag",
        }
        return mapping.get(hit, "cross")
