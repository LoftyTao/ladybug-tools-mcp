#! python 2
# env: prefer LADYBUG_TOOLS_MCP_SRC, then file-relative bootstrap

"""
Link a Honeybee Model to a Flowerpot Garden.
-
This component is the GHPython shell over the formal Python 3 worker.
-

    Args:
        _flowerpot: Opaque Flowerpot dictionary from an FP component.
        model_: Optional Honeybee Model input.
        _write: Optional write trigger. Set to True to persist the connected
            Honeybee Model into the Flowerpot Garden once for this component.
        follow_: Set to True to refresh from the Garden context.

    Returns:
        model: Honeybee Model passed through or refreshed from the Garden.
        flowerpot: Opaque Flowerpot dictionary for downstream FP components.
        changed: Boolean flag indicating whether this solve persisted a model.
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
    ghenv.Component.Name = "FP Honeybee Link"
    ghenv.Component.NickName = "HoneybeeLink"
    ghenv.Component.Message = "1.1.0"
    ghenv.Component.Category = "Flowerpot"
    ghenv.Component.SubCategory = "1 :: Honeybee"
    ghenv.Component.AdditionalHelpFromDocStrings = "1"
    ghenv.Component.Params.Input[0].Optional = False
    ghenv.Component.Params.Input[1].Optional = True
    ghenv.Component.Params.Input[2].Optional = True
    ghenv.Component.Params.Input[3].Optional = True
except Exception:
    pass


def run(_flowerpot, model_, _write, follow_):
    """Link a Honeybee model to a Flowerpot Garden through the worker."""
    return _load_runtime().link_honeybee_model(
        flowerpot=_flowerpot,
        model=model_,
        write_flag=_write,
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


model = globals().get("model_")
flowerpot = globals().get("_flowerpot")
changed = False
report = {
    "status": "idle",
    "message": "No Flowerpot action requested.",
    "warnings": [],
    "details": {},
}

if "_flowerpot" in globals() and _flowerpot is not None:
    if all_required_inputs_ready(ghenv.Component):
        _result = run(
            _flowerpot,
            globals().get("model_"),
            globals().get("_write", False),
            globals().get("follow_", False),
        )
        model = _result["model"]
        flowerpot = _result["flowerpot"]
        changed = _result["changed"]
        report = _result["report"]
