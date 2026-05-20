"""Garden-backed Honeybee and Dragonfly model export services."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import dragonfly_designbuilder._extend_dragonfly  # noqa: F401
import dragonfly_doe2._extend_dragonfly  # noqa: F401
import honeybee_designbuilder._extend_honeybee  # noqa: F401
import honeybee_doe2._extend_honeybee  # noqa: F401
from dragonfly_designbuilder.writer import (
    model_to_dsbxml as dragonfly_model_to_dsbxml,
)
from dragonfly_doe2.writer import model_to_inp as dragonfly_model_to_inp
from honeybee_designbuilder.writer import (
    model_to_dsbxml as honeybee_model_to_dsbxml,
)
from honeybee_doe2.writer import model_to_inp as honeybee_model_to_inp

from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    normalize_dragonfly_model_target,
)
from garden.dragonfly_core.targets import is_dragonfly_model_target
from garden.honeybee_core.model_io import load_honeybee_model
from garden.honeybee_core.targets import (
    is_honeybee_model_target,
    normalize_honeybee_model_target,
)
from garden.manifest import GardenManifest
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts.receipts import make_artifact_receipt
from ladybug_tools_mcp.contracts.report import make_report

DOE_INP_EXPORT_FORMAT = "doe_inp"
DESIGNBUILDER_DSBXML_EXPORT_FORMAT = "designbuilder_dsbxml"
MODEL_EXPORT_ARTIFACT_DIR = Path("artifacts") / "model_export"

_EXPORT_EXTENSIONS = {
    DOE_INP_EXPORT_FORMAT: ".inp",
    DESIGNBUILDER_DSBXML_EXPORT_FORMAT: ".dsbxml",
}


def export_model_file(
    *,
    garden_root: str,
    export_format: str,
    model_target: dict[str, Any],
    name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Export a Garden Honeybee or Dragonfly model to a supported file artifact."""
    normalized_format = _normalize_export_format(export_format)
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    model_domain, resolved_model_target = _normalize_model_target(model_target)
    _validate_model_target_path(
        garden_root=garden_root_path,
        manifest=manifest,
        model_domain=model_domain,
        model_target=resolved_model_target,
    )

    model = (
        load_honeybee_model(garden_root_path, resolved_model_target)
        if model_domain == "honeybee"
        else load_dragonfly_model(garden_root_path, resolved_model_target)
    )
    output_text = _export_text(
        model=model,
        model_domain=model_domain,
        export_format=normalized_format,
    )

    identifier = slugify_name(name or f"{model.identifier}_{normalized_format}")
    extension = _EXPORT_EXTENSIONS[normalized_format]
    output_dir = garden_root_path / MODEL_EXPORT_ARTIFACT_DIR / normalized_format
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{identifier}{extension}"
    stored_text = _write_export_file(
        output_path=output_path,
        export_format=normalized_format,
        text=output_text,
    )
    artifact_path = to_posix_relative(output_path, garden_root_path)
    target = make_model_export_artifact_target(
        manifest=manifest,
        export_format=normalized_format,
        identifier=identifier,
        path=artifact_path,
    )
    _register_artifact(manifest, garden_root_path, target)

    summary_view = {
        "target": target,
        "export_format": normalized_format,
        "model_domain": model_domain,
        "model_target": resolved_model_target,
        "path": artifact_path,
        "extension": extension,
    }
    result: dict[str, Any] = {
        "target": target,
        "model_export_artifact_target": target,
        "summary_view": summary_view,
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=normalized_format,
            artifact_path=artifact_path,
            absolute_path=str(output_path),
            source={
                "export_format": normalized_format,
                "model_domain": model_domain,
                "model_target": resolved_model_target,
            },
        ),
        "report": make_report(
            status="ok",
            message=(
                f"Wrote {normalized_format} export artifact from "
                f"{model_domain} model: {identifier}"
            ),
        ),
    }
    if include_body:
        result["file_body"] = stored_text
    return result


def make_model_export_artifact_target(
    *,
    manifest: GardenManifest,
    export_format: str,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    """Build a model export artifact target."""
    return {
        "target_type": "artifact",
        "garden_id": manifest.garden_id,
        "domain": "model_export",
        "artifact_type": export_format,
        "identifier": identifier,
        "path": path,
    }


def _normalize_export_format(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in _EXPORT_EXTENSIONS:
        allowed = ", ".join(sorted(_EXPORT_EXTENSIONS))
        raise ValueError(f"export_format must be one of: {allowed}.")
    return normalized


def _normalize_model_target(value: Any) -> tuple[str, dict[str, Any]]:
    if value is None:
        raise ValueError("model_target is required.")
    if is_honeybee_model_target(value):
        return "honeybee", normalize_honeybee_model_target(value)
    if is_dragonfly_model_target(value):
        return "dragonfly", normalize_dragonfly_model_target(value)
    raise ValueError("model_target must be a Honeybee Model or Dragonfly Model target.")


def _validate_model_target_path(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    model_domain: str,
    model_target: dict[str, Any],
) -> None:
    target_garden_id = model_target.get("garden_id")
    if target_garden_id != manifest.garden_id:
        raise ValueError("model_target belongs to a different Garden.")
    path_value = model_target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("model_target requires a Garden-relative path.")
    path = Path(path_value)
    if path.is_absolute():
        raise ValueError("model_target path must be Garden-relative.")
    resolved = (garden_root / path).resolve()
    try:
        resolved.relative_to(garden_root.resolve())
    except ValueError as exc:
        raise ValueError("model_target path must stay inside the Garden.") from exc
    expected_suffix = ".hbjson" if model_domain == "honeybee" else ".dfjson"
    if resolved.suffix.lower() != expected_suffix:
        raise ValueError(f"model_target path must point to a {expected_suffix} file.")
    if not resolved.is_file():
        raise ValueError(f"Model file not found: {path_value}")


def _export_text(*, model: Any, model_domain: str, export_format: str) -> str:
    writer = _writer_for(model_domain=model_domain, export_format=export_format)
    try:
        return writer(model)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to export {model_domain} model as {export_format}: {exc}"
        ) from exc


def _writer_for(*, model_domain: str, export_format: str) -> Callable[[Any], str]:
    if model_domain == "honeybee" and export_format == DOE_INP_EXPORT_FORMAT:
        return honeybee_model_to_inp
    if model_domain == "dragonfly" and export_format == DOE_INP_EXPORT_FORMAT:
        return dragonfly_model_to_inp
    if (
        model_domain == "honeybee"
        and export_format == DESIGNBUILDER_DSBXML_EXPORT_FORMAT
    ):
        return honeybee_model_to_dsbxml
    if (
        model_domain == "dragonfly"
        and export_format == DESIGNBUILDER_DSBXML_EXPORT_FORMAT
    ):
        return dragonfly_model_to_dsbxml
    raise ValueError(f"Unsupported model export path: {model_domain} {export_format}.")


def _write_export_file(*, output_path: Path, export_format: str, text: str) -> str:
    if export_format == DESIGNBUILDER_DSBXML_EXPORT_FORMAT:
        encoded = text.encode("iso-8859-15", errors="ignore")
        output_path.write_bytes(encoded)
        return encoded.decode("iso-8859-15")
    output_path.write_text(text, encoding="utf-8", newline="\n")
    return text


def _register_artifact(
    manifest: GardenManifest,
    garden_root: Path,
    target: dict[str, Any],
) -> None:
    manifest.artifacts = [
        item
        for item in manifest.artifacts
        if not (
            item.get("artifact_type") == target["artifact_type"]
            and item.get("identifier") == target["identifier"]
        )
    ]
    manifest.artifacts.append(target)
    manifest.write(garden_root)
