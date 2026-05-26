'MCP tool for detailed_hvac_solar_collector_performance_flat_plate.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_solar_collector_performance_flat_plate tool.'

    @mcp.tool(
        name='solar_collector_performance_flat_plate',
        description=(
            'Create IB_SolarCollectorPerformanceFlatPlate, the Ironbug and EnergyPlus SolarCollectorPerformance:FlatPlate object. It stores SRCC/ASHRAE-style thermal efficiency and incident-angle modifier coefficients for a SolarCollector:FlatPlate:Water child target. This is performance data, not a collector surface, plant-loop component, PV module, or Energy result reader. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'performance', 'solar-collector', 'solar-thermal', 'author'},
        timeout=20,
    )
    def create_ironbug_solar_collector_performance_flat_plate(
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
            Field(description="Stable identifier for the new IB_SolarCollectorPerformanceFlatPlate object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        gross_area: Annotated[
            float | None,
            Field(description='Optional tested collector gross area in m2.'),
        ] = None,
        test_fluid: Annotated[
            str | None,
            Field(description='Optional TestFluid value; maps to Ironbug IB_SolarCollectorPerformanceFlatPlate field TestFluid.'),
        ] = None,
        test_flow_rate: Annotated[
            float | None,
            Field(description='Optional test flow rate in m3/s used for the performance coefficients.'),
        ] = None,
        test_correlation_type: Annotated[
            str | None,
            Field(description='Optional TestCorrelationType value; maps to Ironbug IB_SolarCollectorPerformanceFlatPlate field TestCorrelationType.'),
        ] = None,
        coefficient1of_efficiency_equation: Annotated[
            float | None,
            Field(description='Optional Coefficient1ofEfficiencyEquation value; maps to Ironbug IB_SolarCollectorPerformanceFlatPlate field Coefficient1ofEfficiencyEquation.'),
        ] = None,
        coefficient2of_efficiency_equation: Annotated[
            float | None,
            Field(description='Optional Coefficient2ofEfficiencyEquation value; maps to Ironbug IB_SolarCollectorPerformanceFlatPlate field Coefficient2ofEfficiencyEquation.'),
        ] = None,
        coefficient3of_efficiency_equation: Annotated[
            float | None,
            Field(description='Optional Coefficient3ofEfficiencyEquation value; maps to Ironbug IB_SolarCollectorPerformanceFlatPlate field Coefficient3ofEfficiencyEquation.'),
        ] = None,
        coefficient2of_incident_angle_modifier: Annotated[
            float | None,
            Field(description='Optional Coefficient2ofIncidentAngleModifier value; maps to Ironbug IB_SolarCollectorPerformanceFlatPlate field Coefficient2ofIncidentAngleModifier.'),
        ] = None,
        coefficient3of_incident_angle_modifier: Annotated[
            float | None,
            Field(description='Optional Coefficient3ofIncidentAngleModifier value; maps to Ironbug IB_SolarCollectorPerformanceFlatPlate field Coefficient3ofIncidentAngleModifier.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_SolarCollectorPerformanceFlatPlate field Name.'),
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
        """Create flat-plate solar collector performance data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if gross_area is not None:
            source_fields['GrossArea'] = gross_area
        if test_fluid is not None:
            source_fields['TestFluid'] = test_fluid
        if test_flow_rate is not None:
            source_fields['TestFlowRate'] = test_flow_rate
        if test_correlation_type is not None:
            source_fields['TestCorrelationType'] = test_correlation_type
        if coefficient1of_efficiency_equation is not None:
            source_fields['Coefficient1ofEfficiencyEquation'] = coefficient1of_efficiency_equation
        if coefficient2of_efficiency_equation is not None:
            source_fields['Coefficient2ofEfficiencyEquation'] = coefficient2of_efficiency_equation
        if coefficient3of_efficiency_equation is not None:
            source_fields['Coefficient3ofEfficiencyEquation'] = coefficient3of_efficiency_equation
        if coefficient2of_incident_angle_modifier is not None:
            source_fields['Coefficient2ofIncidentAngleModifier'] = coefficient2of_incident_angle_modifier
        if coefficient3of_incident_angle_modifier is not None:
            source_fields['Coefficient3ofIncidentAngleModifier'] = coefficient3of_incident_angle_modifier
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SolarCollectorPerformanceFlatPlate',
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
