#! python 2
# env: prefer LADYBUG_TOOLS_MCP_SRC, then file-relative bootstrap

"""
Create a Ladybug Tools Garden and wrap it as a Flowerpot.
-
This component is the GHPython shell over the formal Python 3 worker.
-

    Args:
        _name: Text to be used for the Garden name.
        folder_: Optional folder path for the Garden root.
        _create: Set to True to create the Garden and Flowerpot.

    Returns:
        flowerpot: Opaque Flowerpot dictionary for downstream FP components.
        garden_root: Resolved Garden root folder.
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
    ghenv.Component.Name = "FP Create Garden"
    ghenv.Component.NickName = "CreateGarden"
    ghenv.Component.Message = "1.0.0"
    ghenv.Component.Category = "Flowerpot"
    ghenv.Component.SubCategory = "0 :: Garden"
    ghenv.Component.AdditionalHelpFromDocStrings = "1"
    ghenv.Component.Params.Input[0].Optional = False
    ghenv.Component.Params.Input[1].Optional = True
    ghenv.Component.Params.Input[2].Optional = False
except Exception:
    pass


def run(_name, folder_, _create):
    """Create a Garden Flowerpot through the formal worker."""
    if not _create:
        return {
            "flowerpot": None,
            "garden_root": None,
            "report": {
                "status": "idle",
                "message": "Create is false.",
                "warnings": [],
                "details": {},
            },
        }
    return _load_runtime().create_garden_flowerpot(_name, folder_)


def _load_runtime():
    """Reload runtime so Grasshopper picks up local repo edits immediately."""
    return _reload(_runtime)


flowerpot = None
garden_root = None
report = {
    "status": "idle",
    "message": "Create is false.",
    "warnings": [],
    "details": {},
}

if "_name" in globals() and "_create" in globals():
    if all_required_inputs_ready(ghenv.Component):
        _result = run(_name, globals().get("folder_"), _create)
        flowerpot = _result["flowerpot"]
        garden_root = _result["garden_root"]
        report = _result["report"]
