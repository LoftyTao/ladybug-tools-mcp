"""Update one canonical source-backed Ironbug component field."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from garden.ironbug_core.assembly import (
    COMPONENT_LIBRARY_KEY,
    _hydrate_source_object,
    _refresh_embedded_component_copies,
    _save_update,
)
from garden.ironbug_core.create_tools import (
    _class_for_source,
    _expected_source_field_target_types,
    _expected_source_types,
    _source_type_accepts,
)
from garden.ironbug_core.model_io import load_ironbug_model
from garden.ironbug_core.models import _normalize_component_target
from garden.ironbug_core.relationships import _resolve_object
from ladybug_tools_mcp.contracts.report import make_report


_SCALAR_TYPES = (str, int, float, bool)


def _source_class(obj: Any) -> str:
    return str(getattr(obj, "SOURCE_CLASS", obj.__class__.__name__))


def _declared_type(source_class: str, field_name: str, attribute: str) -> tuple[str, bool] | None:
    cls = _class_for_source(source_class)
    raw = str((getattr(cls, attribute, {}) or {}).get(field_name, "")).strip()
    if not raw:
        return None
    is_list = (
        (raw.startswith("List<") and raw.endswith(">"))
        or (raw.startswith("IEnumerable<") and raw.endswith(">"))
    )
    inner = raw[raw.find("<") + 1 : -1] if is_list else raw
    return inner.split(".")[-1], is_list


def _field_kind(source_class: str, field_name: str) -> tuple[str, tuple[str, bool] | None]:
    cls = _class_for_source(source_class)
    property_names = set(getattr(cls, "SOURCE_PROPERTIES", ()) or ())
    data_member_names = set(getattr(cls, "SOURCE_DATA_MEMBERS", ()) or ())
    field_names = set(getattr(cls, "SOURCE_FIELD_NAMES", ()) or ())
    field_target_types = getattr(cls, "SOURCE_FIELD_TARGET_TYPES", {}) or {}

    # Explicit object properties/data members take precedence over a duplicated
    # FieldSet name (for example IB_TableLookup.OutputValues).
    if field_name in property_names:
        return "property", _declared_type(source_class, field_name, "SOURCE_PROPERTY_TYPES")
    if field_name in data_member_names:
        return "data_member", _declared_type(source_class, field_name, "SOURCE_DATA_MEMBER_TYPES")
    if field_name in field_names:
        if field_name in field_target_types:
            return "field_target", _expected_source_field_target_types(source_class, field_name)
        return "field", _declared_type(source_class, field_name, "SOURCE_FIELD_TYPES")
    raise ValueError(
        f"{source_class} does not expose an editable field named {field_name!r}."
    )


def _validate_scalar(value: Any, label: str) -> None:
    if not isinstance(value, _SCALAR_TYPES):
        raise ValueError(
            f"{label} accepts only a scalar string, number, or boolean; "
            "object payloads are not supported."
        )
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number.")


def _validate_value(value: Any, label: str) -> bool:
    """Validate a JSON scalar or flat scalar list and return whether it is a list."""

    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_scalar(item, f"{label}[{index}]")
        return True
    _validate_scalar(value, label)
    return False


def _resolve_typed_reference(
    *,
    model: Any,
    model_target: dict[str, Any],
    reference: Any,
    expected_type: str,
    label: str,
) -> Any:
    resolved = _resolve_object(
        model,
        model_target,
        _normalize_component_target(reference, model_target=model_target),
    )
    actual_type = _source_class(resolved.obj)
    if not _source_type_accepts(actual_type, expected_type):
        raise ValueError(f"{label} accepts {expected_type} targets, got {actual_type}.")
    return resolved.obj


def _reference_value(
    *,
    model: Any,
    model_target: dict[str, Any],
    source_class: str,
    field_name: str,
    kind: str,
    declared: tuple[str, bool] | None,
    reference_target: Any,
    reference_targets: Any,
) -> Any:
    if kind == "field_target":
        expected_type, expects_list = declared or ("", False)
    elif kind == "property":
        expected_type, expects_list = _expected_source_types(source_class, field_name)
    elif kind == "data_member":
        if declared is None:
            raise ValueError(f"{source_class}.{field_name} has no target type metadata.")
        expected_type, expects_list = declared
        if not expected_type.startswith(("IB_", "IIB_")):
            raise ValueError(
                f"{source_class}.{field_name} is a scalar field; use value instead."
            )
    else:
        raise ValueError(f"{source_class}.{field_name} is a scalar field; use value instead.")

    if reference_target is not None:
        if expects_list:
            raise ValueError(f"{source_class}.{field_name} requires reference_targets.")
        return _resolve_typed_reference(
            model=model,
            model_target=model_target,
            reference=reference_target,
            expected_type=expected_type,
            label="reference_target",
        )
    if not isinstance(reference_targets, list):
        raise ValueError("reference_targets must be a list of typed Ironbug component targets.")
    if not expects_list:
        raise ValueError(f"{source_class}.{field_name} requires one reference_target.")
    return [
        _resolve_typed_reference(
            model=model,
            model_target=model_target,
            reference=reference,
            expected_type=expected_type,
            label=f"reference_targets[{index}]",
        )
        for index, reference in enumerate(reference_targets)
    ]


def _clear_field(obj: Any, field_name: str, kind: str, declared: tuple[str, bool] | None) -> None:
    if kind in {"field", "field_target"}:
        attributes = getattr(obj, "CustomAttributes", None)
        if isinstance(attributes, dict):
            attributes.pop(field_name, None)
        return
    if field_name == "display_name":
        obj.display_name = None
        return
    current = getattr(obj, field_name, None)
    if isinstance(current, (list, tuple)) or (declared is not None and declared[1]):
        setattr(obj, field_name, [])
    elif isinstance(current, dict):
        setattr(obj, field_name, {})
    else:
        setattr(obj, field_name, None)


def _set_field(obj: Any, field_name: str, kind: str, value: Any) -> None:
    if kind in {"field", "field_target"}:
        attributes = getattr(obj, "CustomAttributes", None)
        if not isinstance(attributes, dict):
            raise ValueError("Ironbug component CustomAttributes must be a dict.")
        attributes[field_name] = value
    else:
        setattr(obj, field_name, value)


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must contain only numbers.")
    try:
        numeric = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain only finite numbers.") from exc
    if not math.isfinite(numeric):
        raise ValueError(f"{label} must contain only finite numbers.")
    return numeric


def _table_dimensions(
    *,
    source_class: str,
    obj: Any,
    label: str,
) -> tuple[list[int], list[float]]:
    if source_class == "IB_TableIndependentVariable":
        values = getattr(obj, "Values", None)
        if not isinstance(values, (list, tuple)) or len(values) < 2:
            raise ValueError(f"{label}.Values must contain at least two numbers.")
        numeric = [_finite_number(value, f"{label}.Values") for value in values]
        if any(right <= left for left, right in zip(numeric, numeric[1:])):
            raise ValueError(f"{label}.Values must be strictly ascending.")
        return [len(numeric)], numeric
    if source_class != "IB_TableLookup":
        return [], []
    variables = getattr(obj, "Variables", None)
    outputs = getattr(obj, "OutputValues", None)
    if not isinstance(variables, (list, tuple)) or not variables:
        raise ValueError("IB_TableLookup.Variables must not be empty.")
    if not isinstance(outputs, (list, tuple)) or not outputs:
        raise ValueError("IB_TableLookup.OutputValues must not be empty.")
    dimensions: list[int] = []
    for index, variable in enumerate(variables):
        values = getattr(variable, "Values", None)
        if not isinstance(values, (list, tuple)) or len(values) < 2:
            raise ValueError(
                "IB_TableLookup.Variables["
                f"{index}] must reference an independent variable with at least two Values."
            )
        numeric = [_finite_number(value, f"IB_TableLookup.Variables[{index}].Values") for value in values]
        if any(right <= left for left, right in zip(numeric, numeric[1:])):
            raise ValueError(
                f"IB_TableLookup.Variables[{index}].Values must be strictly ascending."
            )
        dimensions.append(len(numeric))
    output_numeric = [_finite_number(value, "IB_TableLookup.OutputValues") for value in outputs]
    expected = math.prod(dimensions)
    if len(output_numeric) != expected:
        raise ValueError(
            "IB_TableLookup.OutputValues count must equal the product of its "
            f"independent-variable dimensions ({expected}); got {len(output_numeric)}."
        )
    return dimensions, output_numeric


def _validate_tables(
    model: Any,
    model_target: dict[str, Any],
    changed_identifier: str,
    changed_source_class: str,
) -> None:
    library = model.user_data.get(COMPONENT_LIBRARY_KEY, {}) if model.user_data else {}
    changed_obj: Any | None = None
    if changed_source_class == "IB_TableIndependentVariable":
        changed_obj = _resolve_object(model, model_target, changed_identifier).obj
        _table_dimensions(
            source_class=changed_source_class,
            obj=changed_obj,
            label=changed_identifier,
        )
    if changed_source_class == "IB_TableLookup":
        changed_obj = _resolve_object(model, model_target, changed_identifier).obj
        _table_dimensions(source_class=changed_source_class, obj=changed_obj, label=changed_identifier)
        return
    if changed_source_class != "IB_TableIndependentVariable":
        return
    if not isinstance(library, dict):
        return
    for identifier, record in library.items():
        if not isinstance(record, dict) or record.get("source_class") != "IB_TableLookup":
            continue
        table = _hydrate_source_object(dict(record.get("data") or {}))
        variables = getattr(table, "Variables", None) or []
        if changed_source_class == "IB_TableIndependentVariable" and not any(
            str(getattr(variable, "identifier", "")) == changed_identifier
            for variable in variables
        ):
            continue
        _table_dimensions(source_class="IB_TableLookup", obj=table, label=str(identifier))


def update_ironbug_model_object(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    target: dict[str, Any],
    field_name: str,
    value: str | int | float | bool | list[str | int | float | bool] | None = None,
    reference_target: dict[str, Any] | None = None,
    reference_targets: list[dict[str, Any]] | None = None,
    clear: bool = False,
) -> dict[str, Any]:
    """Update one metadata-declared field on a canonical Ironbug component."""

    if not isinstance(field_name, str) or not field_name.strip():
        raise ValueError("field_name must be a non-empty string.")
    field_name = field_name.strip()
    if not isinstance(clear, bool):
        raise ValueError("clear must be a boolean.")
    modes = int(value is not None) + int(reference_target is not None) + int(reference_targets is not None) + int(clear)
    if modes != 1:
        raise ValueError(
            "Pass exactly one update mode: value, reference_target, reference_targets, or clear=true."
        )

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, model_target, _, model = load_ironbug_model(
        garden_root_path,
        ironbug_model_target=ironbug_model_target,
    )
    target = _normalize_component_target(target, model_target=model_target)
    resolved = _resolve_object(model, model_target, target)
    if target.get("object_type") != "component":
        raise ValueError("target must target an Ironbug component.")
    obj = resolved.obj
    source_class = _source_class(obj)
    kind, declared = _field_kind(source_class, field_name) if field_name != "display_name" else ("display_name", None)
    identifier = str(getattr(obj, "identifier", ""))
    original_type = getattr(obj, "type", None)

    if clear:
        _clear_field(obj, field_name, kind, declared)
        mode = "clear"
    elif reference_target is not None or reference_targets is not None:
        if field_name == "display_name":
            raise ValueError("display_name accepts a scalar value, not an object reference.")
        updated_value = _reference_value(
            model=model,
            model_target=model_target,
            source_class=source_class,
            field_name=field_name,
            kind=kind,
            declared=declared,
            reference_target=reference_target,
            reference_targets=reference_targets,
        )
        _set_field(obj, field_name, kind, updated_value)
        mode = "reference_target" if reference_target is not None else "reference_targets"
    else:
        if field_name == "display_name" and not isinstance(value, str):
            raise ValueError("display_name requires a scalar string value.")
        is_list = _validate_value(value, field_name)
        if kind == "field_target":
            raise ValueError(f"{source_class}.{field_name} requires a typed reference target.")
        if declared is not None:
            expected_type, expects_list = declared
            if expects_list != is_list and not expected_type.startswith(("IB_", "IIB_")):
                shape = "scalar-list" if expects_list else "scalar"
                raise ValueError(f"{source_class}.{field_name} requires a {shape} value.")
            if expected_type.startswith(("IB_", "IIB_")):
                raise ValueError(f"{source_class}.{field_name} requires a typed reference target.")
        _set_field(obj, field_name, kind, value)
        mode = "scalar-list" if is_list else "scalar"

    if str(getattr(obj, "identifier", "")) != identifier or getattr(obj, "type", None) != original_type:
        raise ValueError("Ironbug component identifier and type cannot be changed.")
    # Keep the canonical library record authoritative before refreshing all
    # embedded copies during _save_update.
    resolved.save(obj)
    model = _refresh_embedded_component_copies(model)
    _validate_tables(model, model_target, identifier, source_class)
    updated_model_target, persisted_path, receipt = _save_update(
        garden_root_path=garden_root_path,
        manifest=manifest,
        target=model_target,
        model=model,
        operation="update_ironbug_model_object",
        change_summary={
            "identifier": identifier,
            "source_class": source_class,
            "field_name": field_name,
            "updated_fields": [field_name],
            "update_mode": mode,
        },
    )
    object_target = dict(resolved.target)
    object_target["model_target"] = updated_model_target
    return {
        "target": object_target,
        "updated_model_target": updated_model_target,
        "summary_view": {
            "identifier": identifier,
            "source_class": source_class,
            "updated_fields": [field_name],
            "update_mode": mode,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="updated",
            message=f"Updated Ironbug component: {source_class}/{identifier}",
            details={"persisted_path": persisted_path, "field_name": field_name},
        ),
    }


__all__ = ["update_ironbug_model_object"]
