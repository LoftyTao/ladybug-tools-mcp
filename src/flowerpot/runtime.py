"""Runtime helpers for Flowerpot platform shell components.

This module is the GHPython/IronPython platform shell that delegates formal
Garden and Flowerpot work to the Python 3 worker in the project `.venv`.
"""

from __future__ import print_function

import json
import os
import subprocess
import sys

try:
    from collections.abc import Mapping
except ImportError:
    from collections import Mapping

try:
    _reload_module = reload
except NameError:
    from importlib import reload as _reload_module

_REQUIRED_COMPONENT_STATE_API = (
    "clear_follow_refresh_pending",
    "clear_follow_refresh_state",
    "consume_write_pulse",
    "get_follow_signature",
    "mark_follow_refresh_pending",
    "set_follow_signature",
)
_component_state = None

_WORKER_SESSION = None
_FOLLOW_POLL_INTERVAL_MS = 1000


def _load_component_state():
    """Return component_state, refreshing stale GH module caches when needed."""
    global _component_state
    import flowerpot.component_state as component_state

    missing = [
        name
        for name in _REQUIRED_COMPONENT_STATE_API
        if not hasattr(component_state, name)
    ]
    if missing:
        component_state = _reload_module(component_state)
    _component_state = component_state
    return _component_state


_load_component_state()


class FlowerpotHandle(object):
    """Grasshopper-friendly opaque handle for Flowerpot values."""

    def __init__(self, flowerpot):
        self._flowerpot = self._validated_payload(flowerpot)

    @classmethod
    def from_payload(cls, payload):
        return cls(payload)

    @staticmethod
    def _validated_payload(payload):
        if not isinstance(payload, Mapping):
            raise TypeError("Flowerpot payload must be a mapping.")
        values = list(payload.values())
        if len(values) == 1 and isinstance(values[0], Mapping):
            nested = values[0]
            if nested.get("type") == "Flowerpot":
                raise TypeError("Flowerpot payload must be a mapping.")
        if payload.get("type") != "Flowerpot":
            raise TypeError("Flowerpot payload must use current Flowerpot shape.")
        payload_context = payload.get("payload_context")
        if not isinstance(payload_context, Mapping):
            raise TypeError("Flowerpot payload must use current Flowerpot shape.")
        target = payload.get("target")
        if target is not None and not isinstance(target, Mapping):
            raise TypeError("Flowerpot payload must use current Flowerpot shape.")
        return dict(payload)

    def __repr__(self):
        return self._display_text()

    def __str__(self):
        return self._display_text()

    def ToString(self):
        return self._display_text()

    def to_dict(self):
        return self.to_payload()

    def to_payload(self):
        return dict(self._flowerpot)

    @property
    def payload_context(self):
        return dict(self._flowerpot.get("payload_context") or {})

    @property
    def flowerpot_id(self):
        return self.payload_context.get("flowerpot_id")

    @property
    def garden_root(self):
        return self.payload_context.get("garden_root")

    @property
    def kind(self):
        return self._flowerpot.get("kind")

    @property
    def label(self):
        return self._flowerpot.get("label")

    def _display_text(self):
        label = self.label
        if not label:
            label = self.flowerpot_id
        if not label:
            label = "Unnamed"
        return "Flowerpot : %s" % label


def create_garden_flowerpot(name, root_folder=None):
    """Create a Garden and return an opaque Flowerpot handle."""
    if not _normalize_optional_string(name):
        raise ValueError("_name is required.")
    response = _run_worker(
        "garden_create",
        {
            "name": name,
            "root_folder": _normalize_optional_string(root_folder),
        },
    )
    return _wrap_response_flowerpots(response)


def list_garden_flowerpots(root_folder=None):
    """List Gardens as opaque Flowerpot handles."""
    response = _run_worker(
        "garden_list",
        {
            "root_folder": _normalize_optional_string(root_folder),
        },
    )
    return _wrap_response_flowerpots(response)


def link_honeybee_model(
    flowerpot,
    model,
    write_flag,
    follow_flag,
    component=None,
):
    """Link a Honeybee model to a Flowerpot Garden."""
    if flowerpot is None:
        raise ValueError("_flowerpot is required.")

    payload = _payload_from_input(model, "Honeybee") if model is not None else None
    state = _load_component_state()
    should_write = state.consume_write_pulse(component, write_flag)
    if payload is not None and not should_write and not follow_flag:
        response = _run_worker(
            "honeybee_link",
            {
                "flowerpot": _flowerpot_to_dict(flowerpot),
                "payload": payload,
                "write": False,
                "follow": False,
                "component": _component_context(component),
            },
        )
        sync_follow_refresh(component, False)
        return {
            "model": model,
            "flowerpot": _wrap_flowerpot(_flowerpot_to_dict(flowerpot)),
            "changed": False,
            "report": response.get("report"),
        }

    response = _run_worker(
        "honeybee_link",
        {
            "flowerpot": _flowerpot_to_dict(flowerpot),
            "payload": payload,
            "write": bool(should_write),
            "follow": bool(follow_flag),
            "component": _component_context(component),
        },
    )
    sync_follow_refresh(component, follow_flag, response.get("flowerpot", flowerpot))
    if response.get("model") is None:
        model_out = None
    else:
        model_out = _honeybee_model_from_dict(response["model"])
    return {
        "model": model_out,
        "flowerpot": _wrap_flowerpot(response.get("flowerpot", flowerpot)),
        "changed": bool(response.get("changed")),
        "report": response.get("report"),
    }


def read_energy_properties_input(
    flowerpot,
    properties_type,
    value=None,
    follow_flag=False,
    component=None,
):
    """Read Honeybee Energy properties from a Flowerpot Garden."""
    return _read_properties_input(
        "energy_properties_input",
        flowerpot,
        properties_type,
        value,
        follow_flag,
        component,
    )


def read_radiance_properties_input(
    flowerpot,
    properties_type,
    value=None,
    follow_flag=False,
    component=None,
):
    """Read Honeybee Radiance properties from a Flowerpot Garden."""
    return _read_properties_input(
        "radiance_properties_input",
        flowerpot,
        properties_type,
        value,
        follow_flag,
        component,
    )


def _read_properties_input(
    action,
    flowerpot,
    properties_type,
    value=None,
    follow_flag=False,
    component=None,
):
    """Read Garden Properties Library objects through the Python 3 worker."""
    if flowerpot is None:
        return _properties_input_result(None, _required_input_report("_flowerpot"))

    normalized_type = _normalize_optional_string(properties_type)
    if not normalized_type:
        return _properties_input_result(None, _required_input_report("_type"))

    normalized_value = _normalize_optional_string(value)
    try:
        response = _run_worker(
            action,
            {
                "flowerpot": _flowerpot_to_dict(flowerpot),
                "type": str(normalized_type),
                "value": None if normalized_value is None else str(normalized_value),
            },
        )
    except Exception as error:
        sync_properties_follow_refresh(component, False, None)
        return _properties_input_result(None, _error_report(str(error)))
    report = response.get("report") or {}
    follow_path = response.get("follow_path")
    if not follow_flag or report.get("status") == "error" or not follow_path:
        sync_properties_follow_refresh(component, False, None)
    else:
        sync_properties_follow_refresh(
            component,
            True,
            follow_path,
        )
    return _properties_input_result(
        response.get("property"),
        report,
    )


def sync_properties_follow_refresh(component, follow_flag, follow_path=None):
    """Schedule or clear follow-mode polling for a properties index path."""
    if component is None:
        return False
    if not follow_flag:
        _load_component_state().clear_follow_refresh_state(component)
        return False
    state = _load_component_state()
    state.set_follow_signature(component, _file_signature(follow_path))
    return _schedule_component_refresh(component)


def _properties_input_result(property_value, report):
    return {
        "property": property_value,
        "report": report,
    }


def _required_input_report(input_name):
    return {
        "status": "idle",
        "message": "%s is required." % input_name,
        "warnings": [],
        "details": {},
    }


def _error_report(message):
    return {
        "status": "error",
        "message": message,
        "warnings": [message],
        "details": {},
    }


def _component_context(component):
    if component is None:
        return {}
    return {
        "name": getattr(component, "Name", None),
        "nickname": getattr(component, "NickName", None),
        "instance_guid": str(getattr(component, "InstanceGuid", "")),
    }


def sync_follow_refresh(component, follow_flag, flowerpot=None):
    """Schedule or clear Grasshopper follow-mode polling for one component."""
    if component is None:
        return False
    if not follow_flag:
        _load_component_state().clear_follow_refresh_state(component)
        return False
    state = _load_component_state()
    state.set_follow_signature(component, _follow_signature(flowerpot))
    return _schedule_component_refresh(component)


def _wrap_response_flowerpots(response):
    wrapped = dict(response)
    if "flowerpot" in wrapped:
        wrapped["flowerpot"] = _wrap_flowerpot(wrapped["flowerpot"])
    if "flowerpots" in wrapped:
        wrapped["flowerpots"] = [
            _wrap_flowerpot(flowerpot)
            for flowerpot in wrapped.get("flowerpots", [])
        ]
    return wrapped


def _wrap_flowerpot(flowerpot):
    if isinstance(flowerpot, FlowerpotHandle):
        return flowerpot
    if isinstance(flowerpot, dict) and flowerpot.get("type") == "Flowerpot":
        try:
            return FlowerpotHandle.from_payload(flowerpot)
        except TypeError:
            return flowerpot
    return flowerpot


def _flowerpot_to_dict(flowerpot):
    unwrapped = _unwrap_grasshopper_input(flowerpot)
    if isinstance(unwrapped, FlowerpotHandle):
        return unwrapped.to_dict()
    if isinstance(unwrapped, dict):
        return unwrapped
    if hasattr(unwrapped, "to_dict"):
        value = unwrapped.to_dict()
        if isinstance(value, dict):
            return value
    return unwrapped


def _honeybee_model_from_dict(payload):
    try:
        from honeybee.model import Model

        return Model.from_dict(payload)
    except Exception:
        return payload


def _payload_from_input(value, label):
    normalized_value = _unwrap_grasshopper_input(value)
    if isinstance(normalized_value, dict):
        return normalized_value
    if isinstance(normalized_value, basestring):
        return json.loads(normalized_value)
    if hasattr(normalized_value, "to_dict"):
        payload = normalized_value.to_dict()
        if isinstance(payload, dict):
            return payload
    raise TypeError(
        "Unsupported %s payload type for Flowerpot Grasshopper runtime: %s."
        % (label, type(value).__name__)
    )


def _unwrap_grasshopper_input(value):
    current = value
    seen = set()
    while current is not None:
        marker = id(current)
        if marker in seen:
            return current
        seen.add(marker)

        singleton_value = _unwrap_singleton_sequence(current)
        if singleton_value is not None:
            current = singleton_value
            continue

        return current
    return None


def _unwrap_singleton_sequence(value):
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return value[0]

    count = getattr(value, "Count", None)
    if isinstance(count, int) and count == 1:
        try:
            return value[0]
        except Exception:
            return None

    length = getattr(value, "Length", None)
    if isinstance(length, int) and length == 1:
        try:
            return value[0]
        except Exception:
            return None
    return None


def _normalize_optional_string(value):
    normalized = _unwrap_grasshopper_input(value)
    if normalized is None:
        return None
    if isinstance(normalized, basestring):
        stripped = normalized.strip()
        return stripped or None
    return normalized


def _run_worker(action, request):
    return _get_worker_session().run(action, request)


def _schedule_component_refresh(component):
    """Ask Grasshopper to expire this component on the next follow poll."""
    state = _load_component_state()
    if not state.mark_follow_refresh_pending(component):
        return False
    try:
        document = component.OnPingDocument()
    except Exception:
        state.clear_follow_refresh_pending(component)
        return False
    if document is None:
        state.clear_follow_refresh_pending(component)
        return False

    def _expire(document_argument):
        state_now = _load_component_state()
        try:
            if _follow_signature_changed(component):
                component.ExpireSolution(False)
            else:
                state_now.clear_follow_refresh_pending(component)
                _schedule_component_refresh(component)
        finally:
            if _follow_signature_changed(component):
                state_now.clear_follow_refresh_pending(component)

    callback = _schedule_delegate(_expire)
    try:
        document.ScheduleSolution(_FOLLOW_POLL_INTERVAL_MS, callback)
        return True
    except Exception:
        state.clear_follow_refresh_pending(component)
        return False


def _schedule_delegate(callback):
    """Return a GH schedule delegate when available, otherwise the callback."""
    try:
        from Grasshopper.Kernel import GH_Document

        return GH_Document.GH_ScheduleDelegate(callback)
    except Exception:
        return callback


def _follow_signature_changed(component):
    """Return True when the followed Garden/model file appears changed."""
    previous = _load_component_state().get_follow_signature(component)
    if previous is None:
        return True
    if not previous.get("exists"):
        return True
    current = _file_signature(previous.get("path"))
    return current != previous


def _follow_signature(flowerpot):
    """Return a lightweight file signature for a Flowerpot target."""
    flowerpot = _flowerpot_to_dict(flowerpot)
    if not isinstance(flowerpot, dict):
        return None
    payload_context = flowerpot.get("payload_context") or {}
    garden_root = payload_context.get("garden_root")
    if not garden_root:
        return None
    target = flowerpot.get("target") or {}
    relative_path = target.get("path")
    if not relative_path:
        return None
    path = os.path.join(garden_root, relative_path.replace("/", os.sep))
    return _file_signature(path)


def _file_signature(path):
    """Return a compact signature for a file path."""
    if not path:
        return None
    try:
        normalized = os.path.abspath(path)
        stat = os.stat(normalized)
    except Exception:
        return {
            "path": os.path.abspath(path),
            "exists": False,
            "mtime": None,
            "size": None,
        }
    return {
        "path": normalized,
        "exists": True,
        "mtime": stat.st_mtime,
        "size": stat.st_size,
    }


def _get_worker_session():
    global _WORKER_SESSION
    if _WORKER_SESSION is None or not _WORKER_SESSION.is_alive():
        _WORKER_SESSION = _start_worker_session()
    return _WORKER_SESSION


def _start_worker_session():
    return _WorkerSession()


class _WorkerSession(object):
    """Persistent Python 3 worker process for GH component calls."""

    def __init__(self):
        self.process = _open_worker_process(session=True)

    def is_alive(self):
        return self.process.poll() is None

    def run(self, action, request):
        if not self.is_alive():
            raise RuntimeError("Grasshopper worker session is not running.")
        message = json.dumps(
            {
                "action": action,
                "request": request,
            },
            ensure_ascii=False,
        )
        self.process.stdin.write(_encode_text(message + "\n"))
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("Worker session returned an empty response.")
        response = json.loads(_decode_text(line))
        if not response.get("ok"):
            raise RuntimeError(response.get("error", "Worker session failed."))
        return response.get("result")


def _open_worker_process(action=None, session=False):
    command = [
        _worker_python_executable(),
        "-m",
        "flowerpot.worker_cli",
    ]
    if session:
        command.append("--session")
    else:
        command.append(action)
    return subprocess.Popen(
        command,
        cwd=_repository_root(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_worker_environment(),
        **_worker_subprocess_flags()
    )


def _run_worker_once(action, request):
    process = _open_worker_process(action=action)
    stdout, stderr = process.communicate(
        json.dumps(request, ensure_ascii=False).encode("utf-8")
    )
    stdout = _decode_text(stdout)
    stderr = _decode_text(stderr)

    if process.returncode != 0:
        message = stderr.strip() or stdout.strip() or (
            "Worker exited with code %s." % process.returncode
        )
        raise RuntimeError(message)
    if not stdout.strip():
        raise RuntimeError("Worker returned an empty response.")

    response = json.loads(stdout)
    if "error" in response:
        raise RuntimeError(str(response["error"]))
    return response


def _worker_python_executable():
    candidates = _worker_python_candidates()
    for python_exe in candidates:
        if os.path.isfile(python_exe):
            return python_exe
    searched = ", ".join(candidates) if candidates else "<none>"
    raise RuntimeError(
        "Flowerpot worker Python was not found. "
        "Create the project .venv before using Grasshopper shell components. "
        "Searched: %s" % searched
    )


def _worker_python_candidates():
    candidates = []

    def _append(candidate):
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    root = _repository_root()
    _append(os.path.join(root, ".venv", "Scripts", "python.exe"))
    parent = os.path.dirname(root)
    if os.path.basename(parent) == ".worktrees":
        _append(
            os.path.join(
                os.path.dirname(parent),
                ".venv",
                "Scripts",
                "python.exe",
            )
        )
    src_root = os.environ.get("LADYBUG_TOOLS_MCP_SRC")
    if src_root:
        _append(
            os.path.join(
                os.path.abspath(os.path.join(src_root, os.pardir)),
                ".venv",
                "Scripts",
                "python.exe",
            )
        )
    if os.path.basename(sys.executable).lower().startswith("python"):
        _append(sys.executable)
    return candidates


def _worker_environment():
    env = os.environ.copy()
    src_root = os.path.join(_repository_root(), "src")
    env["PYTHONIOENCODING"] = "utf-8"
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        src_root if not existing_pythonpath else src_root + os.pathsep + existing_pythonpath
    )
    for variable_name in ("PYTHONHOME", "IRONPYTHONPATH"):
        env.pop(variable_name, None)
    return env


def _worker_subprocess_flags():
    if os.name != "nt":
        return {}

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0x00000001)
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        "startupinfo": startupinfo,
    }


def _repository_root():
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(here, "..", ".."))


def _decode_text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def _encode_text(value):
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8")


try:
    basestring
except NameError:
    basestring = str
