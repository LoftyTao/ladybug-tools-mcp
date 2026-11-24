"""Honeybee Energy HVAC template search and creation services."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

from honeybee.altnumber import autocalculate, autosize, no_limit
from honeybee_energy.hvac.allair import HVAC_TYPES_DICT as ALL_AIR_TYPES
from honeybee_energy.hvac.doas import HVAC_TYPES_DICT as DOAS_TYPES
from honeybee_energy.hvac.heatcool import HVAC_TYPES_DICT as HEAT_COOL_TYPES
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.shw import SHWSystem

from garden.energy.programtypes import _schedule_from_input as _shared_schedule_from_input
from ladybug_tools_mcp.contracts import make_report
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
    garden_root: str | None = None,
) -> Any:
    return _shared_schedule_from_input(
        data,
        field_name=field_name,
        garden_root=garden_root,
    )


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
            "EP_Create_HVAC_Template.identifier -> object_dict",
            "edit_honeybee_room.hvac",
        ],
    }
    if score is not None:
        summary["score"] = score
    return summary


def _ideal_air_template_summary(score: int | None = None) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "system_type": "IdealAirSystem",
        "family": "ideal-air",
        "class_name": "IdealAirSystem",
        "description": _doc_summary(IdealAirSystem),
        "vintages": [],
        "equipment_types": [],
        "economizer_types": _tuple_class_attr(IdealAirSystem, "ECONOMIZER_TYPES"),
        "accepted_parameters": sorted(_class_signature_names(IdealAirSystem)),
        "use_as": [
            "EP_Create_HVAC_Template.identifier -> object_dict",
            "edit_honeybee_room.hvac",
        ],
    }
    if score is not None:
        summary["score"] = score
    return summary


def _score_ideal_air(tokens: tuple[str, ...], raw_query: str | None) -> int:
    if not tokens:
        return 1
    haystack = " ".join(
        [
            "IdealAirSystem",
            "ideal air",
            "ideal-air",
            "idealair",
            _doc_summary(IdealAirSystem) or "",
        ]
    ).lower().replace("_", " ").replace("-", " ")
    score = 0
    if raw_query and raw_query.lower() in haystack:
        score += 20
    for token in tokens:
        if token in haystack:
            score += 4
        if "idealairsystem".startswith(token):
            score += 3
    return score


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
    garden_root: str | None = None,
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
            garden_root=garden_root,
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


def _shw_template_summary(score: int | None = None) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "system_type": "SHWSystem",
        "family": "shw",
        "class_name": "SHWSystem",
        "description": _doc_summary(SHWSystem),
        "vintages": [],
        "equipment_types": list(SHWSystem.EQUIPMENT_TYPES),
        "economizer_types": [],
        "accepted_parameters": sorted(_class_signature_names(SHWSystem)),
        "use_as": [
            "EP_Create_Load(load_type='shw_system') -> object_dict",
            "EP_Create_HVAC_Template(system_type='SHWSystem') -> object_dict",
            "edit_honeybee_room.shw",
        ],
    }
    if score is not None:
        summary["score"] = score
    return summary


def _score_shw(tokens: tuple[str, ...], raw_query: str | None) -> int:
    if not tokens:
        return 0
    haystack = " ".join(
        [
            "SHWSystem",
            "shw",
            "service hot water",
            "water heater",
            " ".join(SHWSystem.EQUIPMENT_TYPES),
        ]
    ).lower().replace("_", " ").replace("-", " ")
    relevant_tokens = {"shw", "shwsystem", "hot", "water", "heater", "tankless", "dhw"}
    if not any(token in relevant_tokens for token in tokens):
        return 0
    score = 0
    if raw_query and raw_query.lower() in haystack:
        score += 20
    for token in tokens:
        if token in haystack:
            score += 4
        if "shwsystem".startswith(token):
            score += 3
    return score


def _shw_summary(shw: SHWSystem) -> dict[str, Any]:
    return {
        "type": "SHWSystem",
        "identifier": shw.identifier,
        "family": "shw",
        "system_type": "SHWSystem",
        "equipment_type": shw.equipment_type,
        "heater_efficiency": shw.heater_efficiency,
        "ambient_condition": shw.ambient_condition,
        "ambient_loss_coefficient": shw.ambient_loss_coefficient,
    }


def create_shw_system(
    *,
    identifier: str,
    equipment_type: str = "Gas_WaterHeater",
    heater_efficiency: float | str | None = None,
    ambient_condition: float | str = 22,
    ambient_loss_coefficient: float = 6,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy SHWSystem object."""
    resolved_efficiency: Any = autocalculate
    if heater_efficiency is not None:
        if isinstance(heater_efficiency, str):
            normalized_eff = heater_efficiency.replace("_", "").replace("-", "").replace(" ", "").lower()
            if normalized_eff == "autocalculate":
                resolved_efficiency = autocalculate
            else:
                try:
                    resolved_efficiency = float(heater_efficiency)
                except ValueError as exc:
                    raise ValueError(
                        "heater_efficiency must be a positive number or 'autocalculate'."
                    ) from exc
        else:
            resolved_efficiency = float(heater_efficiency)
    try:
        shw = SHWSystem(
            identifier,
            equipment_type=equipment_type,
            heater_efficiency=resolved_efficiency,
            ambient_condition=ambient_condition,
            ambient_loss_coefficient=ambient_loss_coefficient,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid SHWSystem input. {exc}") from exc
    object_dict = shw.to_dict()
    result: dict[str, Any] = {
        "object_dict": object_dict,
        "summary_view": {
            **_shw_summary(shw),
            "ready_for": "edit_honeybee_room.shw",
        },
        "report": make_report(
            status="ok",
            message=f"Created SHWSystem: {shw.identifier}",
        ),
    }
    if garden_root:
        saved = save_garden_properties_library_object(
            garden_root=garden_root,
            domain="honeybee_energy",
            object_family="shw_system",
            object_dict=object_dict,
        )
        result["target"] = saved["target"]
        result["persistence_receipt"] = saved["persistence_receipt"]
        result["summary_view"]["target"] = saved["target"]
        if not return_object_dict:
            result.pop("object_dict", None)
    return result


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
            garden_root=garden_root,
        )
        if heating_availability is not None
        else None,
        "cooling_availability": _schedule_from_input(
            cooling_availability,
            field_name="cooling_availability",
            garden_root=garden_root,
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
        garden_root=garden_root,
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


_IDEAL_AIR_ALIASES = {"idealairsystem", "idealair"}
_SHW_ALIASES = {"shwsystem", "shw"}
_IDEAL_AIR_FAMILIES = {"idealair", "ideal-air", "ideal_air"}
_TEMPLATE_ONLY_FIELDS = (
    "vintage",
    "equipment_type",
    "doas_availability_schedule",
    "radiant_type",
    "minimum_operation_time",
    "switch_over_time",
)
_IDEAL_AIR_ONLY_FIELDS = (
    "heating_air_temperature",
    "cooling_air_temperature",
    "heating_limit",
    "cooling_limit",
    "heating_availability",
    "cooling_availability",
)
_SHW_ONLY_FIELDS = (
    "heater_efficiency",
    "ambient_condition",
    "ambient_loss_coefficient",
)


def create_hvac_template(
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
    heating_air_temperature: float | None = None,
    cooling_air_temperature: float | None = None,
    heating_limit: float | str | None = None,
    cooling_limit: float | str | None = None,
    heating_availability: dict[str, Any] | str | None = None,
    cooling_availability: dict[str, Any] | str | None = None,
    heater_efficiency: float | str | None = None,
    ambient_condition: float | str | None = None,
    ambient_loss_coefficient: float | None = None,
    return_object: bool = True,
    garden_root: str | None = None,
    return_object_dict: bool = True,
    limit: int = 10,
) -> dict[str, Any]:
    """Search Honeybee Energy HVAC templates or create IdealAirSystem, SHWSystem, or standards HVAC."""
    if limit < 1:
        raise ValueError("limit must be greater than zero.")
    normalized_family = (
        family.strip().lower().replace("_", "-") if isinstance(family, str) and family.strip() else None
    )
    allowed_families = {None, "all", "allair", "doas", "heatcool", "ideal-air", "idealair", "shw"}
    if normalized_family not in allowed_families:
        raise ValueError(
            "family must be one of: all, allair, doas, heatcool, ideal-air, shw."
        )
    normalized_system_type = (
        system_type.replace("_", "").replace("-", "").replace(" ", "").lower()
        if system_type
        else None
    )

    is_ideal_air = bool(
        (normalized_system_type in _IDEAL_AIR_ALIASES)
        or (system_type is None and normalized_family in {"ideal-air", "idealair"})
    )
    is_shw = bool(
        (normalized_system_type in _SHW_ALIASES)
        or (system_type is None and normalized_family == "shw")
    )
    if (
        not is_ideal_air
        and not is_shw
        and system_type is None
        and normalized_family in {None, "all"}
        and query is not None
    ):
        tokens = _query_tokens(query)
        ideal_score = _score_ideal_air(tokens, query)
        shw_score = _score_shw(tokens, query)
        template_matches = _template_matches(query, normalized_family, limit)
        if not return_object or not identifier:
            extra_matches = []
            if ideal_score > 0:
                extra_matches.append(_ideal_air_template_summary(score=ideal_score))
            if shw_score > 0:
                extra_matches.append(_shw_template_summary(score=shw_score))
            if extra_matches:
                combined = [*extra_matches, *template_matches]
                combined.sort(key=lambda item: (-item["score"], item["family"], item["system_type"]))
                combined = combined[:limit]
                return {
                    "matches": combined,
                    "summary_view": {
                        "query": query,
                        "system_type": system_type,
                        "family": normalized_family or "all",
                        "match_count": len(combined),
                        "created": False,
                        "ready_for": "Pass identifier with a unique match to return an HVAC object_dict.",
                    },
                    "report": make_report(
                        status="ok",
                        message=f"Found {len(combined)} Honeybee HVAC template(s).",
                    ),
                }
        elif ideal_score > 0 and shw_score == 0 and not template_matches:
            is_ideal_air = True
        elif shw_score > 0 and ideal_score == 0 and not template_matches:
            is_shw = True
        elif (ideal_score > 0 or shw_score > 0):
            extra_matches = []
            if ideal_score > 0:
                extra_matches.append(_ideal_air_template_summary(score=ideal_score))
            if shw_score > 0:
                extra_matches.append(_shw_template_summary(score=shw_score))
            combined = [*extra_matches, *template_matches]
            combined.sort(key=lambda item: (-item["score"], item["family"], item["system_type"]))
            combined = combined[:limit]
            return {
                "matches": combined,
                "summary_view": {
                    "query": query,
                    "system_type": system_type,
                    "family": normalized_family or "all",
                    "match_count": len(combined),
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

    if is_shw:
        if normalized_family not in {None, "all", "shw"}:
            raise ValueError(f"SHWSystem belongs to family shw, not {family}.")
        if not identifier or not return_object:
            matches = [_shw_template_summary(score=100)]
            return {
                "matches": matches,
                "summary_view": {
                    "query": query,
                    "system_type": "SHWSystem",
                    "family": normalized_family or "shw",
                    "match_count": 1,
                    "created": False,
                    "ready_for": "Pass identifier and return_object=true to create SHWSystem.",
                },
                "report": make_report(
                    status="ok",
                    message="Found 1 Honeybee SHWSystem template.",
                ),
            }
        non_shw = {
            "vintage": vintage,
            "economizer_type": economizer_type,
            "sensible_heat_recovery": sensible_heat_recovery,
            "latent_heat_recovery": latent_heat_recovery,
            "demand_controlled_ventilation": demand_controlled_ventilation,
            "doas_availability_schedule": doas_availability_schedule,
            "radiant_type": radiant_type,
            "minimum_operation_time": minimum_operation_time,
            "switch_over_time": switch_over_time,
            "heating_air_temperature": heating_air_temperature,
            "cooling_air_temperature": cooling_air_temperature,
            "heating_limit": heating_limit,
            "cooling_limit": cooling_limit,
            "heating_availability": heating_availability,
            "cooling_availability": cooling_availability,
        }
        bad_non_shw = [name for name, value in non_shw.items() if value is not None]
        if bad_non_shw:
            raise ValueError(
                f"SHWSystem does not accept HVAC parameter(s): {', '.join(bad_non_shw)}."
            )
        result = create_shw_system(
            identifier=identifier,
            equipment_type=equipment_type or "Gas_WaterHeater",
            heater_efficiency=heater_efficiency,
            ambient_condition=ambient_condition if ambient_condition is not None else 22,
            ambient_loss_coefficient=(
                ambient_loss_coefficient if ambient_loss_coefficient is not None else 6
            ),
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
        result["matches"] = [_shw_template_summary(score=100)]
        result["summary_view"]["created"] = True
        return result

    shw_only = {
        "heater_efficiency": heater_efficiency,
        "ambient_condition": ambient_condition,
        "ambient_loss_coefficient": ambient_loss_coefficient,
    }
    bad_shw = [name for name, value in shw_only.items() if value is not None]
    if bad_shw:
        raise ValueError(
            f"SHWSystem parameter(s) {', '.join(bad_shw)} require system_type='SHWSystem'."
        )

    if is_ideal_air:
        if normalized_family not in {None, "all", "ideal-air", "idealair"}:
            raise ValueError(
                f"IdealAirSystem belongs to family ideal-air, not {family}."
            )
        if not identifier or not return_object:
            matches = [_ideal_air_template_summary(score=100)]
            return {
                "matches": matches,
                "summary_view": {
                    "query": query,
                    "system_type": "IdealAirSystem",
                    "family": normalized_family or "ideal-air",
                    "match_count": 1,
                    "created": False,
                    "ready_for": "Pass identifier and return_object=true to create IdealAirSystem.",
                },
                "report": make_report(
                    status="ok",
                    message="Found 1 Honeybee HVAC template(s).",
                ),
            }
        template_only = {
            "vintage": vintage,
            "equipment_type": equipment_type,
            "doas_availability_schedule": doas_availability_schedule,
            "radiant_type": radiant_type,
            "minimum_operation_time": minimum_operation_time,
            "switch_over_time": switch_over_time,
        }
        bad_fields = [name for name, value in template_only.items() if value is not None]
        if bad_fields:
            raise ValueError(
                f"IdealAirSystem does not accept template-only parameter(s): {', '.join(bad_fields)}."
            )
        result = create_ideal_air_system(
            identifier=identifier,
            economizer_type=economizer_type,
            demand_controlled_ventilation=demand_controlled_ventilation,
            sensible_heat_recovery=sensible_heat_recovery,
            latent_heat_recovery=latent_heat_recovery,
            heating_air_temperature=heating_air_temperature,
            cooling_air_temperature=cooling_air_temperature,
            heating_limit=heating_limit,
            cooling_limit=cooling_limit,
            heating_availability=heating_availability,
            cooling_availability=cooling_availability,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
        result["matches"] = [_ideal_air_template_summary(score=100)]
        result["summary_view"]["created"] = True
        return result

    ideal_only = {
        "heating_air_temperature": heating_air_temperature,
        "cooling_air_temperature": cooling_air_temperature,
        "heating_limit": heating_limit,
        "cooling_limit": cooling_limit,
        "heating_availability": heating_availability,
        "cooling_availability": cooling_availability,
    }
    bad_ideal = [name for name, value in ideal_only.items() if value is not None]
    if bad_ideal:
        raise ValueError(
            f"IdealAirSystem parameter(s) {', '.join(bad_ideal)} require system_type='IdealAirSystem'."
        )

    if system_type is None and query is None and normalized_family in {None, "all"}:
        template_matches = _template_matches(query, normalized_family, max(limit - 1, 1))
        combined = [_ideal_air_template_summary(score=1), *template_matches][:limit]
        if not identifier or not return_object or len(combined) > 1:
            return {
                "matches": combined,
                "summary_view": {
                    "query": query,
                    "system_type": system_type,
                    "family": normalized_family or "all",
                    "match_count": len(combined),
                    "created": False,
                    "ready_for": "Choose one match and call again with system_type.",
                },
                "report": make_report(
                    status="ok" if (not identifier or not return_object) else "needs_selection",
                    message=(
                        f"Found {len(combined)} Honeybee HVAC template(s)."
                        if (not identifier or not return_object)
                        else "HVAC template selection is ambiguous; call again with system_type."
                    ),
                ),
            }

    return search_hvac_templates(
        query=query,
        system_type=system_type,
        family=normalized_family,
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
        return_object=return_object,
        garden_root=garden_root,
        return_object_dict=return_object_dict,
        limit=limit,
    )
