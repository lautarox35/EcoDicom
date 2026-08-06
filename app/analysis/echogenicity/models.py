"""Modelos de datos para análisis de ecogenicidad por ROI."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ROIRect:
    """Rectángulo ROI en coordenadas de imagen nativa (origen arriba-izquierda)."""

    x: int
    y: int
    width: int
    height: int
    roi_id: str = "ROI 1"

    def is_empty(self) -> bool:
        """True si el área útil es nula."""
        return self.width <= 0 or self.height <= 0

    def clamped(self, img_w: int, img_h: int) -> "ROIRect":
        """Devuelve el ROI recortado a los límites de la imagen."""
        if img_w <= 0 or img_h <= 0 or self.is_empty():
            return ROIRect(0, 0, 0, 0, self.roi_id)
        x0 = max(0, min(img_w, self.x))
        y0 = max(0, min(img_h, self.y))
        x1 = max(0, min(img_w, self.x + self.width))
        y1 = max(0, min(img_h, self.y + self.height))
        return ROIRect(x0, y0, max(0, x1 - x0), max(0, y1 - y0), self.roi_id)

    def normalized(self) -> "ROIRect":
        """Asegura width/height positivos (por si se dibujó al revés)."""
        x, y, w, h = self.x, self.y, self.width, self.height
        if w < 0:
            x = x + w
            w = -w
        if h < 0:
            y = y + h
            h = -h
        return ROIRect(x, y, w, h, self.roi_id)


@dataclass(frozen=True)
class IntensityDistribution:
    """Porcentajes por bandas de intensidad (0–255)."""

    black: float  # 0–50
    dark: float  # 51–100
    gray: float  # 101–150
    light: float  # 151–180
    white: float  # 181–255


@dataclass(frozen=True)
class ROIStatistics:
    """Estadísticas básicas del ROI en escala de grises."""

    pixel_count: int
    min_intensity: int
    max_intensity: int
    mean: float
    median: float
    std_dev: float


@dataclass(frozen=True)
class EcogenicityResult:
    """Resultado completo de un análisis de ecogenicidad."""

    roi: ROIRect
    statistics: ROIStatistics
    white_threshold: int
    white_percentage: float
    distribution: IntensityDistribution
    histogram: tuple[int, ...] = field(default_factory=tuple)
    roi_label: str = "ROI 1"


@dataclass(frozen=True)
class EcogenicityComparison:
    """Comparación entre dos ROI (preparado para UI futura)."""

    roi_a_label: str
    roi_b_label: str
    white_percentage_a: float
    white_percentage_b: float
    difference: float
