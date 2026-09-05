"""MCP tool for ib_curvequadraticlinear."""

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the IB_CurveQuadraticLinear tool."""

    @mcp.tool(
        name="IB_curve_quadratic_linear",
        description="Create IB_CurveQuadraticLinear, an OpenStudio/EnergyPlus Curve:QuadraticLinear performance curve using z = (C1 + C2*x + C3*x^2) + (C4 + C5*x + C6*x^2)*y. This tool authors Ironbug DetailedHVAC curve input only; it does not create equipment, loops, schedules, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.",
        tags={"ironbug", "detailed-hvac", "hvac", "component", "curve", "performance", "equation-fit", "author"},
        timeout=20,
    )
    def create_ironbug_curve_quadratic_linear(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_create['garden_root']."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(description="Required Ironbug model target returned by IB_create_model; pass result['target'], not the .ibjson file path."),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the new IB_CurveQuadraticLinear object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        coefficient1_constant: Annotated[
            float | None,
            Field(description="C1 for Curve:QuadraticLinear; maps to Ironbug field Coefficient1Constant."),
        ] = None,
        coefficient2x: Annotated[
            float | None,
            Field(description="C2 for Curve:QuadraticLinear; maps to Ironbug field Coefficient2x."),
        ] = None,
        coefficient3x_pow2: Annotated[
            float | None,
            Field(description="C3 for Curve:QuadraticLinear; maps to Ironbug field Coefficient3xPOW2."),
        ] = None,
        coefficient4y: Annotated[
            float | None,
            Field(description="C4 for Curve:QuadraticLinear; maps to Ironbug field Coefficient4y."),
        ] = None,
        coefficient5x_timesy: Annotated[
            float | None,
            Field(description="C5 for Curve:QuadraticLinear; maps to Ironbug field Coefficient5xTIMESY."),
        ] = None,
        coefficient6x_pow2_timesy: Annotated[
            float | None,
            Field(description="C6 for Curve:QuadraticLinear; maps to Ironbug field Coefficient6xPOW2TIMESY."),
        ] = None,
        minimum_valueofx: Annotated[
            float | None,
            Field(description="Minimum x for Curve:QuadraticLinear; maps to Ironbug field MinimumValueofx."),
        ] = None,
        maximum_valueofx: Annotated[
            float | None,
            Field(description="Maximum x for Curve:QuadraticLinear; maps to Ironbug field MaximumValueofx."),
        ] = None,
        minimum_valueofy: Annotated[
            float | None,
            Field(description="Minimum y for Curve:QuadraticLinear; maps to Ironbug field MinimumValueofy."),
        ] = None,
        maximum_valueofy: Annotated[
            float | None,
            Field(description="Maximum y for Curve:QuadraticLinear; maps to Ironbug field MaximumValueofy."),
        ] = None,
        minimum_curve_output: Annotated[
            float | None,
            Field(description="Minimum allowable evaluated curve output; maps to Ironbug field MinimumCurveOutput."),
        ] = None,
        maximum_curve_output: Annotated[
            float | None,
            Field(description="Maximum allowable evaluated curve output; maps to Ironbug field MaximumCurveOutput."),
        ] = None,
        input_unit_typefor_x: Annotated[
            str | None,
            Field(description="x input unit type for Curve:QuadraticLinear; maps to Ironbug field InputUnitTypeforX."),
        ] = None,
        input_unit_typefor_y: Annotated[
            str | None,
            Field(description="y input unit type for Curve:QuadraticLinear; maps to Ironbug field InputUnitTypeforY."),
        ] = None,
        output_unit_type: Annotated[
            str | None,
            Field(description="output unit type for Curve:QuadraticLinear; maps to Ironbug field OutputUnitType."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Explicit OpenStudio/EnergyPlus object name for this Curve:QuadraticLinear; maps to Ironbug field Name."),
        ] = None,
        output_variable_names: Annotated[
            list[str] | None,
            Field(description="Optional explicit Ironbug output variable names for this object."),
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
            Field(description="Optional IB_EnergyManagementSystemInternalVariable targets for CustomInternalVariables."),
        ] = None,
        coefficients: Annotated[
            list[float] | None,
            Field(description="Optional 6-value coefficient list in Curve:QuadraticLinear field order, C1 through C6, as a compact alternative to individual coefficient inputs."),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_CurveQuadraticLinear as reviewed performance curve data."""

        from garden.ironbug_core.create_tools import create_source_backed_ironbug_object

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields["Name"] = name
        if coefficient1_constant is not None:
            source_fields["Coefficient1Constant"] = coefficient1_constant
        if coefficient2x is not None:
            source_fields["Coefficient2x"] = coefficient2x
        if coefficient3x_pow2 is not None:
            source_fields["Coefficient3xPOW2"] = coefficient3x_pow2
        if coefficient4y is not None:
            source_fields["Coefficient4y"] = coefficient4y
        if coefficient5x_timesy is not None:
            source_fields["Coefficient5xTIMESY"] = coefficient5x_timesy
        if coefficient6x_pow2_timesy is not None:
            source_fields["Coefficient6xPOW2TIMESY"] = coefficient6x_pow2_timesy
        if minimum_valueofx is not None:
            source_fields["MinimumValueofx"] = minimum_valueofx
        if maximum_valueofx is not None:
            source_fields["MaximumValueofx"] = maximum_valueofx
        if minimum_valueofy is not None:
            source_fields["MinimumValueofy"] = minimum_valueofy
        if maximum_valueofy is not None:
            source_fields["MaximumValueofy"] = maximum_valueofy
        if minimum_curve_output is not None:
            source_fields["MinimumCurveOutput"] = minimum_curve_output
        if maximum_curve_output is not None:
            source_fields["MaximumCurveOutput"] = maximum_curve_output
        if input_unit_typefor_x is not None:
            source_fields["InputUnitTypeforX"] = input_unit_typefor_x
        if input_unit_typefor_y is not None:
            source_fields["InputUnitTypeforY"] = input_unit_typefor_y
        if output_unit_type is not None:
            source_fields["OutputUnitType"] = output_unit_type
        if coefficients is not None:
            coefficient_fields = ("Coefficient1Constant", "Coefficient2x", "Coefficient3xPOW2", "Coefficient4y", "Coefficient5xTIMESY", "Coefficient6xPOW2TIMESY")
            if len(coefficients) != len(coefficient_fields):
                raise ValueError("IB_CurveQuadraticLinear coefficients expects 6 values.")
            source_fields.update(dict(zip(coefficient_fields, coefficients)))
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class="IB_CurveQuadraticLinear",
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
