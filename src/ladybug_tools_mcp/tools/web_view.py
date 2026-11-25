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
    can_open_rune_window,
    capture_web_view,
    discover_rune_viewer_binary,
    discover_rune_web_bundle_dir,
    ensure_initial_interaction_state,
    ensure_initial_present,
    get_web_view_context,
    interaction_state_file_path,
    is_rune_viewer_running,
    launch_rune_viewer,
    present_file_path,
    start_rune_web_server,
    start_web_view_session,
    stop_rune_viewer,
    stop_rune_web_server,
    stop_web_view_session,
    update_present,
)


class WebViewSessionResult(ToolResultModel):
    """Structured output for GD_Web_View_Start_Mode and GD_Web_View_Stop_Mode."""

    session: dict[str, Any] | None = None
    session_path: str | None = None
    viewer: dict[str, Any] | None = None
    rune_viewer: dict[str, Any] | None = None
    web_url: str | None = None
    web_server: dict[str, Any] | None = None
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
            "Start the Garden-local Rune 3D viewer coordination session and optionally launch "
            "the native lbt-rune-viewer desktop window. Automatically seeds tmp/web_view/present.json "
            "from the Garden's base Honeybee or Dragonfly model if present."
        ),
        tags={"preview", "rune", "viewer", "web-view"},
        timeout=30,
    )
    def start_web_view_mode(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        name: Annotated[
            str,
            Field(description="Human-readable Rune 3D viewer session name."),
        ] = "Rune 3D Preview",
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
        open_window: Annotated[
            bool,
            Field(
                description="Whether to spawn the native lbt-rune-viewer desktop window (set False for headless/protocol-only sessions; gracefully falls back with a warning if the binary or display is unavailable)."
            ),
        ] = True,
        serve_web: Annotated[
            bool,
            Field(
                description="Whether to serve the browser-native WASM Rune Web View on local loopback HTTP so the user can view and operate the 3D scene directly in a browser."
            ),
        ] = True,
        web_port: Annotated[
            int | None,
            Field(
                description="Optional local loopback HTTP port for the browser Web View server (defaults to an available ephemeral port).",
                ge=1024,
                le=65535,
            ),
        ] = None,
        preserve_history: Annotated[
            bool,
            Field(description="Preserve existing session preview steps and present revision history when restarting."),
        ] = True,
    ) -> WebViewSessionResult:
        """Enable Rune Web View Mode and prepare viewer protocol files + local browser server."""
        root = Path(garden_root).expanduser().resolve()
        GardenManifest.read(root)
        rune_bin = discover_rune_viewer_binary()
        web_bundle = discover_rune_web_bundle_dir()

        present = ensure_initial_present(
            garden_root=root,
            force_reset=not preserve_history,
            title=name,
        )
        ensure_initial_interaction_state(root, model_path=present.get("model_path"))

        viewer: dict[str, Any] = {
            "ui": "Rune 3D Viewer",
            "library": "rune-wgpu",
            "mode": "rune_viewer",
            "backend": "rune",
            "local_only": True,
            "rune_available": rune_bin is not None,
            "web_bundle_available": web_bundle is not None,
        }
        if rune_bin is not None:
            viewer["rune_binary"] = str(rune_bin)

        warnings_list: list[str] = []
        if open_window:
            can_open, headless_reason = can_open_rune_window()
            if not can_open:
                window_status = "skipped_headless"
                if headless_reason:
                    viewer["rune_launch_warning"] = headless_reason
                    warnings_list.append(headless_reason)
            elif rune_bin is not None:
                launch_info = launch_rune_viewer(garden_root=root, binary_path=rune_bin)
                viewer["rune_process"] = launch_info
                viewer["pid"] = launch_info.get("pid")
                window_status = str(launch_info.get("status") or "started")
            else:
                window_status = "binary_not_found"
                warn = (
                    "lbt-rune-viewer binary not found; protocol files remain active in tmp/web_view/."
                )
                viewer["rune_launch_warning"] = warn
                warnings_list.append(warn)
        else:
            window_status = "already_running" if is_rune_viewer_running(root) else "not_requested"
        viewer["window_status"] = window_status

        web_info: dict[str, Any] | None = None
        web_url: str | None = None
        if serve_web:
            if web_bundle is not None:
                web_info = start_rune_web_server(
                    garden_root=root,
                    port=web_port or 0,
                    bundle_dir=web_bundle,
                )
                web_url = str(web_info.get("url") or "")
                web_status = str(web_info.get("status") or "started")
                viewer["url"] = web_url
                viewer["web_url"] = web_url
                viewer["web_port"] = web_info.get("port")
                viewer["web_server"] = web_info
            else:
                web_status = "bundle_not_found"
                web_warn = (
                    "Rune browser WASM bundle not found under rune_viewer/target/web/; "
                    "run scripts/build_rune_web.py to enable browser preview."
                )
                viewer["web_launch_warning"] = web_warn
                warnings_list.append(web_warn)
        else:
            web_status = "not_requested"
        viewer["web_status"] = web_status

        result = start_web_view_session(
            garden_root=str(root),
            name=name,
            preview_kinds=preview_kinds,
            viewer_metadata=viewer,
            preserve_history=preserve_history,
        )
        result["viewer"] = viewer
        result["web_url"] = web_url
        result["web_server"] = web_info
        result["present"] = present
        result["present_path"] = str(present_file_path(root))
        result["interaction_state_path"] = str(interaction_state_file_path(root))
        result["summary_view"]["viewer_backend"] = "rune"
        result["summary_view"]["window_status"] = window_status
        result["summary_view"]["web_status"] = web_status
        if web_url:
            result["summary_view"]["web_url"] = web_url
        result["summary_view"]["rune_available"] = rune_bin is not None
        result["summary_view"]["present_revision"] = present.get("revision")
        result["summary_view"]["model_path"] = present.get("model_path")
        result["report"] = make_report(
            status="ok",
            message=(
                f"Rune Web View mode started (browser URL: {web_url})."
                if web_url
                else "Rune Web View mode started."
            ),
            warnings=warnings_list,
        )
        return validate_output(WebViewSessionResult, result)

    @mcp.tool(
        name="GD_Web_View_Stop_Mode",
        description=(
            "Stop Garden Rune Web View Mode by marking the local preview session inactive and "
            "stopping any tracked lbt-rune-viewer window process and browser HTTP server."
        ),
        tags={"preview", "rune", "viewer", "web-view"},
        timeout=20,
    )
    def stop_web_view_mode(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
    ) -> WebViewSessionResult:
        """Disable Rune Web View Mode for a Garden."""
        result = stop_web_view_session(garden_root=garden_root)
        rune_stop = stop_rune_viewer(garden_root=garden_root)
        web_stop = stop_rune_web_server(garden_root=garden_root)
        result["rune_viewer"] = rune_stop
        result["web_server"] = web_stop
        result["viewer"] = {
            "status": "stopped",
            "ui": "Rune 3D Viewer",
            "library": "rune-wgpu",
            "mode": "rune_viewer",
            "backend": "rune",
            "local_only": True,
            "window_status": rune_stop.get("status"),
            "web_status": web_stop.get("status"),
        }
        result["report"] = make_report(
            status="ok",
            message="Rune Web View mode stopped.",
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
            Field(description="Optional Garden model target (defaults to current or base Honeybee/Dragonfly model)."),
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
            ]
            | None,
            Field(description="Face/room coloring mode: type, boundary_condition, story, zone, program_type, construction_set, or hvac."),
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
