"""garden MCP tools."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


CleanupScope = Literal["artifacts", "flowerpots", "imports", "payloads", "runs", "tmp"]


def register(mcp: FastMCP) -> None:
    """Register garden tools."""

    @mcp.tool(
        name="GD_Cleanup_Workspace",
        description=(
            'Remove selected non-authoring Garden workspace directories such as tmp, artifacts, '
            'flowerpots, payloads, imports, or runs. A later workflow recreates its directory '
            'when needed. This maintenance tool does not touch garden.json, models/, or '
            'libraries/, and dry_run reports what would be cleaned before deleting files. Use it '
            'to remove temporary or generated workspace files while preserving project authoring '
            'truth. Returns removed/skipped lists, summary_view, persistence_receipt, and report.'
        ),
        tags={
            "cleanup",
            "garden",
            "workspace",
            "maintenance",
        },
        timeout=30,
    )
    def cleanup_garden_workspace(
        garden_root: Annotated[
            str, Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root'] or a path selected from GD_List.")
        ],
        cleanup_scopes: Annotated[
            list[CleanupScope],
            Field(
                description=(
                    'Explicit Garden workspace scopes to clean. Allowed values are tmp, '
                    'artifacts, flowerpots, payloads, imports, and runs.'
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
        description='Create a Ladybug Tools Garden project workspace with garden.json and a Garden-local .gitignore policy. When Git is available on PATH, the tool also initializes the Garden-local .git repository by default. When Git is unavailable, Garden creation still succeeds and report.warnings states that version management is unavailable; after Git is installed, any Garden version tool initializes the repository. Model, library, import, run, artifact, Flowerpot, payload, and temporary directories are created only when their workflows first write to them. Use this before authoring models, running simulations, or saving artifacts when no Garden exists yet. Omit root_dir to use the default Gardens root, or pass root_dir as the exact Garden root path. Existing Gardens are reused idempotently and gain a .git repository when Git is available and the repository is missing; they are not deleted. Returns garden_root, target/garden_target, summary_view, persistence_receipt, and report; pass the top-level garden_root string to later Garden, Energy, Radiance, and Ironbug tools.',
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
                    'Optional exact Garden root path string. If omitted, the Garden is created '
                    'under the default Gardens root; takes the target Garden directory path.'
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
        name="GD_Create_Version",
        description=(
            'Create a compact Garden version checkpoint tracking garden.json, models, and '
            'libraries. Returns target, version_target, summary_view, and persistence_receipt '
            'metadata without file bodies or diffs.'
        ),
        tags={
            "checkpoint",
            "garden",
            "history",
            "version",
        },
        timeout=20,
    )
    def create_garden_version(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; this must be the Garden whose "
                    "authoring truth should receive the version checkpoint."
                )
            ),
        ],
        subject: Annotated[
            str,
            Field(
                description=(
                    "Required short checkpoint subject, for example 'add office windows' or 'feat: "
                    "add office windows'."
                )
            ),
        ],
        summary: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    'Optional compact structured summary for the Garden version.'
                )
            ),
        ] = None,
        details: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    'Optional compact structured details merged into summary.'
                )
            ),
        ] = None,
        source: Annotated[
            str | None,
            Field(
                description=(
                    "Optional source label for the Garden history record, such as "
                    "agent, user, grasshopper, manual, or test."
                )
            ),
        ] = "agent",
    ) -> dict[str, Any]:
        """Create a Garden version."""
        from garden.versions import create_garden_version as service

        if isinstance(summary, str):
            summary = {"note": summary}
        if details is not None:
            if summary is None:
                summary = {"details": details}
            elif isinstance(summary, dict) and "details" not in summary:
                summary = {**summary, "details": details}
        return service(
            garden_root=garden_root,
            subject=subject,
            summary=summary,
            source=source,
        )

    @mcp.tool(
        name="GD_Export_Model_File",
        description=(
            "Export an explicit Garden Honeybee Model or Dragonfly Model target to "
            "a Garden-managed DOE-2 INP or DesignBuilder dsbXML export artifact. "
            "Requires garden_root, export_format, and a nested model_target from "
            "a Honeybee/Dragonfly create tool, GD_List_Models, "
            "GD_Get_Base_Honeybee_Model, or GD_Get_Base_Dragonfly_Model. "
            "The tool derives Honeybee vs Dragonfly from model_target, validates "
            "that the source is a Garden-relative .hbjson or .dfjson file, and "
            "returns target, model_export_artifact_target, artifact_receipt, "
            "summary_view, and report. It does not export arbitrary files and "
            "does not return file_body unless include_body is true."
        ),
        tags={
            "artifact",
            "designbuilder",
            "doe2",
            "export",
            "garden",
            "honeybee",
            "model",
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
            Literal["doe_inp", "designbuilder_dsbxml"],
            Field(
                description=(
                    "Required export format enum. Use doe_inp for a DOE-2 .inp "
                    "artifact or designbuilder_dsbxml for a DesignBuilder .dsbxml "
                    "artifact; the same value becomes the artifact type."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required exact Honeybee Model or Dragonfly Model target. Pass the nested '
                    'model_target dict from a model create, list, or base-model tool. Targets from '
                    'GD_List_Models must include a Garden-relative path to .hbjson or .dfjson.'
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
                    'Return the exported DOE-2 INP or DesignBuilder dsbXML text as file_body. Keep '
                    'false for compact artifact targets.'
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Export a Honeybee or Dragonfly model file artifact."""
        from garden.model_export import export_model_file as service

        return service(
            garden_root=garden_root,
            export_format=export_format,
            model_target=model_target,
            name=name,
            include_body=include_body,
        )

    @mcp.tool(
        name="GD_Get_Base_Dragonfly_Model",
        description=(
            'Read the current Garden base Dragonfly model slot and return its target handoff with '
            'minimal summary_view context. Use this when a later Dragonfly, UWG, visualization, '
            'Honeybee conversion, or export tool needs the active Dragonfly model target. Use '
            'GD_List_Models to list all models and DF_Validate_Model to validate.'
        ),
        tags={
            "base-model",
            "dragonfly",
            "garden",
            "model",
            "summary",
            "target",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def get_base_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; read the Dragonfly base-model "
                    "slot from this Garden manifest."
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Return the Garden base Dragonfly model target."""
        from garden.store import get_base_dragonfly_model as service

        return service(garden_root=garden_root)

    @mcp.tool(
        name="GD_Get_Base_Honeybee_Model",
        description=(
            'Read the current Garden base Honeybee model slot and return its target handoff with '
            'minimal summary_view context. Use this when a later Honeybee, Energy, Radiance, '
            'visualization, or export tool needs the active Honeybee model target. Use '
            'GD_List_Models to list all models and HB_Validate_Model to validate.'
        ),
        tags={
            "base-model",
            "garden",
            "honeybee",
            "model",
            "summary",
            "target",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def get_base_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; read the Honeybee base-model "
                    "slot from this Garden manifest."
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Return the Garden base Honeybee model target."""
        from garden.store import get_base_honeybee_model as service

        return service(garden_root=garden_root)

    @mcp.tool(
        name="GD_Get",
        description=(
            'Read a compact Garden manifest summary from an existing garden_root. Use this after '
            'GD_List or GD_Create to confirm the selected Garden exists, retrieve its '
            'target/garden_target, see separate Honeybee, Dragonfly, and Fairyfly base-model '
            'targets, and check model/artifact counts. Read-only manifest check. Returns '
            'garden_root, target/garden_target, summary_view, and report.'
        ),
        tags={
            "garden",
            "project",
            "summary",
            "check",
        },
        timeout=20,
    )
    def get_garden(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root'] or a path selected from GD_List matches."),
        ],
    ) -> dict:
        """Return a compact Garden manifest summary."""
        from garden.store import get_garden as service

        return service(garden_root=garden_root)

    @mcp.tool(
        name="GD_Get_Version_Status",
        description=(
            'Check whether Garden authoring truth has uncommitted changes that should become a '
            'Garden version checkpoint. Use before restore or after authoring changes to decide '
            'whether GD_Create_Version is needed. Returns compact dirty-state counts in '
            'summary_view and a report.'
        ),
        tags={
            "checkpoint",
            "garden",
            "history",
            "summary",
            "version",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def get_garden_version_status(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; the status covers Garden "
                    "authoring truth paths, not arbitrary files."
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Return Garden version status."""
        from garden.versions import get_garden_version_status as service

        return service(garden_root=garden_root)

    @mcp.tool(
        name="GD_List_Artifacts",
        description='List visualization, report, validation, export, weather, Radiance, THERM, UWG, and simulation-run artifacts recorded in a Garden manifest. Pass garden_root from GD_Create/GD_Get and optional artifact_type to narrow results to one artifact family such as vtkjs, html, epw, sql, err, wea, sky, or therm output when those records exist. Returns matches plus summary_view and report; each match is an artifact_target-style record for follow-up export, inspection, visualization, or result-reading tools.',
        tags={
            "artifact",
            "garden",
            "result",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def list_garden_artifacts(
        garden_root: Annotated[
            str, Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root'] or GD_Get['garden_root'].")
        ],
        artifact_type: Annotated[
            str | None, Field(description="Optional artifact type filter matching artifact records in garden.json, for example vtkjs, html, epw, sql, err, wea, radiance_sky_file, or fairyfly_therm_result when present.")
        ] = None,
    ) -> dict[str, Any]:
        """List Garden artifacts."""
        from garden.store import list_garden_artifacts as service

        return service(garden_root=garden_root, artifact_type=artifact_type)

    @mcp.tool(
        name="GD_List_Models",
        description="List registered Honeybee, Dragonfly, Fairyfly, and Ironbug model targets in a Garden, including HBJSON, DFJSON, FFJSON, and IBJSON authoring records. Use this to choose an existing model target before edit, export, visualization, energy, Radiance, THERM, or DetailedHVAC workflows. Returns matches plus summary_view with base_honeybee_model, base_dragonfly_model, and base_fairyfly_model when present; Ironbug models have no base slot. Pass a selected model target to downstream model tools.",
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
            str, Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root'] or GD_Get['garden_root'].")
        ],
        include_paths: Annotated[
            bool,
            Field(description="Whether to include Garden-relative HBJSON, DFJSON, FFJSON, or IBJSON model file paths in each match."),
        ] = True,
    ) -> dict[str, Any]:
        """List registered Garden model targets."""
        from garden.store import list_garden_models as service

        return service(garden_root=garden_root, include_paths=include_paths)

    @mcp.tool(
        name="GD_List_Versions",
        description=(
            'List compact Garden version history for choosing undo, restore, go back, previous '
            'step, checkpoint, or rollback targets. Returns newest-first records under matches '
            "and versions; pass a record's version_id or target to GD_Restore_Version. Records "
            'include subjects, metadata, and version targets without diffs or file bodies.'
        ),
        tags={
            "checkpoint",
            "garden",
            "history",
            "rollback",
            "restore",
            "search",
            "version",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def list_garden_versions(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; list history for this one Garden."
                )
            ),
        ],
        limit: Annotated[
            int,
            Field(
                description=(
                    "Maximum number of newest Garden version records to return "
                    "under matches and versions; use 1-50."
                ),
                ge=1,
                le=50,
            ),
        ] = 10,
    ) -> dict[str, Any]:
        """List Garden versions."""
        from garden.versions import list_garden_versions as service

        return service(garden_root=garden_root, limit=limit)

    @mcp.tool(
        name="GD_List",
        description="List existing Ladybug Tools Garden project workspaces by finding folders that contain garden.json. Use this when a user asks to find saved Gardens, choose a project workspace, or continue prior work. Results are sorted with the most recent Gardens first and may include root paths, descriptions, and base-model summaries. Returns matches with reusable garden_target objects plus summary_view cleanup guidance; pass a selected match path as garden_root to GD_Get or downstream tools.",
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
            Field(description="Optional directory to search for Garden folders. If omitted, the default Gardens root is searched; a direct Garden root containing garden.json is also accepted."),
        ] = None,
        include_paths: Annotated[
            bool, Field(description='Whether to include Garden root path strings in matches.')
        ] = True,
        include_base_models: Annotated[
            bool,
            Field(description="Whether to include each Garden's base_honeybee_model, base_dragonfly_model, and related base-model summaries when present."),
        ] = True,
        include_description: Annotated[
            bool, Field(description="Whether to include each Garden description stored in garden.json.")
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
        name="GD_Restore_Version",
        description=(
            'Restore, undo, go back, or roll back Garden authoring truth to a previous Garden '
            'version checkpoint and record that restore as a new history item. Pass either the '
            'version_id from GD_List_Versions matches/versions or the nested garden_version '
            'target as version_target. Returns summary_view, restored_from_version, new_version, '
            'version_target, and persistence_receipt metadata only. Requires clean authoring '
            'truth, appends a new history entry without rewriting history, and returns metadata '
            'only.'
        ),
        tags={
            "checkpoint",
            "garden",
            "history",
            "rollback",
            "restore",
            "version",
        },
        timeout=30,
    )
    def restore_garden_version(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; restore only this Garden's "
                    "authoring truth paths."
                )
            ),
        ],
        version_id: Annotated[
            str | None,
            Field(
                description=(
                    'Garden version_id string from GD_List_Versions matches/versions. Required unless '
                    'version_target is provided.'
                )
            ),
        ] = None,
        version_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional nested garden_version target from GD_List_Versions, "
                    "GD_Create_Version, or GD_Restore_Version. Expected "
                    "shape includes target_type='garden_version', garden_id, and "
                    "version_id; use this instead of the version_id string when "
                    "passing the target handoff is easier."
                )
            ),
        ] = None,
        subject: Annotated[
            str | None,
            Field(
                description=(
                    "Optional short subject for the new Garden restore history "
                    "record. Defaults to restore: garden version <short id>."
                )
            ),
        ] = None,
        summary: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Optional compact restore summary.'
                )
            ),
        ] = None,
        source: Annotated[
            str | None,
            Field(
                description=(
                    "Optional source label for the Garden restore history record, "
                    "such as agent, user, grasshopper, manual, or test."
                )
            ),
        ] = "agent",
    ) -> dict[str, Any]:
        """Restore a Garden version as a new history entry."""
        from garden.versions import restore_garden_version as service

        resolved_version_id = version_id
        if resolved_version_id is None and version_target:
            raw_id = version_target.get("version_id")
            resolved_version_id = str(raw_id) if raw_id else None
        if not resolved_version_id:
            raise ValueError("version_id or version_target is required.")
        return service(
            garden_root=garden_root,
            version_id=resolved_version_id,
            subject=subject,
            summary=summary,
            source=source,
        )

    @mcp.tool(
        name="GD_Save_Base_Dragonfly_Model",
        description=(
            'Persist the current Garden base Dragonfly model back to Garden authoring truth as '
            'DFJSON. Use after Dragonfly edits have changed the in-memory base model and you need '
            'a fresh model_target before versioning, UWG, visualization, Honeybee conversion, or '
            'export. Returns model_target, summary_view, and persistence_receipt.'
        ),
        tags={
            "author",
            "base-model",
            "dragonfly",
            "garden",
            "model",
        },
        timeout=20,
    )
    def save_base_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; save the current Dragonfly "
                    "base-model slot for this Garden."
                )
            ),
        ],
        message: Annotated[
            str | None,
            Field(
                description=(
                    'Optional short save note stored in the persistence receipt and summary_view.'
                )
            ),
        ] = None,
        force: Annotated[
            bool,
            Field(
                description=(
                    "Force the persistence receipt to report a save even when the "
                    "serialized Dragonfly model target appears unchanged."
                )
            ),
        ] = False,
        name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional DFJSON file stem without extension; defaults to the "
                    "current base Dragonfly model identifier."
                )
            ),
        ] = None,
        indent: Annotated[
            int | None,
            Field(description="JSON indentation for the saved DFJSON file; defaults to 2."),
        ] = 2,
        included_prop: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Dragonfly extension property names to include in DFJSON; "
                    "None keeps the SDK default, usually all relevant properties."
                )
            ),
        ] = None,
    ) -> dict[str, object]:
        """Save the current Garden base Dragonfly model."""
        from garden.store import save_base_dragonfly_model as service

        return service(
            garden_root=garden_root,
            message=message,
            force=force,
            name=name,
            indent=indent,
            included_prop=included_prop,
        )

    @mcp.tool(
        name="GD_Save_Base_Honeybee_Model",
        description=(
            "Persist the current Garden base Honeybee model back to Garden "
            "authoring truth as HBJSON. Use after Honeybee edits have changed the "
            "in-memory base model and you need a fresh model_target before "
            "versioning, Energy, Radiance, visualization, or export. Returns "
            "model_target, summary_view, and persistence_receipt; it does not "
            "create a Garden version checkpoint and does not return the full "
            "HBJSON body."
        ),
        tags={
            "author",
            "base-model",
            "garden",
            "honeybee",
            "model",
        },
        timeout=20,
    )
    def save_base_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; save the current Honeybee "
                    "base-model slot for this Garden."
                )
            ),
        ],
        message: Annotated[
            str | None,
            Field(
                description=(
                    'Optional short save note stored in the persistence receipt and summary_view.'
                )
            ),
        ] = None,
        force: Annotated[
            bool,
            Field(
                description=(
                    "Force the persistence receipt to report a save even when the "
                    "serialized Honeybee model target appears unchanged."
                )
            ),
        ] = False,
        name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional HBJSON file stem without extension; defaults to the "
                    "current base Honeybee model identifier."
                )
            ),
        ] = None,
        indent: Annotated[
            int | None,
            Field(description="JSON indentation for the saved HBJSON file; defaults to 2."),
        ] = 2,
        included_prop: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Honeybee extension property names to include in HBJSON; "
                    "None keeps the SDK default, usually all relevant properties."
                )
            ),
        ] = None,
        triangulate_sub_faces: Annotated[
            bool,
            Field(
                description=(
                    "Whether Honeybee sub-faces should be triangulated during "
                    "HBJSON serialization."
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Save the current Garden base Honeybee model."""
        from garden.store import save_base_honeybee_model as service

        return service(
            garden_root=garden_root,
            message=message,
            force=force,
            name=name,
            indent=indent,
            included_prop=included_prop,
            triangulate_sub_faces=triangulate_sub_faces,
        )

    @mcp.tool(
        name="GD_Set_Base_Dragonfly_Model",
        description=(
            'Register or select an existing Dragonfly model target as the Garden base Dragonfly '
            'model slot. Pass the nested model_target from a Dragonfly create tool, '
            'GD_List_Models, or another base-model handoff; this writes garden.json and may add '
            'the target to the manifest model list. Returns model_target, summary_view, and '
            'persistence_receipt for subsequent Dragonfly, UWG, visualization, Honeybee '
            'conversion, versioning, or export calls.'
        ),
        tags={
            "author",
            "base-model",
            "dragonfly",
            "garden",
            "model",
            "target",
        },
        timeout=10,
    )
    def set_base_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; set the Dragonfly base-model "
                    "slot in this Garden manifest."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Nested Dragonfly model target to set as the Garden base Dragonfly model. Pass '
                    'the nested model_target dict.'
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Set the Garden base Dragonfly model."""
        from garden.store import set_domain_base_model

        return set_domain_base_model(
            garden_root=garden_root,
            model_target=model_target,
            domain="dragonfly",
        )

    @mcp.tool(
        name="GD_Set_Base_Honeybee_Model",
        description=(
            'Register or select an existing Honeybee model target as the Garden base Honeybee '
            'model slot. Pass the nested model_target from a Honeybee create tool, '
            'GD_List_Models, or another base-model handoff; this writes garden.json and may add '
            'the target to the manifest model list. Returns model_target, summary_view, and '
            'persistence_receipt for subsequent Honeybee, Energy, Radiance, visualization, '
            'versioning, or export calls.'
        ),
        tags={
            "author",
            "base-model",
            "garden",
            "honeybee",
            "model",
            "target",
        },
        timeout=10,
    )
    def set_base_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; set the Honeybee base-model "
                    "slot in this Garden manifest."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Nested Honeybee model target to set as the Garden base Honeybee model. Pass the '
                    'nested model_target dict.'
                )
            ),
        ],
    ) -> dict[str, Any]:
        """Set the Garden base Honeybee model."""
        from garden.store import set_domain_base_model

        return set_domain_base_model(
            garden_root=garden_root,
            model_target=model_target,
            domain="honeybee",
        )
