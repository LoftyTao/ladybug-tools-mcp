"""FastMCP server factory for Ladybug Tools MCP."""

from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers.skills import SkillProvider
from fastmcp.server.transforms.visibility import Visibility

from ladybug_tools_mcp import __version__
from ladybug_tools_mcp.code_mode import create_code_mode_transform
from ladybug_tools_mcp.operation_protocol import (
    GardenOperationMiddleware,
    GardenOperationTransform,
)
from ladybug_tools_mcp.registry import register_tools
from ladybug_tools_mcp.weather_resources import register_weather_resources

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = PROJECT_ROOT / ".agents" / "skills" / "ladybug-tools-mcp-use"


def create_mcp() -> FastMCP:
    """Create the Ladybug Tools MCP server."""
    providers = []
    if SKILL_PATH.exists():
        providers.append(SkillProvider(SKILL_PATH, supporting_files="template"))

    transforms = [
        Visibility(
            False,
            tags={"debug", "internal", "experimental"},
        ),
        GardenOperationTransform(),
        create_code_mode_transform(),
    ]

    mcp = FastMCP(
        "Ladybug Tools MCP",
        version=__version__,
        providers=providers,
        transforms=transforms,
        on_duplicate="error",
        strict_input_validation=True,
        mask_error_details=False,
    )
    register_tools(mcp)
    register_weather_resources(mcp)
    mcp.add_middleware(GardenOperationMiddleware())
    return mcp


mcp = create_mcp()


if __name__ == "__main__":
    mcp.run(show_banner=False)
