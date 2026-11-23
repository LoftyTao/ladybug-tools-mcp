"""Shared model-file persistence helpers for Garden model domains."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from garden.manifest import GardenManifest, write_json_file
from garden.paths import (
    reject_windows_alias,
    require_garden_root,
    slugify_name,
    to_posix_relative,
    validate_portable_file_name,
)
from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report

_MODEL_SUFFIXES = {
    "honeybee": ".hbjson",
    "dragonfly": ".dfjson",
    "fairyfly": ".ffjson",
}


def _model_filename(identifier: str, domain: str) -> str:
    model_kind = f"{domain.title()} model"
    if not identifier.strip():
        raise ValueError(f"{model_kind} identifier must not be empty.")
    return validate_portable_file_name(
        f"{identifier}{_MODEL_SUFFIXES[domain]}", label=f"{model_kind} file name"
    )


def _model_target_for_manifest(
    garden_id: str, model_identifier: str, domain: str, path: str | None = None
) -> dict[str, Any]:
    target: dict[str, Any] = {
        "target_type": f"{domain}_model",
        "id": model_identifier,
        "garden_id": garden_id,
        "domain": domain,
        "model_identifier": model_identifier,
    }
    if path:
        target["path"] = path
    return target


def _resolve_model_target(
    garden_root: Path,
    model_target: dict[str, Any] | None,
    *,
    domain: str,
    normalize_target: Callable[[Any], dict[str, Any]],
) -> tuple[GardenManifest, dict[str, Any]]:
    model_kind = f"{domain.title()} model"
    manifest = GardenManifest.read(garden_root)
    model_target = model_target or getattr(manifest, f"base_{domain}_model")
    if not model_target:
        raise ValueError(
            f"Garden has no base {model_kind}. Create or set a {model_kind} first."
        )
    model_target = normalize_target(model_target)
    if model_target.get("domain") != domain:
        raise ValueError(f"Only {model_kind} targets are supported by this tool.")
    return manifest, model_target


def _load_model(
    garden_root: Path,
    model_target: dict[str, Any],
    *,
    normalize_target: Callable[[Any], dict[str, Any]],
    target_kind: str,
    loader: Callable[[Path], Any],
) -> Any:
    model_kind = f"{target_kind.title()} model"
    target = normalize_target(model_target)
    path_value = target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError(f"{model_kind} target requires a Garden-relative path.")
    path = Path(path_value)
    if path.is_absolute():
        raise ValueError(f"{model_kind} target path must be Garden-relative.")
    root = garden_root.expanduser().resolve()
    path = (root / path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{model_kind} target path must stay inside the Garden.") from exc
    return loader(path)


def _save_model(
    garden_root: Path,
    manifest: GardenManifest,
    *,
    domain: str,
    output_name: str,
    content: bytes,
    set_base: bool,
    set_default_base: bool = True,
    staged_writes: Mapping[str, bytes] | None = None,
) -> tuple[dict[str, Any], str]:
    model_kind = f"{domain.title()} model"
    persisted_path = (
        Path("models") / domain / _model_filename(output_name, domain)
    ).as_posix()
    other_models = [item for item in manifest.models if item.get("domain") == domain and item.get("model_identifier") != output_name]
    reject_windows_alias(output_name, (item.get("model_identifier") for item in other_models), label=f"{model_kind} identifier")
    reject_windows_alias(persisted_path, (item.get("path") for item in other_models), label=f"{model_kind} path")
    target = _model_target_for_manifest(
        manifest.garden_id, output_name, domain, persisted_path
    )
    manifest.models = [
        item
        for item in manifest.models
        if not (
            item.get("domain") == domain
            and item.get("model_identifier") == output_name
        )
    ]
    manifest.models.append(target)
    if set_base or (
        set_default_base and getattr(manifest, f"base_{domain}_model") is None
    ):
        setattr(manifest, f"base_{domain}_model", target)
    manifest.write(
        garden_root,
        staged_writes={**(staged_writes or {}), persisted_path: content},
    )
    return target, persisted_path


def make_typed_object_target(
    *,
    target_type: str,
    domain: str,
    garden_id: str,
    kind: str,
    identifier: str,
    path: str,
    allowed_kinds: set[str],
    domain_label: str,
) -> dict[str, Any]:
    """Build a Garden-backed typed SDK object target."""
    if kind not in allowed_kinds:
        allowed = ", ".join(sorted(allowed_kinds))
        raise ValueError(f"Unsupported {domain_label} object kind: {kind}. Allowed: {allowed}.")
    return {
        "target_type": target_type,
        "domain": domain,
        "kind": kind,
        "id": identifier,
        "identifier": identifier,
        "path": path,
        "garden_id": garden_id,
    }


def normalize_typed_object_target(
    value: Any,
    *,
    target_type: str,
    domain: str,
    allowed_kinds: set[str],
    domain_label: str,
    expected_kind: str | None = None,
) -> dict[str, Any]:
    """Validate and copy a typed SDK object target dict."""
    if not isinstance(value, dict):
        raise ValueError(f"Expected a {domain_label} object target dict.")
    if "selector" in value:
        raise ValueError(f"{domain_label} object targets do not accept selector-shaped inputs.")
    if value.get("target_type") != target_type:
        raise ValueError(f"target must have target_type '{target_type}'.")
    if value.get("domain") != domain:
        raise ValueError(f"target must reference domain '{domain}'.")
    kind = value.get("kind")
    if kind not in allowed_kinds:
        allowed = ", ".join(sorted(allowed_kinds))
        raise ValueError(f"target kind must be one of: {allowed}.")
    if expected_kind is not None and kind != expected_kind:
        raise ValueError(f"Expected {domain_label} target kind '{expected_kind}'.")
    for field in ("id", "identifier", "path", "garden_id"):
        field_value = value.get(field)
        if not isinstance(field_value, str) or not field_value:
            raise ValueError(f"{domain_label} target requires non-empty '{field}'.")
    return dict(value)


def save_typed_object(
    *,
    garden_root: str | Path,
    domain: str,
    target_type: str,
    domain_label: str,
    kind: str,
    identifier: str,
    obj: Any,
    kind_to_class: Mapping[str, type],
    serializer: Callable[[Any], dict[str, Any]] | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Persist one SDK object under ``models/<domain>/<kind>/`` with compact handoff."""
    root = require_garden_root(garden_root)
    manifest = GardenManifest.read(root)
    expected_cls = kind_to_class.get(kind)
    if expected_cls is None:
        allowed = ", ".join(sorted(kind_to_class))
        raise ValueError(f"Unsupported {domain_label} object kind: {kind}. Allowed: {allowed}.")
    if not isinstance(obj, expected_cls):
        raise ValueError(f"Expected {expected_cls.__name__} for {domain_label} kind '{kind}'.")

    if serializer is not None:
        object_dict = serializer(obj)
    else:
        if not hasattr(obj, "to_dict"):
            raise ValueError(f"{domain_label} object must expose to_dict().")
        object_dict = obj.to_dict()

    object_path = root / "models" / domain / kind / f"{slugify_name(identifier)}.json"
    persisted_path = to_posix_relative(object_path, root)
    target = make_typed_object_target(
        target_type=target_type,
        domain=domain,
        garden_id=manifest.garden_id,
        kind=kind,
        identifier=identifier,
        path=persisted_path,
        allowed_kinds=set(kind_to_class),
        domain_label=domain_label,
    )
    write_json_file(object_path, object_dict, ensure_ascii=False)
    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        persisted_path=persisted_path,
        change_summary={"operation": f"save_{domain}_object", "target": target},
    )
    result = {
        "target": target,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "domain": domain,
            "kind": kind,
            "identifier": identifier,
            "object_type": object_dict.get("type") or obj.__class__.__name__,
            "body_returned": include_body,
        },
        "persistence_receipt": receipt,
        "report": make_report(status="ok", message=f"Saved {domain_label} object: {identifier}"),
    }
    if include_body:
        result["object_dict"] = object_dict
    return result


def load_typed_object(
    *,
    garden_root: str | Path,
    target: dict[str, Any],
    domain: str,
    target_type: str,
    domain_label: str,
    kind_to_class: Mapping[str, type],
    deserializer: Callable[[str, dict[str, Any]], Any] | None = None,
    expected_kind: str | None = None,
) -> Any:
    """Load one typed SDK object from a Garden-contained JSON file."""
    root = require_garden_root(garden_root)
    manifest = GardenManifest.read(root)
    normalized = normalize_typed_object_target(
        target,
        target_type=target_type,
        domain=domain,
        allowed_kinds=set(kind_to_class),
        domain_label=domain_label,
        expected_kind=expected_kind,
    )
    if normalized["garden_id"] != manifest.garden_id:
        raise ValueError(f"{domain_label} target belongs to a different Garden.")
    record_path = (root / normalized["path"]).resolve()
    record_path.relative_to(root)
    with record_path.open("r", encoding="utf-8") as handle:
        record = json.load(handle)
    if not isinstance(record, dict):
        raise ValueError(f"{domain_label} object file must contain a JSON object.")
    if "object_dict" in record:
        raise ValueError(f"{domain_label} storage must be native object JSON, not wrapped object_dict.")
    kind = str(normalized["kind"])
    if deserializer is not None:
        return deserializer(kind, record)
    cls = kind_to_class[kind]
    try:
        return cls.from_dict(record)
    except Exception as exc:  # pragma: no cover - SDK diagnostics vary by class
        raise ValueError(f"Could not load {domain_label} {kind} object. {exc}") from exc


def load_typed_objects(
    *,
    targets: list[dict[str, Any]],
    expected_kind: str,
    loader: Callable[..., Any],
    **kwargs: Any,
) -> list[Any]:
    """Load a non-empty list of typed SDK objects of one kind."""
    if not targets:
        raise ValueError(f"At least one {expected_kind} target is required.")
    return [loader(target=target, expected_kind=expected_kind, **kwargs) for target in targets]


def _numeric_coords(value: Any, *, length: int, field_name: str) -> tuple[float, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != length:
        raise ValueError(f"{field_name} must be a Point{length}D coordinate list.")
    try:
        return tuple(float(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must contain numeric coordinates.") from exc


def points2d_polygon(points: list[list[float]], *, field_name: str) -> Any:
    """Create a Ladybug Polygon2D from 2D coordinate pairs."""
    from ladybug_geometry.geometry2d.pointvector import Point2D
    from ladybug_geometry.geometry2d.polygon import Polygon2D

    if len(points) < 3:
        raise ValueError(f"{field_name} must include at least three 2D points.")
    return Polygon2D(
        tuple(
            Point2D(*_numeric_coords(point, length=2, field_name=f"{field_name}[{index}]"))
            for index, point in enumerate(points)
        )
    )


def points2d_polyline(points: list[list[float]], *, field_name: str) -> Any:
    """Create a LineSegment2D (2 points) or Polyline2D (3+ points) from 2D pairs."""
    from ladybug_geometry.geometry2d.line import LineSegment2D
    from ladybug_geometry.geometry2d.pointvector import Point2D
    from ladybug_geometry.geometry2d.polyline import Polyline2D

    if len(points) < 2:
        raise ValueError(f"{field_name} must include at least two 2D points.")
    vertices = [
        Point2D(*_numeric_coords(point, length=2, field_name=f"{field_name}[{index}]"))
        for index, point in enumerate(points)
    ]
    if len(vertices) == 2:
        return LineSegment2D.from_end_points(vertices[0], vertices[1])
    return Polyline2D(tuple(vertices))


def points3d_list(points: list[list[float]] | None, *, field_name: str) -> list[Any] | None:
    """Convert optional 3D coordinate triples into Ladybug Point3D objects."""
    if points is None:
        return None
    from ladybug_geometry.geometry3d.pointvector import Point3D

    return [
        Point3D(*_numeric_coords(point, length=3, field_name=f"{field_name}[{index}]"))
        for index, point in enumerate(points)
    ]
