"""Project-specific exceptions."""


class LadybugToolsMCPError(Exception):
    """Base exception for Ladybug Tools MCP errors."""


class GardenError(LadybugToolsMCPError):
    """Raised when a Garden operation cannot be completed."""
