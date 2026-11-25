"""web_view MCP tools."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.manifest import GardenManifest
from ladybug_tools_mcp.contracts import (
    ArtifactResultModel,
    BuildingModelTargetRef,
    BuildingObjectTargetRef,
    ToolResultModel,
    dump_input,
    dump_target,
    dump_targets,
    make_report,
    validate_output,
)
from web_view import (
    capture_web_view,
    discover_rune_viewer_binary,
    ensure_initial_interaction_state,
    ensure_initial_present,
    get_web_view_context,
    interaction_state_file_path,
    launch_rune_viewer,
    present_file_path,
    start_preview_url_fallback,
    start_web_view_session,
    stop_preview_url_fallback,
    stop_rune_viewer,
    stop_web_view_session,
    update_present,
)


class WebViewSessionResult(ToolResultModel):
    """Structured output for GD_Web_View_Start_Mode and GD_Web_View_Stop_Mode."""

    session: dict[str, Any] | None = None
    session_path: str | None = None
    viewer: dict[str, Any] | None = None
    present: dict[str, Any] | None = None
    present_path: str | None = None
    interaction_state_path: str | None = None


class WebViewPresentResult(ToolResultModel):
    """Structured output for GD_Web_View_Present."""

    revision: int
    view_type: str
    model_path: str | None = None
    color_by: str
    present_path: str
    present: dict[str, Any]


class WebViewContextResult(ToolResultModel):
    """Structured output for GD_Web_View_Get_Context."""

    garden_id: str
    selected_targets: list[dict[str, Any]] = Field(default_factory=list)
    annotations: list[dict[str, Any]] = Field(default_factory=list)
    open_annotation_count: int = 0
    resolved_annotation_count: int = 0
    resolved_ids: list[str] = Field(default_factory=list)
    viewport: dict[str, Any] = Field(default_factory=dict)
    pending_intents: list[dict[str, Any]] = Field(default_factory=list)
    viewer_pid: int | None = None
    updated_at: str | None = None


class WebViewCaptureResult(ArtifactResultModel):
    """Structured output for GD_Web_View_Capture."""

    artifact_path: str
    absolute_path: str
    width: int
    height: int
    renderer: str
    view: str | dict[str, Any]
    request_id: str


def register(mcp: FastMCP) -> None:
    """Register the 5 web_view tools."""

    @mcp.tool(
        name="GD_Web_View_Start_Mode",
        description=(
            "Start the Garden-local 3D viewer coordination session (native Rune 3D viewer protocol "
            "and/or offline vtk.js local URL workbench). Automatically seeds tmp/web_view/present.json "
            "from the Garden's base Honeybee model if present so the viewer never opens blank."
        ),
        tags={"preview", "rune", "vtkjs", "web-view"},
        timeout=30,
    )
    def start_web_view_mode(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        name: Annotated[
            str,
            Field(description="Human-readable viewer session name."),
        ] = "Code Mode vtk.js Preview",
        preview_kinds: Annotated[
            list[
                Literal[
                    "base_honeybee_model",
                    "base_dragonfly_model",
                    "object_edit",
                    "search_highlight",
                    "analysis_overlay",
                ]
            ]
            | None,
            Field(
                description="Optional preview kinds such as object_edit, base_honeybee_model, base_dragonfly_model, search_highlight, or analysis_overlay."
            ),
        ] = None,
        port: Annotated[
            int | None,
            Field(
                description="Optional local loopback port (1-65535). When omitted, binds an ephemeral port; when specified and already occupied, raises a port conflict error.",
                ge=1,
                le=65535,
            ),
        ] = None,
        viewer_backend: Annotated[
            Literal["auto", "rune", "web"],
            Field(
                description="Viewer backend: 'auto' (native Rune when open_window=True without explicit port, else local web workbench fallback), 'rune' (native Rune protocol without web server/vtkjs exports), or 'web' (local vtk.js HTTP server)."
            ),
        ] = "auto",
        open_window: Annotated[
            bool,
            Field(description="Whether to spawn the lbt-rune-viewer desktop window for this Garden."),
        ] = False,
        preserve_history: Annotated[
            bool,
            Field(description="Preserve existing session preview steps and present revision history when restarting."),
        ] = True,
    ) -> WebViewSessionResult:
        """Enable local Web View Mode and prepare viewer protocol files."""
        root = Path(garden_root).expanduser().resolve()
        GardenManifest.read(root)
        rune_bin = discover_rune_viewer_binary()

        use_web_server = (
            viewer_backend == "web"
            or (viewer_backend == "auto" and (not open_window or port is not None or rune_bin is None))
        )
        if use_web_server:
            viewer = start_preview_url_fallback(garden_root=str(root), name=name, port=port)
            viewer["backend"] = viewer_backend
            viewer["web_fallback_active"] = True
            viewer["rune_available"] = rune_bin is not None
            if rune_bin is not None:
                viewer["rune_binary"] = str(rune_bin)
        else:
            stop_preview_url_fallback(garden_root=str(root))
            viewer = {
                "ui": "Rune 3D Viewer",
                "library": "rune-wgpu",
                "mode": "rune_viewer",
                "backend": "rune",
                "web_fallback_active": False,
                "local_only": True,
                "rune_available": rune_bin is not None,
            }
            if rune_bin is not None:
                viewer["rune_binary"] = str(rune_bin)

        present = ensure_initial_present(
            garden_root=root,
            force_reset=not preserve_history,
            title=name,
        )
        ensure_initial_interaction_state(root, model_path=present.get("model_path"))

        if open_window and viewer_backend != "web":
            if rune_bin is not None:
                launch_info = launch_rune_viewer(garden_root=root, binary_path=rune_bin)
                viewer["rune_process"] = launch_info
                viewer["pid"] = launch_info.get("pid")
            elif viewer_backend == "rune":
                raise FileNotFoundError(
                    "lbt-rune-viewer binary not found. Set LBT_RUNE_VIEWER_BIN or build rune_viewer first."
                )
            else:
                viewer["rune_launch_warning"] = (
                    "lbt-rune-viewer binary not found; using local web fallback server."
                )

        result = start_web_view_session(
            garden_root=str(root),
            name=name,
            preview_kinds=preview_kinds,
            viewer_metadata=viewer,
            preserve_history=preserve_history,
        )
        result["viewer"] = viewer
        result["present"] = present
        result["present_path"] = str(present_file_path(root))
        result["interaction_state_path"] = str(interaction_state_file_path(root))
        result["summary_view"]["viewer_backend"] = viewer.get("backend")
        result["summary_view"]["present_revision"] = present.get("revision")
        result["summary_view"]["model_path"] = present.get("model_path")
        if "url" in viewer:
            result["summary_view"]["viewer_url"] = viewer["url"]
            result["summary_view"]["viewer_port"] = viewer["port"]
        result["report"] = make_report(
            status="ok",
            message="Web View mode started.",
        )
        return validate_output(WebViewSessionResult, result)

    @mcp.tool(
        name="GD_Web_View_Stop_Mode",
        description=(
            "Stop Garden Web View Mode by marking the local preview session inactive, closing any "
            "local fallback URL server, and stopping any tracked lbt-rune-viewer window process."
        ),
        tags={"preview", "rune", "vtkjs", "web-view"},
        timeout=20,
    )
    def stop_web_view_mode(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
    ) -> WebViewSessionResult:
        """Disable Web View Mode for a Garden."""
        result = stop_web_view_session(garden_root=garden_root)
        result["url_fallback"] = stop_preview_url_fallback(garden_root=garden_root)
        result["rune_viewer"] = stop_rune_viewer(garden_root=garden_root)
        result["viewer"] = {
            "status": "stopped",
            "ui": "Local sidebar viewer",
            "library": "vtk.js",
            "mode": "mcp_app_preview",
        }
        result["report"] = make_report(
            status="ok",
            message="Web View mode stopped.",
        )
        return validate_output(WebViewSessionResult, result)

    @mcp.tool(
        name="GD_Web_View_Present",
        description=(
            "Direct the 3D viewer by atomically updating tmp/web_view/present.json with a "
            "monotonic revision: set view_type, model_target, color_by, highlight_targets, "
            "isolation_mode, validation_issues, camera preset/pose, section plane, callouts, title, and note."
        ),
        tags={"camera", "highlight", "present", "preview", "rune", "web-view"},
        timeout=20,
    )
    def present_web_view(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        view_type: Annotated[
            Literal["model", "highlight", "validation", "analysis", "document", "diff", "split"] | None,
            Field(description="Presentation mode: model, highlight, validation, analysis, document, diff, or split."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Optional Garden model target (defaults to current or base Honeybee model)."),
        ] = None,
        color_by: Annotated[
            Literal[
                "type",
                "boundary_condition",
                "story",
                "zone",
                "program_type",
                "construction_set",
                "hvac",
                "wwr",
            ]
            | None,
            Field(description="Face/room coloring mode: type, boundary_condition, story, zone, program_type, construction_set, hvac, or wwr."),
        ] = None,
        highlight_targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(description="List of BuildingObjectTargetRef dicts to highlight or isolate in the 3D viewport."),
        ] = None,
        isolation_mode: Annotated[
            Literal["highlight", "ghost_context", "isolate"] | None,
            Field(description="Context handling for highlighted objects: highlight, ghost_context, or isolate."),
        ] = None,
        validation_issues: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional validation issue dicts (e.g. from HB_Validate_Model) to display in validation view."),
        ] = None,
        camera: Annotated[
            str | dict[str, Any] | None,
            Field(description="Camera preset ('keep', 'fit', 'fit_highlights', 'axon', 'top', 'north', 'south', 'east', 'west') or {position, target, up?, orthographic?} dict."),
        ] = None,
        section: Annotated[
            dict[str, Any] | None,
            Field(description="Optional section cut spec {enabled, axis, value, story, invert}."),
        ] = None,
        callouts: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional spatial callout dicts attached to targets or world coordinates."),
        ] = None,
        title: Annotated[
            str | None,
            Field(description="Optional HUD title shown in the viewer."),
        ] = None,
        note: Annotated[
            str | None,
            Field(description="Optional HUD subtitle or director note shown in the viewer."),
        ] = None,
    ) -> WebViewPresentResult:
        """Atomically update tmp/web_view/present.json for the active viewer."""
        root = Path(garden_root).expanduser().resolve()
        present = update_present(
            garden_root=root,
            view_type=view_type,
            model_target=dump_target(model_target),
            color_by=color_by,
            highlight_targets=dump_targets(highlight_targets),
            isolation_mode=isolation_mode,
            validation_issues=dump_input(validation_issues),
            camera=dump_input(camera),
            section=dump_input(section),
            callouts=dump_input(callouts),
            title=title,
            note=note,
        )
        manifest = GardenManifest.read(root)
        return validate_output(
            WebViewPresentResult,
            {
                "revision": present["revision"],
                "view_type": present["view_type"],
                "model_path": present.get("model_path"),
                "color_by": present["color_by"],
                "present_path": str(present_file_path(root)),
                "present": present,
                "summary_view": {
                    "garden_target": manifest.target(),
                    "revision": present["revision"],
                    "view_type": present["view_type"],
                    "model_path": present.get("model_path"),
                    "color_by": present["color_by"],
                    "highlight_count": len(present.get("highlight_targets") or []),
                    "validation_issue_count": len(present.get("validation_issues") or []),
                    "callout_count": len(present.get("callouts") or []),
                    "camera": present.get("camera"),
                    "section": present.get("section"),
                },
                "report": make_report(
                    status="ok",
                    message=f"Updated viewer present.json (revision {present['revision']}, view_type={present['view_type']}).",
                ),
            },
        )

    @mcp.tool(
        name="GD_Web_View_Get_Context",
        description=(
            "Read user spatial interaction context from tmp/web_view/interaction_state.json, "
            "returning selected BuildingObjectTargetRef targets, spatial annotations, viewport state, "
            "and pending intents. Optionally resolves annotations atomically when resolve_annotations is passed."
        ),
        tags={"annotations", "context", "rune", "selection", "web-view"},
        timeout=20,
    )
    def get_web_view_context_tool(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        only_open_annotations: Annotated[
            bool,
            Field(description="When true, return only annotations with status='open'; when false, return both open and resolved annotations."),
        ] = True,
        resolve_annotations: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional list of {id, resolution_note} dicts to mark matching annotations resolved atomically."),
        ] = None,
    ) -> WebViewContextResult:
        """Read selected targets, annotations, viewport, and pending intents from the viewer."""
        root = Path(garden_root).expanduser().resolve()
        manifest = GardenManifest.read(root)
        ctx = get_web_view_context(
            garden_root=root,
            only_open_annotations=only_open_annotations,
            resolve_annotations=dump_input(resolve_annotations),
        )
        ctx["summary_view"] = {
            "garden_target": manifest.target(),
            "selected_count": len(ctx["selected_targets"]),
            "returned_annotation_count": len(ctx["annotations"]),
            "open_annotation_count": ctx["open_annotation_count"],
            "resolved_annotation_count": ctx["resolved_annotation_count"],
            "resolved_ids": ctx["resolved_ids"],
            "pending_intent_count": len(ctx["pending_intents"]),
            "viewer_pid": ctx["viewer_pid"],
        }
        ctx["report"] = make_report(
            status="ok",
            message=(
                f"Read viewer context ({len(ctx['selected_targets'])} selected, "
                f"{ctx['open_annotation_count']} open annotations)."
            ),
        )
        return validate_output(WebViewContextResult, ctx)

    @mcp.tool(
        name="GD_Web_View_Capture",
        description=(
            "Capture a visual verification PNG under tmp/web_view/captures/ by trying the live "
            "Rune viewer capture handshake first, headless lbt-rune-viewer --snap second, and "
            "offscreen VTK rendering third."
        ),
        tags={"capture", "png", "preview", "rune", "screenshot", "web-view"},
        timeout=60,
    )
    def capture_web_view_tool(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        view: Annotated[
            str | dict[str, Any],
            Field(description="Camera view preset ('fit', 'axon', 'top', 'north', 'south', 'east', 'west') or explicit camera/Plane dict."),
        ] = "fit",
        width: Annotated[
            int,
            Field(description="Captured PNG width in pixels.", ge=64, le=4096),
        ] = 1280,
        height: Annotated[
            int,
            Field(description="Captured PNG height in pixels.", ge=64, le=4096),
        ] = 720,
        timeout_secs: Annotated[
            float,
            Field(description="Maximum wait seconds for live Rune capture handshake before falling back.", gt=0, le=120),
        ] = 5.0,
    ) -> WebViewCaptureResult:
        """Capture a PNG screenshot of the current Garden scene."""
        res = capture_web_view(
            garden_root=garden_root,
            view=dump_input(view),
            width=width,
            height=height,
            timeout_secs=timeout_secs,
        )
        return validate_output(WebViewCaptureResult, res)
