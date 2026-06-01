#! python 2
# env: prefer LADYBUG_TOOLS_MCP_SRC, then file-relative bootstrap

"""
List Ladybug Tools Gardens and wrap each one as a Flowerpot.
-
This component is the GHPython shell over the formal Python 3 worker.
-

    Args:
        folder_: Optional folder containing Garden project folders.
        refresh_: Set to True to refresh the list of Gardens.

    Returns:
        flowerpots: Opaque Flowerpot dictionaries for downstream FP components.
        garden_roots: Resolved Garden root folders.
        names: Garden names.
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

import flowerpot.runtime as _runtime
from flowerpot.input_guard import all_required_inputs_ready

try:
    _reload = reload
except NameError:
    from importlib import reload as _reload

try:
    ghenv.Component.Name = "FP Garden List"
    ghenv.Component.NickName = "GardenList"
    ghenv.Component.Message = "1.1.0"
    ghenv.Component.Category = "Flowerpot"
    ghenv.Component.SubCategory = "0 :: Garden"
    ghenv.Component.AdditionalHelpFromDocStrings = "1"
    ghenv.Component.Params.Input[0].Optional = True
    ghenv.Component.Params.Input[1].Optional = True
except Exception:
    pass


def run(folder_, refresh_):
    """List Garden Flowerpots through the formal worker."""
    if not refresh_:
        return {
            "flowerpots": [],
            "garden_roots": [],
            "names": [],
            "report": {
                "status": "idle",
                "message": "Refresh is false.",
                "warnings": [],
                "details": {},
            },
        }
    return _load_runtime().list_garden_flowerpots(folder_)


def _load_runtime():
    """Reload runtime so Grasshopper picks up local repo edits immediately."""
    return _reload(_runtime)


flowerpots = []
garden_roots = []
names = []
report = {
    "status": "idle",
    "message": "Refresh is false.",
    "warnings": [],
    "details": {},
}

if "ghenv" in globals():
    if all_required_inputs_ready(ghenv.Component):
        _result = run(globals().get("folder_"), globals().get("refresh_", False))
        flowerpots = _result["flowerpots"]
        garden_roots = _result["garden_roots"]
        names = _result["names"]
        report = _result["report"]
