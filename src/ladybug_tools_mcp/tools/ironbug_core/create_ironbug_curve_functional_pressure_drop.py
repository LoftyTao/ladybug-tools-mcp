"""MCP tool for ib_curvefunctionalpressuredrop."""

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the IB_CurveFunctionalPressureDrop tool."""

    @mcp.tool(
        name="IB_curve_functional_pressure_drop",
        description="Create IB_CurveFunctionalPressureDrop, an OpenStudio/EnergyPlus Curve:Functional:PressureDrop performance curve using pressure drop from minor-loss and friction parameters. This tool authors Ironbug DetailedHVAC curve input only; it does not create equipment, loops, schedules, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.",
        tags={"ironbug", "detailed-hvac", "hvac", "component", "curve", "performance", "equation-fit", "author"},
        timeout=20,
    )
    def create_ironbug_curve_functional_pressure_drop(
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
            Field(description="Stable identifier for the new IB_CurveFunctionalPressureDrop object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        diameter: Annotated[
            float | None,
            Field(description="Equivalent diameter D in metres for Curve:Functional:PressureDrop; maps to Ironbug field Diameter."),
        ] = None,
        minor_loss_coefficient: Annotated[
            float | None,
            Field(description="Minor-loss coefficient K for Curve:Functional:PressureDrop; maps to Ironbug field MinorLossCoefficient."),
        ] = None,
        length: Annotated[
            float | None,
            Field(description="Friction length L in metres for Curve:Functional:PressureDrop; maps to Ironbug field Length."),
        ] = None,
        roughness: Annotated[
            float | None,
            Field(description="Absolute roughness in metres for Curve:Functional:PressureDrop; maps to Ironbug field Roughness."),
        ] = None,
        fixed_friction_factor: Annotated[
            float | None,
            Field(description="Fixed friction factor f for Curve:Functional:PressureDrop; maps to Ironbug field FixedFrictionFactor."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Explicit OpenStudio/EnergyPlus object name for this Curve:Functional:PressureDrop; maps to Ironbug field Name."),
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
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_CurveFunctionalPressureDrop as reviewed performance curve data."""

        from garden.ironbug_core.create_tools import create_source_backed_ironbug_object

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields["Name"] = name
        if diameter is not None:
            source_fields["Diameter"] = diameter
        if minor_loss_coefficient is not None:
            source_fields["MinorLossCoefficient"] = minor_loss_coefficient
        if length is not None:
            source_fields["Length"] = length
        if roughness is not None:
            source_fields["Roughness"] = roughness
        if fixed_friction_factor is not None:
            source_fields["FixedFrictionFactor"] = fixed_friction_factor
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class="IB_CurveFunctionalPressureDrop",
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
