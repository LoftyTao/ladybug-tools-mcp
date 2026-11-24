"""garden MCP tools."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


CleanupScope = Literal["artifacts", "flowerpots", "imports", "payloads", "runs", "tmp"]
RunDomain = Literal[
    "all",
    "energy",
    "honeybee_energy",
    "radiance",
    "honeybee_radiance",
    "uwg",
    "dragonfly_uwg",
    "urbanopt",
    "des",
    "dragonfly_des",
    "grid",
    "dragonfly_grid",
    "fairyfly",
]


def _normalize_version_summary(
    summary: dict[str, Any] | str | None,
    details: dict[str, Any] | str | None,
) -> dict[str, Any] | None:
    normalized = {"note": summary} if isinstance(summary, str) else (
        dict(summary) if isinstance(summary, dict) else None
    )
    if details is not None:
        if normalized is None:
            normalized = {"details": details}
        elif "details" not in normalized:
            normalized["details"] = details
    return normalized


def register(mcp: FastMCP) -> None:
    """Register garden tools."""

    @mcp.tool(
        name="GD_Cancel_Run",
        description=(
            "Cancel a queued or running Garden simulation across any domain, terminate its "
            "background worker process (and child process tree on Windows) if active, and mark "
            "the run ledger as cancelled. Pass run_target or run_id (optionally with domain/recipe)."
        ),
        tags={
            "cancel",
            "garden",
            "run",
            "runtime",
        },
        annotations={"destructiveHint": True},
        timeout=30,
    )
    def cancel_garden_run(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional run target returned by a start simulation tool or GD_List_Runs."
            ),
        ] = None,
        domain: Annotated[
            RunDomain | None,
            Field(
                description="Optional run domain when run_target is omitted (e.g., energy, radiance, uwg, urbanopt, des, grid, fairyfly)."
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        recipe: Annotated[
            str | None,
            Field(
                description="Optional recipe name for multi-index domains (e.g., des: urbanopt/sys_param/modelica; grid: rnm/opendss/reopt)."
            ),
        ] = None,
        reason: Annotated[
            str | None,
            Field(description="Optional cancellation reason recorded in the run ledger."),
        ] = None,
    ) -> dict[str, Any]:
        """Cancel an active Garden run and update its ledger."""
        from garden.runs_control import cancel_run as service

        return service(
            garden_root=garden_root,
            run_target=run_target,
            domain=domain,
            run_id=run_id,
            recipe=recipe,
            reason=reason,
        )

    @mcp.tool(
        name="GD_Cleanup_Workspace",
        description=(
            "Remove selected non-authoring Garden workspace directories such as tmp, artifacts, "
            "flowerpots, payloads, imports, or runs. A later workflow recreates its directory "
            "when needed. This maintenance tool does not touch garden.json, models/, or "
            "libraries/, and dry_run reports what would be cleaned before deleting files. Use it "
            "to remove temporary or generated workspace files while preserving project authoring "
            "truth. Returns removed/skipped lists, summary_view, persistence_receipt, and report."
        ),
        tags={
            "cleanup",
            "garden",
            "workspace",
            "maintenance",
        },
        annotations={"destructiveHint": True},
        timeout=30,
    )
    def cleanup_garden_workspace(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root'] or a path selected from GD_List."
            ),
        ],
        cleanup_scopes: Annotated[
            list[CleanupScope],
            Field(
                description=(
                    "Explicit Garden workspace scopes to clean. Allowed values are tmp, "
                    "artifacts, flowerpots, payloads, imports, and runs."
                ),
                min_length=1,
            ),
        ],
        dry_run: Annotated[
            bool,
            Field(
                description="If true, report which selected scopes would be cleaned without deleting files; use this before destructive cleanup when the user has not explicitly confirmed."
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Clean selected non-authoring workspace directories inside one Garden root."""
        from garden.store import (
            cleanup_garden_workspace as cleanup_garden_workspace_service,
        )

        return cleanup_garden_workspace_service(
            garden_root=garden_root,
            cleanup_scopes=list(cleanup_scopes),
            dry_run=dry_run,
        )

    @mcp.tool(
        name="GD_Create",
        description=(
            "Create a Ladybug Tools Garden project workspace with garden.json and a Garden-local .gitignore policy. "
            "When Git is available on PATH, the tool also initializes the Garden-local .git repository by default. "
            "When Git is unavailable, Garden creation still succeeds and report.warnings states that version management is unavailable; "
            "after Git is installed, any Garden version tool initializes the repository. Model, library, import, run, artifact, Flowerpot, payload, and temporary directories are created only when their workflows first write to them. "
            "Use this before authoring models, running simulations, or saving artifacts when no Garden exists yet. "
            "Omit root_dir to use the default Gardens root, or pass root_dir as the exact Garden root path. Existing Gardens are reused idempotently and gain a .git repository when Git is available and the repository is missing; they are not deleted. "
            "Returns garden_root, target/garden_target, summary_view, persistence_receipt, and report; pass the top-level garden_root string to later Garden, Energy, Radiance, and Ironbug tools."
        ),
        tags={
            "garden",
            "project",
            "workspace",
        },
        timeout=20,
    )
    def create_garden(
        name: Annotated[
            str | None,
            Field(
                description="Optional user-facing Garden project name, for example 'Office Study Garden'. If omitted, the name is derived from root_dir or defaults to 'Ladybug Tools Garden'."
            ),
        ] = None,
        root_dir: Annotated[
            str | None,
            Field(
                description=(
                    "Optional exact Garden root path string. If omitted, the Garden is created "
                    "under the default Gardens root; takes the target Garden directory path."
                )
            ),
        ] = None,
        description: Annotated[
            str | None,
            Field(description="Optional Garden description text stored in garden.json."),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(
                description=(
                    "Optional create-tool hygiene flag. Existing Gardens are reused idempotently; "
                    "overwrite does not delete garden.json, models, libraries, or artifacts."
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Create a Garden and return its Garden target, summary, report, and receipt."""
        from garden.store import create_garden as create_garden_service

        name = name or (Path(root_dir).name if root_dir else "Ladybug Tools Garden")
        return create_garden_service(
            name=name, root_dir=root_dir, description=description
        )

    @mcp.tool(
        name="GD_Export_Model_File",
        description=(
            "Export an explicit Garden Honeybee Model or Dragonfly Model target to "
            "a Garden-managed export artifact across energy, daylight, and geometry formats: "
            "doe_inp (.inp), designbuilder_dsbxml (.dsbxml), osm (.osm), idf (.idf), "
            "epjson (.epjson), gbxml (.xml), trace_gbxml (.xml), sdd (.xml), rad (.rad), "
            "rad_folder (directory), hbpkl (.hbpkl), or stl (.stl). "
            "Requires garden_root, export_format, and a nested model_target from "
            "a Honeybee/Dragonfly create tool, GD_List_Models, or GD_Manage_Base_Model. "
            "Accepts optional export_options dict forwarding DOE-2, DesignBuilder, gbXML, "
            "OpenStudio, Radiance, or Dragonfly-to-Honeybee options."
        ),
        tags={
            "artifact",
            "designbuilder",
            "doe2",
            "export",
            "garden",
            "gbxml",
            "honeybee",
            "model",
            "openstudio",
            "radiance",
            "dragonfly",
        },
        timeout=60,
    )
    def export_model_file(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; the model target and export "
                    "artifact must belong to this Garden."
                )
            ),
        ],
        export_format: Annotated[
            Literal[
                "doe_inp",
                "designbuilder_dsbxml",
                "osm",
                "idf",
                "epjson",
                "gbxml",
                "trace_gbxml",
                "sdd",
                "rad",
                "rad_folder",
                "hbpkl",
                "stl",
            ],
            Field(
                description=(
                    "Required export format: doe_inp, designbuilder_dsbxml, osm, idf, epjson, "
                    "gbxml, trace_gbxml, sdd, rad, rad_folder, hbpkl, or stl."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required exact Honeybee Model or Dragonfly Model target. Pass the nested "
                    "model_target dict from a model create, list, or base-model tool. Targets from "
                    "GD_List_Models must include a Garden-relative path to .hbjson or .dfjson."
                )
            ),
        ],
        name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional export artifact file stem without extension; the "
                    "extension is chosen from export_format."
                )
            ),
        ] = None,
        include_body: Annotated[
            bool,
            Field(
                description=(
                    "Return the exported text as file_body for text-based formats. Keep "
                    "false for compact artifact targets."
                )
            ),
        ] = False,
        export_options: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional format-specific export options forwarded to DOE-2, DesignBuilder, "
                    "gbXML, TRACE gbXML, OpenStudio, IDF, SDD, Radiance, HBpkl, or Dragonfly-to-Honeybee."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Export a Honeybee or Dragonfly model file artifact."""
        from garden.model_export import export_model_file as service

        return service(
            garden_root=garden_root,
            export_format=export_format,
            model_target=model_target,
            name=name,
            include_body=include_body,
            export_options=export_options,
        )

    @mcp.tool(
        name="GD_Get",
        description=(
            "Read a compact Garden manifest summary from an existing garden_root. Use this after "
            "GD_List or GD_Create to confirm the selected Garden exists, retrieve its "
            "target/garden_target, see separate Honeybee, Dragonfly, and Fairyfly base-model "
            "targets, and check model/artifact counts. Read-only manifest check. Returns "
            "garden_root, target/garden_target, summary_view, and report."
        ),
        tags={
            "garden",
            "project",
            "summary",
            "check",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_garden(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root'] or a path selected from GD_List matches."
            ),
        ],
    ) -> dict[str, Any]:
        """Return a compact Garden manifest summary."""
        from garden.store import get_garden as service

        return service(garden_root=garden_root)

    @mcp.tool(
        name="GD_List",
        description=(
            "List existing Ladybug Tools Garden project workspaces by finding folders that contain garden.json. "
            "Use this when a user asks to find saved Gardens, choose a project workspace, or continue prior work. "
            "Results are sorted with the most recent Gardens first and may include root paths, descriptions, and base-model summaries. "
            "Returns matches with reusable garden_target objects plus summary_view cleanup guidance; pass a selected match path as garden_root to GD_Get or downstream tools."
        ),
        tags={
            "garden",
            "project",
            "search",
            "workspace",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def list_gardens(
        root_dir: Annotated[
            str | None,
            Field(
                description="Optional directory to search for Garden folders. If omitted, the default Gardens root is searched; a direct Garden root containing garden.json is also accepted."
            ),
        ] = None,
        include_paths: Annotated[
            bool,
            Field(description="Whether to include Garden root path strings in matches."),
        ] = True,
        include_base_models: Annotated[
            bool,
            Field(
                description="Whether to include each Garden's base_honeybee_model, base_dragonfly_model, and related base-model summaries when present."
            ),
        ] = True,
        include_description: Annotated[
            bool,
            Field(description="Whether to include each Garden description stored in garden.json."),
        ] = True,
    ) -> dict[str, Any]:
        """List Gardens under a root directory."""
        from garden.store import list_gardens as list_gardens_service

        return list_gardens_service(
            root_dir=root_dir,
            include_paths=include_paths,
            include_base_models=include_base_models,
            include_description=include_description,
        )

    @mcp.tool(
        name="GD_List_Artifacts",
        description=(
            "List visualization, report, validation, export, weather, Radiance, THERM, UWG, and "
            "simulation-run artifacts recorded in a Garden manifest. Supports artifact_type aliases "
            "(sky, view, sensor_grid, hdr, gif, wea, vtkjs, html, svg) or canonical types, plus "
            "optional domain, query substring, and limit filters. Returns matches, artifact_paths, "
            "summary_view, and report."
        ),
        tags={
            "artifact",
            "garden",
            "result",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def list_garden_artifacts(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root'] or GD_Get['garden_root']."
            ),
        ],
        artifact_type: Annotated[
            str | None,
            Field(
                description=(
                    "Optional artifact type filter or alias, e.g. sky/radiance_sky_file, view/radiance_view, "
                    "sensor_grid/radiance_sensor_grid, hdr/radiance_hdr_image, gif/radiance_gif_image, "
                    "wea/wea_file, vtkjs/visualization_vtkjs, html/visualization_html, svg/visualization_svg, "
                    "or fairyfly_therm_result."
                )
            ),
        ] = None,
        domain: Annotated[
            str | None,
            Field(
                description="Optional domain filter (e.g., honeybee_radiance, honeybee_energy, visualize, fairyfly, dragonfly_uwg, dragonfly_des, dragonfly_grid, urbanopt)."
            ),
        ] = None,
        query: Annotated[
            str | None,
            Field(
                description="Optional case-insensitive substring matched against artifact name, identifier, path, type, or domain."
            ),
        ] = None,
        limit: Annotated[
            int | None,
            Field(description="Optional maximum number of matching artifacts to return.", ge=1),
        ] = None,
    ) -> dict[str, Any]:
        """List Garden artifacts."""
        from garden.store import list_garden_artifacts as service

        return service(
            garden_root=garden_root,
            artifact_type=artifact_type,
            domain=domain,
            query=query,
            limit=limit,
        )

    @mcp.tool(
        name="GD_List_Models",
        description=(
            "List registered Honeybee, Dragonfly, Fairyfly, and Ironbug model targets in a Garden, "
            "including HBJSON, DFJSON, FFJSON, and IBJSON authoring records. Use this to choose an "
            "existing model target before edit, export, visualization, energy, Radiance, THERM, or "
            "DetailedHVAC workflows. Returns matches plus summary_view with base_honeybee_model, "
            "base_dragonfly_model, and base_fairyfly_model when present; Ironbug models have no base slot."
        ),
        tags={
            "garden",
            "model",
            "search",
            "honeybee",
            "dragonfly",
            "fairyfly",
            "ironbug",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def list_garden_models(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root'] or GD_Get['garden_root']."
            ),
        ],
        include_paths: Annotated[
            bool,
            Field(
                description="Whether to include Garden-relative HBJSON, DFJSON, FFJSON, or IBJSON model file paths in each match."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """List registered Garden model targets."""
        from garden.store import list_garden_models as service

        return service(garden_root=garden_root, include_paths=include_paths)

    @mcp.tool(
        name="GD_List_Runs",
        description=(
            "List simulation run records across all or one Garden domain (energy, radiance, uwg, "
            "urbanopt, des, grid, fairyfly), sorted newest first. Returns matches carrying "
            "target/run_target, domain, recipe, status, created_at, and run_folder for use with "
            "GD_Poll_Run, GD_Cancel_Run, and GD_Read_Run_Logs."
        ),
        tags={
            "garden",
            "ledger",
            "run",
            "runtime",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_garden_runs(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        domain: Annotated[
            RunDomain,
            Field(
                description="Domain filter ('all', 'energy', 'radiance', 'uwg', 'urbanopt', 'des', 'grid', 'fairyfly', or full domain names)."
            ),
        ] = "all",
        status: Annotated[
            str | None,
            Field(
                description="Optional status filter such as running, queued, completed, failed, blocked, or cancelled."
            ),
        ] = None,
        limit: Annotated[
            int | None,
            Field(description="Optional maximum number of newest runs to return.", ge=1),
        ] = None,
    ) -> dict[str, Any]:
        """List Garden runs across domains."""
        from garden.runs_control import list_runs as service

        return service(
            garden_root=garden_root,
            domain=domain,
            status=status,
            limit=limit,
        )

    @mcp.tool(
        name="GD_Manage_Base_Model",
        description=(
            "Read ('get'), select ('set'), or persist ('save') a Garden base model slot for "
            "Honeybee, Dragonfly, or Fairyfly. For action='get', omit domain to read all three slots "
            "or pass domain to read one slot. For action='set', pass model_target (and optional domain). "
            "For action='save', persists the current base HBJSON, DFJSON, or FFJSON model back to "
            "Garden authoring truth."
        ),
        tags={
            "author",
            "base-model",
            "dragonfly",
            "fairyfly",
            "garden",
            "honeybee",
            "model",
            "target",
        },
        timeout=20,
    )
    def manage_base_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        action: Annotated[
            Literal["get", "set", "save"],
            Field(
                description="Base-model operation: 'get' slot(s), 'set' active model_target, or 'save' base model to disk."
            ),
        ],
        domain: Annotated[
            Literal["honeybee", "dragonfly", "fairyfly"] | None,
            Field(
                description="Optional model domain ('honeybee', 'dragonfly', or 'fairyfly'). For 'get', omit to inspect all three."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Required for action='set': nested Honeybee, Dragonfly, or Fairyfly model_target dict."
            ),
        ] = None,
        message: Annotated[
            str | None,
            Field(description="For action='save': optional short save note stored in persistence_receipt."),
        ] = None,
        force: Annotated[
            bool,
            Field(description="For action='save': force the persistence receipt status to report persisted."),
        ] = False,
        name: Annotated[
            str | None,
            Field(description="For action='save': optional output file stem without extension."),
        ] = None,
        indent: Annotated[
            int | None,
            Field(description="For action='save': JSON indentation for the saved model file; defaults to 2."),
        ] = 2,
        included_prop: Annotated[
            list[str] | None,
            Field(description="For action='save' (Honeybee/Dragonfly): extension property names to include."),
        ] = None,
        triangulate_sub_faces: Annotated[
            bool,
            Field(description="For action='save' (Honeybee): whether sub-faces should be triangulated."),
        ] = False,
    ) -> dict[str, Any]:
        """Get, set, or save a Garden base model slot."""
        from garden.store import manage_base_model as service

        return service(
            garden_root=garden_root,
            action=action,
            domain=domain,
            model_target=model_target,
            message=message,
            force=force,
            name=name,
            indent=indent,
            included_prop=included_prop,
            triangulate_sub_faces=triangulate_sub_faces,
        )

    @mcp.tool(
        name="GD_Manage_Versions",
        description=(
            "Inspect, list, create, or restore Git-backed Garden authoring-truth checkpoints "
            "(garden.json, models/, libraries/). Use action='status' to check dirty state, "
            "action='list' for newest-first version targets, action='create' (requires subject) "
            "to commit a checkpoint, and action='restore' (requires version_id or version_target) "
            "to restore a prior checkpoint as a new commit."
        ),
        tags={
            "checkpoint",
            "garden",
            "history",
            "restore",
            "rollback",
            "version",
        },
        annotations={"destructiveHint": True},
        timeout=30,
    )
    def manage_garden_versions(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        action: Annotated[
            Literal["status", "list", "create", "restore"],
            Field(
                description="Version operation: 'status', 'list', 'create', or 'restore'."
            ),
        ],
        version_id: Annotated[
            str | None,
            Field(
                description="For action='restore': Garden version_id from GD_Manage_Versions(action='list')."
            ),
        ] = None,
        version_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="For action='restore': optional nested garden_version target containing version_id."
            ),
        ] = None,
        subject: Annotated[
            str | None,
            Field(
                description="Required for action='create'; optional short commit subject for action='restore'."
            ),
        ] = None,
        summary: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional compact structured summary stored in the version commit."),
        ] = None,
        details: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional compact details merged into summary."),
        ] = None,
        source: Annotated[
            str | None,
            Field(
                description="Optional source label for history records, such as agent, user, grasshopper, manual, or test."
            ),
        ] = "agent",
        limit: Annotated[
            int,
            Field(
                description="For action='list': maximum number of newest version records to return (1-50).",
                ge=1,
                le=50,
            ),
        ] = 10,
    ) -> dict[str, Any]:
        """Manage Garden authoring-truth versions."""
        if action == "status":
            from garden.versions import get_garden_version_status as service

            return service(garden_root=garden_root)
        if action == "list":
            from garden.versions import list_garden_versions as service

            return service(garden_root=garden_root, limit=limit)
        normalized_summary = _normalize_version_summary(summary, details)
        if action == "create":
            if not subject or not subject.strip():
                raise ValueError("subject is required when action='create'.")
            from garden.versions import create_garden_version as service

            return service(
                garden_root=garden_root,
                subject=subject,
                summary=normalized_summary,
                source=source,
            )

        resolved_version_id = version_id
        if resolved_version_id is None and isinstance(version_target, dict):
            raw_id = version_target.get("version_id")
            resolved_version_id = str(raw_id) if raw_id else None
        if not resolved_version_id:
            raise ValueError("version_id or version_target is required when action='restore'.")
        from garden.versions import restore_garden_version as service

        return service(
            garden_root=garden_root,
            version_id=resolved_version_id,
            subject=subject,
            summary=normalized_summary,
            source=source,
        )

    @mcp.tool(
        name="GD_Poll_Run",
        description=(
            "Poll one Garden simulation run across any domain (energy, radiance, uwg, urbanopt, "
            "des, grid, fairyfly). Optionally pass wait_seconds to block until queued/running "
            "work settles or the timeout elapses. Set include_outputs=false for lightweight status "
            "polling without output arrays. Returns target/run_target, runtime_status, summary_view, "
            "and report."
        ),
        tags={
            "garden",
            "ledger",
            "poll",
            "run",
            "runtime",
        },
        annotations={"readOnlyHint": True},
        timeout=330,
    )
    def poll_garden_run(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional run target returned by any start simulation tool or GD_List_Runs."
            ),
        ] = None,
        domain: Annotated[
            RunDomain | None,
            Field(
                description="Optional run domain when run_target is omitted (e.g., energy, radiance, uwg, urbanopt, des, grid, fairyfly)."
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        recipe: Annotated[
            str | None,
            Field(
                description="Optional recipe name for multi-index domains (e.g., des: urbanopt/sys_param/modelica; grid: rnm/opendss/reopt)."
            ),
        ] = None,
        wait_seconds: Annotated[
            float | None,
            Field(
                description="Optional maximum seconds to wait while the run is queued or running.",
                ge=0,
            ),
        ] = None,
        poll_interval: Annotated[
            float | None,
            Field(
                description="Optional sleep interval in seconds between status checks while waiting (defaults to 1.0).",
                gt=0,
            ),
        ] = None,
        include_outputs: Annotated[
            bool,
            Field(description="Include output file metadata in the response; set false for compact polling."),
        ] = True,
    ) -> dict[str, Any]:
        """Poll one Garden run across any domain."""
        from garden.runs_control import poll_run as service

        return service(
            garden_root=garden_root,
            run_target=run_target,
            domain=domain,
            run_id=run_id,
            recipe=recipe,
            wait_seconds=wait_seconds,
            poll_interval=poll_interval,
            include_outputs=include_outputs,
        )

    @mcp.tool(
        name="GD_Read_Run_Logs",
        description=(
            "Read the tail of a run's background stdio or engine error log strictly inside its "
            "run_folder (searching background_stdio.log, recipe_stdio.log, uwg_stdio.log, "
            "eplusout.err, or a caller-specified relative log_file). Returns log_text, log_file, "
            "available_logs, summary_view, and report."
        ),
        tags={
            "diagnostics",
            "garden",
            "logs",
            "run",
            "runtime",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def read_garden_run_logs(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional run target returned by any start simulation tool or GD_List_Runs."
            ),
        ] = None,
        domain: Annotated[
            RunDomain | None,
            Field(
                description="Optional run domain when run_target is omitted (e.g., energy, radiance, uwg, urbanopt, des, grid, fairyfly)."
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        recipe: Annotated[
            str | None,
            Field(
                description="Optional recipe name for multi-index domains (e.g., des: urbanopt/sys_param/modelica; grid: rnm/opendss/reopt)."
            ),
        ] = None,
        tail_lines: Annotated[
            int,
            Field(description="Number of trailing lines to read from the selected log file.", ge=1),
        ] = 100,
        log_file: Annotated[
            str | None,
            Field(
                description="Optional relative path inside the run_folder (e.g. 'background_stdio.log' or 'openstudio/run/eplusout.err')."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Read tail lines from one Garden run's contained log file."""
        from garden.runs_control import read_run_logs as service

        return service(
            garden_root=garden_root,
            run_target=run_target,
            domain=domain,
            run_id=run_id,
            recipe=recipe,
            tail_lines=tail_lines,
            log_file=log_file,
        )
