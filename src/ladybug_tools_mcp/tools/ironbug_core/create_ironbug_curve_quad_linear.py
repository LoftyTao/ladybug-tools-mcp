"""MCP tool for ib_curvequadlinear."""

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the IB_CurveQuadLinear tool."""

    @mcp.tool(
        name="IB_curve_quad_linear",
        description="Create IB_CurveQuadLinear, an OpenStudio/EnergyPlus Curve:QuadLinear performance curve using linear performance function of w, x, y, and z. This tool authors Ironbug DetailedHVAC curve input only; it does not create equipment, loops, schedules, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.",
        tags={"ironbug", "detailed-hvac", "hvac", "component", "curve", "performance", "equation-fit", "author"},
        timeout=20,
    )
    def create_ironbug_curve_quad_linear(
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
            Field(description="Stable identifier for the new IB_CurveQuadLinear object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        coefficient1_constant: Annotated[
            float | None,
            Field(description="C1 for Curve:QuadLinear; maps to Ironbug field Coefficient1Constant."),
        ] = None,
        coefficient2w: Annotated[
            float | None,
            Field(description="C2 for Curve:QuadLinear; maps to Ironbug field Coefficient2w."),
        ] = None,
        coefficient3x: Annotated[
            float | None,
            Field(description="C3 for Curve:QuadLinear; maps to Ironbug field Coefficient3x."),
        ] = None,
        coefficient4y: Annotated[
            float | None,
            Field(description="C4 for Curve:QuadLinear; maps to Ironbug field Coefficient4y."),
        ] = None,
        coefficient5z: Annotated[
            float | None,
            Field(description="C5 for Curve:QuadLinear; maps to Ironbug field Coefficient5z."),
        ] = None,
        minimum_valueofw: Annotated[
            float | None,
            Field(description="Minimum w for Curve:QuadLinear; maps to Ironbug field MinimumValueofw."),
        ] = None,
        maximum_valueofw: Annotated[
            float | None,
            Field(description="Maximum w for Curve:QuadLinear; maps to Ironbug field MaximumValueofw."),
        ] = None,
        minimum_valueofx: Annotated[
            float | None,
            Field(description="Minimum x for Curve:QuadLinear; maps to Ironbug field MinimumValueofx."),
        ] = None,
        maximum_valueofx: Annotated[
            float | None,
            Field(description="Maximum x for Curve:QuadLinear; maps to Ironbug field MaximumValueofx."),
        ] = None,
        minimum_valueofy: Annotated[
            float | None,
            Field(description="Minimum y for Curve:QuadLinear; maps to Ironbug field MinimumValueofy."),
        ] = None,
        maximum_valueofy: Annotated[
            float | None,
            Field(description="Maximum y for Curve:QuadLinear; maps to Ironbug field MaximumValueofy."),
        ] = None,
        minimum_valueofz: Annotated[
            float | None,
            Field(description="Minimum z for Curve:QuadLinear; maps to Ironbug field MinimumValueofz."),
        ] = None,
        maximum_valueofz: Annotated[
            float | None,
            Field(description="Maximum z for Curve:QuadLinear; maps to Ironbug field MaximumValueofz."),
        ] = None,
        minimum_curve_output: Annotated[
            float | None,
            Field(description="Minimum allowable evaluated curve output; maps to Ironbug field MinimumCurveOutput."),
        ] = None,
        maximum_curve_output: Annotated[
            float | None,
            Field(description="Maximum allowable evaluated curve output; maps to Ironbug field MaximumCurveOutput."),
        ] = None,
        input_unit_typeforw: Annotated[
            str | None,
            Field(description="w input unit type for Curve:QuadLinear; maps to Ironbug field InputUnitTypeforw."),
        ] = None,
        input_unit_typeforx: Annotated[
            str | None,
            Field(description="x input unit type for Curve:QuadLinear; maps to Ironbug field InputUnitTypeforx."),
        ] = None,
        input_unit_typefory: Annotated[
            str | None,
            Field(description="y input unit type for Curve:QuadLinear; maps to Ironbug field InputUnitTypefory."),
        ] = None,
        input_unit_typeforz: Annotated[
            str | None,
            Field(description="z input unit type for Curve:QuadLinear; maps to Ironbug field InputUnitTypeforz."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Explicit OpenStudio/EnergyPlus object name for this Curve:QuadLinear; maps to Ironbug field Name."),
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
            Field(description="Optional 5-value coefficient list in Curve:QuadLinear field order, C1 through C5, as a compact alternative to individual coefficient inputs."),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_CurveQuadLinear as reviewed performance curve data."""

        from garden.ironbug_core.create_tools import create_source_backed_ironbug_object

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields["Name"] = name
        if coefficient1_constant is not None:
            source_fields["Coefficient1Constant"] = coefficient1_constant
        if coefficient2w is not None:
            source_fields["Coefficient2w"] = coefficient2w
        if coefficient3x is not None:
            source_fields["Coefficient3x"] = coefficient3x
        if coefficient4y is not None:
            source_fields["Coefficient4y"] = coefficient4y
        if coefficient5z is not None:
            source_fields["Coefficient5z"] = coefficient5z
        if minimum_valueofw is not None:
            source_fields["MinimumValueofw"] = minimum_valueofw
        if maximum_valueofw is not None:
            source_fields["MaximumValueofw"] = maximum_valueofw
        if minimum_valueofx is not None:
            source_fields["MinimumValueofx"] = minimum_valueofx
        if maximum_valueofx is not None:
            source_fields["MaximumValueofx"] = maximum_valueofx
        if minimum_valueofy is not None:
            source_fields["MinimumValueofy"] = minimum_valueofy
        if maximum_valueofy is not None:
            source_fields["MaximumValueofy"] = maximum_valueofy
        if minimum_valueofz is not None:
            source_fields["MinimumValueofz"] = minimum_valueofz
        if maximum_valueofz is not None:
            source_fields["MaximumValueofz"] = maximum_valueofz
        if minimum_curve_output is not None:
            source_fields["MinimumCurveOutput"] = minimum_curve_output
        if maximum_curve_output is not None:
            source_fields["MaximumCurveOutput"] = maximum_curve_output
        if input_unit_typeforw is not None:
            source_fields["InputUnitTypeforw"] = input_unit_typeforw
        if input_unit_typeforx is not None:
            source_fields["InputUnitTypeforx"] = input_unit_typeforx
        if input_unit_typefory is not None:
            source_fields["InputUnitTypefory"] = input_unit_typefory
        if input_unit_typeforz is not None:
            source_fields["InputUnitTypeforz"] = input_unit_typeforz
        if coefficients is not None:
            coefficient_fields = ("Coefficient1Constant", "Coefficient2w", "Coefficient3x", "Coefficient4y", "Coefficient5z")
            if len(coefficients) != len(coefficient_fields):
                raise ValueError("IB_CurveQuadLinear coefficients expects 5 values.")
            source_fields.update(dict(zip(coefficient_fields, coefficients)))
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class="IB_CurveQuadLinear",
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
