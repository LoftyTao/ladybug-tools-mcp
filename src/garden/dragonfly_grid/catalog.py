"""OpenDSS catalog search services for Dragonfly Electric Grid."""

from __future__ import annotations

from typing import Any

from dragonfly_energy.opendss.lib.powerlines import POWER_LINES
from dragonfly_energy.opendss.lib.transformers import TRANSFORMER_PROPERTIES
from dragonfly_energy.opendss.lib.wires import WIRES
from ladybug_tools_mcp.contracts.report import make_report


CATALOGS = {
    "transformer_properties": TRANSFORMER_PROPERTIES,
    "power_lines": POWER_LINES,
    "wires": WIRES,
}


def search_opendss(
    *,
    keywords: list[str] | None = None,
    catalogs: list[str] | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Search compact OpenDSS catalog identifiers."""
    if limit <= 0:
        raise ValueError("limit must be a positive integer.")
    selected = catalogs or list(CATALOGS)
    unknown = [catalog for catalog in selected if catalog not in CATALOGS]
    if unknown:
        allowed = ", ".join(sorted(CATALOGS))
        raise ValueError(f"Unknown OpenDSS catalog(s): {unknown}. Allowed: {allowed}.")
    terms = [term.strip().lower() for term in (keywords or []) if term.strip()]
    matches: list[dict[str, Any]] = []
    for catalog in selected:
        for identifier in CATALOGS[catalog]:
            text = identifier.lower()
            if terms and not all(term in text for term in terms):
                continue
            matches.append({"catalog": catalog, "identifier": identifier})
            if len(matches) >= limit:
                break
        if len(matches) >= limit:
            break
    return {
        "matches": matches,
        "summary_view": {
            "keywords": keywords or [],
            "catalogs": selected,
            "returned_count": len(matches),
            "total_count": sum(len(CATALOGS[catalog]) for catalog in selected),
            "limit": limit,
            "body_returned": False,
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(matches)} OpenDSS catalog records.",
        ),
    }
