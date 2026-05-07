"""Summary helpers for Ladybug DataCollection objects."""

from __future__ import annotations

from typing import Any


def data_collection_summary(data_collection: Any) -> dict[str, Any]:
    """Return a compact summary for a Ladybug DataCollection."""
    header = data_collection.header
    values = data_collection.values
    analysis_period = header.analysis_period.to_dict()
    data_type = header.data_type.to_dict()
    return {
        "type": data_collection.to_dict().get("type"),
        "unit": header.unit,
        "data_type": data_type,
        "analysis_period": analysis_period,
        "metadata": dict(header.metadata),
        "timestep": analysis_period.get("timestep"),
        "value_count": len(values),
        "min": data_collection.min,
        "max": data_collection.max,
        "average": data_collection.average,
        "median": data_collection.median,
        "total": data_collection.total,
        "is_continuous": data_collection.is_continuous,
    }
