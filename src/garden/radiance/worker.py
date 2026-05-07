"""Background Radiance run worker entrypoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from garden.radiance.run import run_radiance_recipe


def main(argv: list[str] | None = None) -> int:
    """Run one serialized Radiance recipe request."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise SystemExit("Usage: python -m garden.radiance.worker REQUEST_JSON")
    request_path = Path(args[0]).expanduser().resolve()
    kwargs = json.loads(request_path.read_text(encoding="utf-8"))
    run_radiance_recipe(**kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
