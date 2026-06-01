"""Command-line entrypoint for the Python Ironbug Console."""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence

from garden.ironbug_console.console_app import save_hvac_to_osm


def main(argv: Sequence[str] | None = None) -> int:
    """Run the C# Console-compatible two-file application command."""

    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("Hello, this is Python Ironbug Console app!")
        print("Usage: python -m garden.ironbug_console <model.osm> <hvac.json>")
        return 0

    try:
        result = save_hvac_to_osm(osm_path=args[0], hvac_json_path=args[1])
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1

    print(json.dumps(result.to_dict(), indent=2))
    return 0 if result.status == "written" else 2
