"""MCP tool for IB_table_lookup."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the IB_table_lookup tool."""

    @mcp.tool(
        name="IB_table_lookup",
        description=(
            "Create IB_TableLookup, an EnergyPlus/OpenStudio Table:Lookup "
            "performance curve with typed independent-variable targets and a "
            "flattened output-value table. output_values must contain exactly the "
            "product of the supplied variable dimensions; this tool authors "
            "Ironbug DetailedHVAC input only and does not create equipment or run "
            "simulation. Returns target, summary_view, persistence_receipt, and "
            "report."
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
    def create_ironbug_table_lookup(
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
            Field(description="Stable identifier for the new IB_TableLookup object."),
        ],
        variable_targets: Annotated[
            list[dict[str, Any] | str],
            Field(
                description=(
                    "One or more IB_TableIndependentVariable targets, ordered by "
                    "table dimension."
                )
            ),
        ],
        output_values: Annotated[
            list[float],
            Field(
                description=(
                    "Finite flattened table outputs in the order of the supplied "
                    "independent variables. Its count must equal the product of "
                    "their value counts."
                )
            ),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        normalization_method: Annotated[
            Literal["None", "DivisorOnly", "AutomaticWithDivisor"] | None,
            Field(description="OpenStudio table normalization method; defaults to None."),
        ] = None,
        normalization_divisor: Annotated[
            float | None,
            Field(description="Optional normalization divisor for the table outputs."),
        ] = None,
        minimum_output: Annotated[
            float | None,
            Field(description="Optional lower bound for table outputs."),
        ] = None,
        maximum_output: Annotated[
            float | None,
            Field(description="Optional upper bound for table outputs."),
        ] = None,
        output_unit_type: Annotated[
            Literal["Dimensionless", "Capacity", "Power"] | None,
            Field(description="OpenStudio unit type for table outputs."),
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
        """Create IB_TableLookup as reviewed tabulated performance data."""

        from garden.ironbug_core.create_tools import (
            create_source_backed_ironbug_object,
            validate_ironbug_table_lookup_dimensions,
        )

        validate_ironbug_table_lookup_dimensions(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            variable_targets=variable_targets,
            output_values=output_values,
        )

        source_fields: dict[str, Any] = {
            key: value
            for key, value in {
                "NormalizationMethod": normalization_method,
                "NormalizationDivisor": normalization_divisor,
                "MinimumOutput": minimum_output,
                "MaximumOutput": maximum_output,
                "OutputUnitType": output_unit_type,
                "Name": name,
            }.items()
            if value is not None
        }
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class="IB_TableLookup",
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_properties={"OutputValues": output_values},
            source_property_targets={"Variables": variable_targets},
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
