import hashlib
import json
import sys
import types
from types import SimpleNamespace

import pytest

from flowerpot import runtime


class _AssemblyName:
    Name = "Ironbug.HVAC"
    Version = "1.26.0"


class _Assembly:
    def GetName(self):
        return _AssemblyName()


class _ClrType:
    FullName = "Ironbug.HVAC.IB_HVACSystem"
    Assembly = _Assembly()


class _NativeSystem:
    def GetType(self):
        return _ClrType()

    def ToJson(self):
        return "{}"


class _NativeHvac:
    class IB_HVACSystem:
        @staticmethod
        def FromJson(payload):
            assert json.loads(payload)["AirLoops"] == []
            return _NativeSystem()


class _FromJsonMethod:
    def Invoke(self, target, arguments):
        assert target is None
        assert json.loads(arguments[0])["AirLoops"] == []
        return _NativeSystem()


class _ReflectedHvacType:
    def GetMethod(self, name):
        return _FromJsonMethod() if name == "FromJson" else None


class _FollowDocument:
    def __init__(self):
        self.callbacks = []

    def ScheduleSolution(self, interval, callback):
        self.callbacks.append(callback)


class _FollowComponent:
    def __init__(self, document, identifier):
        self.document = document
        self.InstanceGuid = identifier
        self.expired = 0
        self.document_requests = 0

    def OnPingDocument(self):
        self.document_requests += 1
        return self.document

    def ExpireSolution(self, recompute):
        self.expired += 1


class _FakeTimer:
    created = []

    def __init__(self, interval, callback):
        self.interval = interval
        self.callback = callback
        self.cancelled = False
        self.daemon = False
        self.started = False
        self.__class__.created.append(self)

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True


def _worker_response(tmp_path, status="ok"):
    return {
        "specification": {"AirLoops": []},
        "allowlist": ["Ironbug.HVAC.IB_HVACSystem, Ironbug.HVAC"],
        "metadata": {"model_identifier": "hvac", "model_display_name": "HVAC"},
        "follow_path": str(tmp_path / "hvac.ibjson"),
        "report": {
            "status": status,
            "message": "ok",
            "warnings": [],
            "details": {},
        },
    }


def test_detail_ironbug_hvac_returns_native_system(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "_run_worker", lambda action, request: _worker_response(tmp_path))
    monkeypatch.setattr(runtime, "_load_native_ironbug_hvac", lambda: _NativeHvac)
    monkeypatch.setattr(runtime, "_sync_ironbug_follow_refresh", lambda *args: False)

    result = runtime.detail_ironbug_hvac({"type": "Flowerpot"})

    assert isinstance(result["hvac_system"], _NativeSystem)
    assert result["report"]["details"]["model_identifier"] == "hvac"
    assert "specification" not in result["report"]


def test_detail_hvac_reports_follow_source_and_keeps_snapshot_detached(
    monkeypatch, tmp_path
):
    model_path = tmp_path / "hvac.ibjson"
    model_path.write_text("garden authoring truth", encoding="utf-8")
    document = _FollowDocument()
    component = _FollowComponent(document, str(tmp_path))
    _FakeTimer.created = []
    monkeypatch.setattr(runtime.threading, "Timer", _FakeTimer)
    monkeypatch.setattr(runtime, "_run_worker", lambda action, request: _worker_response(tmp_path))
    monkeypatch.setattr(runtime, "_load_native_ironbug_hvac", lambda: _NativeHvac)

    before = hashlib.sha256(model_path.read_bytes()).digest()
    result = runtime.detail_ironbug_hvac(
        {"type": "Flowerpot"}, follow_flag=True, component=component
    )
    result["hvac_system"].edited = True

    details = result["report"]["details"]
    assert details["model_identifier"] == "hvac"
    assert details["model_display_name"] == "HVAC"
    assert details["follow"] is True
    assert details["follow_source"] == str(tmp_path / "hvac.ibjson")
    assert "specification" not in result["report"]
    assert hashlib.sha256(model_path.read_bytes()).digest() == before
    assert document.callbacks == []
    assert len(_FakeTimer.created) == 1


def test_detail_hvac_follow_false_clears_state_and_does_not_schedule(
    monkeypatch, tmp_path
):
    model_path = tmp_path / "hvac.ibjson"
    model_path.write_text("authoring truth", encoding="utf-8")
    document = _FollowDocument()
    component = _FollowComponent(document, str(tmp_path))
    monkeypatch.setattr(runtime, "_run_worker", lambda action, request: _worker_response(tmp_path))
    monkeypatch.setattr(runtime, "_load_native_ironbug_hvac", lambda: _NativeHvac)

    result = runtime.detail_ironbug_hvac(
        {"type": "Flowerpot"}, follow_flag=False, component=component
    )

    assert document.callbacks == []
    assert runtime._load_component_state().get_follow_signature(component) is None
    assert result["report"]["details"]["follow"] is False
    assert result["report"]["details"]["follow_source"] is None


def test_follow_refresh_uses_selected_file_and_stops_after_disable(
    monkeypatch, tmp_path
):
    path_one = tmp_path / "one.ibjson"
    path_two = tmp_path / "two.ibjson"
    path_one.write_text("one", encoding="utf-8")
    path_two.write_text("two", encoding="utf-8")
    document = _FollowDocument()
    component = _FollowComponent(document, str(tmp_path))
    _FakeTimer.created = []
    monkeypatch.setattr(runtime.threading, "Timer", _FakeTimer)

    runtime._sync_ironbug_follow_refresh(component, True, str(path_one))
    first_timer = _FakeTimer.created[-1]
    runtime._sync_ironbug_follow_refresh(component, True, str(path_two))
    second_timer = _FakeTimer.created[-1]
    assert first_timer.cancelled is True
    assert runtime._load_component_state().get_follow_signature(component)["path"] == str(
        path_two
    )

    path_one.write_text("one changed", encoding="utf-8")
    first_timer.callback()
    assert component.expired == 0
    second_timer.callback()
    assert document.callbacks == []
    third_timer = _FakeTimer.created[-1]

    path_two.write_text("two changed", encoding="utf-8")
    third_timer.callback()
    assert len(document.callbacks) == 1
    assert component.document_requests == 2
    runtime._sync_ironbug_follow_refresh(component, False)
    document.callbacks.pop(0)(document)
    assert component.expired == 0
    assert document.callbacks == []


def test_selection_error_clears_old_follow_callback(monkeypatch, tmp_path):
    model_path = tmp_path / "hvac.ibjson"
    model_path.write_text("authoring truth", encoding="utf-8")
    document = _FollowDocument()
    component = _FollowComponent(document, str(tmp_path))
    _FakeTimer.created = []
    monkeypatch.setattr(runtime.threading, "Timer", _FakeTimer)
    error_response = {
        "specification": None,
        "allowlist": [],
        "metadata": {},
        "follow_path": None,
        "report": {
            "status": "error",
            "message": "model not found",
            "warnings": ["model not found"],
            "details": {"candidate_identifiers": []},
        },
    }
    responses = [_worker_response(tmp_path), error_response]
    monkeypatch.setattr(runtime, "_run_worker", lambda action, request: responses.pop(0))
    monkeypatch.setattr(runtime, "_load_native_ironbug_hvac", lambda: _NativeHvac)

    runtime.detail_ironbug_hvac(
        {"type": "Flowerpot"}, follow_flag=True, component=component
    )
    stale_callback = _FakeTimer.created[-1].callback
    result = runtime.detail_ironbug_hvac(
        {"type": "Flowerpot"}, follow_flag=True, component=component
    )
    stale_callback()

    assert result["hvac_system"] is None
    assert result["report"]["details"]["follow"] is False
    assert runtime._load_component_state().get_follow_signature(component) is None
    assert component.expired == 0


def test_blocked_worker_readiness_still_returns_native_system(monkeypatch, tmp_path):
    monkeypatch.setattr(
        runtime,
        "_run_worker",
        lambda action, request: _worker_response(tmp_path, status="blocked"),
    )
    monkeypatch.setattr(runtime, "_load_native_ironbug_hvac", lambda: _NativeHvac)
    monkeypatch.setattr(runtime, "_sync_ironbug_follow_refresh", lambda *args: False)

    result = runtime.detail_ironbug_hvac({"type": "Flowerpot"})

    assert isinstance(result["hvac_system"], _NativeSystem)
    assert result["report"]["status"] == "blocked"
    assert result["report"]["details"]["failed_gate"] is None


def test_from_json_failure_returns_actionable_report(monkeypatch, tmp_path):
    class _FailingHvac:
        class IB_HVACSystem:
            @staticmethod
            def FromJson(payload):
                raise RuntimeError("invalid native payload")

    monkeypatch.setattr(
        runtime, "_run_worker", lambda action, request: _worker_response(tmp_path)
    )
    monkeypatch.setattr(runtime, "_load_native_ironbug_hvac", lambda: _FailingHvac)
    monkeypatch.setattr(runtime, "_sync_ironbug_follow_refresh", lambda *args: False)

    result = runtime.detail_ironbug_hvac({"type": "Flowerpot"})

    assert result["hvac_system"] is None
    assert result["report"]["status"] == "error"
    assert result["report"]["details"]["failed_gate"] == "from_json"
    assert "invalid native payload" in result["report"]["message"]


def test_reflected_loaded_type_calls_from_json_without_loading_another_assembly():
    result = runtime._call_native_from_json(
        _ReflectedHvacType(), json.dumps({"AirLoops": []})
    )

    assert isinstance(result, _NativeSystem)


def test_worker_candidates_allow_missing_ironpython_executable(monkeypatch):
    monkeypatch.setattr(runtime.sys, "executable", None)

    assert isinstance(runtime._worker_python_candidates(), list)


def test_loaded_hvac_prefers_default_assembly_context(monkeypatch):
    load_file_type, default_type = object(), object()

    class _LoadedAssembly:
        def __init__(self, context, system_type):
            self.context = context
            self.system_type = system_type

        def GetName(self):
            return SimpleNamespace(Name="Ironbug.HVAC")

        def GetType(self, name):
            assert name == "Ironbug.HVAC.IB_HVACSystem"
            return self.system_type

    load_file = _LoadedAssembly("LoadFile", load_file_type)
    default = _LoadedAssembly("Default", default_type)
    system = types.ModuleType("System")
    system.AppDomain = SimpleNamespace(
        CurrentDomain=SimpleNamespace(GetAssemblies=lambda: [load_file, default])
    )
    loader = types.ModuleType("System.Runtime.Loader")
    loader.AssemblyLoadContext = SimpleNamespace(
        GetLoadContext=lambda assembly: SimpleNamespace(Name=assembly.context)
    )
    monkeypatch.setitem(sys.modules, "System", system)
    monkeypatch.setitem(sys.modules, "System.Runtime.Loader", loader)

    assert runtime._loaded_native_ironbug_hvac() is default_type


def test_allowlist_rejects_nested_type_before_from_json(monkeypatch):
    called = []

    monkeypatch.setattr(
        runtime,
        "_load_native_ironbug_hvac",
        lambda: called.append(True),
    )
    with pytest.raises(runtime._NativeHvacGateError, match="Disallowed \\$type"):
        runtime._native_hvac_from_specification(
            {"AirLoops": [{"$type": "Ironbug.HVAC.Untrusted, Ironbug.HVAC"}]},
            ["Ironbug.HVAC.IB_HVACSystem, Ironbug.HVAC"],
        )
    assert called == []


@pytest.mark.parametrize(
    "gate, native",
    [
        ("clr_type", type("WrongSystem", (), {"GetType": lambda self: _ClrType()})()),
        ("assembly_version", _NativeSystem()),
        (
            "to_json",
            type(
                "NoJsonSystem",
                (),
                {
                    "GetType": lambda self: _ClrType(),
                    "ToJson": lambda self: (_ for _ in ()).throw(RuntimeError("boom")),
                },
            )(),
        ),
    ],
)
def test_native_hvac_hard_gates(monkeypatch, gate, native):
    if gate == "clr_type":
        wrong_type = type("WrongType", (), {"FullName": "Wrong.Type", "Assembly": _Assembly()})
        native.GetType = lambda: wrong_type()
    elif gate == "assembly_version":
        bad_assembly = type("BadAssembly", (), {"GetName": lambda self: type("Name", (), {"Version": "1.25.0"})()})
        native.GetType = lambda: type("Type", (), {"FullName": "Ironbug.HVAC.IB_HVACSystem", "Assembly": bad_assembly()})()
    monkeypatch.setattr(runtime, "_load_native_ironbug_hvac", lambda: SimpleNamespace(IB_HVACSystem=SimpleNamespace(FromJson=lambda payload: native)))

    with pytest.raises(runtime._NativeHvacGateError) as error:
        runtime._native_hvac_from_specification(
            {"AirLoops": []},
            ["Ironbug.HVAC.IB_HVACSystem, Ironbug.HVAC"],
        )
    assert error.value.gate == gate
