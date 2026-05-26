"""Semantic Ironbug loop assembly services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from garden.ironbug_core.assembly import (
    add_ironbug_plant_loop,
    add_ironbug_hvac_component,
    _component_library,
    set_ironbug_plant_loop_components,
)
from garden.ironbug_core.model_io import load_ironbug_model
from garden.ironbug_core.targets import make_ironbug_model_object_target

PUMP_SOURCE_CLASSES = {"IB_PumpConstantSpeed", "IB_PumpVariableSpeed"}


def _garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def create_ironbug_semantic_water_loop(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    identifier: str,
    loop_name: str,
    loop_type: str,
    supply_branch_component_targets: list[Any] | None = None,
    demand_branch_component_targets: list[Any] | None = None,
    setpoint_c: float | None = None,
    fluid_type: str = "Water",
    loop_design_temperature_difference: float = 6.7,
    source_fields: dict[str, Any] | None = None,
    source_field_targets: dict[str, Any] | None = None,
    sizing_plant_target: Any | None = None,
    sizing_plant_identifier: str | None = None,
    sizing_plant_fields: dict[str, Any] | None = None,
    operation_scheme_target: Any | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create a semantic water loop while keeping generic PlantLoop assembly private."""

    created = add_ironbug_plant_loop(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        identifier=identifier,
        loop_name=loop_name,
        fluid_type=fluid_type,
        loop_type=loop_type,
        design_loop_exit_temperature=setpoint_c,
        loop_design_temperature_difference=loop_design_temperature_difference,
        source_fields=source_fields,
        source_field_targets=source_field_targets,
        sizing_plant_target=sizing_plant_target,
        sizing_plant_identifier=sizing_plant_identifier,
        sizing_plant_fields=sizing_plant_fields,
        operation_scheme_target=operation_scheme_target,
        overwrite=overwrite,
    )
    if (
        supply_branch_component_targets is None
        and demand_branch_component_targets is None
        and setpoint_c is None
    ):
        return created
    model_target = created.get("updated_model_target") or ironbug_model_target
    supply_targets = list(supply_branch_component_targets or [])
    supply_targets_are_nested = _has_branch_groups(supply_targets)
    auto_pump_target: dict[str, Any] | None = None
    auto_pump_identifier: str | None = None
    if not _references_include_pump(
        garden_root=garden_root,
        ironbug_model_target=model_target,
        references=supply_targets,
    ):
        auto_pump_identifier = f"{identifier}_pump"
        auto_pump_target, model_target = _default_pump_target(
            garden_root=garden_root,
            ironbug_model_target=model_target,
            identifier=auto_pump_identifier,
        )
        supply_targets.insert(0, auto_pump_target)
        if supply_targets_are_nested:
            supply_targets[0] = [auto_pump_target]
    updated = set_ironbug_plant_loop_components(
        garden_root=garden_root,
        ironbug_model_target=model_target,
        plant_loop_target=created["target"],
        supply_branch_components=supply_targets,
        demand_branch_components=demand_branch_component_targets,
        setpoint_c=setpoint_c,
    )
    summary = dict(updated.get("summary_view") or {})
    summary["loop_type"] = loop_type
    summary["semantic_loop_tool"] = True
    summary["auto_pump_added"] = auto_pump_target is not None
    summary["auto_pump_identifier"] = auto_pump_identifier
    updated["summary_view"] = summary
    return updated


def _references_include_pump(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    references: list[Any],
) -> bool:
    """Return True when any reference resolves to an Ironbug pump source class."""

    if not references:
        return False
    _, _, _, model = load_ironbug_model(
        _garden_root(garden_root),
        ironbug_model_target=ironbug_model_target,
    )
    library = _component_library(model)
    for reference in _flatten_references(references):
        source_class: str | None = None
        if isinstance(reference, str):
            record = library.get(reference)
            if isinstance(record, dict):
                source_class = str(record.get("source_class") or "")
        elif isinstance(reference, dict):
            source_class = str(reference.get("source_class") or "")
            identifier = reference.get("identifier")
            if not source_class and isinstance(identifier, str):
                record = library.get(identifier)
                if isinstance(record, dict):
                    source_class = str(record.get("source_class") or "")
        if source_class in PUMP_SOURCE_CLASSES:
            return True
    return False


def _has_branch_groups(references: list[Any]) -> bool:
    return any(isinstance(reference, list) for reference in references)


def _flatten_references(references: list[Any]) -> list[Any]:
    flattened: list[Any] = []
    for reference in references:
        if isinstance(reference, list):
            flattened.extend(reference)
        else:
            flattened.append(reference)
    return flattened


def _default_pump_target(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    identifier: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create or reuse a source-backed default constant-speed pump target."""

    _, model_target, _, model = load_ironbug_model(
        _garden_root(garden_root),
        ironbug_model_target=ironbug_model_target,
    )
    library = _component_library(model)
    if identifier in library:
        record = library[identifier]
        source_class = str(record.get("source_class") or "")
        if source_class not in PUMP_SOURCE_CLASSES:
            raise ValueError(
                f"Default semantic-loop pump identifier is already used by "
                f"{source_class}: {identifier}"
            )
        return (
            make_ironbug_model_object_target(
                model_target=model_target,
                object_type="component",
                object_path=f"user_data.ironbug_component_library.{identifier}",
                source_class=source_class,
                identifier=identifier,
            ),
            model_target,
        )
    pump = add_ironbug_hvac_component(
        garden_root=garden_root,
        ironbug_model_target=model_target,
        component_type="pump_constant_speed",
        identifier=identifier,
    )
    return pump["target"], pump["updated_model_target"]
