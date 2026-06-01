"""FastMCP App backend tool for vtk.js preview bytes."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from fastmcp.apps import AppConfig
from pydantic import Field

from web_view.app import PREVIEW_ARTIFACT_TOOL, app_meta, read_preview_artifact


def register(mcp: FastMCP) -> None:
    """Register the App-only preview_artifact tool."""

    @mcp.tool(
        name="preview_artifact",
        description=(
            "App-only backend for the FastMCP vtk.js preview. Reads the active "
            "Garden-local .vtkjs preview file, validates that it stays inside the "
            "Garden, and returns a base64 payload plus revision metadata for the "
            "iframe; use web_view_start_mode for the user-facing App."
        ),
        tags={
            "preview",
            "vtkjs",
            "web-view",
        },
        timeout=20,
        app=AppConfig(visibility=["app"]),
        meta=app_meta(PREVIEW_ARTIFACT_TOOL),
    )
    def preview_artifact(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root'].")],
        artifact_path: Annotated[str, Field(description="Garden-relative .vtkjs artifact path returned by preview_state.")],
        revision: Annotated[
            str | None,
            Field(description="Optional sha256 revision from preview_state; mismatches ask the App to refresh state."),
        ] = None,
    ) -> dict[str, Any]:
        """Return current `.vtkjs` bytes for the FastMCP App."""
        return read_preview_artifact(
            garden_root=garden_root,
            artifact_path=artifact_path,
            revision=revision,
        )
