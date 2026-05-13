"""Background worker for Garden-managed UWG runs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from garden.run_uwg.run import run_uwg


def main() -> int:
    """Run UWG from a JSON request file."""
    request_path = Path(sys.argv[1])
    kwargs = json.loads(request_path.read_text(encoding="utf-8"))
    run_uwg(**kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
