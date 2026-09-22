#! python 2
# env: installed runtime, then development source fallback

"""
Rebuild a Garden Ironbug authoring model as a native Ironbug HVAC system.
-
This component is the GHPython shell over the Flowerpot runtime.
-

    Args:
        _flowerpot: Opaque Flowerpot handle from an FP component.
        model_: Optional exact Ironbug authoring model identifier.
        follow_: Set to True to refresh when the selected model changes.

    Returns:
        hvac_system: Native Ironbug.HVAC.IB_HVACSystem or None on hard failure.
        report: Handoff and hard-gate diagnostics.
"""
import io
import json
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
    record_path = os.environ.get("LADYBUG_TOOLS_MCP_INSTALLATION") or os.path.join(
        os.path.expanduser("~"), ".ladybug-tools-mcp", "installation.json"
    )
    if os.path.isfile(record_path):
        with io.open(record_path, "r", encoding="utf-8") as stream:
            record = json.load(stream)
        if record.get("schema_version") != 1:
            raise ValueError("Unsupported Ladybug Tools MCP installation record.")
        candidates.append(record.get("package_root"))
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
    raise ImportError("Run the Ladybug Tools MCP installer with Grasshopper enabled to configure its runtime.")


_ensure_src_root()

from flowerpot.input_guard import all_required_inputs_ready
import flowerpot.runtime as _runtime

try:
    _reload = reload
except NameError:
    from importlib import reload as _reload

try:
    ghenv.Component.Name = "FP Detail HVAC"
    ghenv.Component.NickName = "DetailHVAC"
    ghenv.Component.Message = "1.3.0.dev0"
    ghenv.Component.Category = "Flowerpot"
    ghenv.Component.SubCategory = "Flowerpot"
    ghenv.Component.AdditionalHelpFromDocStrings = "4"
    ghenv.Component.Params.Input[0].Optional = False
    ghenv.Component.Params.Input[1].Optional = True
    ghenv.Component.Params.Input[2].Optional = True
except Exception:
    pass


def run(_flowerpot, model_=None, follow_=False):
    """Return a native Ironbug HVAC system from a Flowerpot Garden."""
    return _load_runtime().detail_ironbug_hvac(
        flowerpot=_flowerpot,
        model_identifier=model_,
        follow_flag=bool(follow_),
        component=_component_from_ghenv(),
    )


def _load_runtime():
    """Reload runtime so Grasshopper picks up local repo edits immediately."""
    return _reload(_runtime)


def _component_from_ghenv():
    """Return the live GHPython component instance when running in Grasshopper."""
    try:
        return ghenv.Component
    except Exception:
        return None


hvac_system = None
report = {
    "status": "idle",
    "message": "No Ironbug HVAC input requested.",
    "warnings": [],
    "details": {},
}

if "_flowerpot" in globals() and _flowerpot is not None:
    if all_required_inputs_ready(ghenv.Component):
        _result = run(
            _flowerpot,
            globals().get("model_"),
            globals().get("follow_", False),
        )
        hvac_system = _result["hvac_system"]
        report = _result["report"]

try:
    from Grasshopper.Kernel.Types import GH_ObjectWrapper

    report = GH_ObjectWrapper(report)
except Exception:
    pass
