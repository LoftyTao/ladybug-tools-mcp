"""Source-backed Ironbug object creation services."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from ironbug import hvac

from garden.ironbug_core.assembly import (
    COMPONENT_LIBRARY_KEY,
    _component_library,
    _component_target,
    _dump_source_object,
    _plant_loop_target,
    _save_update,
)
from garden.ironbug_core.model_io import load_ironbug_model
from garden.ironbug_core.targets import make_ironbug_model_object_target
from ladybug_tools_mcp.contracts.report import make_report


def _garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _class_for_source(source_class: str) -> type[Any]:
    if not source_class.startswith(("IB_", "IIB_")):
        raise ValueError(f"Unsupported Ironbug source class name: {source_class}")
    if not hasattr(hvac, source_class):
        raise ValueError(f"Ironbug source class is unavailable in ironbug.hvac: {source_class}")
    cls = getattr(hvac, source_class)
    if not isinstance(cls, type):
        raise ValueError(f"Ironbug source class is not a class: {source_class}")
    return cls


def _hydrate_child(data: dict[str, Any] | None) -> Any:
    if data is None:
        return None
    source_type = data.get("type")
    if not isinstance(source_type, str) or not hasattr(hvac, source_type):
        raise ValueError(f"Child objects must include a supported Ironbug type: {source_type!r}")
    return getattr(hvac, source_type).model_validate(data)


def _hydrate_source_value(value: Any) -> Any:
    if isinstance(value, dict) and isinstance(value.get("type"), str):
        return _hydrate_child(value)
    if isinstance(value, list):
        return [_hydrate_source_value(item) for item in value]
    return value


def _output_variable_object(variable_name: str, reporting_frequency: str) -> Any:
    return hvac.IB_OutputVariable(VariableName=variable_name, TimeStep=reporting_frequency)


def _resolve_object_param_targets(
    *,
    model: Any,
    model_target: dict[str, Any],
    references: list[Any] | None,
    allowed_source_classes: set[str],
    label: str,
) -> list[Any] | None:
    if references is None:
        return None
    from garden.ironbug_core.relationships import _resolve_object

    objects: list[Any] = []
    for reference in references:
        resolved = _resolve_object(model, model_target, reference)
        source_class = getattr(resolved.obj, "SOURCE_CLASS", resolved.obj.__class__.__name__)
        if source_class not in allowed_source_classes:
            raise ValueError(
                f"{label} accepts {sorted(allowed_source_classes)}, got {source_class}."
            )
        objects.append(resolved.obj)
    return objects


def _resolve_child_target_slots(
    *,
    model: Any,
    model_target: dict[str, Any],
    references: list[Any | None] | None,
    label: str,
) -> list[dict[str, Any] | None] | None:
    if references is None:
        return None
    from garden.ironbug_core.relationships import _resolve_object

    children: list[dict[str, Any] | None] = []
    for reference in references:
        if reference is None:
            children.append(None)
            continue
        resolved = _resolve_object(model, model_target, reference)
        source_class = getattr(resolved.obj, "SOURCE_CLASS", resolved.obj.__class__.__name__)
        if not source_class.startswith(("IB_", "IIB_")):
            raise ValueError(f"{label} accepts Ironbug object targets, got {source_class}.")
        children.append(_dump_source_object(resolved.obj))
    return children


def _resolve_ib_property_target_map(
    *,
    model: Any,
    model_target: dict[str, Any],
    references: dict[str, Any | None] | None,
    label: str,
) -> dict[str, Any] | None:
    if not references:
        return None
    from garden.ironbug_core.relationships import _resolve_object

    resolved_targets: dict[str, Any] = {}
    for key, reference in references.items():
        if reference is None:
            continue
        resolved = _resolve_object(model, model_target, reference)
        source_class = getattr(resolved.obj, "SOURCE_CLASS", resolved.obj.__class__.__name__)
        if not source_class.startswith(("IB_", "IIB_")):
            raise ValueError(f"{label}.{key} accepts Ironbug object targets, got {source_class}.")
        resolved_targets[key] = _dump_source_object(resolved.obj)
    return resolved_targets or None


def _source_type_accepts(source_class: str, expected_type: str) -> bool:
    if source_class == expected_type:
        return True
    if expected_type in {"IB_ModelObject", "IB_HVACObject"} and source_class.startswith("IB_"):
        return True
    if not hasattr(hvac, source_class):
        return False
    cls = getattr(hvac, source_class)
    source_bases = set(getattr(cls, "SOURCE_BASES", ()))
    source_interfaces = set(getattr(cls, "SOURCE_INTERFACES", ()))
    if expected_type in source_bases or expected_type in source_interfaces:
        return True
    pending = list(source_bases)
    seen: set[str] = set()
    while pending:
        base_name = pending.pop()
        if base_name in seen:
            continue
        seen.add(base_name)
        if base_name == expected_type:
            return True
        if hasattr(hvac, base_name):
            pending.extend(getattr(getattr(hvac, base_name), "SOURCE_BASES", ()))
    return False


def _expected_source_types(source_class: str, property_name: str) -> tuple[str, bool]:
    cls = _class_for_source(source_class)
    property_types = getattr(cls, "SOURCE_PROPERTY_TYPES", {}) or {}
    expected = str(property_types.get(property_name, "")).strip()
    if not expected:
        raise ValueError(f"{source_class}.{property_name} has no source property type metadata.")
    is_list = expected.startswith("List<") and expected.endswith(">")
    inner = expected[5:-1] if is_list else expected
    inner = inner.split(".")[-1]
    if not inner.startswith(("IB_", "IIB_")):
        raise ValueError(
            f"{source_class}.{property_name} is not an Ironbug object target property: {expected}"
        )
    return inner, is_list


def _as_reference_list(value: Any, *, is_list: bool, label: str) -> list[Any]:
    if value is None:
        return []
    if is_list:
        if not isinstance(value, list):
            raise ValueError(f"{label} requires a list of Ironbug object targets.")
        return value
    if isinstance(value, list):
        raise ValueError(f"{label} accepts one Ironbug object target, not a list.")
    return [value]


def _resolve_source_property_target_map(
    *,
    model: Any,
    model_target: dict[str, Any],
    source_class: str,
    references: dict[str, Any | None] | None,
) -> dict[str, Any] | None:
    if not references:
        return None
    from garden.ironbug_core.relationships import _resolve_object

    resolved_targets: dict[str, Any] = {}
    for property_name, reference in references.items():
        if reference is None:
            continue
        expected_type, is_list = _expected_source_types(source_class, property_name)
        label = f"{source_class}.{property_name}"
        objects: list[Any] = []
        for item in _as_reference_list(reference, is_list=is_list, label=label):
            resolved = _resolve_object(model, model_target, item)
            resolved_source_class = getattr(
                resolved.obj,
                "SOURCE_CLASS",
                resolved.obj.__class__.__name__,
            )
            if not _source_type_accepts(str(resolved_source_class), expected_type):
                raise ValueError(
                    f"{label} accepts {expected_type} targets, got {resolved_source_class}."
                )
            objects.append(resolved.obj)
        resolved_targets[property_name] = objects if is_list else objects[0]
    return resolved_targets or None


def _expected_source_field_target_types(source_class: str, field_name: str) -> tuple[str, bool]:
    cls = _class_for_source(source_class)
    target_types = getattr(cls, "SOURCE_FIELD_TARGET_TYPES", {}) or {}
    expected = str(target_types.get(field_name, "")).strip()
    if not expected:
        raise ValueError(f"{source_class}.{field_name} has no source field target metadata.")
    list_names = set(getattr(cls, "SOURCE_FIELD_TARGET_LIST_NAMES", ()) or ())
    return expected, field_name in list_names


def _resolve_source_field_target_map(
    *,
    model: Any,
    model_target: dict[str, Any],
    source_class: str,
    references: dict[str, Any | None] | None,
) -> dict[str, Any] | None:
    if not references:
        return None
    from garden.ironbug_core.relationships import _resolve_object

    resolved_targets: dict[str, Any] = {}
    for field_name, reference in references.items():
        if reference is None:
            continue
        expected_type, is_list = _expected_source_field_target_types(source_class, field_name)
        label = f"{source_class}.{field_name}"
        objects: list[Any] = []
        for item in _as_reference_list(reference, is_list=is_list, label=label):
            resolved = _resolve_object(model, model_target, item)
            resolved_source_class = getattr(
                resolved.obj,
                "SOURCE_CLASS",
                resolved.obj.__class__.__name__,
            )
            if not _source_type_accepts(str(resolved_source_class), expected_type):
                raise ValueError(
                    f"{label} accepts {expected_type} targets, got {resolved_source_class}."
                )
            objects.append(resolved.obj)
        resolved_targets[field_name] = objects if is_list else objects[0]
    return resolved_targets or None


def _as_inline_child_sequence(value: Any, *, is_list: bool, label: str) -> list[Any]:
    if value is None:
        return []
    if is_list:
        if not isinstance(value, list):
            raise ValueError(f"{label} requires a list of per-child values.")
        return value
    if isinstance(value, list):
        raise ValueError(f"{label} accepts one child value, not a list.")
    return [value]


def _inline_child_count(
    *,
    identifiers: Any,
    source_fields: dict[str, Any],
    source_field_targets: dict[str, Any],
    is_list: bool,
    label: str,
) -> int:
    lengths: list[int] = []
    for name, value in {
        "identifiers": identifiers,
        **source_fields,
        **source_field_targets,
    }.items():
        if value is None:
            continue
        sequence = _as_inline_child_sequence(value, is_list=is_list, label=f"{label}.{name}")
        lengths.append(len(sequence))
    if not lengths:
        return 0
    expected = lengths[0]
    if any(length != expected for length in lengths):
        raise ValueError(
            f"{label} inline child parameter lists must have the same length; got {lengths}."
        )
    if expected == 0:
        raise ValueError(f"{label} inline child parameter lists cannot be empty.")
    return expected


def _inline_child_slot_value(
    value: Any,
    *,
    index: int,
    is_list: bool,
    label: str,
) -> Any:
    sequence = _as_inline_child_sequence(value, is_list=is_list, label=label)
    return sequence[index]


def _inline_child_identifier(
    *,
    identifiers: Any,
    parent_identifier: str,
    property_name: str,
    index: int,
    is_list: bool,
) -> str:
    if identifiers is not None:
        value = _inline_child_slot_value(
            identifiers,
            index=index,
            is_list=is_list,
            label=f"{property_name}.identifiers",
        )
        if value is None or str(value).strip() == "":
            raise ValueError(f"{property_name} inline child identifiers cannot be empty.")
        return str(value)
    suffix = re.sub(r"(?<!^)(?=[A-Z])", "_", property_name).lower()
    if is_list:
        return f"{parent_identifier}_{suffix}_{index + 1}"
    return f"{parent_identifier}_{suffix}"


def _resolve_inline_source_property_children(
    *,
    model: Any,
    model_target: dict[str, Any],
    parent_source_class: str,
    parent_identifier: str,
    children: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not children:
        return None
    resolved: dict[str, Any] = {}
    for property_name, spec in children.items():
        if not isinstance(spec, dict):
            raise ValueError(f"{parent_source_class}.{property_name} inline child spec must be a dict.")
        expected_type, is_list = _expected_source_types(parent_source_class, property_name)
        child_source_class = str(spec.get("source_class") or expected_type)
        if not _source_type_accepts(child_source_class, expected_type):
            raise ValueError(
                f"{parent_source_class}.{property_name} accepts {expected_type}, got {child_source_class}."
            )
        source_fields = dict(spec.get("source_fields") or {})
        source_field_targets = dict(spec.get("source_field_targets") or {})
        identifiers = spec.get("identifiers")
        label = f"{parent_source_class}.{property_name}"
        count = _inline_child_count(
            identifiers=identifiers,
            source_fields=source_fields,
            source_field_targets=source_field_targets,
            is_list=is_list,
            label=label,
        )
        if count == 0:
            continue
        objects: list[Any] = []
        for index in range(count):
            child_fields = {
                field_name: _inline_child_slot_value(
                    value,
                    index=index,
                    is_list=is_list,
                    label=f"{label}.{field_name}",
                )
                for field_name, value in source_fields.items()
                if _inline_child_slot_value(
                    value,
                    index=index,
                    is_list=is_list,
                    label=f"{label}.{field_name}",
                )
                is not None
            }
            child_target_refs = {
                field_name: _inline_child_slot_value(
                    value,
                    index=index,
                    is_list=is_list,
                    label=f"{label}.{field_name}",
                )
                for field_name, value in source_field_targets.items()
                if _inline_child_slot_value(
                    value,
                    index=index,
                    is_list=is_list,
                    label=f"{label}.{field_name}",
                )
                is not None
            }
            resolved_child_targets = _resolve_source_field_target_map(
                model=model,
                model_target=model_target,
                source_class=child_source_class,
                references=child_target_refs or None,
            )
            child_obj = _make_source_object(
                source_class=child_source_class,
                identifier=_inline_child_identifier(
                    identifiers=identifiers,
                    parent_identifier=parent_identifier,
                    property_name=property_name,
                    index=index,
                    is_list=is_list,
                ),
                display_name=None,
                source_fields={**child_fields, **dict(resolved_child_targets or {})} or None,
                source_properties=None,
                source_data_members=None,
                custom_attributes=None,
                ib_properties=None,
                children=None,
                output_variable_names=None,
                output_reporting_frequency="Hourly",
                ems_sensor_objects=None,
                ems_actuator_objects=None,
                ems_internal_variable_objects=None,
            )
            objects.append(child_obj)
        resolved[property_name] = objects if is_list else objects[0]
    return resolved or None


def _make_source_object(
    *,
    source_class: str,
    identifier: str,
    display_name: str | None,
    source_fields: dict[str, Any] | None,
    source_properties: dict[str, Any] | None,
    source_data_members: dict[str, Any] | None,
    custom_attributes: dict[str, Any] | None,
    ib_properties: dict[str, Any] | None,
    children: list[dict[str, Any] | None] | None,
    output_variable_names: list[str] | None,
    output_reporting_frequency: str,
    ems_sensor_objects: list[Any] | None,
    ems_actuator_objects: list[Any] | None,
    ems_internal_variable_objects: list[Any] | None,
) -> Any:
    cls = _class_for_source(source_class)
    source_field_names = set(getattr(cls, "SOURCE_FIELD_NAMES", ()))
    source_property_names = set(getattr(cls, "SOURCE_PROPERTIES", ()))
    source_data_member_names = set(getattr(cls, "SOURCE_DATA_MEMBERS", ()))
    source_field_values = dict(source_fields or {})
    source_data_member_values = dict(source_data_members or {})
    custom_attribute_values = dict(custom_attributes or {})
    if (
        "Name" in source_field_values
        and "Name" not in source_field_names
        and getattr(cls, "SOURCE_FIELD_SET", None)
    ):
        custom_attribute_values.setdefault("Name", source_field_values.pop("Name"))
    invalid_fields = set(source_field_values) - source_field_names
    if invalid_fields:
        raise ValueError(
            f"{source_class} does not expose source fields: {sorted(invalid_fields)}"
        )
    invalid_properties = set(source_properties or {}) - source_property_names
    if invalid_properties:
        raise ValueError(
            f"{source_class} does not expose source properties: {sorted(invalid_properties)}"
        )
    invalid_data_members = set(source_data_member_values) - source_data_member_names
    if invalid_data_members:
        raise ValueError(
            f"{source_class} does not expose source data members: {sorted(invalid_data_members)}"
        )
    payload: dict[str, Any] = {
        "identifier": identifier,
        "CustomAttributes": {**custom_attribute_values, **source_field_values},
        "IBProperties": dict(ib_properties or {}),
        "Children": [_hydrate_child(child) for child in (children or [])],
    }
    for property_name, value in dict(source_properties or {}).items():
        payload[property_name] = _hydrate_source_value(value)
    for data_member_name, value in source_data_member_values.items():
        payload[data_member_name] = _hydrate_source_value(value)
    if display_name is not None:
        payload["display_name"] = display_name
    if source_class in {"IB_AirLoopHVAC", "IB_PlantLoop"}:
        payload.setdefault("SupplyComponents", [])
        payload.setdefault("DemandComponents", [])
    if output_variable_names:
        payload["CustomOutputVariables"] = [
            _output_variable_object(name.strip(), output_reporting_frequency)
            for name in output_variable_names
            if name.strip()
        ]
    if ems_sensor_objects:
        payload["CustomSensors"] = ems_sensor_objects
    if ems_actuator_objects:
        payload["CustomActuators"] = ems_actuator_objects
    if ems_internal_variable_objects:
        payload["CustomInternalVariables"] = ems_internal_variable_objects
    return cls.model_construct(**payload)


def _replace_or_append_by_identifier(
    objects: list[Any],
    obj: Any,
    *,
    overwrite: bool,
) -> tuple[list[Any], int, bool]:
    identifier = str(obj.identifier)
    for index, existing in enumerate(objects):
        if str(getattr(existing, "identifier", "")) == identifier:
            if not overwrite:
                raise ValueError(
                    f"Ironbug object already exists: {identifier}. "
                    "Pass overwrite=true to replace it."
                )
            updated = list(objects)
            updated[index] = obj
            return updated, index, True
    updated = [*objects, obj]
    return updated, len(updated) - 1, False


def _store_library_object(
    *,
    model: Any,
    model_target: dict[str, Any],
    obj: Any,
    source_class: str,
    overwrite: bool,
) -> tuple[dict[str, Any], bool]:
    library = _component_library(model)
    identifier = str(obj.identifier)
    replaced = identifier in library
    if replaced and not overwrite:
        raise ValueError(
            f"Ironbug object already exists: {identifier}. "
            "Pass overwrite=true to replace it."
        )
    library[identifier] = {
        "component_type": source_class,
        "source_class": source_class,
        "data": _dump_source_object(obj),
    }
    return (
        _component_target(
            model_target=model_target,
            identifier=identifier,
            source_class=source_class,
        ),
        replaced,
    )


def _store_system_object(
    *,
    model: Any,
    model_target: dict[str, Any],
    obj: Any,
    source_class: str,
    overwrite: bool,
) -> tuple[dict[str, Any], bool]:
    identifier = str(obj.identifier)
    if source_class == "IB_HVACSystem":
        replaced = model.HVACSystem is not None
        if replaced and not overwrite:
            raise ValueError(
                "Ironbug model already has an HVACSystem. The default "
                "create_ironbug_model path initializes one; create AirLoop, "
                "PlantLoop, and VRF objects directly so they append to the "
                "existing HVACSystem, or create the model with "
                "include_hvac_system=False before calling create_ironbug_hvac_system."
            )
        model.HVACSystem = obj
        return (
            make_ironbug_model_object_target(
                model_target=model_target,
                object_type="hvac_system",
                object_path="HVACSystem",
                source_class=source_class,
                identifier=identifier,
            ),
            replaced,
        )
    if model.HVACSystem is None:
        raise ValueError(
            "Ironbug model has no HVACSystem. Create one with "
            "create_ironbug_hvac_system first, or create the model with "
            "include_hvac_system=True so AirLoop, PlantLoop, and VRF objects "
            "can append to it."
        )
    if source_class == "IB_AirLoopHVAC":
        air_loops, index, replaced = _replace_or_append_by_identifier(
            list(model.HVACSystem.AirLoops or []),
            obj,
            overwrite=overwrite,
        )
        model.HVACSystem.AirLoops = air_loops
        return (
            make_ironbug_model_object_target(
                model_target=model_target,
                object_type="air_loop",
                object_path=f"HVACSystem.AirLoops[{index}]",
                source_class=source_class,
                identifier=identifier,
            ),
            replaced,
        )
    if source_class == "IB_PlantLoop":
        plant_loops, index, replaced = _replace_or_append_by_identifier(
            list(model.HVACSystem.PlantLoops or []),
            obj,
            overwrite=overwrite,
        )
        model.HVACSystem.PlantLoops = plant_loops
        return (
            _plant_loop_target(model_target=model_target, loop=obj, index=index),
            replaced,
        )
    if source_class == "IB_AirConditionerVariableRefrigerantFlow":
        vrfs, index, replaced = _replace_or_append_by_identifier(
            list(model.HVACSystem.VariableRefrigerantFlows or []),
            obj,
            overwrite=overwrite,
        )
        model.HVACSystem.VariableRefrigerantFlows = vrfs
        return (
            make_ironbug_model_object_target(
                model_target=model_target,
                object_type="vrf",
                object_path=f"HVACSystem.VariableRefrigerantFlows[{index}]",
                source_class=source_class,
                identifier=identifier,
            ),
            replaced,
        )
    return _store_library_object(
        model=model,
        model_target=model_target,
        obj=obj,
        source_class=source_class,
        overwrite=overwrite,
    )


def create_source_backed_ironbug_object(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    source_class: str,
    identifier: str,
    display_name: str | None = None,
    source_fields: dict[str, Any] | None = None,
    source_properties: dict[str, Any] | None = None,
    source_data_members: dict[str, Any] | None = None,
    custom_attributes: dict[str, Any] | None = None,
    ib_properties: dict[str, Any] | None = None,
    children: list[dict[str, Any]] | None = None,
    output_variable_names: list[str] | None = None,
    output_reporting_frequency: str = "Hourly",
    ems_sensor_targets: list[Any] | None = None,
    ems_actuator_targets: list[Any] | None = None,
    ems_internal_variable_targets: list[Any] | None = None,
    child_targets: list[Any | None] | None = None,
    ib_property_targets: dict[str, Any | None] | None = None,
    source_field_targets: dict[str, Any | None] | None = None,
    source_property_targets: dict[str, Any | None] | None = None,
    inline_source_property_children: dict[str, Any] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create one source-backed Ironbug object in a Garden-managed model."""

    garden_root_path = _garden_root(garden_root)
    manifest, target, _, model = load_ironbug_model(
        garden_root_path,
        ironbug_model_target=ironbug_model_target,
    )
    if output_reporting_frequency not in {"Detail", "Hourly", "Daily", "Monthly", "RunPeriod"}:
        raise ValueError(
            f"Unsupported Ironbug output reporting frequency: {output_reporting_frequency}"
        )
    ems_sensor_objects = _resolve_object_param_targets(
        model=model,
        model_target=target,
        references=ems_sensor_targets,
        allowed_source_classes={"IB_EnergyManagementSystemSensor"},
        label="ems_sensor_targets",
    )
    ems_actuator_objects = _resolve_object_param_targets(
        model=model,
        model_target=target,
        references=ems_actuator_targets,
        allowed_source_classes={"IB_EnergyManagementSystemActuator"},
        label="ems_actuator_targets",
    )
    ems_internal_variable_objects = _resolve_object_param_targets(
        model=model,
        model_target=target,
        references=ems_internal_variable_targets,
        allowed_source_classes={"IB_EnergyManagementSystemInternalVariable"},
        label="ems_internal_variable_targets",
    )
    child_target_slots = _resolve_child_target_slots(
        model=model,
        model_target=target,
        references=child_targets,
        label="child_targets",
    )
    resolved_ib_property_targets = _resolve_ib_property_target_map(
        model=model,
        model_target=target,
        references=ib_property_targets,
        label="ib_property_targets",
    )
    resolved_source_property_targets = _resolve_source_property_target_map(
        model=model,
        model_target=target,
        source_class=source_class,
        references=source_property_targets,
    )
    resolved_source_field_targets = _resolve_source_field_target_map(
        model=model,
        model_target=target,
        source_class=source_class,
        references=source_field_targets,
    )
    inline_property_names = set(inline_source_property_children or {})
    conflicts = inline_property_names & (
        set(source_properties or {}) | set(source_property_targets or {})
    )
    if conflicts:
        raise ValueError(
            "Inline source-property child parameters cannot be combined with "
            f"direct source property targets/values for: {sorted(conflicts)}"
        )
    resolved_inline_source_properties = _resolve_inline_source_property_children(
        model=model,
        model_target=target,
        parent_source_class=source_class,
        parent_identifier=identifier,
        children=inline_source_property_children,
    )
    merged_ib_properties = {
        **dict(ib_properties or {}),
        **dict(resolved_ib_property_targets or {}),
    }
    merged_source_fields = {
        **dict(source_fields or {}),
        **dict(resolved_source_field_targets or {}),
    }
    merged_source_properties = {
        **dict(source_properties or {}),
        **dict(resolved_source_property_targets or {}),
        **dict(resolved_inline_source_properties or {}),
    }
    obj = _make_source_object(
        source_class=source_class,
        identifier=identifier,
        display_name=display_name,
        source_fields=merged_source_fields or None,
        source_properties=merged_source_properties or None,
        source_data_members=source_data_members or None,
        custom_attributes=custom_attributes,
        ib_properties=merged_ib_properties or None,
        children=child_target_slots if child_target_slots is not None else children,
        output_variable_names=output_variable_names,
        output_reporting_frequency=output_reporting_frequency,
        ems_sensor_objects=ems_sensor_objects,
        ems_actuator_objects=ems_actuator_objects,
        ems_internal_variable_objects=ems_internal_variable_objects,
    )
    object_target, replaced = _store_system_object(
        model=model,
        model_target=target,
        obj=obj,
        source_class=source_class,
        overwrite=overwrite,
    )
    updated_target, persisted_path, receipt = _save_update(
        garden_root_path=garden_root_path,
        manifest=manifest,
        target=target,
        model=model,
        operation="create_source_backed_ironbug_object",
        change_summary={
            "source_class": source_class,
            "identifier": identifier,
            "replaced": replaced,
            "library_key": COMPONENT_LIBRARY_KEY,
        },
    )
    object_target["model_target"] = updated_target
    return {
        "target": object_target,
        "object_target": object_target,
        "updated_model_target": updated_target,
        "summary_view": {
            "identifier": identifier,
            "source_class": source_class,
            "replaced": replaced,
            "source_fields": sorted((merged_source_fields or {}).keys()),
            "source_properties": sorted((merged_source_properties or {}).keys()),
            "source_data_members": sorted((source_data_members or {}).keys()),
            "output_variable_count": len(output_variable_names or []),
            "ems_sensor_count": len(ems_sensor_objects or []),
            "ems_actuator_count": len(ems_actuator_objects or []),
            "ems_internal_variable_count": len(ems_internal_variable_objects or []),
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="updated" if replaced else "created",
            message=f"Created Ironbug source-backed object: {source_class}/{identifier}",
            details={"persisted_path": persisted_path},
        ),
    }
