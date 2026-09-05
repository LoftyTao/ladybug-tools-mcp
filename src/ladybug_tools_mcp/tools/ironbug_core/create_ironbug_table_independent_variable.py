"""MCP tool for IB_table_independent_variable."""

from __future__ import annotations

import math
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the IB_table_independent_variable tool."""

    @mcp.tool(
        name="IB_table_independent_variable",
        description=(
            "Create IB_TableIndependentVariable, one sorted independent-variable "
            "dimension for an EnergyPlus/OpenStudio Table:Lookup performance table. "
            "Values must be finite and strictly ascending; use its target in "
            "IB_table_lookup.variable_targets. This tool authors Ironbug "
            "DetailedHVAC input only and does not create a table, equipment, or "
            "run simulation. Returns target, summary_view, persistence_receipt, "
            "and report."
        ),
        tags={
            "ironbug",
            "detailed-hvac",
            "hvac",
            "component",
            "curve",
            "table",
            "performance",
            "author",
        },
        timeout=20,
    )
    def create_ironbug_table_independent_variable(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_create['garden_root']."
                )
            ),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Ironbug model target returned by IB_create_model; "
                    "pass result['target'], not the .ibjson file path."
                )
            ),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the new IB_TableIndependentVariable object."),
        ],
        values: Annotated[
            list[float],
            Field(
                description=(
                    "Finite, strictly ascending values for this table dimension; "
                    "at least two values are required."
                )
            ),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        interpolation_method: Annotated[
            Literal["Linear", "Cubic"] | None,
            Field(description="Interpolation method for values; defaults to Linear."),
        ] = None,
        extrapolation_method: Annotated[
            Literal["Constant", "Linear"] | None,
            Field(description="Extrapolation method outside the value range; defaults to Constant."),
        ] = None,
        minimum_value: Annotated[
            float | None,
            Field(description="Optional lower bound for this independent variable."),
        ] = None,
        maximum_value: Annotated[
            float | None,
            Field(description="Optional upper bound for this independent variable."),
        ] = None,
        normalization_reference_value: Annotated[
            float | None,
            Field(description="Optional normalization reference value for this independent variable."),
        ] = None,
        unit_type: Annotated[
            Literal[
                "Dimensionless",
                "Temperature",
                "VolumetricFlow",
                "MassFlow",
                "Power",
                "Distance",
                "Angle",
            ]
            | None,
            Field(description="OpenStudio unit type for the independent variable."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional OpenStudio object name; defaults to identifier."),
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
        """Create IB_TableIndependentVariable as reviewed table dimension data."""

        if len(values) < 2:
            raise ValueError("IB_TableIndependentVariable values require at least two numbers.")
        if not all(math.isfinite(value) for value in values):
            raise ValueError("IB_TableIndependentVariable values must be finite numbers.")
        if any(right <= left for left, right in zip(values, values[1:])):
            raise ValueError("IB_TableIndependentVariable values must be strictly ascending.")

        from garden.ironbug_core.create_tools import create_source_backed_ironbug_object

        source_fields: dict[str, Any] = {"Values": values}
        source_fields.update(
            {
                key: value
                for key, value in {
                    "InterpolationMethod": interpolation_method,
                    "ExtrapolationMethod": extrapolation_method,
                    "MinimumValue": minimum_value,
                    "MaximumValue": maximum_value,
                    "NormalizationReferenceValue": normalization_reference_value,
                    "UnitType": unit_type,
                    "Name": name,
                }.items()
                if value is not None
            }
        )
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class="IB_TableIndependentVariable",
            identifier=identifier,
            display_name=display_name,
            source_fields={key: value for key, value in source_fields.items() if key != "Values"},
            source_properties={"Values": values},
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
