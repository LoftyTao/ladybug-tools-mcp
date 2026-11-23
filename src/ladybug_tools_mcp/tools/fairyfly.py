"""fairyfly MCP tools."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register fairyfly tools."""

    @mcp.tool(
        name="FF_Add_Boundary_To_Model",
        description=(
            "Add a Fairyfly Boundary to a Garden-backed Fairyfly Model from Ladybug "
            "Geometry 2D line segment input. The boundary is saved into the model, "
            "not as a separate target. Use THERM run/result tools after exporting or "
            "running the two-dimensional section."
        ),
        tags={"fairyfly", "therm", "model", "geometry", "boundary", "2d"},
        timeout=20,
    )
    def add_fairyfly_boundary_to_model(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        line_segments_2d: Annotated[
            list[list[list[float]]],
            Field(description="Fairyfly Boundary line segments as [[[x1, y1], [x2, y2]], ...] in model units."),
        ],
        temperature: Annotated[
            float,
            Field(description="Steady-state boundary temperature in degrees Celsius."),
        ],
        film_coefficient: Annotated[
            float,
            Field(description="Boundary film coefficient in W/m2-K."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Fairyfly Model target dict, usually FF_Create_Model['target']; "
                    "defaults to the Garden base Fairyfly Model."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional display name for the Boundary and its condition."),
        ] = None,
        emissivity: Annotated[
            float,
            Field(description="Radiant environment emissivity."),
        ] = 1.0,
        radiant_temperature: Annotated[
            float | None,
            Field(description="Optional radiant temperature in degrees Celsius."),
        ] = None,
        heat_flux: Annotated[
            float,
            Field(description="Optional heat flux in W/m2."),
        ] = 0,
        relative_humidity: Annotated[
            float,
            Field(description="Boundary relative humidity from 0 to 1."),
        ] = 0.5,
        u_factor_tag: Annotated[
            str | None,
            Field(description="Optional THERM U-Factor tag such as Frame or Edge."),
        ] = None,
        rgb_color: Annotated[
            list[int] | None,
            Field(description="Optional RGB color as [r, g, b]."),
        ] = None,
    ) -> dict[str, Any]:
        """Add a Fairyfly Boundary to a model."""
        from garden.fairyfly.model import add_fairyfly_boundary_to_model as service

        return service(
            garden_root=garden_root,
            line_segments_2d=line_segments_2d,
            temperature=temperature,
            film_coefficient=film_coefficient,
            model_target=model_target,
            name=name,
            emissivity=emissivity,
            radiant_temperature=radiant_temperature,
            heat_flux=heat_flux,
            relative_humidity=relative_humidity,
            u_factor_tag=u_factor_tag,
            rgb_color=rgb_color,
        )

    @mcp.tool(
        name="FF_Add_Shape_To_Model",
        description=(
            'Add a Fairyfly Shape to a Garden-backed Fairyfly Model from Ladybug Geometry 2D '
            'polygon input and a THERM material object_dict. The shape is saved into the model, '
            'not as a separate target.'
        ),
        tags={"fairyfly", "therm", "model", "geometry", "shape", "2d"},
        timeout=20,
    )
    def add_fairyfly_shape_to_model(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        vertices_2d: Annotated[
            list[list[float]],
            Field(description="Fairyfly Shape polygon vertices as [[x, y], ...] in two-dimensional model units."),
        ],
        material: Annotated[
            dict[str, Any],
            Field(description='Fairyfly THERM material object_dict, such as FF_Create_Solid_Material.object_dict.'),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Fairyfly Model target dict, usually FF_Create_Model['target']; "
                    "defaults to the Garden base Fairyfly Model."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional display name for the Shape."),
        ] = None,
        holes_2d: Annotated[
            list[list[list[float]]] | None,
            Field(description="Optional hole polygons as [[[x, y], ...], ...]."),
        ] = None,
        rgb_color: Annotated[
            list[int] | None,
            Field(description="Optional RGB color as [r, g, b]."),
        ] = None,
        tolerance: Annotated[
            float | None,
            Field(description="Optional cleanup tolerance for duplicate and colinear vertices."),
        ] = None,
    ) -> dict[str, Any]:
        """Add a Fairyfly Shape to a model."""
        from garden.fairyfly.model import add_fairyfly_shape_to_model as service

        return service(
            garden_root=garden_root,
            vertices_2d=vertices_2d,
            material=material,
            model_target=model_target,
            name=name,
            holes_2d=holes_2d,
            rgb_color=rgb_color,
            tolerance=tolerance,
        )

    @mcp.tool(
        name="FF_Create_Model",
        description=(
            'Create an empty Fairyfly two-dimensional heat-transfer model in a Garden and '
            'optionally set it as the base Fairyfly model. Fairyfly SDK model identifiers are '
            "UUIDs; this tool's identifier is the stable Garden model identifier and FFJSON file "
            'name. Use this for a create Fairyfly two dimensional heat transfer model request '
            'before adding Shapes, Boundaries, writing THMZ, or running THERM. Returns target and '
            'model_target for downstream Fairyfly tools.'
        ),
        tags={"fairyfly", "therm", "model", "author", "2d"},
        timeout=20,
    )
    def create_fairyfly_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str,
            Field(
                description="Required stable Garden Fairyfly model identifier used for the FFJSON file name."
            ),
        ],
        units: Annotated[
            str,
            Field(description="Fairyfly model units string, for example Millimeters."),
        ] = "Millimeters",
        tolerance: Annotated[
            float | None,
            Field(description="Optional Fairyfly model tolerance."),
        ] = None,
        angle_tolerance: Annotated[
            float,
            Field(description="Fairyfly model angle tolerance."),
        ] = 1.0,
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing model display name."),
        ] = None,
        save_back: Annotated[
            bool,
            Field(description="Whether to save the Fairyfly Model into the Garden and return a Fairyfly model target."),
        ] = True,
        set_base: Annotated[
            bool,
            Field(description="Whether to set as Garden base Fairyfly model."),
        ] = True,
        include_body: Annotated[
            bool,
            Field(description="Whether to return full model body if not saved."),
        ] = False,
    ) -> dict[str, Any]:
        """Create a Fairyfly Model."""
        from garden.fairyfly.model import create_fairyfly_model as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            units=units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
            display_name=display_name,
            save_back=save_back,
            set_base=set_base,
            include_body=include_body,
        )

    @mcp.tool(
        name="FF_Create_Solid_Material",
        description=(
            "Create a Fairyfly THERM SolidMaterial payload for use with "
            "FF_Add_Shape_To_Model. This returns an inline object_dict, not a "
            "Garden target, and it does not attach the material to a model by itself."
        ),
        tags={"fairyfly", "therm", "material", "author", "thermal"},
        timeout=20,
    )
    def create_fairyfly_solid_material(
        name: Annotated[
            str,
            Field(description="Required display name for the Fairyfly/THERM solid material object_dict."),
        ],
        conductivity: Annotated[
            float,
            Field(description="Thermal conductivity in W/m-K."),
        ],
        emissivity: Annotated[
            float,
            Field(description="Front-side infrared hemispherical emissivity."),
        ] = 0.9,
        emissivity_back: Annotated[
            float | None,
            Field(description="Optional back-side emissivity. Defaults to emissivity."),
        ] = None,
        density: Annotated[
            float | None,
            Field(description="Optional density in kg/m3."),
        ] = None,
        porosity: Annotated[
            float | None,
            Field(description="Optional porosity from 0 to 1."),
        ] = None,
        specific_heat: Annotated[
            float | None,
            Field(description="Optional specific heat in J/kg-K."),
        ] = None,
        vapor_diffusion_resistance: Annotated[
            float | None,
            Field(description="Optional vapor diffusion resistance factor."),
        ] = None,
        reflectance: Annotated[
            float | None,
            Field(description="Optional solar reflectance from 0 to 1."),
        ] = None,
        transmittance: Annotated[
            float | None,
            Field(description="Optional solar transmittance from 0 to 1."),
        ] = None,
        rgb_color: Annotated[
            list[int] | None,
            Field(description="Optional RGB color as [r, g, b]."),
        ] = None,
    ) -> dict:
        """Create a Fairyfly SolidMaterial payload."""
        from garden.fairyfly.model import create_fairyfly_solid_material as service

        return service(
            name=name,
            conductivity=conductivity,
            emissivity=emissivity,
            emissivity_back=emissivity_back,
            density=density,
            porosity=porosity,
            specific_heat=specific_heat,
            vapor_diffusion_resistance=vapor_diffusion_resistance,
            reflectance=reflectance,
            transmittance=transmittance,
            rgb_color=rgb_color,
        )

    @mcp.tool(
        name="FF_Model_To_Visualization_Set",
        description=(
            'Create a Ladybug Display VisualizationSet from a Garden Fairyfly model. Set '
            'return_visualization_set=false to save a compact visualization_set_target for '
            'LB_Set_To_HTML, SVG, or vtk.js export.'
        ),
        tags={"fairyfly", "therm", "visualization-set", "model", "visualize", "preview"},
        timeout=20,
    )
    def fairyfly_model_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Fairyfly Model target dict, usually FF_Create_Model['target']; "
                    "defaults to the Garden base Fairyfly Model."
                )
            ),
        ] = None,
        color_by: Annotated[
            str,
            Field(description="Model coloring mode. Supported: material, none."),
        ] = "material",
        include_boundaries: Annotated[
            bool,
            Field(description="Whether to include Fairyfly Boundary line geometry."),
        ] = True,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier and artifact name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Return the full VisualizationSet dict. False saves and returns a compact visualization_set_target for export tools."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Fairyfly model VisualizationSet."""
        from garden.fairyfly.model import fairyfly_model_to_visualization_set as service

        return service(
            garden_root=garden_root,
            model_target=model_target,
            color_by=color_by,
            include_boundaries=include_boundaries,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="FF_Result_To_Visualization_Set",
        description=(
            'Create a Ladybug Display VisualizationSet from Fairyfly THERM temperature or '
            'heat-flux results. Poll FF_Poll_Simulation before visualizing results from a '
            'run_target. If the THMZ has no result arrays, returns no_results instead of creating '
            'an empty view. Returns visualization_set_target when saved.'
        ),
        tags={"fairyfly", "therm", "visualization-set", "result", "visualize", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def fairyfly_therm_result_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        thmz_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional fairyfly_thmz target returned by FF_Write_Model_To_THMZ.'),
        ] = None,
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional completed fairyfly_therm_run target returned by FF_Start_Simulation. Poll before visualizing results.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when thmz_target/run_target are omitted."),
        ] = None,
        data_type: Annotated[
            str,
            Field(description="Result data type to visualize: temperature or heat_flux."),
        ] = "temperature",
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier/name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Whether to return the VisualizationSet body. Set false to save a Garden VisualizationSet target."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a VisualizationSet from a Fairyfly THERM result."""
        from garden.fairyfly.model import fairyfly_therm_result_to_visualization_set as service

        return service(
            garden_root=garden_root,
            thmz_target=thmz_target,
            run_target=run_target,
            run_id=run_id,
            data_type=data_type,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="FF_Get_Base_Model",
        description=(
            'Read the Garden base Fairyfly model target and minimal context. Use '
            'FF_Validate_Model for model validation and THERM tools after a model exists.'
        ),
        tags={"fairyfly", "therm", "model", "summary", "garden"},
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def get_base_fairyfly_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
    ) -> dict[str, Any]:
        """Return the Garden base Fairyfly model target."""
        from garden.store import get_base_fairyfly_model as service

        return service(garden_root=garden_root)

    @mcp.tool(
        name="FF_Poll_Simulation",
        description=(
            "Get one Garden Fairyfly THERM run record by fairyfly_therm_run "
            "target or run_id. Use this after starting a THERM run to inspect "
            "runtime_status without returning large result data. Returns "
            "runtime_status, poll_next, summary_view, and report. Treat a "
            "failed runtime_status as requiring report review before reading THERM "
            "or U-factor results."
        ),
        tags={"fairyfly", "therm", "runtime", "poll", "ledger"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_fairyfly_therm_run(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional fairyfly_therm_run target returned by FF_Start_Simulation.'
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional THERM run identifier when run_target is not supplied."),
        ] = None,
    ) -> dict[str, Any]:
        """Get one Fairyfly THERM run record."""
        from garden.fairyfly.therm import get_fairyfly_therm_run as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)

    @mcp.tool(
        name="FF_List_Runs",
        description=(
            "List Fairyfly THERM run records stored in a Garden. Returns compact "
            "ledger entries, runtime_status values in summary_view, and report "
            "for two-dimensional heat-transfer runs. Use FF_Poll_Simulation on a "
            "specific run before result reads."
        ),
        tags={"fairyfly", "therm", "runtime", "search", "ledger"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_fairyfly_therm_runs(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        status: Annotated[
            str | None,
            Field(description="Optional runtime_status or readiness_status filter for Garden THERM run ledger records, such as completed, failed, or blocked."),
        ] = None,
    ) -> dict[str, Any]:
        """List Fairyfly THERM runs."""
        from garden.fairyfly.therm import list_fairyfly_therm_runs as service

        return service(garden_root=garden_root, status=status)

    @mcp.tool(
        name="FF_Read_Result",
        description=(
            'Read compact temperature or heat-flux statistics from a Fairyfly THERM THMZ file. '
            'Poll FF_Poll_Simulation before reading THERM results from a run_target. If the THMZ '
            'has no result arrays, returns status no_results with a diagnostic. Returns '
            'therm_result_target, summary_view, and report when values exist.'
        ),
        tags={"fairyfly", "therm", "result", "data-collection", "temperature"},
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def read_fairyfly_therm_result(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        thmz_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional fairyfly_thmz target returned by FF_Write_Model_To_THMZ.'),
        ] = None,
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional completed fairyfly_therm_run target returned by FF_Start_Simulation. Poll before reading result data.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when thmz_target/run_target are omitted."),
        ] = None,
        data_type: Annotated[
            str,
            Field(description="Result data type: temperature or heat_flux."),
        ] = "temperature",
        include_values: Annotated[
            bool,
            Field(description="Whether to include raw numeric values in the tool response."),
        ] = False,
    ) -> dict[str, Any]:
        """Read Fairyfly THERM temperature or heat-flux result statistics."""
        from garden.fairyfly.therm import read_fairyfly_therm_result as service

        return service(
            garden_root=garden_root,
            thmz_target=thmz_target,
            run_target=run_target,
            run_id=run_id,
            data_type=data_type,
            include_values=include_values,
        )

    @mcp.tool(
        name="FF_Read_U_Factor",
        description=(
            "Read U-Factor summaries from a Fairyfly THERM THMZ file. Use this "
            "after assigning U-Factor tags, running THERM, and polling "
            "FF_Poll_Simulation before reading from a run_target. If results "
            "are missing, returns no_results with a tag/runtime diagnostic. Returns "
            "u_factor_result_target, summary_view, and report when values exist; use "
            "FF_Read_Result for temperature or heat-flux statistics."
        ),
        tags={"fairyfly", "therm", "u-factor", "result", "summary"},
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def read_fairyfly_u_factor_result(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        thmz_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional fairyfly_thmz target returned by FF_Write_Model_To_THMZ.'),
        ] = None,
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional completed fairyfly_therm_run target returned by FF_Start_Simulation. Poll before reading U-factor results.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when thmz_target/run_target are omitted."),
        ] = None,
    ) -> dict[str, Any]:
        """Read Fairyfly THERM U-Factor result summaries."""
        from garden.fairyfly.therm import read_fairyfly_u_factor_result as service

        return service(
            garden_root=garden_root,
            thmz_target=thmz_target,
            run_target=run_target,
            run_id=run_id,
        )

    @mcp.tool(
        name="FF_Set_Base_Model",
        description=(
            'Register or select an existing Fairyfly model target as the Garden base Fairyfly '
            'model. Returns target, summary_view, and report for downstream Fairyfly tools.'
        ),
        tags={"fairyfly", "therm", "model", "garden", "base-model"},
        timeout=10,
    )
    def set_base_fairyfly_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any],
            Field(description="Fairyfly model target with target_type=fairyfly_model to set as the Garden base Fairyfly model."),
        ],
    ) -> dict[str, Any]:
        """Set the Garden base Fairyfly model."""
        from garden.store import set_domain_base_model

        return set_domain_base_model(
            garden_root=garden_root,
            model_target=model_target,
            domain="fairyfly",
        )

    @mcp.tool(
        name="FF_Start_Simulation",
        description=(
            'Start a Fairyfly THERM two-dimensional heat-transfer run for a Garden Fairyfly model '
            'and return a fairyfly_therm_run target. Use this for a start Fairyfly THERM run '
            'request. THERM execution is Windows-only; when the THERM executable is unavailable, '
            'the tool saves readiness_status=blocked with intervention_reason=missing_runtime. '
            'Returns run_target, runtime_status, poll_next, and report; poll before reading THERM '
            'or U-factor results. Treat a failed runtime_status as requiring report review.'
        ),
        tags={"fairyfly", "therm", "simulate", "u-factor", "runtime", "start"},
        timeout=120,
    )
    def start_fairyfly_therm_run(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Fairyfly Model target dict, usually FF_Create_Model['target']; "
                    "defaults to the Garden base Fairyfly Model."
                )
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable THERM run identifier for the Garden run ledger. Omit to generate one."),
        ] = None,
        silent: Annotated[
            bool,
            Field(description="Run THERM silently when the runtime supports it."),
        ] = True,
    ) -> dict[str, Any]:
        """Start a Fairyfly THERM run and return a run target."""
        from garden.fairyfly.therm import start_fairyfly_therm_run as service

        return service(
            garden_root=garden_root,
            model_target=model_target,
            run_id=run_id,
            silent=silent,
        )

    @mcp.tool(
        name="FF_Validate_Model",
        description=(
            'Validate a Garden-backed Fairyfly Model with Fairyfly SDK checks. Returns '
            'validation_status through summary_view/report, compact issues, object counts, and '
            'report.'
        ),
        tags={"fairyfly", "therm", "model", "validate", "check"},
        timeout=20,
    )
    def validate_fairyfly_model(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Fairyfly Model target dict, usually FF_Create_Model['target']; "
                    "defaults to the Garden base Fairyfly Model."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Validate a Fairyfly model."""
        from garden.fairyfly.model import validate_fairyfly_model as service

        return service(garden_root=garden_root, model_target=model_target)

    @mcp.tool(
        name="FF_Write_Model_To_THMZ",
        description=(
            "Write a Garden Fairyfly two-dimensional heat-transfer model to a "
            "THERM THMZ artifact without starting THERM. Use this when a user "
            "needs an inspectable THERM input file, or before a separate "
            'FF_Start_Simulation call. Returns thmz_target, artifact_target, '
            "and report; result arrays appear only after a THERM run."
        ),
        tags={"fairyfly", "therm", "export", "artifact", "thmz"},
        timeout=60,
    )
    def write_fairyfly_model_to_thmz(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Fairyfly Model target dict, usually FF_Create_Model['target']; "
                    "defaults to the Garden base Fairyfly Model."
                )
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run or artifact identifier. Omit to generate one."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional THMZ artifact file stem. Defaults to model."),
        ] = None,
    ) -> dict[str, Any]:
        """Write a Fairyfly model to a THMZ artifact."""
        from garden.fairyfly.therm import write_fairyfly_model_to_thmz as service

        return service(
            garden_root=garden_root,
            model_target=model_target,
            run_id=run_id,
            name=name,
        )
