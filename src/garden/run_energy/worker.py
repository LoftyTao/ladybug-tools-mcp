"""Background Energy run worker entrypoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from garden.run_energy.annual import run_energy


def main(argv: list[str] | None = None) -> int:
    """Run one serialized Energy recipe request."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise SystemExit("Usage: python -m garden.run_energy.worker REQUEST_JSON")
    request_path = Path(args[0]).expanduser().resolve()
    kwargs = json.loads(request_path.read_text(encoding="utf-8"))
    run_energy(**kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
