"""Loading and validation of the brochure content."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .errors import ContentError
from .models import Brochure


def _read_yaml(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except FileNotFoundError as exc:
        raise ContentError(f"File di contenuto non trovato: {path}") from exc
    except yaml.YAMLError as exc:
        raise ContentError(f"YAML non valido in {path}:\n{exc}") from exc


def load_brochure(content_file: Path, assets_dir: Path) -> Brochure:
    """Load and validate ``content_file``, checking that every image exists.

    ``retailers.source`` names a YAML file, relative to ``content_file``, with
    the stores by region: the same format as the lookbook's ``retailers.yaml``,
    so the list can be copied from there as it is.
    """
    raw = _read_yaml(content_file)
    if not isinstance(raw, dict):
        raise ContentError(f"{content_file} deve contenere una mappa YAML al livello radice")
    retailers = raw.get("retailers")
    if isinstance(retailers, dict) and "source" in retailers:
        retailers["regions"] = _read_yaml(content_file.parent / retailers.pop("source"))
    try:
        brochure = Brochure.model_validate(raw)
    except ValidationError as exc:
        lines = [f"Contenuto non valido in {content_file}:"]
        for issue in exc.errors():
            location = ".".join(str(part) for part in issue["loc"])
            lines.append(f"  - {location}: {issue['msg']}")
        raise ContentError("\n".join(lines)) from exc

    missing = sorted({str(p) for p in brochure.asset_paths() if not (assets_dir / p).is_file()})
    if missing:
        listing = "\n".join(f"  - {name}" for name in missing)
        raise ContentError(f"Immagini mancanti in {assets_dir}:\n{listing}")
    return brochure
