# ruff: noqa: UP003, UP010, UP020, UP025, UP031
"""Installed runtime settings, readable by both CPython and Rhino IronPython."""

from __future__ import print_function

import io
import json
import os


def installation_path():
    explicit = os.environ.get("LADYBUG_TOOLS_MCP_INSTALLATION")
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    home_dir = os.environ.get("LADYBUG_TOOLS_MCP_HOME")
    if home_dir:
        candidate = os.path.abspath(os.path.expanduser(
            os.path.join(home_dir, "config", "installation.json")
        ))
        if os.path.isfile(candidate):
            return candidate
    return os.path.abspath(os.path.expanduser(
        os.path.join("~", ".ladybug-tools-mcp", "installation.json")
    ))


def _is_text(value):
    return isinstance(value, (str, type(u"")))


def read_installation(path=None):
    path = path or installation_path()
    if not os.path.isfile(path):
        return {}
    with io.open(path, "r", encoding="utf-8") as stream:
        result = json.load(stream)
    if not isinstance(result, dict) or result.get("schema_version") != 1:
        raise ValueError("Unsupported Ladybug Tools MCP installation record: " + path)
    for key in ("python", "package_root", "gardens_root"):
        value = result.get(key)
        if not _is_text(value) or not os.path.isabs(value):
            raise ValueError("Invalid %s in installation record: %s" % (key, path))
    for key in ("home", "launcher", "runtime_config"):
        if key in result and result[key] is not None:
            value = result[key]
            if not _is_text(value) or not os.path.isabs(value):
                raise ValueError("Invalid %s in installation record: %s" % (key, path))
    for key in ("distribution_mode", "version"):
        if key in result and result[key] is not None:
            value = result[key]
            if not _is_text(value) or not value.strip():
                raise ValueError("Invalid %s in installation record: %s" % (key, path))
    if "packs" in result and result["packs"] is not None:
        if not isinstance(result["packs"], (list, dict)):
            raise ValueError("Invalid packs in installation record: " + path)
    return result
