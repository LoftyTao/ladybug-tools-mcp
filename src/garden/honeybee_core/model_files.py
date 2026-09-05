"""Honeybee model-file import service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from honeybee.model import Model
from honeybee.typing import clean_string

from garden.honeybee_core.model_io import save_honeybee_model
from garden.manifest import GardenManifest
from garden.paths import to_posix_relative
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report


def _resolve_garden_hbjson(garden_root: Path, file_path: str) -> Path:
    source_path = (garden_root / file_path).resolve()
    try:
        source_path.relative_to(garden_root)
    except ValueError as exc:
        raise ValueError("Honeybee model file path must stay inside the Garden.") from exc
    if source_path.suffix.lower() != ".hbjson":
        raise ValueError("Honeybee model file must use the .hbjson extension.")
    if not source_path.is_file():
        raise ValueError(f"Honeybee model file was not found: {file_path}")
    return source_path


def import_honeybee_model_file(
    *,
    garden_root: str,
    file_path: str,
    identifier: str | None = None,
    set_base: bool = True,
) -> dict[str, Any]:
    """Import a Garden-local HBJSON file as Honeybee authoring truth."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    source_path = _resolve_garden_hbjson(garden_root_path, file_path)
    model = Model.from_hbjson(str(source_path), cleanup_irrational=False)
    if identifier:
        model.identifier = clean_string(identifier, "honeybee model identifier")
        model.display_name = identifier
    model_target, persisted_path = save_honeybee_model(
        garden_root_path,
        manifest,
        model,
        name=model.identifier,
        set_base=set_base,
        set_default_base=False,
    )
    source_relative_path = to_posix_relative(source_path, garden_root_path)
    return {
        "target": model_target,
        "model_target": model_target,
        "summary_view": {
            "source_path": source_relative_path,
            "model_identifier": model.identifier,
            "room_count": len(model.rooms),
            "orphaned_shade_count": len(model.orphaned_shades),
            "base_honeybee_model_changed": bool(set_base),
        },
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            base_honeybee_model_changed=bool(set_base),
            model_target=model_target,
            persisted_path=persisted_path,
            change_summary={
                "operation": "import_honeybee_model_file",
                "source_path": source_relative_path,
                "source_file_type": "hbjson",
            },
        ),
        "report": make_report(status="ok", message="Imported Honeybee HBJSON model."),
    }
