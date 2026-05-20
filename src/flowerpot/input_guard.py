"""Required-input gating for Grasshopper GHPython shell components."""


def all_required_inputs_ready(component):
    """Return whether all required Grasshopper inputs currently have data."""
    try:
        from ladybug_rhino.grasshopper import all_required_inputs
    except ImportError as exc:
        raise RuntimeError(
            "ladybug_rhino.grasshopper.all_required_inputs is required "
            "for Flowerpot Grasshopper components."
        ) from exc

    if not callable(all_required_inputs):
        raise RuntimeError(
            "ladybug_rhino.grasshopper.all_required_inputs is required "
            "for Flowerpot Grasshopper components."
        )
    return bool(all_required_inputs(component))

