"""Contract tests for the Ironbug .NET bridge RPC client, runtime resolution, and service guards."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

from fastmcp import Client

from garden.ironbug.client import (
    _STDERR_RING_MAXLEN,
    IronbugBridgeClient,
    IronbugBridgeError,
    _format_stderr_tail,
)
from garden.ironbug.runtime import (
    IronbugRuntimePaths,
    IronbugRuntimeUnavailable,
    resolve_runtime_paths,
)
from garden.ironbug.service import (
    configure_ironbug_loops,
    create_ironbug_system,
    upsert_ironbug_components,
    validate_ironbug_system,
)
from garden.ironbug.store import empty_draft, save_ironbug_system
from garden.manifest import GardenManifest
from garden.store import create_garden
from ladybug_tools_mcp.server import create_mcp

_MOCK_WORKER_SOURCE = textwrap.dedent(
    """
    import json
    import os
    import sys
    import time

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        req = json.loads(line)
        req_id = req["id"]
        method = req["method"]

        if method == "noisy_stderr":
            written = 0
            for idx in range(1200):
                msg = f"stderr-line-{idx:04d} " + ("X" * 64) + "\\n"
                sys.stderr.write(msg)
                written += len(msg.encode("utf-8"))
            tail = "STDERR_TAIL_SENTINEL_OK\\n"
            sys.stderr.write(tail)
            written += len(tail.encode("utf-8"))
            sys.stderr.flush()
            sys.stdout.write(
                json.dumps(
                    {
                        "id": req_id,
                        "ok": True,
                        "result": {"bytes_written": written, "pid": os.getpid()},
                    }
                )
                + "\\n"
            )
            sys.stdout.flush()
        elif method == "hang":
            sys.stderr.write("about-to-hang-sentinel\\n")
            sys.stderr.flush()
            time.sleep(30.0)
        elif method == "ping":
            sys.stdout.write(
                json.dumps({"id": req_id, "ok": True, "result": {"pong": True, "pid": os.getpid()}})
                + "\\n"
            )
            sys.stdout.flush()
        else:
            sys.stdout.write(
                json.dumps(
                    {
                        "id": req_id,
                        "ok": False,
                        "error": {"type": "UnknownMethod", "message": f"Unknown {method}"},
                    }
                )
                + "\\n"
            )
            sys.stdout.flush()
    """
).lstrip()


def _probe_live_ironbug_runtime() -> tuple[bool, str]:
    try:
        resolve_runtime_paths(require_openstudio=True)
    except IronbugRuntimeUnavailable as exc:
        return False, str(exc)
    return True, "Ironbug + OpenStudio C# runtime available"


_LIVE_IRONBUG_OK, _LIVE_IRONBUG_REASON = _probe_live_ironbug_runtime()


def _parse_execute_payload(res: object) -> dict[str, object]:
    data = getattr(res, "data", None)
    if isinstance(data, dict):
        return data
    content = getattr(res, "content", []) or []
    for block in content:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            return json.loads(text)
    raise AssertionError(f"Unable to parse Code Mode execute result: {res!r}")


class TestIronbugBridgeProtocol(unittest.TestCase):
    """Test IronbugBridgeClient pipe draining, timeout recovery, guards, and live PTAC flow."""

    def _dummy_paths(self, root: Path) -> IronbugRuntimePaths:
        return IronbugRuntimePaths(
            ironbug_dir=root,
            ironbug_exe=None,
            openstudio_csharp_dir=None,
            dotnet_exe=sys.executable,
            bridge_dll=root / "IronbugBridge.dll",
        )

    def _make_popen_interceptor(self, worker_script: Path):
        real_popen = subprocess.Popen

        def fake_popen(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
            return real_popen([sys.executable, "-u", str(worker_script)], *args, **kwargs)

        return fake_popen

    def test_large_stderr_output_does_not_deadlock_and_captures_ring_tail(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            worker = root / "mock_worker.py"
            worker.write_text(_MOCK_WORKER_SOURCE, encoding="utf-8")
            client = IronbugBridgeClient(self._dummy_paths(root))

            try:
                with mock.patch(
                    "garden.ironbug.client.subprocess.Popen",
                    side_effect=self._make_popen_interceptor(worker),
                ):
                    result = client.call("noisy_stderr", timeout=5.0)
                    self.assertGreater(result["bytes_written"], 65_536)
                    self.assertIsNotNone(client._stderr_ring)
                    assert client._stderr_ring is not None
                    self.assertEqual(len(client._stderr_ring), _STDERR_RING_MAXLEN)
                    tail = _format_stderr_tail(client._stderr_ring, client._stderr_lock)
                    self.assertIn("STDERR_TAIL_SENTINEL_OK", tail)
                    self.assertNotIn("stderr-line-0000", list(client._stderr_ring))
            finally:
                client.close(force=True)

    def test_rpc_timeout_kills_worker_and_auto_restarts_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            worker = root / "mock_worker.py"
            worker.write_text(_MOCK_WORKER_SOURCE, encoding="utf-8")
            client = IronbugBridgeClient(self._dummy_paths(root))

            try:
                with mock.patch(
                    "garden.ironbug.client.subprocess.Popen",
                    side_effect=self._make_popen_interceptor(worker),
                ):
                    first = client.call("ping", timeout=3.0)
                    self.assertTrue(first["pong"])
                    pid_before = first["pid"]

                    with self.assertRaises(IronbugBridgeError) as ctx:
                        client.call("hang", timeout=0.5)
                    self.assertEqual(ctx.exception.error_type, "TimeoutError")
                    self.assertIn("about-to-hang-sentinel", str(ctx.exception))
                    self.assertIsNone(client._proc)

                    second = client.call("ping", timeout=3.0)
                    self.assertTrue(second["pong"])
                    self.assertNotEqual(second["pid"], pid_before)
            finally:
                client.close(force=True)

    def test_resolve_runtime_paths_without_openstudio(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ironbug_dir = root / "ironbug"
            ironbug_dir.mkdir()
            bridge_dll = root / "IronbugBridge.dll"
            bridge_dll.write_bytes(b"")

            with (
                mock.patch("garden.ironbug.runtime.resolve_ironbug_dir", return_value=ironbug_dir),
                mock.patch("garden.ironbug.runtime.resolve_ironbug_console_exe", return_value=None),
                mock.patch("garden.ironbug.runtime.resolve_openstudio_csharp_dir", return_value=None),
                mock.patch("garden.ironbug.runtime.shutil.which", return_value=sys.executable),
                mock.patch("garden.ironbug.runtime._repo_or_packaged_bridge_dll", return_value=bridge_dll),
            ):
                paths = resolve_runtime_paths(require_openstudio=False)
                self.assertEqual(paths.ironbug_dir, ironbug_dir)
                self.assertIsNone(paths.openstudio_csharp_dir)
                self.assertEqual(paths.bridge_dll, bridge_dll)

                with self.assertRaises(IronbugRuntimeUnavailable) as ctx:
                    resolve_runtime_paths(require_openstudio=True)
                self.assertTrue(
                    any("OpenStudio.dll" in item for item in ctx.exception.missing),
                    f"Expected OpenStudio.dll in missing: {ctx.exception.missing}",
                )

    def test_imported_only_draft_overwrite_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            garden_root = Path(tmpdir) / "ironbug_guard_garden"
            create_garden(name="ironbug_guard_garden", root_dir=str(garden_root))
            manifest = GardenManifest.read(garden_root)
            target, _, _ = save_ironbug_system(
                garden_root,
                manifest,
                identifier="imported_sys",
                specification_json=json.dumps({"$type": "Ironbug.HVAC.IB_HVACSystem, Ironbug.HVAC"}),
                draft=empty_draft(display_name="Imported", imported_only=True),
                overwrite=True,
            )

            with self.assertRaises(ValueError) as upsert_err:
                upsert_ironbug_components(
                    garden_root=str(garden_root),
                    ironbug_model_target=target,
                    components={"fan": {"type": "IB_FanOnOff"}},
                    replace=False,
                )
            self.assertIn("replace=true", str(upsert_err.exception))

            with self.assertRaises(ValueError) as loops_err:
                configure_ironbug_loops(
                    garden_root=str(garden_root),
                    ironbug_model_target=target,
                    thermal_zones=[{"room_name": "Room1", "zone_equipments": []}],
                    replace=False,
                )
            self.assertIn("replace=true", str(loops_err.exception))

    @unittest.skipUnless(_LIVE_IRONBUG_OK, _LIVE_IRONBUG_REASON)
    def test_live_ptac_build_and_validate(self) -> None:
        async def _run() -> dict[str, object]:
            with tempfile.TemporaryDirectory() as tmpdir:
                garden_root = (Path(tmpdir) / "live_ptac_garden").as_posix()
                mcp = create_mcp()
                code = textwrap.dedent(
                    f"""
                    g = await call_tool("GD_create", {{"name": "live_ptac_garden", "root_dir": {garden_root!r}}})
                    g_root = g["garden_root"]
                    sys_res = await call_tool("IB_create_system", {{
                        "garden_root": g_root,
                        "identifier": "ptac_contract",
                        "overwrite": True,
                    }})
                    ib_target = sys_res["target"]
                    await call_tool("IB_upsert_components", {{
                        "garden_root": g_root,
                        "ironbug_model_target": ib_target,
                        "components": {{
                            "ptac_fan": {{"type": "IB_FanOnOff"}},
                            "ptac_hc": {{"type": "IB_CoilHeatingElectric"}},
                            "ptac_cc": {{"type": "IB_CoilCoolingDXSingleSpeed"}},
                            "ptac": {{
                                "type": "IB_ZoneHVACPackagedTerminalAirConditioner",
                                "ctor_args": ["ptac_fan", "ptac_hc", "ptac_cc"],
                            }},
                        }},
                    }})
                    await call_tool("IB_configure_loops", {{
                        "garden_root": g_root,
                        "ironbug_model_target": ib_target,
                        "thermal_zones": [{{"room_name": "Room1", "zone_equipments": ["ptac"]}}],
                    }})
                    val = await call_tool("IB_validate_system", {{
                        "garden_root": g_root,
                        "ironbug_model_target": ib_target,
                    }})
                    return val
                    """
                ).strip()
                async with Client(mcp) as client:
                    res = await client.call_tool("execute", {"code": code})
                    return _parse_execute_payload(res)

        payload = asyncio.run(_run())
        self.assertFalse(payload.get("blocked"), f"Ironbug runtime blocked unexpectedly: {payload}")
        self.assertTrue(payload.get("valid"), f"Expected valid=True, got: {payload}")
        self.assertTrue(payload.get("ready"), f"Expected ready=True, got: {payload}")
        self.assertEqual(payload.get("errors"), [])
        self.assertTrue(payload.get("openstudio_summary"))

    def test_remove_only_upsert_fcu_precheck_and_live_autosize(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            g_root = Path(tmpdir) / "ib_stage_garden"
            create_garden(name="ib_stage_garden", root_dir=str(g_root))

            class _FakeBridgeClient:
                def call(self, method: str, payload: dict[str, object], timeout: float = 30.0) -> dict[str, object]:
                    del timeout
                    if method == "build":
                        comps = payload.get("components") or {}
                        assert isinstance(comps, dict)
                        return {
                            "specification_json": json.dumps({"$type": "Ironbug.HVAC.IB_HVACSystem, Ironbug.HVAC"}),
                            "summary": {"component_ids": sorted(comps.keys())},
                        }
                    if method == "validate":
                        return {
                            "valid": True,
                            "errors": [],
                            "warnings": [],
                            "thermal_zones": ["Room1"],
                            "system_summary": {"thermal_zones": ["Room1"]},
                            "openstudio_summary": {},
                        }
                    return {}

            with mock.patch("garden.ironbug.service.get_bridge_client", return_value=_FakeBridgeClient()):
                sys_res = create_ironbug_system(garden_root=str(g_root), identifier="fcu_test", overwrite=True)
                ib_target = sys_res["target"]
                upsert_ironbug_components(
                    garden_root=str(g_root),
                    ironbug_model_target=ib_target,
                    components={
                        "c1": {"type": "IB_FanVariableVolume"},
                        "c2": {"type": "IB_PumpConstantSpeed"},
                        "fcu": {
                            "type": "IB_ZoneHVACFourPipeFanCoil",
                            "fields": {"CapacityControlMethod": "CyclingFan"},
                            "wiring": {"fan": "c1"},
                        },
                    },
                )
                rm_res = upsert_ironbug_components(
                    garden_root=str(g_root),
                    ironbug_model_target=ib_target,
                    remove_ids=["c2"],
                )
                self.assertEqual(rm_res["summary_view"]["component_count"], 2)
                self.assertNotIn("c2", rm_res["summary_view"]["components"])

                val_res = validate_ironbug_system(garden_root=str(g_root), ironbug_model_target=ib_target)
                self.assertFalse(val_res["valid"])
                self.assertTrue(
                    any(issue.get("code") == "ironbug_fcu_cycling_fan_type_mismatch" for issue in val_res["blocking_issues"]),
                    f"Expected ironbug_fcu_cycling_fan_type_mismatch in {val_res['blocking_issues']}",
                )

        if _LIVE_IRONBUG_OK:
            async def _run_live() -> dict[str, object]:
                with tempfile.TemporaryDirectory() as tmpdir2:
                    g2 = (Path(tmpdir2) / "ib_live_autosize").as_posix()
                    mcp = create_mcp()
                    code = textwrap.dedent(
                        f"""
                        g = await call_tool("GD_create", {{"name": "ib_live_autosize", "root_dir": {g2!r}}})
                        gr = g["garden_root"]
                        s = await call_tool("IB_create_system", {{"garden_root": gr, "identifier": "autosize_sys", "overwrite": True}})
                        t = s["target"]
                        await call_tool("IB_upsert_components", {{
                            "garden_root": gr,
                            "ironbug_model_target": t,
                            "components": {{
                                "fan": {{"type": "IB_FanOnOff"}},
                                "hc": {{"type": "IB_CoilHeatingElectric"}},
                                "cc": {{"type": "IB_CoilCoolingDXSingleSpeed"}},
                                "ptac": {{"type": "IB_ZoneHVACPackagedTerminalAirConditioner", "ctor_args": ["fan", "hc", "cc"]}},
                                "pump": {{"type": "IB_PumpVariableSpeed", "fields": {{"RatedFlowRate": "autosize"}}}},
                                "chiller": {{"type": "IB_ChillerElectricEIR", "fields": {{"ReferenceCapacity": "autosize", "ReferenceCOP": 5.5}}}},
                                "coil_cw": {{"type": "IB_CoilCoolingWater"}},
                            }},
                        }})
                        await call_tool("IB_configure_loops", {{
                            "garden_root": gr,
                            "ironbug_model_target": t,
                            "thermal_zones": [{{"room_name": "Room1", "zone_equipments": ["ptac"]}}],
                            "plant_loops": [{{
                                "name": "CHWLoop",
                                "loop_type": "Cooling",
                                "supply": ["pump"],
                                "supply_branches": [["chiller"]],
                                "supply_setpoint": 6.7,
                                "demand_branches": [["coil_cw"]],
                            }}],
                        }})
                        return await call_tool("IB_validate_system", {{"garden_root": gr, "ironbug_model_target": t}})
                        """
                    ).strip()
                    async with Client(mcp) as client:
                        return _parse_execute_payload(await client.call_tool("execute", {"code": code}))

            live_val = asyncio.run(_run_live())
            self.assertTrue(live_val.get("valid"), live_val)
            os_sum = live_val.get("openstudio_summary") or {}
            assert isinstance(os_sum, dict)
            for key in (
                "pumps_constant_speed",
                "pumps_variable_speed",
                "fans_on_off",
                "fans_constant_volume",
                "fans_variable_volume",
            ):
                self.assertIn(key, os_sum)
            self.assertGreaterEqual(int(os_sum["pumps_variable_speed"]), 1)
            self.assertGreaterEqual(int(os_sum["fans_on_off"]), 1)


if __name__ == "__main__":
    unittest.main()
