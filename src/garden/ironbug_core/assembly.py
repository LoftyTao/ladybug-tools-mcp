"""Garden services for assembling source-backed Ironbug HVAC systems."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from ironbug import hvac
from ironbug.hvac import (
    IB_BoilerHotWater,
    IB_CoilHeatingWater,
    IB_CoolingTowerSingleSpeed,
    IB_CoolingTowerVariableSpeed,
    IB_DistrictCooling,
    IB_DistrictHeatingSteam,
    IB_DistrictHeatingWater,
    IB_HVACObject,
    IB_HeatExchangerFluidToFluid,
    IB_LoadProfilePlant,
    IB_PipeAdiabatic,
    IB_PlantEquipmentOperationCoolingLoad,
    IB_PlantEquipmentOperationHeatingLoad,
    IB_PlantLoop,
    IB_PlantLoopBranches,
    IB_PumpConstantSpeed,
    IB_PumpVariableSpeed,
    IB_SetpointManagerScheduled,
    IB_SizingPlant,
)
from ironbug.hvac.operation_schemes import (
    PLANT_OPERATION_DEFAULT_UPPER_LIMIT_W,
    plant_equipment_operation_ib_properties,
)

from garden.ironbug_core.model_io import load_ironbug_model, save_ironbug_model
from garden.ironbug_core.targets import (
    make_ironbug_model_object_target,
    normalize_ironbug_model_target,
)
from garden.manifest import GardenManifest
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report


COMPONENT_LIBRARY_KEY = "ironbug_component_library"


def _garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _fields(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _source_type_accepts(source_class: str, expected_type: str) -> bool:
    if source_class == expected_type:
        return True
    if expected_type in {"IB_ModelObject", "IB_HVACObject"} and source_class.startswith("IB_"):
        return True
    if not hasattr(hvac, source_class):
        return False
    cls = getattr(hvac, source_class)
    pending = list(getattr(cls, "SOURCE_BASES", ()) or ())
    pending.extend(getattr(cls, "SOURCE_INTERFACES", ()) or ())
    seen: set[str] = set()
    while pending:
        base_name = pending.pop()
        if base_name in seen:
            continue
        seen.add(base_name)
        if base_name == expected_type:
            return True
        if hasattr(hvac, base_name):
            base_cls = getattr(hvac, base_name)
            pending.extend(getattr(base_cls, "SOURCE_BASES", ()) or ())
            pending.extend(getattr(base_cls, "SOURCE_INTERFACES", ()) or ())
    return False


def _resolve_plant_loop_target(
    *,
    model: Any,
    model_target: dict[str, Any],
    reference: Any,
    expected_type: str,
    label: str,
) -> Any:
    from garden.ironbug_core.relationships import _resolve_object

    resolved = _resolve_object(model, model_target, reference)
    source_class = getattr(resolved.obj, "SOURCE_CLASS", resolved.obj.__class__.__name__)
    if not _source_type_accepts(str(source_class), expected_type):
        raise ValueError(f"{label} accepts {expected_type} targets, got {source_class}.")
    return resolved.obj


def _resolve_plant_loop_field_targets(
    *,
    model: Any,
    model_target: dict[str, Any],
    source_field_targets: dict[str, Any] | None,
) -> dict[str, Any]:
    if not source_field_targets:
        return {}
    expected = {
        "PlantEquipmentOperationHeatingLoadSchedule": ("IB_Schedule", False),
        "PlantEquipmentOperationCoolingLoadSchedule": ("IB_Schedule", False),
        "PrimaryPlantEquipmentOperationSchemeSchedule": ("IB_Schedule", False),
        "ComponentSetpointOperationSchemeSchedule": ("IB_Schedule", False),
        "AvailabilityManagers": ("IB_AvailabilityManager", True),
    }
    resolved_targets: dict[str, Any] = {}
    for field_name, reference in source_field_targets.items():
        if reference is None:
            continue
        if field_name not in expected:
            raise ValueError(f"Unsupported IB_PlantLoop source field target: {field_name}")
        expected_type, is_list = expected[field_name]
        references = reference if is_list else [reference]
        if is_list and not isinstance(references, list):
            raise ValueError(f"IB_PlantLoop.{field_name} requires a list of targets.")
        objects = [
            _resolve_plant_loop_target(
                model=model,
                model_target=model_target,
                reference=item,
                expected_type=expected_type,
                label=f"IB_PlantLoop.{field_name}",
            )
            for item in references
        ]
        resolved_targets[field_name] = objects if is_list else objects[0]
    return resolved_targets


def _constant_speed_pump(identifier: str, attrs: dict[str, Any]) -> IB_PumpConstantSpeed:
    return IB_PumpConstantSpeed(
        identifier=identifier,
        CustomAttributes={
            **_fields(
                RatedPumpHead=179352,
                MotorEfficiency=0.9,
                RatedFlowRate="Autosize",
                PumpControlType="Intermittent",
            ),
            **attrs,
        },
    )


def _variable_speed_pump(identifier: str, attrs: dict[str, Any]) -> IB_PumpVariableSpeed:
    return IB_PumpVariableSpeed(
        identifier=identifier,
        CustomAttributes={
            **_fields(
                RatedPumpHead=179352,
                MotorEfficiency=0.9,
                RatedFlowRate="Autosize",
                PumpControlType="Intermittent",
                Coefficient1ofthePartLoadPerformanceCurve=0,
                Coefficient2ofthePartLoadPerformanceCurve=1,
                Coefficient3ofthePartLoadPerformanceCurve=0,
                Coefficient4ofthePartLoadPerformanceCurve=0,
            ),
            **attrs,
        },
    )


def _simple_component(cls: type[Any], identifier: str, attrs: dict[str, Any]) -> Any:
    return cls(identifier=identifier, CustomAttributes=attrs)


def _plant_loop_branch_group(
    *,
    identifier: str,
    branches: list[list[IB_HVACObject]],
) -> IB_PlantLoopBranches:
    return IB_PlantLoopBranches(
        identifier=identifier,
        Branches=branches,
    )


def _plant_loop_branch_groups_from_references(
    model: Any,
    references: list[Any],
) -> list[list[IB_HVACObject]]:
    if not references:
        return []
    if any(isinstance(reference, list) for reference in references):
        branches: list[list[IB_HVACObject]] = []
        for reference in references:
            if isinstance(reference, list):
                branches.append(_components_from_references(model, reference))
            else:
                branches.append(_components_from_references(model, [reference]))
        return branches
    return [_components_from_references(model, references)]


def _plant_loop_supply_components_from_branch_references(
    model: Any,
    loop_identifier: str,
    references: list[Any],
) -> list[IB_HVACObject]:
    branches = _plant_loop_branch_groups_from_references(model, references)
    pumps: list[tuple[int, int, IB_HVACObject]] = []
    for branch_index, branch in enumerate(branches):
        for component_index, component in enumerate(branch):
            if isinstance(component, (IB_PumpConstantSpeed, IB_PumpVariableSpeed)):
                pumps.append((branch_index, component_index, component))
    if len(pumps) != 1:
        return [
            _plant_loop_branch_group(
                identifier=f"{loop_identifier}_supply_branches",
                branches=branches,
            )
        ]
    pump_branch_index, pump_component_index, pump = pumps[0]
    remaining_branches: list[list[IB_HVACObject]] = []
    for branch_index, branch in enumerate(branches):
        remaining_branch = list(branch)
        if branch_index == pump_branch_index:
            remaining_branch.pop(pump_component_index)
        if remaining_branch:
            remaining_branches.append(remaining_branch)
    if not remaining_branches:
        return [pump]
    return [
        pump,
        _plant_loop_branch_group(
            identifier=f"{loop_identifier}_supply_branches",
            branches=remaining_branches,
        ),
    ]


def _plant_loop_branch_count(components: list[Any]) -> int:
    return sum(
        len(component.Branches)
        for component in components
        if isinstance(component, IB_PlantLoopBranches)
    )


def _plant_loop_branch_lengths(components: list[Any]) -> list[int]:
    lengths: list[int] = []
    for component in components:
        if isinstance(component, IB_PlantLoopBranches):
            lengths.extend(len(branch) for branch in component.Branches)
    return lengths


COMPONENT_REGISTRY: dict[str, dict[str, Any]] = {
    "pump_constant_speed": {
        "source_class": "IB_PumpConstantSpeed",
        "factory": _constant_speed_pump,
        "examples": ["example_1", "example_3"],
    },
    "pump_variable_speed": {
        "source_class": "IB_PumpVariableSpeed",
        "factory": _variable_speed_pump,
        "examples": ["example_3"],
    },
    "chiller_electric_eir": {
        "source_class": "IB_ChillerElectricEIR",
        "factory": lambda identifier, attrs: _simple_component(
            hvac.IB_ChillerElectricEIR,
            identifier,
            {
                **_fields(
                    ReferenceCapacity="Autosize",
                    ReferenceCOP=5.5,
                    CondenserType="WaterCooled",
                    ReferenceLeavingChilledWaterTemperature=6.7,
                ),
                **attrs,
            },
        ),
        "examples": ["example_1"],
    },
    "cooling_tower_variable_speed": {
        "source_class": "IB_CoolingTowerVariableSpeed",
        "factory": lambda identifier, attrs: _simple_component(
            IB_CoolingTowerVariableSpeed,
            identifier,
            {
                **_fields(
                    DesignWaterFlowRate="Autosize",
                    DesignAirFlowRate="Autosize",
                    DesignFanPower="Autosize",
                ),
                **attrs,
            },
        ),
        "examples": ["example_1"],
    },
    "cooling_tower_single_speed": {
        "source_class": "IB_CoolingTowerSingleSpeed",
        "factory": lambda identifier, attrs: _simple_component(
            IB_CoolingTowerSingleSpeed,
            identifier,
            {**_fields(NominalCapacity=100000.0), **attrs},
        ),
        "examples": ["example_3"],
    },
    "district_cooling": {
        "source_class": "IB_DistrictCooling",
        "factory": lambda identifier, attrs: _simple_component(
            IB_DistrictCooling,
            identifier,
            {**_fields(Name=identifier, NominalCapacity="Autosize"), **attrs},
        ),
        "examples": ["example_3"],
    },
    "district_heating_water": {
        "source_class": "IB_DistrictHeatingWater",
        "factory": lambda identifier, attrs: _simple_component(
            IB_DistrictHeatingWater,
            identifier,
            {**_fields(Name=identifier, NominalCapacity="Autosize"), **attrs},
        ),
        "examples": ["district_heating_loop"],
    },
    "district_heating_steam": {
        "source_class": "IB_DistrictHeatingSteam",
        "factory": lambda identifier, attrs: _simple_component(
            IB_DistrictHeatingSteam,
            identifier,
            {**_fields(Name=identifier), **attrs},
        ),
        "examples": ["district_heating_loop"],
    },
    "heat_exchanger_fluid_to_fluid": {
        "source_class": "IB_HeatExchangerFluidToFluid",
        "factory": lambda identifier, attrs: _simple_component(
            IB_HeatExchangerFluidToFluid,
            identifier,
            attrs,
        ),
        "examples": ["example_3"],
    },
    "load_profile_plant": {
        "source_class": "IB_LoadProfilePlant",
        "factory": lambda identifier, attrs: _simple_component(
            IB_LoadProfilePlant,
            identifier,
            attrs,
        ),
        "examples": ["example_1", "example_3"],
    },
    "boiler_hot_water": {
        "source_class": "IB_BoilerHotWater",
        "factory": lambda identifier, attrs: _simple_component(
            IB_BoilerHotWater,
            identifier,
            {
                **_fields(
                    Name=identifier,
                    FuelType="NaturalGas",
                    NominalCapacity="Autosize",
                    NominalThermalEfficiency=0.8,
                ),
                **attrs,
            },
        ),
        "examples": ["boiler_hot_water_loop"],
    },
    "coil_heating_water": {
        "source_class": "IB_CoilHeatingWater",
        "factory": lambda identifier, attrs: _simple_component(
            IB_CoilHeatingWater,
            identifier,
            {**_fields(Name=identifier, MaximumWaterFlowRate="Autosize"), **attrs},
        ),
        "examples": ["boiler_hot_water_loop", "vav_reheat"],
    },
    "pipe_adiabatic": {
        "source_class": "IB_PipeAdiabatic",
        "factory": lambda identifier, attrs: _simple_component(
            IB_PipeAdiabatic,
            identifier,
            {**_fields(Name=identifier), **attrs},
        ),
        "examples": ["example_1"],
    },
}

COMPONENT_TYPE_ALIASES = {
    "pumpconstantspeed": "pump_constant_speed",
    "ibpumpconstantspeed": "pump_constant_speed",
    "pumpvariablespeed": "pump_variable_speed",
    "ibpumpvariablespeed": "pump_variable_speed",
    "chillerelectriceir": "chiller_electric_eir",
    "ibchillerelectriceir": "chiller_electric_eir",
    "coolingtowervariablespeed": "cooling_tower_variable_speed",
    "ibcoolingtowervariablespeed": "cooling_tower_variable_speed",
    "coolingtowersinglespeed": "cooling_tower_single_speed",
    "ibcoolingtowersinglespeed": "cooling_tower_single_speed",
    "districtcooling": "district_cooling",
    "ibdistrictcooling": "district_cooling",
    "districtheatingwater": "district_heating_water",
    "ibdistrictheatingwater": "district_heating_water",
    "districtheatingsteam": "district_heating_steam",
    "ibdistrictheatingsteam": "district_heating_steam",
    "heatexchangerfluidtofluid": "heat_exchanger_fluid_to_fluid",
    "ibheatexchangerfluidtofluid": "heat_exchanger_fluid_to_fluid",
    "loadprofileplant": "load_profile_plant",
    "ibloadprofileplant": "load_profile_plant",
    "boilerhotwater": "boiler_hot_water",
    "ibboilerhotwater": "boiler_hot_water",
    "coilheatingwater": "coil_heating_water",
    "ibcoilheatingwater": "coil_heating_water",
    "pipeadiabatic": "pipe_adiabatic",
    "ibpipeadiabatic": "pipe_adiabatic",
}


def _normalize_component_type(component_type: str) -> str:
    normalized = component_type.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in COMPONENT_REGISTRY:
        return normalized
    compact = "".join(ch for ch in normalized if ch.isalnum())
    if compact in COMPONENT_TYPE_ALIASES:
        return COMPONENT_TYPE_ALIASES[compact]
    return normalized


def list_ironbug_hvac_component_types(
    *,
    garden_root: str | None = None,
    ironbug_model_target: dict[str, Any] | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    """Return source-backed component types supported by the assembly tools."""

    normalized_query = (query or "").strip().lower()
    items = []
    for component_type, info in COMPONENT_REGISTRY.items():
        cls = getattr(hvac, info["source_class"])
        searchable = " ".join(
            [
                component_type,
                info["source_class"],
                cls.SOURCE_PATH,
                " ".join(info.get("examples") or []),
            ]
        ).lower()
        if normalized_query and normalized_query not in searchable:
            continue
        items.append(
            {
                "component_type": component_type,
                "source_class": info["source_class"],
                "source_path": cls.SOURCE_PATH,
                "source_field_names": list(cls.SOURCE_FIELD_NAMES),
                "examples": list(info["examples"]),
            }
        )
    return {
        "component_types": items,
        "summary_view": {
            "count": len(items),
            "example_1_ready_component_types": [
                item["component_type"]
                for item in items
                if "example_1" in item["examples"]
            ],
            "example_3_plant_core_component_types": [
                item["component_type"]
                for item in items
                if "example_3" in item["examples"]
            ],
            "boiler_hot_water_loop_component_types": [
                item["component_type"]
                for item in items
                if "boiler_hot_water_loop" in item["examples"]
            ],
        },
        "report": make_report(
            status="ok",
            message="Listed source-backed Ironbug HVAC assembly component types.",
        ),
    }


def _component_library(model: Any) -> dict[str, Any]:
    if model.user_data is None:
        model.user_data = {}
    library = model.user_data.setdefault(COMPONENT_LIBRARY_KEY, {})
    if not isinstance(library, dict):
        raise ValueError("Ironbug component library in user_data must be a dict.")
    return library


def _component_target(
    *,
    model_target: dict[str, Any],
    identifier: str,
    source_class: str,
) -> dict[str, Any]:
    return make_ironbug_model_object_target(
        model_target=model_target,
        object_type="component",
        object_path=f"user_data.{COMPONENT_LIBRARY_KEY}.{identifier}",
        source_class=source_class,
        identifier=identifier,
    )


def _plant_loop_target(
    *,
    model_target: dict[str, Any],
    loop: IB_PlantLoop,
    index: int,
) -> dict[str, Any]:
    return make_ironbug_model_object_target(
        model_target=model_target,
        object_type="plant_loop",
        object_path=f"HVACSystem.PlantLoops[{index}]",
        source_class=loop.SOURCE_CLASS,
        identifier=str(loop.identifier),
    )


def _dump_source_object(value: BaseModel) -> dict[str, Any]:
    return value.model_dump(by_alias=True, exclude_none=True)


def _hydrate_source_object(data: dict[str, Any]) -> Any:
    if "type" not in data:
        return {
            key: [
                _hydrate_source_object(item) if isinstance(item, dict) else item
                for item in value
            ]
            if isinstance(value, list)
            else _hydrate_source_object(value)
            if isinstance(value, dict)
            else value
            for key, value in data.items()
        }
    data = {
        key: [
            _hydrate_source_object(item) if isinstance(item, dict) else item
            for item in value
        ]
        if isinstance(value, list)
        else _hydrate_source_object(value)
        if isinstance(value, dict)
        else value
        for key, value in data.items()
    }
    source_type = data.get("type")
    if not isinstance(source_type, str) or not hasattr(hvac, source_type):
        raise ValueError(f"Unsupported Ironbug source object type: {source_type!r}")
    payload = dict(data)
    if "DisplayName" in payload and "display_name" not in payload:
        payload["display_name"] = payload.pop("DisplayName")
    return getattr(hvac, source_type).model_construct(**payload)


def _load_model_for_update(
    garden_root: str,
    ironbug_model_target: dict[str, Any],
) -> tuple[Path, GardenManifest, dict[str, Any], Any]:
    garden_root_path = _garden_root(garden_root)
    manifest, target, _, model = load_ironbug_model(
        garden_root_path,
        ironbug_model_target=ironbug_model_target,
    )
    if model.HVACSystem is None:
        raise ValueError("Ironbug model has no HVACSystem.")
    return garden_root_path, manifest, target, model


def _save_update(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    target: dict[str, Any],
    model: Any,
    operation: str,
    change_summary: dict[str, Any],
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    updated_target, persisted_path = save_ironbug_model(
        garden_root_path,
        manifest,
        model,
        identifier=str(target["id"]),
        overwrite=True,
    )
    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        model_target=updated_target,
        persisted_path=persisted_path,
        change_summary={"operation": operation, **change_summary},
    )
    return updated_target, persisted_path, receipt


def add_ironbug_hvac_component(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    component_type: str,
    identifier: str,
    display_name: str | None = None,
    custom_attributes: dict[str, Any] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create or update a source-backed component in an Ironbug model library."""

    normalized_type = _normalize_component_type(component_type)
    if normalized_type not in COMPONENT_REGISTRY:
        raise ValueError(f"Unsupported Ironbug component_type: {component_type}")
    garden_root_path, manifest, target, model = _load_model_for_update(
        garden_root,
        ironbug_model_target,
    )
    library = _component_library(model)
    if identifier in library and not overwrite:
        raise ValueError(
            f"Ironbug component already exists: {identifier}. "
            "Pass overwrite=true to replace it."
        )
    info = COMPONENT_REGISTRY[normalized_type]
    component = info["factory"](identifier, custom_attributes or {})
    if display_name is not None:
        component.display_name = display_name
    library[identifier] = {
        "component_type": normalized_type,
        "source_class": info["source_class"],
        "data": _dump_source_object(component),
    }
    updated_target, persisted_path, receipt = _save_update(
        garden_root_path=garden_root_path,
        manifest=manifest,
        target=target,
        model=model,
        operation="add_ironbug_hvac_component",
        change_summary={
            "component_type": normalized_type,
            "component_identifier": identifier,
        },
    )
    object_target = _component_target(
        model_target=updated_target,
        identifier=identifier,
        source_class=info["source_class"],
    )
    return {
        "target": object_target,
        "component_target": object_target,
        "updated_model_target": updated_target,
        "summary_view": {
            "component_type": normalized_type,
            "identifier": identifier,
            "source_class": info["source_class"],
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=f"Added Ironbug HVAC component: {identifier}",
            details={"persisted_path": persisted_path},
        ),
    }


def add_ironbug_plant_loop(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    identifier: str,
    loop_name: str,
    fluid_type: str = "Water",
    loop_type: str = "Cooling",
    design_loop_exit_temperature: float | None = None,
    loop_design_temperature_difference: float = 6.7,
    source_fields: dict[str, Any] | None = None,
    source_field_targets: dict[str, Any] | None = None,
    sizing_plant_target: Any | None = None,
    sizing_plant_identifier: str | None = None,
    sizing_plant_fields: dict[str, Any] | None = None,
    operation_scheme_target: Any | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Append an empty source-backed plant loop to an Ironbug model."""

    garden_root_path, manifest, target, model = _load_model_for_update(
        garden_root,
        ironbug_model_target,
    )
    plant_loops = list(model.HVACSystem.PlantLoops or [])
    existing_index = next(
        (index for index, loop in enumerate(plant_loops) if loop.identifier == identifier),
        None,
    )
    if existing_index is not None and not overwrite:
        raise ValueError(f"Ironbug plant loop already exists: {identifier}")
    if existing_index is not None:
        plant_loops.pop(existing_index)
    source_field_values = dict(source_fields or {})
    source_field_values.setdefault("FluidType", fluid_type)
    resolved_field_targets = _resolve_plant_loop_field_targets(
        model=model,
        model_target=target,
        source_field_targets=source_field_targets,
    )
    if sizing_plant_target is not None and sizing_plant_fields:
        raise ValueError(
            "Provide either sizing_plant_target or inline sizing_plant_* parameters, not both."
        )
    sizing = None
    if sizing_plant_target is not None:
        sizing = _resolve_plant_loop_target(
            model=model,
            model_target=target,
            reference=sizing_plant_target,
            expected_type="IB_SizingPlant",
            label="sizing_plant_target",
        )
    elif sizing_plant_fields:
        sizing_attrs = dict(sizing_plant_fields)
        sizing_attrs.setdefault("LoopType", loop_type)
        if design_loop_exit_temperature is not None:
            sizing_attrs.setdefault("DesignLoopExitTemperature", design_loop_exit_temperature)
        sizing_attrs.setdefault(
            "LoopDesignTemperatureDifference",
            loop_design_temperature_difference,
        )
        sizing = IB_SizingPlant(
            identifier=sizing_plant_identifier or f"{identifier}_sizing",
            CustomAttributes=_fields(**sizing_attrs),
        )
    elif design_loop_exit_temperature is not None:
        sizing = IB_SizingPlant(
            identifier=f"{identifier}_sizing",
            CustomAttributes=_fields(
                LoopType=loop_type,
                DesignLoopExitTemperature=design_loop_exit_temperature,
                LoopDesignTemperatureDifference=loop_design_temperature_difference,
            ),
        )
    operation_scheme = None
    if operation_scheme_target is not None:
        operation_scheme = _resolve_plant_loop_target(
            model=model,
            model_target=target,
            reference=operation_scheme_target,
            expected_type="IB_PlantEquipmentOperationSchemeBase",
            label="operation_scheme_target",
        )
    loop = IB_PlantLoop.model_construct(
        identifier=identifier,
        CustomAttributes={
            **_fields(Name=loop_name),
            **source_field_values,
            **resolved_field_targets,
        },
        SizingPlant=sizing,
        OperationScheme=operation_scheme,
        SupplyComponents=[],
        DemandComponents=[],
    )
    plant_loops.append(loop)
    model.HVACSystem.PlantLoops = plant_loops
    updated_target, persisted_path, receipt = _save_update(
        garden_root_path=garden_root_path,
        manifest=manifest,
        target=target,
        model=model,
        operation="add_ironbug_plant_loop",
        change_summary={"plant_loop_identifier": identifier},
    )
    object_target = _plant_loop_target(
        model_target=updated_target,
        loop=loop,
        index=len(plant_loops) - 1,
    )
    return {
        "target": object_target,
        "plant_loop_target": object_target,
        "updated_model_target": updated_target,
        "summary_view": {
            "identifier": identifier,
            "source_class": loop.SOURCE_CLASS,
            "loop_name": loop_name,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=f"Added Ironbug plant loop: {identifier}",
            details={"persisted_path": persisted_path},
        ),
    }


def _component_from_target(model: Any, component_target: dict[str, Any]) -> Any:
    target = dict(component_target)
    if target.get("object_type") != "component":
        raise ValueError("Expected an ironbug_model_object target with object_type='component'.")
    identifier = target.get("identifier")
    library = _component_library(model)
    if not isinstance(identifier, str) or identifier not in library:
        raise ValueError(f"Ironbug component not found: {identifier}")
    return _hydrate_source_object(dict(library[identifier]["data"]))


def _component_from_identifier(model: Any, identifier: str) -> Any:
    library = _component_library(model)
    if identifier not in library:
        raise ValueError(f"Ironbug component not found: {identifier}")
    return _hydrate_source_object(dict(library[identifier]["data"]))


def _component_from_reference(model: Any, reference: Any) -> Any:
    if isinstance(reference, dict):
        return _component_from_target(model, reference)
    if isinstance(reference, str):
        return _component_from_identifier(model, reference)
    raise ValueError("Component references must be component targets or identifiers.")


def _components_from_references(model: Any, references: list[Any] | None) -> list[Any]:
    return [_component_from_reference(model, item) for item in (references or [])]


def _loop_index_from_target(model: Any, plant_loop_target: dict[str, Any]) -> int:
    target = dict(plant_loop_target)
    if target.get("object_type") != "plant_loop":
        raise ValueError("Expected an ironbug_model_object target with object_type='plant_loop'.")
    identifier = str(target.get("identifier"))
    for index, loop in enumerate(model.HVACSystem.PlantLoops or []):
        if str(loop.identifier) == identifier:
            return index
    raise ValueError(f"Ironbug plant loop not found: {identifier}")


def _loop_index_from_identifier(model: Any, identifier: str) -> int:
    for index, loop in enumerate(model.HVACSystem.PlantLoops or []):
        if str(loop.identifier) == identifier:
            return index
    raise ValueError(f"Ironbug plant loop not found: {identifier}")


def _scheduled_setpoint(identifier: str, value: float) -> IB_SetpointManagerScheduled:
    return IB_SetpointManagerScheduled(
        identifier=identifier,
        CustomAttributes={"ControlVariable": "Temperature"},
        Value=value,
        IsTemperature=True,
    )


def _cooling_operation(identifier: str, equipment: IB_HVACObject, upper_limit_w: int) -> Any:
    return IB_PlantEquipmentOperationCoolingLoad(
        identifier=identifier,
        IBProperties=plant_equipment_operation_ib_properties(
            equipment,
            upper_limit_w=upper_limit_w,
        ),
    )


def _heating_operation(
    identifier: str,
    equipment: IB_HVACObject,
    upper_limit_w: int,
) -> Any:
    return IB_PlantEquipmentOperationHeatingLoad(
        identifier=identifier,
        IBProperties=plant_equipment_operation_ib_properties(
            equipment,
            upper_limit_w=upper_limit_w,
        ),
    )


def _loop_temperature_difference(loop: IB_PlantLoop, default: float) -> float:
    sizing = loop.SizingPlant
    if sizing is None:
        return default
    value = dict(sizing.CustomAttributes or {}).get("LoopDesignTemperatureDifference")
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _ensure_loop_heating_sizing(
    loop: IB_PlantLoop,
    *,
    setpoint_c: float | None,
) -> None:
    temperature_difference = _loop_temperature_difference(loop, default=11.0)
    exit_temperature = 60.0 if setpoint_c is None else setpoint_c
    if loop.SizingPlant is None:
        loop.SizingPlant = IB_SizingPlant(
            identifier=f"{loop.identifier}_sizing",
            CustomAttributes=_fields(
                LoopType="Heating",
                DesignLoopExitTemperature=exit_temperature,
                LoopDesignTemperatureDifference=temperature_difference,
            ),
        )
        return
    attrs = dict(loop.SizingPlant.CustomAttributes or {})
    attrs["LoopType"] = "Heating"
    attrs["DesignLoopExitTemperature"] = exit_temperature
    attrs["LoopDesignTemperatureDifference"] = temperature_difference
    loop.SizingPlant.CustomAttributes = attrs


def _resolve_operation_scheme_type(
    operation_scheme_type: str,
    operation_equipment: IB_HVACObject,
) -> str:
    normalized = (
        operation_scheme_type.strip().lower().replace("-", "_").replace(" ", "_")
    )
    if normalized in {
        "cooling",
        "cooling_load",
        "plant_equipment_operation_cooling_load",
    }:
        return "cooling_load"
    if normalized in {
        "heating",
        "heating_load",
        "plant_equipment_operation_heating_load",
    }:
        return "heating_load"
    if normalized != "auto":
        raise ValueError(
            "operation_scheme_type must be auto, cooling_load, or heating_load."
        )
    if isinstance(
        operation_equipment,
        (
            IB_BoilerHotWater,
            IB_CoilHeatingWater,
            hvac.IB_DistrictHeating,
            hvac.IB_DistrictHeatingWater,
            hvac.IB_DistrictHeatingSteam,
        ),
    ):
        return "heating_load"
    return "cooling_load"


def set_ironbug_plant_loop_components(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    plant_loop_target: dict[str, Any] | None = None,
    loop_target: dict[str, Any] | None = None,
    supply_component_targets: list[dict[str, Any]] | None = None,
    demand_component_targets: list[dict[str, Any]] | None = None,
    operation_equipment_target: dict[str, Any] | str | None = None,
    plant_loop_identifier: str | None = None,
    loop_identifier: str | None = None,
    identifier: str | None = None,
    supply_component_identifiers: list[str] | None = None,
    demand_component_identifiers: list[str] | None = None,
    supply_components: list[Any] | None = None,
    demand_components: list[Any] | None = None,
    supply_side_components: list[Any] | None = None,
    demand_side_components: list[Any] | None = None,
    supply_branch_components: list[Any] | None = None,
    demand_branch_components: list[Any] | None = None,
    supply: list[Any] | None = None,
    demand: list[Any] | None = None,
    operation_equipment_identifier: str | None = None,
    operation_upper_limit_w: int = PLANT_OPERATION_DEFAULT_UPPER_LIMIT_W,
    operation_scheme_type: str = "auto",
    setpoint_c: float | None = None,
) -> dict[str, Any]:
    """Replace a plant loop's supply/demand component lists from component targets."""

    garden_root_path, manifest, target, model = _load_model_for_update(
        garden_root,
        ironbug_model_target,
    )
    if plant_loop_target is not None and loop_target is not None:
        raise ValueError("Pass either plant_loop_target or loop_target, not both.")
    resolved_loop_target = plant_loop_target or loop_target
    loop_identifier_values = [
        value
        for value in (plant_loop_identifier, loop_identifier, identifier)
        if value is not None
    ]
    if len(loop_identifier_values) > 1:
        raise ValueError(
            "Pass only one of plant_loop_identifier, loop_identifier, or identifier."
        )
    resolved_loop_identifier = loop_identifier_values[0] if loop_identifier_values else None
    if resolved_loop_target is not None and resolved_loop_identifier is not None:
        raise ValueError("Pass a loop target or plant_loop_identifier, not both.")
    if resolved_loop_target is None and resolved_loop_identifier is None:
        plant_loops = list(model.HVACSystem.PlantLoops or [])
        if not plant_loops:
            raise ValueError(
                "Ironbug model has no plant loops. Call add_ironbug_plant_loop "
                "first and pass its plant_loop_target to "
                "set_ironbug_plant_loop_components."
            )
        if len(plant_loops) != 1:
            raise ValueError(
                "Pass a plant_loop_target, loop_target, plant_loop_identifier, "
                "or identifier unless the model contains exactly one plant loop."
            )
    if supply_component_targets is not None and supply_component_identifiers is not None:
        raise ValueError(
            "Pass either supply_component_targets or supply_component_identifiers, not both."
        )
    if supply_components is not None and (
        supply_component_targets is not None or supply_component_identifiers is not None
    ):
        raise ValueError(
            "Pass supply_components, supply_component_targets, or "
            "supply_component_identifiers; not more than one."
        )
    if supply_side_components is not None and (
        supply_components is not None
        or supply_component_targets is not None
        or supply_component_identifiers is not None
    ):
        raise ValueError(
            "Pass supply_side_components, supply_components, supply_component_targets, "
            "or supply_component_identifiers; not more than one."
        )
    if supply_branch_components is not None and (
        supply_side_components is not None
        or supply_components is not None
        or supply_component_targets is not None
        or supply_component_identifiers is not None
    ):
        raise ValueError(
            "Pass supply_branch_components, supply_side_components, "
            "supply_components, supply_component_targets, or "
            "supply_component_identifiers; not more than one."
        )
    if supply is not None and (
        supply_branch_components is not None
        or supply_side_components is not None
        or supply_components is not None
        or supply_component_targets is not None
        or supply_component_identifiers is not None
    ):
        raise ValueError("Pass only one supply component reference list.")
    if demand_component_targets is not None and demand_component_identifiers is not None:
        raise ValueError(
            "Pass either demand_component_targets or demand_component_identifiers, not both."
        )
    if demand_components is not None and (
        demand_component_targets is not None or demand_component_identifiers is not None
    ):
        raise ValueError(
            "Pass demand_components, demand_component_targets, or "
            "demand_component_identifiers; not more than one."
        )
    if demand_side_components is not None and (
        demand_components is not None
        or demand_component_targets is not None
        or demand_component_identifiers is not None
    ):
        raise ValueError(
            "Pass demand_side_components, demand_components, demand_component_targets, "
            "or demand_component_identifiers; not more than one."
        )
    if demand_branch_components is not None and (
        demand_side_components is not None
        or demand_components is not None
        or demand_component_targets is not None
        or demand_component_identifiers is not None
    ):
        raise ValueError(
            "Pass demand_branch_components, demand_side_components, "
            "demand_components, demand_component_targets, or "
            "demand_component_identifiers; not more than one."
        )
    if demand is not None and (
        demand_branch_components is not None
        or demand_side_components is not None
        or demand_components is not None
        or demand_component_targets is not None
        or demand_component_identifiers is not None
    ):
        raise ValueError("Pass only one demand component reference list.")
    if operation_equipment_target is not None and operation_equipment_identifier is not None:
        raise ValueError(
            "Pass either operation_equipment_target or operation_equipment_identifier, not both."
        )
    if resolved_loop_target is not None:
        loop_index = _loop_index_from_target(model, resolved_loop_target)
    elif resolved_loop_identifier is not None:
        loop_index = _loop_index_from_identifier(model, str(resolved_loop_identifier))
    else:
        loop_index = 0
    loop = model.HVACSystem.PlantLoops[loop_index]
    if supply is not None:
        supply_components = _components_from_references(model, supply)
    elif supply_branch_components is not None:
        supply_components = _plant_loop_supply_components_from_branch_references(
            model,
            loop.identifier,
            supply_branch_components,
        )
    elif supply_side_components is not None:
        supply_components = _components_from_references(model, supply_side_components)
    elif supply_components is not None:
        supply_components = _components_from_references(model, supply_components)
    elif supply_component_targets is not None:
        supply_components = [
            _component_from_target(model, component_target)
            for component_target in supply_component_targets
        ]
    else:
        supply_components = [
            _component_from_identifier(model, identifier)
            for identifier in (supply_component_identifiers or [])
        ]
    if demand is not None:
        demand_components = _components_from_references(model, demand)
    elif demand_branch_components is not None:
        demand_components = [
            _plant_loop_branch_group(
                identifier=f"{loop.identifier}_demand_branches",
                branches=_plant_loop_branch_groups_from_references(
                    model, demand_branch_components
                ),
            )
        ]
    elif demand_side_components is not None:
        demand_components = _components_from_references(model, demand_side_components)
    elif demand_components is not None:
        demand_components = _components_from_references(model, demand_components)
    elif demand_component_targets is not None:
        demand_components = [
            _component_from_target(model, component_target)
            for component_target in demand_component_targets
        ]
    else:
        demand_components = [
            _component_from_identifier(model, identifier)
            for identifier in (demand_component_identifiers or [])
        ]
    if setpoint_c is not None:
        supply_components.append(
            _scheduled_setpoint(f"{loop.identifier}_setpoint", setpoint_c)
        )
    loop.SupplyComponents = supply_components
    loop.DemandComponents = demand_components
    if operation_equipment_target is not None or operation_equipment_identifier is not None:
        if isinstance(operation_equipment_target, str):
            operation_equipment = _component_from_identifier(model, operation_equipment_target)
        elif operation_equipment_target is not None:
            operation_equipment = _component_from_target(model, operation_equipment_target)
        else:
            operation_equipment = _component_from_identifier(
                model,
                str(operation_equipment_identifier),
            )
        resolved_operation_scheme_type = _resolve_operation_scheme_type(
            operation_scheme_type,
            operation_equipment,
        )
        if resolved_operation_scheme_type == "heating_load":
            _ensure_loop_heating_sizing(loop, setpoint_c=setpoint_c)
            loop.OperationScheme = _heating_operation(
                f"{loop.identifier}_heating_operation",
                operation_equipment,
                operation_upper_limit_w,
            )
        else:
            loop.OperationScheme = _cooling_operation(
                f"{loop.identifier}_cooling_operation",
                operation_equipment,
                operation_upper_limit_w,
            )
    else:
        resolved_operation_scheme_type = None
    model.HVACSystem.PlantLoops[loop_index] = loop
    updated_target, persisted_path, receipt = _save_update(
        garden_root_path=garden_root_path,
        manifest=manifest,
        target=target,
        model=model,
        operation="set_ironbug_plant_loop_components",
        change_summary={"plant_loop_identifier": loop.identifier},
    )
    object_target = _plant_loop_target(
        model_target=updated_target,
        loop=loop,
        index=loop_index,
    )
    return {
        "target": object_target,
        "plant_loop_target": object_target,
        "updated_model_target": updated_target,
        "summary_view": {
            "identifier": loop.identifier,
            "supply_component_count": len(supply_components),
            "demand_component_count": len(demand_components),
            "supply_branch_count": _plant_loop_branch_count(supply_components),
            "supply_branch_lengths": _plant_loop_branch_lengths(supply_components),
            "demand_branch_count": _plant_loop_branch_count(demand_components),
            "demand_branch_lengths": _plant_loop_branch_lengths(demand_components),
            "operation_scheme_present": resolved_operation_scheme_type is not None,
            "operation_scheme_type": resolved_operation_scheme_type,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=f"Updated Ironbug plant loop components: {loop.identifier}",
            details={"persisted_path": persisted_path},
        ),
    }


def component_library_matches(model: Any, model_target: dict[str, Any]) -> list[dict[str, Any]]:
    """Return compact search matches for component-library objects."""

    matches = []
    for identifier, record in _component_library(model).items():
        matches.append(
            {
                "object_type": "component",
                "identifier": identifier,
                "component_type": record["component_type"],
                "source_class": record["source_class"],
                "target": _component_target(
                    model_target=model_target,
                    identifier=identifier,
                    source_class=record["source_class"],
                ),
                "summary_view": {
                    "component_type": record["component_type"],
                    "source_class": record["source_class"],
                },
            }
        )
    return matches


__all__ = [
    "COMPONENT_LIBRARY_KEY",
    "add_ironbug_hvac_component",
    "add_ironbug_plant_loop",
    "component_library_matches",
    "list_ironbug_hvac_component_types",
    "set_ironbug_plant_loop_components",
]
