"""des MCP tools."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register des tools."""

    @mcp.tool(
        name="DF_DES_Assign_Building_Loads",
        description=(
            "Attach URBANopt building load results to the DES feature GeoJSON "
            "and scenario CSV artifacts before system-parameter sizing. The "
            "response reports runtime_status, summary_view, and any warnings "
            "from the Dragonfly Energy load handoff, including sensible-load "
            "substitution when district load columns are missing."
        ),
        tags={"dragonfly", "district-energy", "urbanopt", "load", "csv", "runtime", "target"},
        timeout=60,
    )
    def assign_building_loads(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; updated DES artifacts remain inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="DES feature GeoJSON artifact target receiving the building load references.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="DES scenario CSV artifact target paired with the feature GeoJSON.")],
    ) -> dict[str, Any]:
        """Assign building loads for DES."""
        from garden.dragonfly_des.runs import assign_building_loads as service

        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
        )

    @mcp.tool(
        name="DF_DES_Create_Fifth_Gen_Thermal_Loop",
        description=(
            "Create a Dragonfly DES FifthGenThermalLoop from ThermalConnector targets "
            "plus optional soil and horizontal-pipe parameter targets. Use it for "
            "ambient-water district loops without a GHE field. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "ground-loop", "loop", "pipe", "target"},
        timeout=20,
    )
    def create_fifth_gen_thermal_loop(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved FifthGenThermalLoop target.")],
        connector_targets: Annotated[list[dict[str, Any]], Field(description="One or more Dragonfly DES ThermalConnector targets to include in the loop.")],
        clockwise_flow: Annotated[bool, Field(description="Whether loop connector flow should be interpreted as clockwise.")] = False,
        soil_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES SoilParameter target for horizontal-pipe heat transfer context.")] = None,
        horizontal_pipe_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES HorizontalPipeParameter target for connector pipe properties.")] = None,
        heat_rejection_type: Annotated[str, Field(description="Dragonfly Energy heat rejection type for the fifth-generation loop: CoolingTower, FluidCooler, EvaporativeFluidCooler, DistrictCooling, or None.")] = "CoolingTower",
        supplemental_heat_type: Annotated[str, Field(description="Dragonfly Energy supplemental heat type for the fifth-generation loop: Electricity, NaturalGas, DistrictHeating, or None.")] = "Electricity",
        display_name: Annotated[str | None, Field(description="Optional display name stored on SDK objects that support display_name.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES FifthGenThermalLoop."""
        from garden.dragonfly_des.authoring import create_fifth_gen_thermal_loop as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            connector_targets=connector_targets,
            clockwise_flow=clockwise_flow,
            soil_parameter_target=soil_parameter_target,
            horizontal_pipe_parameter_target=horizontal_pipe_parameter_target,
            heat_rejection_type=heat_rejection_type,
            supplemental_heat_type=supplemental_heat_type,
            display_name=display_name,
        )

    @mcp.tool(
        name="DF_DES_Create_Fourth_Gen_Thermal_Loop",
        description=(
            "Create a Dragonfly DES FourthGenThermalLoop target for high-temperature "
            "district heating or cooling loop authoring. Slice 1 omits plant target "
            "binding and records that boundary in the report. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "heating", "cooling", "loop", "target"},
        timeout=20,
    )
    def create_fourth_gen_thermal_loop(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved FourthGenThermalLoop target.")],
        economizer_type: Annotated[str, Field(description="Dragonfly Energy economizer type for the fourth-generation loop.")] = "None",
        heating_type: Annotated[str, Field(description="Dragonfly Energy heating type for the fourth-generation loop.")] = "NaturalGas",
        display_name: Annotated[str | None, Field(description="Optional display name stored on SDK objects that support display_name.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES FourthGenThermalLoop."""
        from garden.dragonfly_des.authoring import create_fourth_gen_thermal_loop as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            economizer_type=economizer_type,
            heating_type=heating_type,
            display_name=display_name,
        )

    @mcp.tool(
        name="DF_DES_Create_GHE_Borehole_Parameter",
        description=(
            "Create a Dragonfly DES BoreholeParameter for GHE field sizing, "
            "including depth, spacing, buried depth, and borehole diameter. Use the "
            "returned target in GHE thermal loop authoring. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"borehole", "dragonfly", "district-energy", "author", "geothermal", "parameter", "target"},
        timeout=20,
    )
    def create_ghe_borehole_parameter(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved BoreholeParameter target.")],
        min_depth: Annotated[float | None, Field(description="Optional minimum borehole depth in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        max_depth: Annotated[float | None, Field(description="Optional maximum borehole depth in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        min_spacing: Annotated[float | None, Field(description="Optional minimum borehole spacing in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        max_spacing: Annotated[float | None, Field(description="Optional maximum borehole spacing in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        buried_depth: Annotated[float | None, Field(description="Optional borehole buried depth in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        diameter: Annotated[float | None, Field(description="Optional borehole diameter in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES BoreholeParameter."""
        from garden.dragonfly_des.authoring import create_ghe_borehole_parameter as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            min_depth=min_depth,
            max_depth=max_depth,
            min_spacing=min_spacing,
            max_spacing=max_spacing,
            buried_depth=buried_depth,
            diameter=diameter,
        )

    @mcp.tool(
        name="DF_DES_Create_GHE_Design_Parameter",
        description=(
            "Create a Dragonfly DES GHEDesignParameter for GHE sizing criteria, "
            "including flow rate, flow type, entering-fluid temperature limits, "
            "simulation month count, and sizing method. Returns target, summary_view, "
            "persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "geothermal", "parameter", "sizing", "target"},
        timeout=20,
    )
    def create_ghe_design_parameter(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved GHEDesignParameter target.")],
        flow_rate: Annotated[float | None, Field(description="Optional GHE design flow rate; omitted values use the Dragonfly Energy SDK default.")] = None,
        flow_type: Annotated[str | None, Field(description="Optional SDK flow type such as Borehole; omitted values use the Dragonfly Energy SDK default.")] = None,
        max_eft: Annotated[float | None, Field(description="Optional maximum entering-fluid temperature in Celsius; omitted values use the Dragonfly Energy SDK default.")] = None,
        min_eft: Annotated[float | None, Field(description="Optional minimum entering-fluid temperature in Celsius; omitted values use the Dragonfly Energy SDK default.")] = None,
        month_count: Annotated[int | None, Field(description="Optional simulation month count for design sizing; omitted values use the Dragonfly Energy SDK default.")] = None,
        method: Annotated[str | None, Field(description="Optional SDK design method such as AreaProportional; omitted values use the Dragonfly Energy SDK default.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES GHEDesignParameter."""
        from garden.dragonfly_des.authoring import create_ghe_design_parameter as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            flow_rate=flow_rate,
            flow_type=flow_type,
            max_eft=max_eft,
            min_eft=min_eft,
            month_count=month_count,
            method=method,
        )

    @mcp.tool(
        name="DF_DES_Create_GHE_Fluid_Parameter",
        description=(
            "Create a Dragonfly DES FluidParameter for a ground heat exchanger loop, "
            "including fluid type, concentration, and design temperature. Use the "
            "returned target in GHE thermal loop authoring. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "fluid", "geothermal", "parameter", "target"},
        timeout=20,
    )
    def create_ghe_fluid_parameter(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved FluidParameter target.")],
        fluid_type: Annotated[str | None, Field(description="Optional SDK fluid type such as Water or EthyleneGlycol; omitted values use the Dragonfly Energy SDK default.")] = None,
        concentration: Annotated[float | None, Field(description="Optional fluid concentration percentage; omitted values use the Dragonfly Energy SDK default.")] = None,
        temperature: Annotated[float | None, Field(description="Optional fluid temperature in Celsius; omitted values use the Dragonfly Energy SDK default.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES FluidParameter."""
        from garden.dragonfly_des.authoring import create_ghe_fluid_parameter as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            fluid_type=fluid_type,
            concentration=concentration,
            temperature=temperature,
        )

    @mcp.tool(
        name="DF_DES_Create_GHE_Pipe_Parameter",
        description=(
            "Create a Dragonfly DES PipeParameter for ground heat exchanger borehole "
            "pipes, including inner and outer diameters, shank spacing, roughness, "
            "conductivity, heat capacity, and U-tube arrangement. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "geothermal", "parameter", "pipe", "target"},
        timeout=20,
    )
    def create_ghe_pipe_parameter(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved PipeParameter target.")],
        inner_diameter: Annotated[float | None, Field(description="Optional pipe inner diameter in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        outer_diameter: Annotated[float | None, Field(description="Optional pipe outer diameter in meters; must be greater than inner_diameter when both are set.")] = None,
        shank_spacing: Annotated[float | None, Field(description="Optional U-tube shank spacing in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        roughness: Annotated[float | None, Field(description="Optional pipe roughness in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        conductivity: Annotated[float | None, Field(description="Optional pipe conductivity in W/m-K; omitted values use the Dragonfly Energy SDK default.")] = None,
        heat_capacity: Annotated[float | None, Field(description="Optional pipe heat capacity in J/m3-K; omitted values use the Dragonfly Energy SDK default.")] = None,
        arrangement: Annotated[str | None, Field(description="Optional SDK pipe arrangement such as SingleUTube, DoubleUTubeSeries, or DoubleUTubeParallel.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES PipeParameter."""
        from garden.dragonfly_des.authoring import create_ghe_pipe_parameter as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            inner_diameter=inner_diameter,
            outer_diameter=outer_diameter,
            shank_spacing=shank_spacing,
            roughness=roughness,
            conductivity=conductivity,
            heat_capacity=heat_capacity,
            arrangement=arrangement,
        )

    @mcp.tool(
        name="DF_DES_Create_GHE_Soil_Parameter",
        description=(
            "Create a Dragonfly DES SoilParameter for ground heat exchanger design, "
            "including soil and grout conductivity, heat capacity, and optional "
            "undisturbed temperature. Use the returned target in GHE field or loop "
            "authoring. Returns target, summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "geothermal", "ground-loop", "parameter", "target"},
        timeout=20,
    )
    def create_ghe_soil_parameter(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved SoilParameter target.")],
        conductivity: Annotated[float | None, Field(description="Optional soil conductivity in W/m-K; omitted values use the Dragonfly Energy SDK default.")] = None,
        heat_capacity: Annotated[float | None, Field(description="Optional soil heat capacity in J/m3-K; omitted values use the Dragonfly Energy SDK default.")] = None,
        undisturbed_temperature: Annotated[float | None, Field(description="Optional undisturbed ground temperature in Celsius; omit to keep the SDK Autocalculate value.")] = None,
        grout_conductivity: Annotated[float | None, Field(description="Optional grout conductivity in W/m-K; omitted values use the Dragonfly Energy SDK default.")] = None,
        grout_heat_capacity: Annotated[float | None, Field(description="Optional grout heat capacity in J/m3-K; omitted values use the Dragonfly Energy SDK default.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES SoilParameter."""
        from garden.dragonfly_des.authoring import create_ghe_soil_parameter as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            conductivity=conductivity,
            heat_capacity=heat_capacity,
            undisturbed_temperature=undisturbed_temperature,
            grout_conductivity=grout_conductivity,
            grout_heat_capacity=grout_heat_capacity,
        )

    @mcp.tool(
        name="DF_DES_Create_GHE_Thermal_Loop",
        description=(
            "Create a Dragonfly DES GHEThermalLoop from GroundHeatExchanger and "
            "ThermalConnector targets plus optional soil, fluid, pipe, borehole, "
            "design, and horizontal-pipe parameter targets. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"borehole", "dragonfly", "district-energy", "author", "geothermal", "ground-heat-exchanger", "ground-loop", "loop", "target"},
        timeout=20,
    )
    def create_ghe_thermal_loop(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved GHEThermalLoop target.")],
        ground_heat_exchanger_targets: Annotated[list[dict[str, Any]], Field(description="One or more Dragonfly DES GroundHeatExchanger targets for the loop.")],
        connector_targets: Annotated[list[dict[str, Any]], Field(description="One or more Dragonfly DES ThermalConnector targets for the loop piping.")],
        clockwise_flow: Annotated[bool, Field(description="Whether loop connector flow should be interpreted as clockwise.")] = False,
        soil_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES SoilParameter target for the GHE loop.")] = None,
        fluid_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES FluidParameter target for the GHE loop.")] = None,
        pipe_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES PipeParameter target for borehole pipe properties.")] = None,
        borehole_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES BoreholeParameter target for borehole depth and spacing.")] = None,
        design_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES GHEDesignParameter target for GHE sizing criteria.")] = None,
        horizontal_pipe_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES HorizontalPipeParameter target for connector pipe properties.")] = None,
        heat_rejection_type: Annotated[str, Field(description="Dragonfly Energy heat rejection type for the GHE thermal loop: CoolingTower, FluidCooler, EvaporativeFluidCooler, DistrictCooling, or None.")] = "CoolingTower",
        supplemental_heat_type: Annotated[str, Field(description="Dragonfly Energy supplemental heat type for the GHE thermal loop: Electricity, NaturalGas, DistrictHeating, or None.")] = "Electricity",
        display_name: Annotated[str | None, Field(description="Optional display name stored on SDK objects that support display_name.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES GHEThermalLoop."""
        from garden.dragonfly_des.authoring import create_ghe_thermal_loop as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            ground_heat_exchanger_targets=ground_heat_exchanger_targets,
            connector_targets=connector_targets,
            clockwise_flow=clockwise_flow,
            soil_parameter_target=soil_parameter_target,
            fluid_parameter_target=fluid_parameter_target,
            pipe_parameter_target=pipe_parameter_target,
            borehole_parameter_target=borehole_parameter_target,
            design_parameter_target=design_parameter_target,
            horizontal_pipe_parameter_target=horizontal_pipe_parameter_target,
            heat_rejection_type=heat_rejection_type,
            supplemental_heat_type=supplemental_heat_type,
            display_name=display_name,
        )

    @mcp.tool(
        name="DF_DES_Create_Ground_Heat_Exchanger",
        description=(
            "Create a Dragonfly DES GroundHeatExchanger from a 2D field footprint "
            "and optional SDK-required 3D borehole positions. Use the returned target "
            "as a ground heat exchanger input for a GHE thermal loop. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"borehole", "dragonfly", "district-energy", "author", "geometry", "geothermal", "ground-heat-exchanger", "target"},
        timeout=20,
    )
    def create_ground_heat_exchanger(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved GroundHeatExchanger target.")],
        footprint_points: Annotated[list[list[float]], Field(description="Ordered 2D footprint points as [[x, y], ...] for the GHE field polygon.")],
        borehole_positions: Annotated[list[list[float]] | None, Field(description="Optional borehole Point3D coordinates as [[x, y, z], ...], matching the current Dragonfly Energy SDK requirement.")] = None,
        display_name: Annotated[str | None, Field(description="Optional display name stored on SDK objects that support display_name.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES GroundHeatExchanger."""
        from garden.dragonfly_des.authoring import create_ground_heat_exchanger as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            footprint_points=footprint_points,
            borehole_positions=borehole_positions,
            display_name=display_name,
        )

    @mcp.tool(
        name="DF_DES_Create_Horizontal_Pipe_Parameter",
        description=(
            "Create a Dragonfly DES HorizontalPipeParameter for thermal connector "
            "pipe sizing, burial, insulation, pressure-drop, and pump defaults. Use "
            "the returned target in fifth-generation or GHE thermal loop creation. "
            "Returns target, summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "parameter", "pipe", "target"},
        timeout=20,
    )
    def create_horizontal_pipe_parameter(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved HorizontalPipeParameter target.")],
        buried_depth: Annotated[float | None, Field(description="Optional pipe buried depth in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        diameter_ratio: Annotated[float | None, Field(description="Optional pipe diameter ratio from 11 to 17; omitted values use the Dragonfly Energy SDK default.")] = None,
        pressure_drop_per_meter: Annotated[float | None, Field(description="Optional pressure drop per meter in Pa/m; omitted values use the Dragonfly Energy SDK default.")] = None,
        insulation_conductivity: Annotated[float | None, Field(description="Optional insulation conductivity in W/m-K; omitted values use the Dragonfly Energy SDK default.")] = None,
        insulation_thickness: Annotated[float | None, Field(description="Optional insulation thickness in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        heat_capacity: Annotated[float | None, Field(description="Optional pipe heat capacity in J/m3-K; omitted values use the Dragonfly Energy SDK default.")] = None,
        roughness: Annotated[float | None, Field(description="Optional pipe roughness in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        hydraulic_diameter: Annotated[float | None, Field(description="Optional hydraulic diameter in meters; omit to keep the SDK Autosize value.")] = None,
        pump_design_head: Annotated[float | None, Field(description="Optional pump design head in Pa; omit to keep the SDK Autosize value.")] = None,
        pump_flow_rate: Annotated[float | None, Field(description="Optional pump flow rate in m3/s; omit to keep the SDK Autosize value.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES HorizontalPipeParameter."""
        from garden.dragonfly_des.authoring import create_horizontal_pipe_parameter as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            buried_depth=buried_depth,
            diameter_ratio=diameter_ratio,
            pressure_drop_per_meter=pressure_drop_per_meter,
            insulation_conductivity=insulation_conductivity,
            insulation_thickness=insulation_thickness,
            heat_capacity=heat_capacity,
            roughness=roughness,
            hydraulic_diameter=hydraulic_diameter,
            pump_design_head=pump_design_head,
            pump_flow_rate=pump_flow_rate,
        )

    @mcp.tool(
        name="DF_DES_Thermal_Connector",
        description=(
            "Create a Dragonfly DES ThermalConnector from Grasshopper-style 2D "
            "polyline points for a district thermal network. Use the returned target "
            "as a connector input for fifth-generation or GHE thermal loops. Returns "
            "target, summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "geometry", "pipe", "target"},
        timeout=20,
    )
    def create_thermal_connector(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the saved Dragonfly DES ThermalConnector target."),
        ],
        polyline_points: Annotated[
            list[list[float]],
            Field(description="Ordered 2D points as [[x, y], ...]; two points create a line segment and three or more create a polyline."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display name stored on SDK objects that support display_name."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES ThermalConnector."""
        from garden.dragonfly_des.authoring import create_thermal_connector as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            polyline_points=polyline_points,
            display_name=display_name,
        )

    @mcp.tool(
        name="DF_DES_Export_Model",
        description=(
            'Write the Dragonfly Energy DES handoff files for a Dragonfly Model, thermal loop, '
            'and EPW weather target. The response gives Garden artifact targets for feature '
            'GeoJSON, scenario CSV, and the SDK system_params JSON file, plus summary_view, '
            'persistence_receipt, and report. Use this before DES load, sys-param, or Modelica '
            'steps; file contents remain on disk.'
        ),
        tags={"dragonfly", "district-energy", "export", "artifact", "epw", "weather", "target"},
        timeout=60,
    )
    def export_model_to_des(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; DES export artifacts are saved inside this Garden.")],
        des_loop_target: Annotated[dict[str, Any], Field(description="DES thermal-loop target that should be translated into system parameters.")],
        weather_target: Annotated[dict[str, Any], Field(description="Garden weather_file target with an EPW path for the DES export.")],
        model_target: Annotated[dict[str, Any] | None, Field(description="Specific Dragonfly Model target to export; omit to export the Garden base_dragonfly_model.") ] = None,
        location: Annotated[dict[str, Any] | None, Field(description="Optional Ladybug Location override; omit to let the writer read location from the EPW.") ] = None,
        point: Annotated[list[float] | None, Field(description="Optional [x, y] model coordinate for the weather location marker.") ] = None,
        folder_name: Annotated[str | None, Field(description="Optional Garden DES export folder name; long names are shortened to keep URBANopt paths usable on Windows.") ] = None,
        tolerance: Annotated[float | None, Field(description="Optional geometry tolerance for the Dragonfly Energy DES writer.") ] = None,
    ) -> dict[str, Any]:
        """Export a Dragonfly Model to DES artifacts."""
        from garden.dragonfly_des.export import export_model_to_des as service

        return service(
            garden_root=garden_root,
            des_loop_target=des_loop_target,
            weather_target=weather_target,
            model_target=model_target,
            location=location,
            point=point,
            folder_name=folder_name,
            tolerance=tolerance,
        )

    @mcp.tool(
        name="DF_DES_Export_URBANopt_Model",
        description=(
            "Translate a Garden Dragonfly Model into the URBANopt files needed "
            "for district energy workflows. The response gives Garden artifact "
            "targets for the feature GeoJSON and generated Honeybee HBJSON files, "
            "plus summary_view, persistence_receipt, and report. Use a DES loop "
            "target only when the exported GeoJSON should carry district thermal "
            "loop data; use Dragonfly Grid targets when RNM, OpenDSS, or REopt "
            "post-processing needs roads, electrical networks, or ground PV. "
            "Full file bodies stay on disk."
        ),
        tags={"dragonfly", "district-energy", "urbanopt", "export", "artifact", "target"},
        timeout=60,
    )
    def export_urbanopt_model(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; export artifacts are saved inside this Garden.")],
        location: Annotated[dict[str, Any], Field(description="Ladybug Location fields for the URBANopt project, including latitude and longitude.")],
        model_target: Annotated[dict[str, Any] | None, Field(description="Specific Dragonfly Model target to export; omit to export the Garden base_dragonfly_model.") ] = None,
        des_loop_target: Annotated[dict[str, Any] | None, Field(description="Optional DES thermal-loop target to embed in the URBANopt feature GeoJSON.") ] = None,
        electrical_network_target: Annotated[dict[str, Any] | None, Field(description="Optional DF_Grid_Electrical_Network target to embed in the URBANopt feature GeoJSON for OpenDSS/RNM-adjacent workflows.") ] = None,
        road_network_target: Annotated[dict[str, Any] | None, Field(description="Optional DF_Grid_Road_Network target to embed Road features in the URBANopt feature GeoJSON for RNM.") ] = None,
        ground_pv_targets: Annotated[list[dict[str, Any]] | None, Field(description="Optional DF_Grid_Ground_Photovoltaics targets to embed ground PV features for REopt.") ] = None,
        point: Annotated[list[float] | None, Field(description="Optional [x, y] model coordinate for the project location marker.") ] = None,
        folder_name: Annotated[str | None, Field(description="Optional URBANopt project folder name; when omitted, the model display_name is used with LBT portable-name rules.") ] = None,
        shade_distance: Annotated[float | None, Field(description="Optional shade search distance passed to the Dragonfly Energy URBANopt writer.") ] = None,
        use_multiplier: Annotated[bool, Field(description="Keep Dragonfly Story multipliers as Honeybee Room multipliers when translating buildings.") ] = True,
        exclude_plenums: Annotated[bool, Field(description="Exclude generated ceiling and floor plenum rooms from the Honeybee translation.") ] = False,
        solve_ceiling_adjacencies: Annotated[bool, Field(description="Solve matching ceiling adjacencies between interior stories before writing HBJSON files.") ] = False,
        merge_method: Annotated[str, Field(description="Dragonfly Energy room merge method, such as None, Zones, PlenumZones, Stories, or PlenumStories.") ] = "None",
        tolerance: Annotated[float | None, Field(description="Optional geometry tolerance for the Dragonfly Energy URBANopt writer.") ] = None,
    ) -> dict[str, Any]:
        """Export a Dragonfly Model to URBANopt artifacts."""
        from garden.dragonfly_des.export import export_urbanopt_model as service

        return service(
            garden_root=garden_root,
            location=location,
            model_target=model_target,
            des_loop_target=des_loop_target,
            electrical_network_target=electrical_network_target,
            road_network_target=road_network_target,
            ground_pv_targets=ground_pv_targets,
            point=point,
            folder_name=folder_name,
            shade_distance=shade_distance,
            use_multiplier=use_multiplier,
            exclude_plenums=exclude_plenums,
            solve_ceiling_adjacencies=solve_ceiling_adjacencies,
            merge_method=merge_method,
            tolerance=tolerance,
        )

    @mcp.tool(
        name="DF_DES_List_URBANopt_Run_Outputs",
        description=(
            'List the saved output files for one Garden URBANopt DES run as compact path records. '
            'Use after polling has found completed or failed status to locate SQL, ERR, HTML, '
            'CSV, or log file paths. Accepts run_target or run_id and returns matches, '
            'summary_view, and report.'
        ),
        tags={"dragonfly", "district-energy", "urbanopt", "outputs", "run", "artifact", "target"},
        timeout=20,
    )
    def list_urbanopt_run_outputs(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; output records are discovered under this Garden's run folder.")],
        run_target: Annotated[dict[str, Any] | None, Field(description="URBANopt DES run target whose outputs should be listed.") ] = None,
        run_id: Annotated[str | None, Field(description="URBANopt run id to list when run_target is not available.") ] = None,
    ) -> dict[str, Any]:
        """List URBANopt run outputs."""
        from garden.dragonfly_des.runs import list_urbanopt_run_outputs as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)

    @mcp.tool(
        name="DF_DES_Poll_Modelica_Simulation",
        description=(
            'Read the compact Garden ledger for a DES Modelica project write or Docker simulation '
            'to inspect runtime_status, poll_next, and output paths.'
        ),
        tags={"dragonfly", "district-energy", "poll", "runtime", "run", "target"},
        timeout=20,
    )
    def poll_modelica_simulation(
        garden_root: Annotated[str, Field(description='Garden root containing garden.json.')],
        run_target: Annotated[dict[str, Any] | None, Field(description=(
            'DES Modelica run target returned by DF_DES_Write_Modelica_Project or '
            'DF_DES_Start_Modelica_Simulation.'
        )) ] = None,
        run_id: Annotated[str | None, Field(description='Optional Modelica run id when run_target is not available.') ] = None,
    ) -> dict[str, Any]:
        """Poll a Modelica run."""
        from garden.dragonfly_des.runs import poll_modelica_simulation as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)

    @mcp.tool(
        name="DF_DES_Poll_Sys_Param",
        description=(
            'Read the compact Garden ledger for a DES system-parameter run. Use after the start '
            'tool to check runtime_status and confirm whether system_parameter_json_target is '
            'ready for Modelica steps.'
        ),
        tags={"dragonfly", "district-energy", "poll", "runtime", "run", "sizing", "target"},
        timeout=20,
    )
    def poll_sys_param(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the sys-param run ledger is read from this Garden.")],
        run_target: Annotated[dict[str, Any] | None, Field(description="DES system-parameter run target returned by the start tool.") ] = None,
        run_id: Annotated[str | None, Field(description="System-parameter run id to poll when run_target is not available.") ] = None,
    ) -> dict[str, Any]:
        """Poll a DES system-parameter run."""
        from garden.dragonfly_des.runs import poll_sys_param as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)

    @mcp.tool(
        name="DF_DES_Poll_URBANopt_Simulation",
        description=(
            'Read the compact Garden ledger for an URBANopt DES run. Use it after the start tool '
            'to check runtime_status, poll_next, and the output inventory before load assignment '
            'or system-parameter work.'
        ),
        tags={"dragonfly", "district-energy", "urbanopt", "poll", "runtime", "run", "target"},
        timeout=20,
    )
    def poll_urbanopt_simulation(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the URBANopt run ledger is read from this Garden.")],
        run_target: Annotated[dict[str, Any] | None, Field(description="URBANopt DES run target returned by the start tool.") ] = None,
        run_id: Annotated[str | None, Field(description="URBANopt run id to poll when run_target is not available.") ] = None,
    ) -> dict[str, Any]:
        """Poll an URBANopt run."""
        from garden.dragonfly_des.runs import poll_urbanopt_simulation as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)

    @mcp.tool(
        name="DF_DES_Prepare_URBANopt_Project",
        description=(
            "Create the URBANopt runner setup for a DES feature GeoJSON artifact "
            "that does not yet have a scenario CSV target. The tool records the "
            "scenario CSV as a Garden artifact and reports runtime_status, "
            "summary_view, persistence_receipt, and report. When the URBANopt "
            "runtime is unavailable it returns blocked with config guidance."
        ),
        tags={"dragonfly", "district-energy", "urbanopt", "project", "artifact", "runtime", "target"},
        timeout=30,
    )
    def prepare_urbanopt_project(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; runner setup is written inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="DES feature GeoJSON artifact target to prepare as an URBANopt project.")],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden weather_file target; when provided its EPW is written into the base Honeybee OSW before URBANopt simulation."),
        ] = None,
        cpu_count: Annotated[int | None, Field(description="Optional positive CPU count for the URBANopt runner configuration.") ] = None,
        verbose: Annotated[bool, Field(description="Ask the generated runner configuration to emit verbose progress output.") ] = False,
    ) -> dict[str, Any]:
        """Prepare an URBANopt project folder."""
        from garden.dragonfly_des.runs import prepare_urbanopt_project as service

        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            weather_target=weather_target,
            cpu_count=cpu_count,
            verbose=verbose,
        )

    @mcp.tool(
        name="DF_DES_Start_Modelica_Simulation",
        description=(
            'Start a Modelica Docker run from a DES modelica_project_target, returning '
            'run_target, runtime_status, poll_next, summary_view, and report (reports blocked '
            'when Docker, OpenModelica, or GMT is missing).'
        ),
        tags={"dragonfly", "district-energy", "simulate", "runtime", "run", "poll", "target"},
        timeout=30,
    )
    def start_modelica_simulation(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the Modelica run ledger is written inside this Garden.")],
        modelica_project_target: Annotated[dict[str, Any], Field(description='DES Modelica project artifact target returned by DF_DES_Write_Modelica_Project.')],
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.") ] = None,
    ) -> dict[str, Any]:
        """Start a Modelica simulation."""
        from garden.dragonfly_des.runs import start_modelica_simulation as service

        return service(
            garden_root=garden_root,
            modelica_project_target=modelica_project_target,
            run_id=run_id,
        )

    @mcp.tool(
        name="DF_DES_Start_Sys_Param",
        description=(
            "Start the DES system-parameter sizing/update step after URBANopt "
            "outputs and building loads are ready. The tool records a Garden "
            "run ledger and returns run_target, runtime_status, poll_next, "
            "summary_view, and a system_parameter_json_target handoff when one "
            "is available. Missing GMT/uo_des is returned as blocked."
        ),
        tags={"dragonfly", "district-energy", "run", "runtime", "poll", "sizing", "target"},
        timeout=30,
    )
    def start_sys_param(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the sys-param run ledger is written inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="DES feature GeoJSON artifact target for the system-parameter step.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="DES scenario CSV artifact target for the system-parameter step.")],
        system_parameter_json_target: Annotated[dict[str, Any] | None, Field(description="Existing system_params JSON artifact target to carry through the ledger, when already exported.") ] = None,
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.") ] = None,
    ) -> dict[str, Any]:
        """Start a DES system-parameter run."""
        from garden.dragonfly_des.runs import start_sys_param as service

        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            system_parameter_json_target=system_parameter_json_target,
            run_id=run_id,
        )

    @mcp.tool(
        name="DF_DES_Start_URBANopt_Simulation",
        description=(
            "Start the URBANopt simulation step for DES artifacts already saved "
            "in a Garden. The tool writes a Garden run ledger and returns "
            "run_target, runtime_status, poll_next, summary_view, and report "
            "without waiting for result parsing. Missing URBANopt is reported as "
            "blocked, with LB_Get_Runtime_Config named as the next check."
        ),
        tags={"dragonfly", "district-energy", "urbanopt", "run", "simulate", "runtime", "poll", "target"},
        timeout=30,
    )
    def start_urbanopt_simulation(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the URBANopt run ledger is written inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="DES feature GeoJSON artifact target for the URBANopt simulation.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="DES scenario CSV artifact target paired with the feature GeoJSON.")],
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.") ] = None,
        cpu_count: Annotated[int | None, Field(description="Optional CPU count passed to the Dragonfly Energy URBANopt runner.") ] = None,
    ) -> dict[str, Any]:
        """Start an URBANopt simulation."""
        from garden.dragonfly_des.runs import start_urbanopt_simulation as service

        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            run_id=run_id,
            cpu_count=cpu_count,
        )

    @mcp.tool(
        name="DF_DES_Write_Modelica_Project",
        description=(
            'Write a Modelica project from Garden DES artifact targets (system_params JSON, '
            'feature GeoJSON, and scenario CSV), returning runtime_status, run_target, '
            'modelica_project_target, summary_view, poll_next, and report.'
        ),
        tags={"dragonfly", "district-energy", "project", "artifact", "runtime", "run", "target"},
        timeout=60,
    )
    def write_modelica_project(
        garden_root: Annotated[str, Field(description='Garden root containing garden.json.')],
        system_parameter_json_target: Annotated[dict[str, Any], Field(description="DES system_params JSON artifact target from export or sys-param sizing.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="DES feature GeoJSON artifact target used to build the Modelica project.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="DES scenario CSV artifact target used to build the Modelica project.")],
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.") ] = None,
    ) -> dict[str, Any]:
        """Write a DES Modelica project."""
        from garden.dragonfly_des.runs import write_modelica_project as service

        return service(
            garden_root=garden_root,
            system_parameter_json_target=system_parameter_json_target,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            run_id=run_id,
        )
