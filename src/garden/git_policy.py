"""Garden-local Git ignore policy."""

from __future__ import annotations

GARDEN_GITIGNORE = """# Garden authoring truth is intentionally narrow.
*
!garden.json
!models/
!models/**
!libraries/
!libraries/**

# Generated or exchange-only content stays out of Garden Git.
artifacts/
runs/
flowerpots/
payloads/
imports/
tmp/
.cache/
"""


def garden_gitignore_text() -> str:
    """Return the Garden-local .gitignore content."""
    return GARDEN_GITIGNORE
