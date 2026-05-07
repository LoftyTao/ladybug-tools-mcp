"""Required-input gating for Grasshopper GHPython shell components."""


def all_required_inputs_ready(component):
    """Return whether all required Grasshopper inputs currently have data."""
    try:
        from ladybug_rhino.grasshopper import all_required_inputs

        return bool(all_required_inputs(component))
    except Exception:
        return _fallback_all_required_inputs(component)


def _fallback_all_required_inputs(component):
    """Approximate Ladybug Tools required-input gating for non-Rhino tests."""
    try:
        params = component.Params.Input
    except Exception:
        return True

    for param in params:
        if getattr(param, "Optional", False):
            continue
        volatile_count = getattr(param, "VolatileDataCount", None)
        if volatile_count is not None:
            if volatile_count <= 0:
                return False
            continue
        try:
            branch_count = len(param.VolatileData)
        except Exception:
            branch_count = None
        if branch_count is not None and branch_count <= 0:
            return False
    return True

