"""Search Radiance parameter inputs recorded on Garden runs."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.manifest import GardenManifest
from garden.radiance.run import _read_index
from ladybug_tools_mcp.contracts.report import make_report


def _relative_run_parameter_match(
    garden_root_path: Path,
    garden_id: str,
    record: dict[str, Any],
) -> dict[str, Any] | None:
    parameter_path = record.get("radiance_parameters_path")
    if not parameter_path:
        return None
    path = (garden_root_path / str(parameter_path)).resolve()
    try:
        path.relative_to(garden_root_path)
    except ValueError:
        return None
    if not path.is_file():
        return None
    radiance_parameters = path.read_text(encoding="utf-8").strip()
    identifier = f"{record.get('run_id')}_radiance_parameters"
    target = {
        "target_type": "radiance_parameters",
        "domain": "honeybee_radiance",
        "garden_id": garden_id,
        "identifier": identifier,
        "path": str(parameter_path).replace("\\", "/"),
        "radiance_parameters": radiance_parameters,
        "value": radiance_parameters,
    }
    return {
        "identifier": identifier,
        "run_id": record.get("run_id"),
        "recipe": record.get("recipe"),
        "path": target["path"],
        "target": target,
        "radiance_parameters": radiance_parameters,
    }


def register(mcp: FastMCP) -> None:
    """Register the search_radiance_parameters tool."""

    @mcp.tool(
        name="search_radiance_parameters",
        description="Search Radiance parameter strings recorded on Garden Radiance runs and return compact radiance_parameters targets usable with start_radiance_*_run. If no stored parameters exist, call create_radiance_parameters or pass a Radiance parameter string directly.",
        tags={
            "honeybee-radiance",
            "radiance",
            "radiance-parameters",
            "search",
            "read-only",
            "safe",
            "alias",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_parameters(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        query: Annotated[str | None, Field(description="Optional run_id, identifier, path, or parameter substring filter.")] = None,
        identifier: Annotated[
            str | None,
            Field(description="Alias for query accepted for Agent compatibility."),
        ] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
        return_object_dict: Annotated[bool | None, Field(description="Ignored compatibility hint.")] = None,
    ) -> dict[str, Any]:
        """Search stored Radiance parameter inputs."""
        _ = return_object_dict
        if query is None and identifier is not None:
            query = identifier
        garden_root_path = Path(garden_root).expanduser().resolve()
        manifest = GardenManifest.read(garden_root_path)
        query_text = (query or "").strip().lower()
        matches: list[dict[str, Any]] = []
        for record in _read_index(garden_root_path):
            match = _relative_run_parameter_match(
                garden_root_path,
                manifest.garden_id,
                record,
            )
            if match is None:
                continue
            searchable = " ".join(
                str(value)
                for value in (
                    match.get("identifier"),
                    match.get("run_id"),
                    match.get("recipe"),
                    match.get("path"),
                    match.get("radiance_parameters"),
                )
                if value
            ).lower()
            if query_text and query_text not in searchable:
                continue
            matches.append(match)
            if limit is not None and len(matches) >= limit:
                break
        result: dict[str, Any] = {
            "matches": matches,
            "summary_view": {
                "garden_target": manifest.target(),
                "count": len(matches),
                "query": query,
                "recommended_fallback": "create_radiance_parameters",
            },
            "report": make_report(
                status="ok",
                message=f"Found {len(matches)} stored Radiance parameter input(s).",
            ),
        }
        if len(matches) == 1:
            result["target"] = matches[0]["target"]
        return result
