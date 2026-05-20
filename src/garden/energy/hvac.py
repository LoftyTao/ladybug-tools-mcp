"""Honeybee Energy HVAC template search and creation services."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

from honeybee.altnumber import autosize, no_limit
from honeybee_energy.hvac.allair import HVAC_TYPES_DICT as ALL_AIR_TYPES
from honeybee_energy.hvac.doas import HVAC_TYPES_DICT as DOAS_TYPES
from honeybee_energy.hvac.heatcool import HVAC_TYPES_DICT as HEAT_COOL_TYPES
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.lib.schedules import schedule_by_identifier
from honeybee_energy.schedule.dictutil import dict_to_schedule

from ladybug_tools_mcp.contracts.report import make_report
from garden.libraries.properties import save_garden_properties_library_object


@dataclass(frozen=True)
class _HVACTemplate:
    system_type: str
    family: str
    cls: type


_TEMPLATES: tuple[_HVACTemplate, ...] = tuple(
    [_HVACTemplate(name, "allair", cls) for name, cls in ALL_AIR_TYPES.items()]
    + [_HVACTemplate(name, "doas", cls) for name, cls in DOAS_TYPES.items()]
    + [_HVACTemplate(name, "heatcool", cls) for name, cls in HEAT_COOL_TYPES.items()]
)
_TEMPLATES_BY_NORMALIZED = {
    template.system_type.replace("_", "").replace("-", "").lower(): template
    for template in _TEMPLATES
}


def _schedule_from_input(
    data: dict[str, Any] | str | None,
    *,
    field_name: str,
) -> Any:
    if data is None:
        return None
    try:
        if isinstance(data, str):
            return schedule_by_identifier(data)
        if isinstance(data, dict):
            return dict_to_schedule(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(
            f"{field_name} must be a valid Honeybee Energy schedule. {exc}"
        ) from exc
    raise ValueError(f"{field_name} must be a schedule dict or library identifier.")


def _alt_number_from_input(value: float | str | None, *, field_name: str) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.replace("_", "").replace("-", "").replace(" ", "").lower()
        if normalized == "autosize":
            return autosize
        if normalized in {"nolimit", "unlimited"}:
            return no_limit
        raise ValueError(f"{field_name} must be a number, 'autosize', or 'no_limit'.")
    return value


def _class_signature_names(cls: type) -> set[str]:
    signature = inspect.signature(cls)
    return set(signature.parameters)


def _tuple_class_attr(cls: type, attr: str) -> list[str]:
    value = getattr(cls, attr, ())
    return list(value) if value else []


def _doc_summary(cls: type) -> str | None:
    doc = inspect.getdoc(cls)
    if not doc:
        return None
    return doc.splitlines()[0].strip()


def _template_summary(
    template: _HVACTemplate,
    score: int | None = None,
) -> dict[str, Any]:
    cls = template.cls
    summary = {
        "system_type": template.system_type,
        "family": template.family,
        "class_name": cls.__name__,
        "description": _doc_summary(cls),
        "vintages": _tuple_class_attr(cls, "VINTAGES"),
        "equipment_types": _tuple_class_attr(cls, "EQUIPMENT_TYPES"),
        "economizer_types": _tuple_class_attr(cls, "ECONOMIZER_TYPES"),
        "accepted_parameters": sorted(_class_signature_names(cls)),
        "use_as": [
            "search_hvac_templates.identifier -> object_dict",
            "edit_honeybee_room.hvac",
        ],
    }
    if score is not None:
        summary["score"] = score
    return summary


def _query_tokens(query: str | None) -> tuple[str, ...]:
    if not query:
        return ()
    normalized = query.lower().replace("_", " ").replace("-", " ")
    return tuple(token for token in normalized.split() if token)


def _score_template(
    template: _HVACTemplate,
    tokens: tuple[str, ...],
    raw_query: str | None,
) -> int:
    if not tokens:
        return 1
    cls = template.cls
    haystack = " ".join(
        str(item)
        for item in [
            template.system_type,
            template.family,
            cls.__name__,
            _doc_summary(cls) or "",
            " ".join(_tuple_class_attr(cls, "EQUIPMENT_TYPES")),
        ]
    ).lower().replace("_", " ").replace("-", " ")
    score = 0
    if raw_query and raw_query.lower() in haystack:
        score += 20
    for token in tokens:
        if token in haystack:
            score += 4
        if template.system_type.lower().startswith(token) or cls.__name__.lower().startswith(
            token
        ):
            score += 3
    return score


def _resolve_template(system_type: str) -> _HVACTemplate:
    normalized = system_type.replace("_", "").replace("-", "").replace(" ", "").lower()
    template = _TEMPLATES_BY_NORMALIZED.get(normalized)
    if template is None:
        allowed = ", ".join(template.system_type for template in _TEMPLATES)
        raise ValueError(f"system_type must be one of: {allowed}.")
    return template


def _template_matches(
    query: str | None,
    family: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    tokens = _query_tokens(query)
    matches: list[dict[str, Any]] = []
    for template in _TEMPLATES:
        if family not in {None, "", "all"} and template.family != family:
            continue
        score = _score_template(template, tokens, query)
        if score <= 0:
            continue
        matches.append(_template_summary(template, score))
    matches.sort(key=lambda item: (-item["score"], item["family"], item["system_type"]))
    return matches[:limit]


def _instantiate_template(
    template: _HVACTemplate,
    *,
    identifier: str,
    vintage: str | None,
    equipment_type: str | None,
    economizer_type: str | None,
    sensible_heat_recovery: float | None,
    latent_heat_recovery: float | None,
    demand_controlled_ventilation: bool | None,
    doas_availability_schedule: dict[str, Any] | str | None,
    radiant_type: str | None,
    minimum_operation_time: float | None,
    switch_over_time: float | None,
) -> Any:
    candidate_kwargs: dict[str, Any] = {
        "vintage": vintage,
        "equipment_type": equipment_type,
        "economizer_type": economizer_type,
        "sensible_heat_recovery": sensible_heat_recovery,
        "latent_heat_recovery": latent_heat_recovery,
        "demand_controlled_ventilation": demand_controlled_ventilation,
        "doas_availability_schedule": _schedule_from_input(
            doas_availability_schedule,
            field_name="doas_availability_schedule",
        )
        if doas_availability_schedule is not None
        else None,
        "radiant_type": radiant_type,
        "minimum_operation_time": minimum_operation_time,
        "switch_over_time": switch_over_time,
    }
    signature_names = _class_signature_names(template.cls)
    kwargs: dict[str, Any] = {}
    unsupported = []
    for name, value in candidate_kwargs.items():
        if value is None:
            continue
        if name not in signature_names:
            unsupported.append(name)
        else:
            kwargs[name] = value
    if unsupported:
        allowed = ", ".join(sorted(signature_names))
        raise ValueError(
            f"{template.system_type} does not accept: {', '.join(unsupported)}. "
            f"Accepted parameters: {allowed}."
        )
    try:
        return template.cls(identifier, **kwargs)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid {template.system_type} HVAC input. {exc}") from exc


def _hvac_summary(
    hvac: Any,
    *,
    family: str | None = None,
    system_type: str | None = None,
) -> dict[str, Any]:
    summary = {
        "type": hvac.__class__.__name__,
        "identifier": hvac.identifier,
        "family": family,
        "system_type": system_type or hvac.__class__.__name__,
    }
    for field in (
        "vintage",
        "equipment_type",
        "economizer_type",
        "demand_controlled_ventilation",
        "sensible_heat_recovery",
        "latent_heat_recovery",
        "heating_air_temperature",
        "cooling_air_temperature",
        "radiant_type",
        "minimum_operation_time",
        "switch_over_time",
    ):
        if hasattr(hvac, field):
            value = getattr(hvac, field)
            if hasattr(value, "identifier"):
                summary[field] = value.identifier
            elif isinstance(value, str | int | float | bool) or value is None:
                summary[field] = value
            else:
                summary[field] = str(value)
    return summary


def create_ideal_air_system(
    *,
    identifier: str,
    economizer_type: str | None = None,
    demand_controlled_ventilation: bool | None = None,
    sensible_heat_recovery: float | None = None,
    latent_heat_recovery: float | None = None,
    heating_air_temperature: float | None = None,
    cooling_air_temperature: float | None = None,
    heating_limit: float | str | None = None,
    cooling_limit: float | str | None = None,
    heating_availability: dict[str, Any] | str | None = None,
    cooling_availability: dict[str, Any] | str | None = None,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy IdealAirSystem object."""
    warnings: list[str] = []
    if (
        heating_air_temperature is not None
        and cooling_air_temperature is not None
        and heating_air_temperature <= cooling_air_temperature
    ):
        warnings.append(
            "Ignored heating_air_temperature and cooling_air_temperature because "
            "they look like room setpoints. IdealAirSystem supply air temperature "
            "requires heating_air_temperature > cooling_air_temperature; omit these "
            "fields for a simple HVAC."
        )
        heating_air_temperature = None
        cooling_air_temperature = None
    kwargs: dict[str, Any] = {}
    for name, value in {
        "economizer_type": economizer_type,
        "demand_controlled_ventilation": demand_controlled_ventilation,
        "sensible_heat_recovery": sensible_heat_recovery,
        "latent_heat_recovery": latent_heat_recovery,
        "heating_air_temperature": heating_air_temperature,
        "cooling_air_temperature": cooling_air_temperature,
        "heating_limit": _alt_number_from_input(
            heating_limit,
            field_name="heating_limit",
        ),
        "cooling_limit": _alt_number_from_input(
            cooling_limit,
            field_name="cooling_limit",
        ),
        "heating_availability": _schedule_from_input(
            heating_availability,
            field_name="heating_availability",
        )
        if heating_availability is not None
        else None,
        "cooling_availability": _schedule_from_input(
            cooling_availability,
            field_name="cooling_availability",
        )
        if cooling_availability is not None
        else None,
    }.items():
        if value is not None:
            kwargs[name] = value
    try:
        hvac = IdealAirSystem(identifier, **kwargs)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid IdealAirSystem input. {exc}") from exc
    object_dict = hvac.to_dict()
    result = {
        "object_dict": hvac.to_dict(),
        "summary_view": {
            **_hvac_summary(hvac, family="ideal-air", system_type="IdealAirSystem"),
            "ready_for": "edit_honeybee_room.hvac",
            "warnings": warnings,
        },
        "report": make_report(
            status="ok",
            message=f"Created IdealAirSystem: {hvac.identifier}",
            warnings=warnings,
        ),
    }
    if garden_root:
        saved = save_garden_properties_library_object(
            garden_root=garden_root,
            domain="honeybee_energy",
            object_family="hvac",
            object_dict=object_dict,
        )
        result["target"] = saved["target"]
        result["persistence_receipt"] = saved["persistence_receipt"]
        result["summary_view"]["target"] = saved["target"]
        if not return_object_dict:
            result.pop("object_dict", None)
    return result


def search_hvac_templates(
    *,
    query: str | None = None,
    system_type: str | None = None,
    family: str | None = None,
    identifier: str | None = None,
    vintage: str | None = None,
    equipment_type: str | None = None,
    economizer_type: str | None = None,
    sensible_heat_recovery: float | None = None,
    latent_heat_recovery: float | None = None,
    demand_controlled_ventilation: bool | None = None,
    doas_availability_schedule: dict[str, Any] | str | None = None,
    radiant_type: str | None = None,
    minimum_operation_time: float | None = None,
    switch_over_time: float | None = None,
    return_object: bool = True,
    garden_root: str | None = None,
    return_object_dict: bool = True,
    limit: int = 10,
) -> dict[str, Any]:
    """Search SDK HVAC templates and optionally instantiate one."""
    if limit < 1:
        raise ValueError("limit must be greater than zero.")
    if family not in {None, "", "all", "allair", "doas", "heatcool"}:
        raise ValueError("family must be one of: all, allair, doas, heatcool.")

    selected_template: _HVACTemplate | None = None
    matches: list[dict[str, Any]]
    if system_type:
        selected_template = _resolve_template(system_type)
        if family not in {None, "", "all"} and selected_template.family != family:
            raise ValueError(
                f"{system_type} belongs to family {selected_template.family}, not {family}."
            )
        matches = [_template_summary(selected_template, score=100)]
    else:
        matches = _template_matches(query, family, limit)
        if identifier and return_object and len(matches) == 1:
            selected_template = _resolve_template(str(matches[0]["system_type"]))

    if not identifier or not return_object:
        return {
            "matches": matches,
            "summary_view": {
                "query": query,
                "system_type": system_type,
                "family": family or "all",
                "match_count": len(matches),
                "created": False,
                "ready_for": "Pass identifier with a unique match to return an HVAC object_dict.",
            },
            "report": make_report(
                status="ok",
                message=f"Found {len(matches)} Honeybee HVAC template(s).",
            ),
        }

    if selected_template is None:
        return {
            "matches": matches,
            "summary_view": {
                "query": query,
                "system_type": system_type,
                "family": family or "all",
                "match_count": len(matches),
                "created": False,
                "ready_for": "Choose one match and call again with system_type.",
            },
            "report": make_report(
                status="needs_selection",
                message="HVAC template selection is ambiguous; call again with system_type.",
                warnings=[
                    "No HVAC object was created because the search did not resolve to one template."
                ],
            ),
        }

    hvac = _instantiate_template(
        selected_template,
        identifier=identifier,
        vintage=vintage,
        equipment_type=equipment_type,
        economizer_type=economizer_type,
        sensible_heat_recovery=sensible_heat_recovery,
        latent_heat_recovery=latent_heat_recovery,
        demand_controlled_ventilation=demand_controlled_ventilation,
        doas_availability_schedule=doas_availability_schedule,
        radiant_type=radiant_type,
        minimum_operation_time=minimum_operation_time,
        switch_over_time=switch_over_time,
    )
    object_dict = hvac.to_dict()
    result = {
        "matches": matches,
        "object_dict": object_dict,
        "summary_view": {
            **_hvac_summary(
                hvac,
                family=selected_template.family,
                system_type=selected_template.system_type,
            ),
            "created": True,
            "ready_for": "edit_honeybee_room.hvac",
        },
        "report": make_report(
            status="ok",
            message=f"Created {selected_template.system_type} HVAC: {hvac.identifier}",
        ),
    }
    if garden_root:
        saved = save_garden_properties_library_object(
            garden_root=garden_root,
            domain="honeybee_energy",
            object_family="hvac",
            object_dict=object_dict,
        )
        result["target"] = saved["target"]
        result["persistence_receipt"] = saved["persistence_receipt"]
        result["summary_view"]["target"] = saved["target"]
        if not return_object_dict:
            result.pop("object_dict", None)
    return result
