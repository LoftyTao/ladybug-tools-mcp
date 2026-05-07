"""Persistent per-component state for Grasshopper shell runtime behavior."""

_WRITE_TOGGLE_STATE = {}
_FOLLOW_REFRESH_PENDING = {}
_FOLLOW_SIGNATURE_STATE = {}


def consume_write_pulse(component, write_flag):
    """Treat one component's _write input as a rising-edge trigger."""
    write_requested = bool(write_flag)
    key = _component_state_key(component)
    if key is None:
        return write_requested

    previous = bool(_WRITE_TOGGLE_STATE.get(key, False))
    _WRITE_TOGGLE_STATE[key] = write_requested
    return write_requested and not previous


def mark_follow_refresh_pending(component):
    """Mark one component as having a scheduled follow refresh."""
    key = _component_state_key(component)
    if key is None:
        return False
    if _FOLLOW_REFRESH_PENDING.get(key):
        return False
    _FOLLOW_REFRESH_PENDING[key] = True
    return True


def clear_follow_refresh_pending(component):
    """Clear the scheduled follow refresh marker for one component."""
    key = _component_state_key(component)
    if key is None:
        return
    _FOLLOW_REFRESH_PENDING.pop(key, None)


def clear_follow_refresh_state(component):
    """Remove follow refresh state for one component."""
    clear_follow_refresh_pending(component)
    key = _component_state_key(component)
    if key is not None:
        _FOLLOW_SIGNATURE_STATE.pop(key, None)


def set_follow_signature(component, signature):
    """Store the last followed Garden/model file signature for one component."""
    key = _component_state_key(component)
    if key is None:
        return
    _FOLLOW_SIGNATURE_STATE[key] = signature


def get_follow_signature(component):
    """Return the last followed Garden/model file signature for one component."""
    key = _component_state_key(component)
    if key is None:
        return None
    return _FOLLOW_SIGNATURE_STATE.get(key)


def _component_state_key(component):
    """Return a stable key for one Grasshopper component instance."""
    if component is None:
        return None
    instance_guid = getattr(component, "InstanceGuid", None)
    if instance_guid is not None:
        return str(instance_guid)
    return "component-{0}".format(id(component))
