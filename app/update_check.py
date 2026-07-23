"""Chequeo simple de actualizaciones vía GitHub Releases."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from app.config import APP_VERSION

GITHUB_OWNER = "lautarox35"
GITHUB_REPO = "EcoDicom"
RELEASES_API = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
RELEASES_PAGE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"


@dataclass
class UpdateInfo:
    current: str
    latest: str
    html_url: str
    update_available: bool
    asset_name: Optional[str] = None
    message: str = ""


def _normalize_version(value: str) -> tuple[int, ...]:
    """Convierte 'v0.2.1' / '0.2.1' en tupla comparable."""
    cleaned = (value or "").strip().lstrip("vV")
    parts = re.findall(r"\d+", cleaned)
    if not parts:
        return (0,)
    return tuple(int(p) for p in parts)


def check_latest_release(timeout: float = 8.0) -> UpdateInfo:
    """
    Consulta solo el endpoint de latest release de GitHub.
    No descarga ni instala nada.
    """
    current = APP_VERSION
    req = urllib.request.Request(
        RELEASES_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"EcoDICOM/{current}",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return UpdateInfo(
                current=current,
                latest=current,
                html_url=RELEASES_PAGE,
                update_available=False,
                message="No hay releases publicadas todavía en GitHub.",
            )
        return UpdateInfo(
            current=current,
            latest=current,
            html_url=RELEASES_PAGE,
            update_available=False,
            message=f"No se pudo consultar GitHub (HTTP {exc.code}).",
        )
    except Exception as exc:  # noqa: BLE001
        return UpdateInfo(
            current=current,
            latest=current,
            html_url=RELEASES_PAGE,
            update_available=False,
            message=f"Sin conexión o error al consultar Releases:\n{exc}",
        )

    tag = str(payload.get("tag_name") or "").strip()
    html_url = str(payload.get("html_url") or RELEASES_PAGE)
    latest = tag.lstrip("vV") or current

    asset_name = None
    for asset in payload.get("assets") or []:
        name = str(asset.get("name") or "")
        if name.lower().endswith(".zip") and "mac" in name.lower():
            asset_name = name
            break
    if asset_name is None:
        for asset in payload.get("assets") or []:
            name = str(asset.get("name") or "")
            if name.lower().endswith(".zip"):
                asset_name = name
                break

    newer = _normalize_version(latest) > _normalize_version(current)
    if newer:
        msg = (
            f"Hay una versión nueva: {latest} (tenés {current}).\n\n"
            f"Descargala desde Releases"
            + (f" ({asset_name})" if asset_name else "")
            + "."
        )
    else:
        msg = f"Estás al día. Versión actual: {current}."

    return UpdateInfo(
        current=current,
        latest=latest,
        html_url=html_url,
        update_available=newer,
        asset_name=asset_name,
        message=msg,
    )
