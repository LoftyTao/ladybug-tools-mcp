"""Repository-local incubation package for Ironbug-Core."""

from __future__ import annotations

from ironbug.ibjson import (
    IBJSON_EXTENSION,
    IBJSON_ROOT_TYPE,
    model_from_ibjson,
    model_from_ibjson_string,
    model_to_ibjson,
    model_to_ibjson_string,
)

__version__ = "1.0.0"

__all__ = [
    "IBJSON_EXTENSION",
    "IBJSON_ROOT_TYPE",
    "model_from_ibjson",
    "model_from_ibjson_string",
    "model_to_ibjson",
    "model_to_ibjson_string",
]
