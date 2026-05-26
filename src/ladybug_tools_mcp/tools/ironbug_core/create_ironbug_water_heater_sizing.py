'MCP tool for detailed_hvac_water_heater_sizing.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_water_heater_sizing tool.'

    @mcp.tool(
        name='water_heater_sizing',
        description=(
            'Create IB_WaterHeaterSizing, the Ironbug and EnergyPlus WaterHeater:Sizing child used by WaterHeater:Mixed or stratified tanks to autosize tank volume and heater capacity. Use it as sizing metadata for a water heater, not as a water heater, plant loop, water-use fixture, or result reader. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'sizing', 'water-heater', 'service-hot-water', 'storage', 'author'},
        timeout=20,
    )
    def create_ironbug_water_heater_sizing(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json for the Ironbug model."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Ironbug model target returned by detailed_hvac_create_model; '
                    "pass result['target'], not the .ibjson file path."
                )
            ),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the new IB_WaterHeaterSizing object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        design_mode: Annotated[
            str | None,
            Field(description='Optional WaterHeater:Sizing design mode, such as PeakDraw, PerPerson, PerFloorArea, PerUnit, or PerSolarCollectorArea.'),
        ] = None,
        time_storage_can_meet_peak_draw: Annotated[
            float | None,
            Field(description='Optional hours that storage can meet peak draw when DesignMode is PeakDraw.'),
        ] = None,
        timefor_tank_recovery: Annotated[
            float | None,
            Field(description='Optional TimeforTankRecovery value; maps to Ironbug IB_WaterHeaterSizing field TimeforTankRecovery.'),
        ] = None,
        nominal_tank_volumefor_autosizing_plant_connections: Annotated[
            float | None,
            Field(description='Optional NominalTankVolumeforAutosizingPlantConnections value; maps to Ironbug IB_WaterHeaterSizing field NominalTankVolumeforAutosizingPlantConnections.'),
        ] = None,
        numberof_bedrooms: Annotated[
            int | None,
            Field(description='Optional NumberofBedrooms value; maps to Ironbug IB_WaterHeaterSizing field NumberofBedrooms.'),
        ] = None,
        numberof_bathrooms: Annotated[
            int | None,
            Field(description='Optional NumberofBathrooms value; maps to Ironbug IB_WaterHeaterSizing field NumberofBathrooms.'),
        ] = None,
        storage_capacityper_person: Annotated[
            float | None,
            Field(description='Optional StorageCapacityperPerson value; maps to Ironbug IB_WaterHeaterSizing field StorageCapacityperPerson.'),
        ] = None,
        recovery_capacityper_person: Annotated[
            float | None,
            Field(description='Optional RecoveryCapacityperPerson value; maps to Ironbug IB_WaterHeaterSizing field RecoveryCapacityperPerson.'),
        ] = None,
        storage_capacityper_floor_area: Annotated[
            float | None,
            Field(description='Optional StorageCapacityperFloorArea value; maps to Ironbug IB_WaterHeaterSizing field StorageCapacityperFloorArea.'),
        ] = None,
        recovery_capacityper_floor_area: Annotated[
            float | None,
            Field(description='Optional RecoveryCapacityperFloorArea value; maps to Ironbug IB_WaterHeaterSizing field RecoveryCapacityperFloorArea.'),
        ] = None,
        numberof_units: Annotated[
            float | None,
            Field(description='Optional NumberofUnits value; maps to Ironbug IB_WaterHeaterSizing field NumberofUnits.'),
        ] = None,
        storage_capacityper_unit: Annotated[
            float | None,
            Field(description='Optional StorageCapacityperUnit value; maps to Ironbug IB_WaterHeaterSizing field StorageCapacityperUnit.'),
        ] = None,
        recovery_capacity_per_unit: Annotated[
            float | None,
            Field(description='Optional RecoveryCapacityPerUnit value; maps to Ironbug IB_WaterHeaterSizing field RecoveryCapacityPerUnit.'),
        ] = None,
        storage_capacityper_collector_area: Annotated[
            float | None,
            Field(description='Optional StorageCapacityperCollectorArea value; maps to Ironbug IB_WaterHeaterSizing field StorageCapacityperCollectorArea.'),
        ] = None,
        height_aspect_ratio: Annotated[
            float | None,
            Field(description='Optional HeightAspectRatio value; maps to Ironbug IB_WaterHeaterSizing field HeightAspectRatio.'),
        ] = None,
        output_variable_names: Annotated[
            list[str] | None,
            Field(
                description="Optional explicit Ironbug output variable names for this object."
            ),
        ] = None,
        output_reporting_frequency: Annotated[
            Literal["Detail", "Hourly", "Daily", "Monthly", "RunPeriod"],
            Field(description="Reporting frequency used for output_variable_names."),
        ] = "Hourly",
        ems_sensor_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional IB_EnergyManagementSystemSensor targets for CustomSensors."),
        ] = None,
        ems_actuator_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional IB_EnergyManagementSystemActuator targets for CustomActuators."),
        ] = None,
        ems_internal_variable_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_EnergyManagementSystemInternalVariable targets for CustomInternalVariables."
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create Ironbug water-heater sizing metadata."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if design_mode is not None:
            source_fields['DesignMode'] = design_mode
        if time_storage_can_meet_peak_draw is not None:
            source_fields['TimeStorageCanMeetPeakDraw'] = time_storage_can_meet_peak_draw
        if timefor_tank_recovery is not None:
            source_fields['TimeforTankRecovery'] = timefor_tank_recovery
        if nominal_tank_volumefor_autosizing_plant_connections is not None:
            source_fields['NominalTankVolumeforAutosizingPlantConnections'] = nominal_tank_volumefor_autosizing_plant_connections
        if numberof_bedrooms is not None:
            source_fields['NumberofBedrooms'] = numberof_bedrooms
        if numberof_bathrooms is not None:
            source_fields['NumberofBathrooms'] = numberof_bathrooms
        if storage_capacityper_person is not None:
            source_fields['StorageCapacityperPerson'] = storage_capacityper_person
        if recovery_capacityper_person is not None:
            source_fields['RecoveryCapacityperPerson'] = recovery_capacityper_person
        if storage_capacityper_floor_area is not None:
            source_fields['StorageCapacityperFloorArea'] = storage_capacityper_floor_area
        if recovery_capacityper_floor_area is not None:
            source_fields['RecoveryCapacityperFloorArea'] = recovery_capacityper_floor_area
        if numberof_units is not None:
            source_fields['NumberofUnits'] = numberof_units
        if storage_capacityper_unit is not None:
            source_fields['StorageCapacityperUnit'] = storage_capacityper_unit
        if recovery_capacity_per_unit is not None:
            source_fields['RecoveryCapacityPerUnit'] = recovery_capacity_per_unit
        if storage_capacityper_collector_area is not None:
            source_fields['StorageCapacityperCollectorArea'] = storage_capacityper_collector_area
        if height_aspect_ratio is not None:
            source_fields['HeightAspectRatio'] = height_aspect_ratio
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_WaterHeaterSizing',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
