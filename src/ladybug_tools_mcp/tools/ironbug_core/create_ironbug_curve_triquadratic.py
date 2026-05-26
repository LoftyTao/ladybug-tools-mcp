'MCP tool for detailed_hvac_curve_triquadratic.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_curve_triquadratic tool.'

    @mcp.tool(
        name='curve_triquadratic',
        description=(
            'Create IB_CurveTriquadratic, an OpenStudio/EnergyPlus Curve:Triquadratic three-variable performance curve with 27 coefficients. Use it as coefficient-based performance data referenced by HVAC equipment, such as microturbine or thermal-storage modifiers that depend on x, y, and z variables. This tool authors Ironbug DetailedHVAC curve input only; it does not create equipment, loops, schedules, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'curve', 'performance', 'equation-fit', 'author'},
        timeout=20,
    )
    def create_ironbug_curve_triquadratic(
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
            Field(description="Stable identifier for the new IB_CurveTriquadratic object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        coefficient1_constant: Annotated[
            float | None,
            Field(description='Constant coefficient C1 for the Curve:Triquadratic equation; maps to Ironbug field Coefficient1Constant.'),
        ] = None,
        coefficient2x_pow2: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C2 for the x^2 term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient2xPOW2.'),
        ] = None,
        coefficient3x: Annotated[
            float | None,
            Field(description='Coefficient C3 for the x term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient3x.'),
        ] = None,
        coefficient4y_pow2: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C4 for the y^2 term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient4yPOW2.'),
        ] = None,
        coefficient5y: Annotated[
            float | None,
            Field(description='Coefficient C5 for the y term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient5y.'),
        ] = None,
        coefficient6z_pow2: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C6 for the z^2 term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient6zPOW2.'),
        ] = None,
        coefficient7z: Annotated[
            float | None,
            Field(description='Coefficient C7 for the z term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient7z.'),
        ] = None,
        coefficient8x_pow2_timesypow2: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C8 for the x^2*y^2 term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient8xPOW2TIMESYPOW2.'),
        ] = None,
        coefficient9x_timesy: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C9 for the x*y term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient9xTIMESY.'),
        ] = None,
        coefficient10x_timesypow2: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C10 for the x*y^2 term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient10xTIMESYPOW2.'),
        ] = None,
        coefficient11x_pow2_timesy: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C11 for the x^2*y term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient11xPOW2TIMESY.'),
        ] = None,
        coefficient12x_pow2_timeszpow2: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C12 for the x^2*z^2 term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient12xPOW2TIMESZPOW2.'),
        ] = None,
        coefficient13x_timesz: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C13 for the x*z term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient13xTIMESZ.'),
        ] = None,
        coefficient14x_timeszpow2: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C14 for the x*z^2 term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient14xTIMESZPOW2.'),
        ] = None,
        coefficient15x_pow2_timesz: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C15 for the x^2*z term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient15xPOW2TIMESZ.'),
        ] = None,
        coefficient16y_pow2_timeszpow2: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C16 for the y^2*z^2 term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient16yPOW2TIMESZPOW2.'),
        ] = None,
        coefficient17y_timesz: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C17 for the y*z term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient17yTIMESZ.'),
        ] = None,
        coefficient18y_timeszpow2: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C18 for the y*z^2 term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient18yTIMESZPOW2.'),
        ] = None,
        coefficient19y_pow2_timesz: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C19 for the y^2*z term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient19yPOW2TIMESZ.'),
        ] = None,
        coefficient20x_pow2_timesypow2_timeszpow2: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C20 for the x^2*y^2*z^2 term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient20xPOW2TIMESYPOW2TIMESZPOW2.'),
        ] = None,
        coefficient21x_pow2_timesypow2_timesz: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C21 for the x^2*y^2*z term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient21xPOW2TIMESYPOW2TIMESZ.'),
        ] = None,
        coefficient22x_pow2_timesytimeszpow2: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C22 for the x^2*y*z^2 term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient22xPOW2TIMESYTIMESZPOW2.'),
        ] = None,
        coefficient23x_timesypow2_timeszpow2: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C23 for the x*y^2*z^2 term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient23xTIMESYPOW2TIMESZPOW2.'),
        ] = None,
        coefficient24x_pow2_timesytimesz: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C24 for the x^2*y*z term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient24xPOW2TIMESYTIMESZ.'),
        ] = None,
        coefficient25x_timesypow2_timesz: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C25 for the x*y^2*z term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient25xTIMESYPOW2TIMESZ.'),
        ] = None,
        coefficient26x_timesytimeszpow2: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C26 for the x*y*z^2 term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient26xTIMESYTIMESZPOW2.'),
        ] = None,
        coefficient27x_timesytimesz: Annotated[
            str | float | int | bool | None,
            Field(description='Coefficient C27 for the x*y*z term in the Curve:Triquadratic equation; maps to Ironbug field Coefficient27xTIMESYTIMESZ.'),
        ] = None,
        minimum_valueofx: Annotated[
            float | None,
            Field(description='Minimum allowed x input before Curve:Triquadratic evaluation; maps to Ironbug field MinimumValueofx.'),
        ] = None,
        maximum_valueofx: Annotated[
            float | None,
            Field(description='Maximum allowed x input before Curve:Triquadratic evaluation; maps to Ironbug field MaximumValueofx.'),
        ] = None,
        minimum_valueofy: Annotated[
            float | None,
            Field(description='Minimum allowed y input before Curve:Triquadratic evaluation; maps to Ironbug field MinimumValueofy.'),
        ] = None,
        maximum_valueofy: Annotated[
            float | None,
            Field(description='Maximum allowed y input before Curve:Triquadratic evaluation; maps to Ironbug field MaximumValueofy.'),
        ] = None,
        minimum_valueofz: Annotated[
            float | None,
            Field(description='Minimum allowed z input before Curve:Triquadratic evaluation; maps to Ironbug field MinimumValueofz.'),
        ] = None,
        maximum_valueofz: Annotated[
            float | None,
            Field(description='Maximum allowed z input before Curve:Triquadratic evaluation; maps to Ironbug field MaximumValueofz.'),
        ] = None,
        minimum_curve_output: Annotated[
            float | None,
            Field(description='Minimum allowable evaluated Curve:Triquadratic output; values below this limit are clipped by the curve object. Maps to Ironbug field MinimumCurveOutput.'),
        ] = None,
        maximum_curve_output: Annotated[
            float | None,
            Field(description='Maximum allowable evaluated Curve:Triquadratic output; values above this limit are clipped by the curve object. Maps to Ironbug field MaximumCurveOutput.'),
        ] = None,
        input_unit_typefor_x: Annotated[
            str | None,
            Field(description='Unit type metadata for the x input; coefficients are not converted. Maps to Ironbug field InputUnitTypeforX.'),
        ] = None,
        input_unit_typefor_y: Annotated[
            str | None,
            Field(description='Unit type metadata for the y input; coefficients are not converted. Maps to Ironbug field InputUnitTypeforY.'),
        ] = None,
        input_unit_typefor_z: Annotated[
            str | None,
            Field(description='Unit type metadata for the z input; coefficients are not converted. Maps to Ironbug field InputUnitTypeforZ.'),
        ] = None,
        output_unit_type: Annotated[
            str | None,
            Field(description='Unit type metadata for the evaluated curve output; coefficients are not converted. Maps to Ironbug field OutputUnitType.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Explicit OpenStudio/EnergyPlus object name for this Curve:Triquadratic; maps to Ironbug field Name.'),
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
        """Create IB_CurveTriquadratic as reviewed performance curve data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if coefficient1_constant is not None:
            source_fields['Coefficient1Constant'] = coefficient1_constant
        if coefficient2x_pow2 is not None:
            source_fields['Coefficient2xPOW2'] = coefficient2x_pow2
        if coefficient3x is not None:
            source_fields['Coefficient3x'] = coefficient3x
        if coefficient4y_pow2 is not None:
            source_fields['Coefficient4yPOW2'] = coefficient4y_pow2
        if coefficient5y is not None:
            source_fields['Coefficient5y'] = coefficient5y
        if coefficient6z_pow2 is not None:
            source_fields['Coefficient6zPOW2'] = coefficient6z_pow2
        if coefficient7z is not None:
            source_fields['Coefficient7z'] = coefficient7z
        if coefficient8x_pow2_timesypow2 is not None:
            source_fields['Coefficient8xPOW2TIMESYPOW2'] = coefficient8x_pow2_timesypow2
        if coefficient9x_timesy is not None:
            source_fields['Coefficient9xTIMESY'] = coefficient9x_timesy
        if coefficient10x_timesypow2 is not None:
            source_fields['Coefficient10xTIMESYPOW2'] = coefficient10x_timesypow2
        if coefficient11x_pow2_timesy is not None:
            source_fields['Coefficient11xPOW2TIMESY'] = coefficient11x_pow2_timesy
        if coefficient12x_pow2_timeszpow2 is not None:
            source_fields['Coefficient12xPOW2TIMESZPOW2'] = coefficient12x_pow2_timeszpow2
        if coefficient13x_timesz is not None:
            source_fields['Coefficient13xTIMESZ'] = coefficient13x_timesz
        if coefficient14x_timeszpow2 is not None:
            source_fields['Coefficient14xTIMESZPOW2'] = coefficient14x_timeszpow2
        if coefficient15x_pow2_timesz is not None:
            source_fields['Coefficient15xPOW2TIMESZ'] = coefficient15x_pow2_timesz
        if coefficient16y_pow2_timeszpow2 is not None:
            source_fields['Coefficient16yPOW2TIMESZPOW2'] = coefficient16y_pow2_timeszpow2
        if coefficient17y_timesz is not None:
            source_fields['Coefficient17yTIMESZ'] = coefficient17y_timesz
        if coefficient18y_timeszpow2 is not None:
            source_fields['Coefficient18yTIMESZPOW2'] = coefficient18y_timeszpow2
        if coefficient19y_pow2_timesz is not None:
            source_fields['Coefficient19yPOW2TIMESZ'] = coefficient19y_pow2_timesz
        if coefficient20x_pow2_timesypow2_timeszpow2 is not None:
            source_fields['Coefficient20xPOW2TIMESYPOW2TIMESZPOW2'] = coefficient20x_pow2_timesypow2_timeszpow2
        if coefficient21x_pow2_timesypow2_timesz is not None:
            source_fields['Coefficient21xPOW2TIMESYPOW2TIMESZ'] = coefficient21x_pow2_timesypow2_timesz
        if coefficient22x_pow2_timesytimeszpow2 is not None:
            source_fields['Coefficient22xPOW2TIMESYTIMESZPOW2'] = coefficient22x_pow2_timesytimeszpow2
        if coefficient23x_timesypow2_timeszpow2 is not None:
            source_fields['Coefficient23xTIMESYPOW2TIMESZPOW2'] = coefficient23x_timesypow2_timeszpow2
        if coefficient24x_pow2_timesytimesz is not None:
            source_fields['Coefficient24xPOW2TIMESYTIMESZ'] = coefficient24x_pow2_timesytimesz
        if coefficient25x_timesypow2_timesz is not None:
            source_fields['Coefficient25xTIMESYPOW2TIMESZ'] = coefficient25x_timesypow2_timesz
        if coefficient26x_timesytimeszpow2 is not None:
            source_fields['Coefficient26xTIMESYTIMESZPOW2'] = coefficient26x_timesytimeszpow2
        if coefficient27x_timesytimesz is not None:
            source_fields['Coefficient27xTIMESYTIMESZ'] = coefficient27x_timesytimesz
        if minimum_valueofx is not None:
            source_fields['MinimumValueofx'] = minimum_valueofx
        if maximum_valueofx is not None:
            source_fields['MaximumValueofx'] = maximum_valueofx
        if minimum_valueofy is not None:
            source_fields['MinimumValueofy'] = minimum_valueofy
        if maximum_valueofy is not None:
            source_fields['MaximumValueofy'] = maximum_valueofy
        if minimum_valueofz is not None:
            source_fields['MinimumValueofz'] = minimum_valueofz
        if maximum_valueofz is not None:
            source_fields['MaximumValueofz'] = maximum_valueofz
        if minimum_curve_output is not None:
            source_fields['MinimumCurveOutput'] = minimum_curve_output
        if maximum_curve_output is not None:
            source_fields['MaximumCurveOutput'] = maximum_curve_output
        if input_unit_typefor_x is not None:
            source_fields['InputUnitTypeforX'] = input_unit_typefor_x
        if input_unit_typefor_y is not None:
            source_fields['InputUnitTypeforY'] = input_unit_typefor_y
        if input_unit_typefor_z is not None:
            source_fields['InputUnitTypeforZ'] = input_unit_typefor_z
        if output_unit_type is not None:
            source_fields['OutputUnitType'] = output_unit_type
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CurveTriquadratic',
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
