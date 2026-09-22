"""Installed runtime settings, readable by both CPython and Rhino IronPython."""

from __future__ import print_function

import io
import json
import os


def installation_path():
    return os.path.abspath(os.path.expanduser(
        os.environ.get("LADYBUG_TOOLS_MCP_INSTALLATION")
        or os.path.join("~", ".ladybug-tools-mcp", "installation.json")
    ))


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
        if not isinstance(value, (str, type(u""))) or not os.path.isabs(value):
            raise ValueError("Invalid %s in installation record: %s" % (key, path))
    return result
