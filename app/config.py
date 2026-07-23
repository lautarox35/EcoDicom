"""Configuración global de EcoDICOM (Windows / macOS)."""

from __future__ import annotations

import sys
from pathlib import Path


def _app_root() -> Path:
    """
    Raíz de datos de la aplicación.
    - Desarrollo: carpeta del repo (junto a main.py).
    - Empaquetado (.exe / .app): ~/Documents/EcoDICOM
      para no escribir dentro de _internal o del bundle.
    """
    if getattr(sys, "frozen", False):
        return Path.home() / "Documents" / "EcoDICOM"
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _app_root()

# Carpeta de exportación de estudios DICOM
STUDIES_DIR = PROJECT_ROOT / "Estudios"

# Base de datos SQLite local
DATABASE_PATH = PROJECT_ROOT / "estudios.db"

# Imágenes de muestra / temporales
SAMPLE_IMAGES_DIR = PROJECT_ROOT / "sample_images"

# Prefijo OID para UIDs DICOM (raíz de prueba pydicom-compatible)
UID_PREFIX = "1.2.826.0.1.3680043.10.543"

APP_NAME = "EcoDICOM"
APP_VERSION = "0.2.2"

GITHUB_RELEASES_URL = "https://github.com/lautarox35/EcoDicom/releases"

DEFAULT_CAMERA_INDEX = 0

# Resolución preferida de captura (easierCAP / MS210x)
CAPTURE_WIDTH = 720
CAPTURE_HEIGHT = 480
CAPTURE_WARMUP_FRAMES = 12
# Intentos de resolución de mayor a menor calidad usable
CAPTURE_RESOLUTION_CANDIDATES = (
    (1280, 720),
    (800, 600),
    (720, 576),  # PAL
    (720, 480),  # NTSC
    (640, 480),
)

# Realce de imagen (composite USB suele beneficiarse)
ENHANCE_ENABLED = True
ENHANCE_CLAHE_CLIP = 2.2
ENHANCE_DENOISE = 5
ENHANCE_SHARPEN = 0.55
ENHANCE_UPSCALE = 1.5  # 720→~1080 para DICOM/visualización

BUNDLE_ID = "com.ecodicom.app"


def ensure_directories() -> None:
    """Crea carpetas necesarias si no existen."""
    STUDIES_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
