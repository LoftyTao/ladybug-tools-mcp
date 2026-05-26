'MCP tool for detailed_hvac_curve_sigmoid.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_curve_sigmoid tool.'

    @mcp.tool(
        name='curve_sigmoid',
        description=(
            'Create IB_CurveSigmoid, an OpenStudio/EnergyPlus Curve:Sigmoid one-variable performance curve with five coefficients. Use it as coefficient-based performance data referenced by HVAC equipment, including fan component-model normalized dimensionless airflow maps. This tool authors Ironbug DetailedHVAC curve input only; it does not create equipment, loops, schedules, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'curve', 'performance', 'equation-fit', 'fan', 'author'},
        timeout=20,
    )
    def create_ironbug_curve_sigmoid(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
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
            Field(description="Stable identifier for the new IB_CurveSigmoid object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        coefficient1_c1: Annotated[
            float | None,
            Field(
                description="Coefficient C1 for the Curve:Sigmoid equation; maps to Ironbug field Coefficient1C1."
            ),
        ] = None,
        coefficient2_c2: Annotated[
            float | None,
            Field(
                description="Coefficient C2 for the Curve:Sigmoid equation; maps to Ironbug field Coefficient2C2."
            ),
        ] = None,
        coefficient3_c3: Annotated[
            float | None,
            Field(
                description="Coefficient C3 for the Curve:Sigmoid equation; maps to Ironbug field Coefficient3C3."
            ),
        ] = None,
        coefficient4_c4: Annotated[
            float | None,
            Field(
                description="Coefficient C4 for the Curve:Sigmoid equation; maps to Ironbug field Coefficient4C4."
            ),
        ] = None,
        coefficient5_c5: Annotated[
            float | None,
            Field(
                description="Coefficient C5 for the Curve:Sigmoid equation; maps to Ironbug field Coefficient5C5."
            ),
        ] = None,
        minimum_valueofx: Annotated[
            float | None,
            Field(description='Minimum allowed x input before Curve:Sigmoid evaluation; maps to Ironbug field MinimumValueofx.'),
        ] = None,
        maximum_valueofx: Annotated[
            float | None,
            Field(description='Maximum allowed x input before Curve:Sigmoid evaluation; maps to Ironbug field MaximumValueofx.'),
        ] = None,
        minimum_curve_output: Annotated[
            float | None,
            Field(description='Minimum allowable evaluated Curve:Sigmoid output; values below this limit are clipped by the curve object. Maps to Ironbug field MinimumCurveOutput.'),
        ] = None,
        maximum_curve_output: Annotated[
            float | None,
            Field(description='Maximum allowable evaluated Curve:Sigmoid output; values above this limit are clipped by the curve object. Maps to Ironbug field MaximumCurveOutput.'),
        ] = None,
        input_unit_typeforx: Annotated[
            str | None,
            Field(description='Unit type metadata for the x input; coefficients are not converted. Maps to Ironbug field InputUnitTypeforx.'),
        ] = None,
        output_unit_type: Annotated[
            str | None,
            Field(description='Unit type metadata for the evaluated curve output; coefficients are not converted. Maps to Ironbug field OutputUnitType.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Explicit OpenStudio/EnergyPlus object name for this Curve:Sigmoid; maps to Ironbug field Name.'),
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
        coefficients: Annotated[
            list[float] | None,
            Field(description='Optional 5-value coefficient list in Curve:Sigmoid field order, C1 through C5, as a compact alternative to individual coefficient inputs.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_CurveSigmoid as reviewed fan performance curve data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if coefficient1_c1 is not None:
            source_fields['Coefficient1C1'] = coefficient1_c1
        if coefficient2_c2 is not None:
            source_fields['Coefficient2C2'] = coefficient2_c2
        if coefficient3_c3 is not None:
            source_fields['Coefficient3C3'] = coefficient3_c3
        if coefficient4_c4 is not None:
            source_fields['Coefficient4C4'] = coefficient4_c4
        if coefficient5_c5 is not None:
            source_fields['Coefficient5C5'] = coefficient5_c5
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if minimum_valueofx is not None:
            source_fields['MinimumValueofx'] = minimum_valueofx
        if maximum_valueofx is not None:
            source_fields['MaximumValueofx'] = maximum_valueofx
        if minimum_curve_output is not None:
            source_fields['MinimumCurveOutput'] = minimum_curve_output
        if maximum_curve_output is not None:
            source_fields['MaximumCurveOutput'] = maximum_curve_output
        if input_unit_typeforx is not None:
            source_fields['InputUnitTypeforx'] = input_unit_typeforx
        if output_unit_type is not None:
            source_fields['OutputUnitType'] = output_unit_type
        if coefficients is not None:
            coefficient_fields = ('Coefficient1C1', 'Coefficient2C2', 'Coefficient3C3', 'Coefficient4C4', 'Coefficient5C5')
            if len(coefficients) != len(coefficient_fields):
                raise ValueError("IB_CurveSigmoid coefficients expects 5 values.")
            source_fields.update(dict(zip(coefficient_fields, coefficients)))
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CurveSigmoid',
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
