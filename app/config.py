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
APP_VERSION = "0.1.0"

DEFAULT_CAMERA_INDEX = 0

BUNDLE_ID = "com.ecodicom.app"


def ensure_directories() -> None:
    """Crea carpetas necesarias si no existen."""
    STUDIES_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
