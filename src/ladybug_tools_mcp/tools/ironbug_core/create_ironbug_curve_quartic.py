'MCP tool for detailed_hvac_curve_quartic.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_curve_quartic tool.'

    @mcp.tool(
        name='curve_quartic',
        description=(
            'Create IB_CurveQuartic, an OpenStudio/EnergyPlus Curve:Quartic one-variable fourth-order performance curve with five coefficients. Use it as coefficient-based performance data referenced by HVAC equipment, including fan and flow modifiers that need fourth-order behavior. This tool authors Ironbug DetailedHVAC curve input only; it does not create equipment, loops, schedules, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'curve', 'performance', 'equation-fit', 'author'},
        timeout=20,
    )
    def create_ironbug_curve_quartic(
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
            Field(description="Stable identifier for the new IB_CurveQuartic object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        coefficient1_constant: Annotated[
            float | None,
            Field(
                description="Constant coefficient C1 for the Curve:Quartic equation; maps to Ironbug field Coefficient1Constant."
            ),
        ] = None,
        coefficient2x: Annotated[
            float | None,
            Field(
                description="Coefficient C2 for the x term in the Curve:Quartic equation; maps to Ironbug field Coefficient2x."
            ),
        ] = None,
        coefficient3x_pow2: Annotated[
            str | float | int | bool | None,
            Field(
                description="Coefficient C3 for the x^2 term in the Curve:Quartic equation; maps to Ironbug field Coefficient3xPOW2."
            ),
        ] = None,
        coefficient4x_pow3: Annotated[
            str | float | int | bool | None,
            Field(
                description="Coefficient C4 for the x^3 term in the Curve:Quartic equation; maps to Ironbug field Coefficient4xPOW3."
            ),
        ] = None,
        coefficient5x_pow4: Annotated[
            str | float | int | bool | None,
            Field(
                description="Coefficient C5 for the x^4 term in the Curve:Quartic equation; maps to Ironbug field Coefficient5xPOW4."
            ),
        ] = None,
        minimum_valueofx: Annotated[
            float | None,
            Field(description='Minimum allowed x input before Curve:Quartic evaluation; maps to Ironbug field MinimumValueofx.'),
        ] = None,
        maximum_valueofx: Annotated[
            float | None,
            Field(description='Maximum allowed x input before Curve:Quartic evaluation; maps to Ironbug field MaximumValueofx.'),
        ] = None,
        minimum_curve_output: Annotated[
            float | None,
            Field(description='Minimum allowable evaluated Curve:Quartic output; values below this limit are clipped by the curve object. Maps to Ironbug field MinimumCurveOutput.'),
        ] = None,
        maximum_curve_output: Annotated[
            float | None,
            Field(description='Maximum allowable evaluated Curve:Quartic output; values above this limit are clipped by the curve object. Maps to Ironbug field MaximumCurveOutput.'),
        ] = None,
        input_unit_typefor_x: Annotated[
            str | None,
            Field(description='Unit type metadata for the x input; coefficients are not converted. Maps to Ironbug field InputUnitTypeforX.'),
        ] = None,
        output_unit_type: Annotated[
            str | None,
            Field(description='Unit type metadata for the evaluated curve output; coefficients are not converted. Maps to Ironbug field OutputUnitType.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Explicit OpenStudio/EnergyPlus object name for this Curve:Quartic; maps to Ironbug field Name.'),
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
            Field(description='Optional 5-value coefficient list in Curve:Quartic field order, C1 through C5, as a compact alternative to individual coefficient inputs.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_CurveQuartic as reviewed performance curve data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if coefficient1_constant is not None:
            source_fields['Coefficient1Constant'] = coefficient1_constant
        if coefficient2x is not None:
            source_fields['Coefficient2x'] = coefficient2x
        if coefficient3x_pow2 is not None:
            source_fields['Coefficient3xPOW2'] = coefficient3x_pow2
        if coefficient4x_pow3 is not None:
            source_fields['Coefficient4xPOW3'] = coefficient4x_pow3
        if coefficient5x_pow4 is not None:
            source_fields['Coefficient5xPOW4'] = coefficient5x_pow4
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
        if input_unit_typefor_x is not None:
            source_fields['InputUnitTypeforX'] = input_unit_typefor_x
        if output_unit_type is not None:
            source_fields['OutputUnitType'] = output_unit_type
        if coefficients is not None:
            coefficient_fields = ('Coefficient1Constant', 'Coefficient2x', 'Coefficient3xPOW2', 'Coefficient4xPOW3', 'Coefficient5xPOW4')
            if len(coefficients) != len(coefficient_fields):
                raise ValueError("IB_CurveQuartic coefficients expects 5 values.")
            source_fields.update(dict(zip(coefficient_fields, coefficients)))
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CurveQuartic',
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
