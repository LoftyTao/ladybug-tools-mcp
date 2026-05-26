'MCP tool for detailed_hvac_generator_wind_turbine.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_generator_wind_turbine tool.'

    @mcp.tool(
        name='generator_wind_turbine',
        description=(
            'Create IB_GeneratorWindTurbine, an OpenStudio/EnergyPlus Generator:WindTurbine object for an Ironbug ElectricLoadCenter distribution. Use it for onsite wind generation with rotor, rated power, wind-speed limits, and power-coefficient inputs; this is not a fan, pump, hydronic plant component, or Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'electric', 'electric-equipment', 'generator', 'wind', 'performance', 'author'},
        timeout=20,
    )
    def create_ironbug_generator_wind_turbine(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, for example garden_create['garden_root']."),
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
            Field(description="Stable identifier for the new IB_GeneratorWindTurbine object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target controlling when the wind turbine generator is available.'),
        ] = None,
        rotor_type: Annotated[
            str | None,
            Field(description='Optional wind turbine rotor type.'),
        ] = None,
        power_control: Annotated[
            str | None,
            Field(description='Optional PowerControl value; maps to Ironbug IB_GeneratorWindTurbine field PowerControl.'),
        ] = None,
        rated_rotor_speed: Annotated[
            float | None,
            Field(description='Optional RatedRotorSpeed value; maps to Ironbug IB_GeneratorWindTurbine field RatedRotorSpeed.'),
        ] = None,
        rotor_diameter: Annotated[
            float | None,
            Field(description='Optional RotorDiameter value; maps to Ironbug IB_GeneratorWindTurbine field RotorDiameter.'),
        ] = None,
        overall_height: Annotated[
            float | None,
            Field(description='Optional OverallHeight value; maps to Ironbug IB_GeneratorWindTurbine field OverallHeight.'),
        ] = None,
        numberof_blades: Annotated[
            float | None,
            Field(description='Optional NumberofBlades value; maps to Ironbug IB_GeneratorWindTurbine field NumberofBlades.'),
        ] = None,
        rated_power: Annotated[
            float | None,
            Field(description='Optional rated electric power in W for Generator:WindTurbine.'),
        ] = None,
        rated_wind_speed: Annotated[
            float | None,
            Field(description='Optional rated wind speed in m/s.'),
        ] = None,
        cut_in_wind_speed: Annotated[
            float | None,
            Field(description='Optional CutInWindSpeed value; maps to Ironbug IB_GeneratorWindTurbine field CutInWindSpeed.'),
        ] = None,
        cut_out_wind_speed: Annotated[
            float | None,
            Field(description='Optional CutOutWindSpeed value; maps to Ironbug IB_GeneratorWindTurbine field CutOutWindSpeed.'),
        ] = None,
        fraction_system_efficiency: Annotated[
            float | None,
            Field(description='Optional FractionSystemEfficiency value; maps to Ironbug IB_GeneratorWindTurbine field FractionSystemEfficiency.'),
        ] = None,
        maximum_tip_speed_ratio: Annotated[
            float | None,
            Field(description='Optional MaximumTipSpeedRatio value; maps to Ironbug IB_GeneratorWindTurbine field MaximumTipSpeedRatio.'),
        ] = None,
        maximum_power_coefficient: Annotated[
            float | None,
            Field(description='Optional MaximumPowerCoefficient value; maps to Ironbug IB_GeneratorWindTurbine field MaximumPowerCoefficient.'),
        ] = None,
        annual_local_average_wind_speed: Annotated[
            float | None,
            Field(description='Optional AnnualLocalAverageWindSpeed value; maps to Ironbug IB_GeneratorWindTurbine field AnnualLocalAverageWindSpeed.'),
        ] = None,
        heightfor_local_average_wind_speed: Annotated[
            float | None,
            Field(description='Optional HeightforLocalAverageWindSpeed value; maps to Ironbug IB_GeneratorWindTurbine field HeightforLocalAverageWindSpeed.'),
        ] = None,
        blade_chord_area: Annotated[
            float | None,
            Field(description='Optional BladeChordArea value; maps to Ironbug IB_GeneratorWindTurbine field BladeChordArea.'),
        ] = None,
        blade_drag_coefficient: Annotated[
            float | None,
            Field(description='Optional BladeDragCoefficient value; maps to Ironbug IB_GeneratorWindTurbine field BladeDragCoefficient.'),
        ] = None,
        blade_lift_coefficient: Annotated[
            float | None,
            Field(description='Optional BladeLiftCoefficient value; maps to Ironbug IB_GeneratorWindTurbine field BladeLiftCoefficient.'),
        ] = None,
        power_coefficient_c1: Annotated[
            float | None,
            Field(description='Optional PowerCoefficientC1 value; maps to Ironbug IB_GeneratorWindTurbine field PowerCoefficientC1.'),
        ] = None,
        power_coefficient_c2: Annotated[
            float | None,
            Field(description='Optional PowerCoefficientC2 value; maps to Ironbug IB_GeneratorWindTurbine field PowerCoefficientC2.'),
        ] = None,
        power_coefficient_c3: Annotated[
            float | None,
            Field(description='Optional PowerCoefficientC3 value; maps to Ironbug IB_GeneratorWindTurbine field PowerCoefficientC3.'),
        ] = None,
        power_coefficient_c4: Annotated[
            float | None,
            Field(description='Optional PowerCoefficientC4 value; maps to Ironbug IB_GeneratorWindTurbine field PowerCoefficientC4.'),
        ] = None,
        power_coefficient_c5: Annotated[
            float | None,
            Field(description='Optional PowerCoefficientC5 value; maps to Ironbug IB_GeneratorWindTurbine field PowerCoefficientC5.'),
        ] = None,
        power_coefficient_c6: Annotated[
            float | None,
            Field(description='Optional PowerCoefficientC6 value; maps to Ironbug IB_GeneratorWindTurbine field PowerCoefficientC6.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio name for the wind turbine generator object.'),
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
        """Create IB_GeneratorWindTurbine as a reviewed Ironbug Electrical authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if rotor_type is not None:
            source_fields['RotorType'] = rotor_type
        if power_control is not None:
            source_fields['PowerControl'] = power_control
        if rated_rotor_speed is not None:
            source_fields['RatedRotorSpeed'] = rated_rotor_speed
        if rotor_diameter is not None:
            source_fields['RotorDiameter'] = rotor_diameter
        if overall_height is not None:
            source_fields['OverallHeight'] = overall_height
        if numberof_blades is not None:
            source_fields['NumberofBlades'] = numberof_blades
        if rated_power is not None:
            source_fields['RatedPower'] = rated_power
        if rated_wind_speed is not None:
            source_fields['RatedWindSpeed'] = rated_wind_speed
        if cut_in_wind_speed is not None:
            source_fields['CutInWindSpeed'] = cut_in_wind_speed
        if cut_out_wind_speed is not None:
            source_fields['CutOutWindSpeed'] = cut_out_wind_speed
        if fraction_system_efficiency is not None:
            source_fields['FractionSystemEfficiency'] = fraction_system_efficiency
        if maximum_tip_speed_ratio is not None:
            source_fields['MaximumTipSpeedRatio'] = maximum_tip_speed_ratio
        if maximum_power_coefficient is not None:
            source_fields['MaximumPowerCoefficient'] = maximum_power_coefficient
        if annual_local_average_wind_speed is not None:
            source_fields['AnnualLocalAverageWindSpeed'] = annual_local_average_wind_speed
        if heightfor_local_average_wind_speed is not None:
            source_fields['HeightforLocalAverageWindSpeed'] = heightfor_local_average_wind_speed
        if blade_chord_area is not None:
            source_fields['BladeChordArea'] = blade_chord_area
        if blade_drag_coefficient is not None:
            source_fields['BladeDragCoefficient'] = blade_drag_coefficient
        if blade_lift_coefficient is not None:
            source_fields['BladeLiftCoefficient'] = blade_lift_coefficient
        if power_coefficient_c1 is not None:
            source_fields['PowerCoefficientC1'] = power_coefficient_c1
        if power_coefficient_c2 is not None:
            source_fields['PowerCoefficientC2'] = power_coefficient_c2
        if power_coefficient_c3 is not None:
            source_fields['PowerCoefficientC3'] = power_coefficient_c3
        if power_coefficient_c4 is not None:
            source_fields['PowerCoefficientC4'] = power_coefficient_c4
        if power_coefficient_c5 is not None:
            source_fields['PowerCoefficientC5'] = power_coefficient_c5
        if power_coefficient_c6 is not None:
            source_fields['PowerCoefficientC6'] = power_coefficient_c6
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_GeneratorWindTurbine',
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
