"""Persistence helpers for Dragonfly DES SDK objects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dragonfly_energy.des.connector import HorizontalPipeParameter, ThermalConnector
from dragonfly_energy.des.ghe import (
    BoreholeParameter,
    FluidParameter,
    GHEDesignParameter,
    GroundHeatExchanger,
    PipeParameter,
    SoilParameter,
)
from dragonfly_energy.des.loop import (
    FifthGenThermalLoop,
    FourthGenThermalLoop,
    GHEThermalLoop,
)

from garden.manifest import GardenManifest, write_json_file
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report

from .targets import make_des_object_target, normalize_des_object_target


KIND_TO_CLASS = {
    "thermal_connector": ThermalConnector,
    "horizontal_pipe_parameter": HorizontalPipeParameter,
    "ghe_soil_parameter": SoilParameter,
    "ghe_fluid_parameter": FluidParameter,
    "ghe_pipe_parameter": PipeParameter,
    "ghe_borehole_parameter": BoreholeParameter,
    "ghe_design_parameter": GHEDesignParameter,
    "ground_heat_exchanger": GroundHeatExchanger,
    "fourth_gen_thermal_loop": FourthGenThermalLoop,
    "fifth_gen_thermal_loop": FifthGenThermalLoop,
    "ghe_thermal_loop": GHEThermalLoop,
}


def _garden_root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _object_path(root: Path, kind: str, identifier: str) -> Path:
    return root / "models" / "dragonfly_des" / kind / f"{slugify_name(identifier)}.json"


def save_des_object(
    *,
    garden_root: str | Path,
    kind: str,
    identifier: str,
    obj: Any,
    include_body: bool = False,
) -> dict[str, Any]:
    """Save a Dragonfly DES object as native SDK JSON under the Garden."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    expected_cls = KIND_TO_CLASS.get(kind)
    if expected_cls is None:
        allowed = ", ".join(sorted(KIND_TO_CLASS))
        raise ValueError(f"Unsupported Dragonfly DES object kind: {kind}. Allowed: {allowed}.")
    if not isinstance(obj, expected_cls):
        raise ValueError(f"Expected {expected_cls.__name__} for Dragonfly DES kind '{kind}'.")
    if not hasattr(obj, "to_dict"):
        raise ValueError("Dragonfly DES object must expose to_dict().")

    object_dict = obj.to_dict()
    object_path = _object_path(root, kind, identifier)
    persisted_path = to_posix_relative(object_path, root)
    target = make_des_object_target(
        garden_id=manifest.garden_id,
        kind=kind,
        identifier=identifier,
        path=persisted_path,
    )
    write_json_file(object_path, object_dict, ensure_ascii=False)

    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        persisted_path=persisted_path,
        change_summary={
            "operation": "save_dragonfly_des_object",
            "target": target,
        },
    )
    result = {
        "target": target,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "domain": "dragonfly_des",
            "kind": kind,
            "identifier": identifier,
            "object_type": object_dict.get("type") or obj.__class__.__name__,
            "body_returned": include_body,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=f"Saved Dragonfly DES object: {identifier}",
        ),
    }
    if include_body:
        result["object_dict"] = object_dict
    return result


def load_des_object(
    *,
    garden_root: str | Path,
    target: dict[str, Any],
    expected_kind: str | None = None,
) -> Any:
    """Load one Dragonfly DES SDK object from a Garden target."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    target = normalize_des_object_target(target, expected_kind=expected_kind)
    if target["garden_id"] != manifest.garden_id:
        raise ValueError("Dragonfly DES target belongs to a different Garden.")

    record_path = (root / target["path"]).resolve()
    record_path.relative_to(root.resolve())
    with record_path.open("r", encoding="utf-8") as handle:
        record = json.load(handle)
    if not isinstance(record, dict):
        raise ValueError("Dragonfly DES object file must contain a JSON object.")
    if "object_dict" in record:
        raise ValueError("Dragonfly DES storage must be native SDK JSON, not wrapped object_dict.")

    cls = KIND_TO_CLASS[str(target["kind"])]
    try:
        return cls.from_dict(record)
    except Exception as exc:  # pragma: no cover - SDK diagnostics vary by class
        raise ValueError(f"Could not load Dragonfly DES {target['kind']} object. {exc}") from exc


def load_des_objects(
    *,
    garden_root: str | Path,
    targets: list[dict[str, Any]],
    expected_kind: str,
) -> list[Any]:
    """Load a non-empty list of Dragonfly DES objects of one kind."""
    if not targets:
        raise ValueError(f"At least one {expected_kind} target is required.")
    return [
        load_des_object(
            garden_root=garden_root,
            target=target,
            expected_kind=expected_kind,
        )
        for target in targets
    ]
