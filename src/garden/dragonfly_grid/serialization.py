"""Persistence helpers for Dragonfly Electric Grid SDK objects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dragonfly_energy.opendss.connector import ElectricalConnector
from dragonfly_energy.opendss.network import ElectricalNetwork, RoadNetwork
from dragonfly_energy.opendss.substation import Substation
from dragonfly_energy.opendss.transformer import Transformer
from dragonfly_energy.reopt import FinancialParameter, GroundMountPV

from garden.manifest import GardenManifest
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report

from .targets import make_grid_object_target, normalize_grid_object_target


KIND_TO_CLASS = {
    "substation": Substation,
    "transformer": Transformer,
    "electrical_connector": ElectricalConnector,
    "electrical_network": ElectricalNetwork,
    "road_network": RoadNetwork,
    "ground_photovoltaics": GroundMountPV,
    "financial_parameters": FinancialParameter,
}


def _garden_root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _object_path(root: Path, kind: str, identifier: str) -> Path:
    return root / "models" / "dragonfly_grid" / kind / f"{slugify_name(identifier)}.json"


def _object_to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, FinancialParameter):
        return {
            "type": "FinancialParameter",
            "analysis_years": obj.analysis_years,
            "escalation_rate": obj.escalation_rate,
            "tax_rate": obj.tax_rate,
            "discount_rate": obj.discount_rate,
        }
    if not hasattr(obj, "to_dict"):
        raise ValueError("Dragonfly Grid object must expose to_dict().")
    return obj.to_dict()


def _object_from_dict(kind: str, record: dict[str, Any]) -> Any:
    cls = KIND_TO_CLASS[kind]
    if cls is FinancialParameter:
        return FinancialParameter(
            analysis_years=record.get("analysis_years", 25),
            escalation_rate=record.get("escalation_rate", 0.023),
            tax_rate=record.get("tax_rate", 0.26),
            discount_rate=record.get("discount_rate", 0.083),
        )
    return cls.from_dict(record)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def save_grid_object(
    *,
    garden_root: str | Path,
    kind: str,
    identifier: str,
    obj: Any,
    include_body: bool = False,
) -> dict[str, Any]:
    """Save a Dragonfly Electric Grid object under the Garden."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    expected_cls = KIND_TO_CLASS.get(kind)
    if expected_cls is None:
        allowed = ", ".join(sorted(KIND_TO_CLASS))
        raise ValueError(f"Unsupported Dragonfly Grid object kind: {kind}. Allowed: {allowed}.")
    if not isinstance(obj, expected_cls):
        raise ValueError(f"Expected {expected_cls.__name__} for Dragonfly Grid kind '{kind}'.")

    object_dict = _object_to_dict(obj)
    object_path = _object_path(root, kind, identifier)
    persisted_path = to_posix_relative(object_path, root)
    target = make_grid_object_target(
        garden_id=manifest.garden_id,
        kind=kind,
        identifier=identifier,
        path=persisted_path,
    )
    _write_json(object_path, object_dict)
    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        persisted_path=persisted_path,
        change_summary={"operation": "save_dragonfly_grid_object", "target": target},
    )
    result = {
        "target": target,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "domain": "dragonfly_grid",
            "kind": kind,
            "identifier": identifier,
            "object_type": object_dict.get("type") or obj.__class__.__name__,
            "body_returned": include_body,
        },
        "persistence_receipt": receipt,
        "report": make_report(status="ok", message=f"Saved Dragonfly Grid object: {identifier}"),
    }
    if include_body:
        result["object_dict"] = object_dict
    return result


def load_grid_object(
    *,
    garden_root: str | Path,
    target: dict[str, Any],
    expected_kind: str | None = None,
) -> Any:
    """Load one Dragonfly Electric Grid SDK object from a Garden target."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    target = normalize_grid_object_target(target, expected_kind=expected_kind)
    if target["garden_id"] != manifest.garden_id:
        raise ValueError("Dragonfly Grid target belongs to a different Garden.")
    record_path = (root / target["path"]).resolve()
    record_path.relative_to(root.resolve())
    with record_path.open("r", encoding="utf-8") as handle:
        record = json.load(handle)
    if not isinstance(record, dict):
        raise ValueError("Dragonfly Grid object file must contain a JSON object.")
    if "object_dict" in record:
        raise ValueError("Dragonfly Grid storage must be native object JSON, not wrapped object_dict.")
    return _object_from_dict(str(target["kind"]), record)


def load_grid_objects(
    *,
    garden_root: str | Path,
    targets: list[dict[str, Any]],
    expected_kind: str,
) -> list[Any]:
    """Load a non-empty list of Dragonfly Grid objects of one kind."""
    if not targets:
        raise ValueError(f"At least one {expected_kind} target is required.")
    return [
        load_grid_object(
            garden_root=garden_root,
            target=target,
            expected_kind=expected_kind,
        )
        for target in targets
    ]
