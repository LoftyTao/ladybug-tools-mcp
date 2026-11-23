"""FastMCP server factory for Ladybug Tools MCP."""

from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers.skills import SkillProvider
from fastmcp.server.transforms.visibility import Visibility

from ladybug_tools_mcp import __version__
from ladybug_tools_mcp.code_mode import create_code_mode_transform
from ladybug_tools_mcp.registry import register_tools
from ladybug_tools_mcp.weather_resources import register_weather_resources

SKILL_PATH = Path(__file__).resolve().parent / "resources" / "skills" / "ladybug-tools-mcp-use"
if not SKILL_PATH.is_dir():
    SKILL_PATH = Path(__file__).resolve().parents[2] / ".agents" / "skills" / "ladybug-tools-mcp-use"


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
    return mcp


_DEFAULT_MCP: FastMCP | None = None


def __getattr__(name: str):
    """Build the default module-level server lazily when accessed."""
    global _DEFAULT_MCP
    if name == "mcp":
        if _DEFAULT_MCP is None:
            _DEFAULT_MCP = create_mcp()
        return _DEFAULT_MCP
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    create_mcp().run(show_banner=False)
