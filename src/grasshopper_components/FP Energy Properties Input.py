#! python 2
# env: prefer LADYBUG_TOOLS_MCP_SRC, then file-relative bootstrap

"""
Read a Honeybee Energy Properties Library object from a Flowerpot Garden.
-
This component reads existing Garden Properties Library objects. It does not
apply the selected property to the current model.
-

    Args:
        _flowerpot: Opaque Flowerpot dictionary from an FP component.
        _type: Honeybee Energy properties type to read.
        value_: Optional identifier or search text for the properties object.
        follow_: Set to True to refresh when the Garden library changes.

    Returns:
        property: Honeybee Energy properties object dictionary from the Garden.
        report: Reports, errors, warnings, etc.
"""
import os
import sys


def _script_src_root():
    file_path = globals().get("__file__")
    if not file_path:
        return None
    here = os.path.abspath(os.path.dirname(file_path))
    return os.path.abspath(os.path.join(here, ".."))


def _ensure_src_root():
    env_src = os.environ.get("LADYBUG_TOOLS_MCP_SRC")
    candidates = []
    if env_src:
        candidates.append(env_src)
    candidates.append(_script_src_root())
    for src_root in candidates:
        if not src_root:
            continue
        runtime_path = os.path.join(src_root, "flowerpot", "runtime.py")
        if os.path.isfile(runtime_path):
            if src_root not in sys.path:
                sys.path.insert(0, src_root)
            return src_root
    raise ImportError("Could not locate Ladybug Tools MCP src root.")


_ensure_src_root()

from flowerpot.input_guard import all_required_inputs_ready
import flowerpot.runtime as _runtime

try:
    _reload = reload
except NameError:
    from importlib import reload as _reload

try:
    ghenv.Component.Name = "FP Energy Properties Input"
    ghenv.Component.NickName = "EnergyProps"
    ghenv.Component.Message = "1.0.0"
    ghenv.Component.Category = "Flowerpot"
    ghenv.Component.SubCategory = "2 :: Energy"
    ghenv.Component.AdditionalHelpFromDocStrings = "1"
    ghenv.Component.Params.Input[0].Optional = False
    ghenv.Component.Params.Input[1].Optional = False
    ghenv.Component.Params.Input[2].Optional = True
    ghenv.Component.Params.Input[3].Optional = True
except Exception:
    pass


def run(_flowerpot, _type, value_, follow_):
    """Read Honeybee Energy properties from a Flowerpot Garden."""
    return _load_runtime().read_energy_properties_input(
        flowerpot=_flowerpot,
        properties_type=_type,
        value=value_,
        follow_flag=bool(follow_),
        component=_component_from_ghenv(),
    )


def _load_runtime():
    """Reload runtime so Grasshopper picks up local repo edits immediately."""
    return _reload(_runtime)


def _component_from_ghenv():
    """Return the live GHPython component instance when running inside Grasshopper."""
    try:
        return ghenv.Component
    except Exception:
        return None


property = None
report = {
    "status": "idle",
    "message": "No Energy properties input requested.",
    "warnings": [],
    "details": {},
}

if "_flowerpot" in globals() and "_type" in globals():
    if all_required_inputs_ready(ghenv.Component):
        _result = run(
            _flowerpot,
            _type,
            globals().get("value_"),
            globals().get("follow_", False),
        )
        property = _result["property"]
        report = _result["report"]
