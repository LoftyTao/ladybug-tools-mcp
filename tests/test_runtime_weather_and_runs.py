"""Tests for runtime Code Mode error recovery, weather download/search, EnergyPlus run isolation, and run_energy schemas."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
from pathlib import Path
import shutil
import ssl
from types import SimpleNamespace
from typing import Any
from unittest import mock
from urllib.error import HTTPError, URLError
import zipfile

from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
import pytest

from garden.manifest import GardenManifest
from garden.run_energy import annual, config as weather_config, weather_download
from garden.store import create_garden
from ladybug_tools_mcp.code_mode import PreviewMontySandboxProvider
from ladybug_tools_mcp.contracts import MutationResultModel
from ladybug_tools_mcp.registry import register_tools
from ladybug_tools_mcp.server import create_mcp


_REPO_ROOT = Path(__file__).resolve().parents[1]


def _parse_tool_result(res: Any) -> dict[str, Any]:
    structured = getattr(res, "structured_content", None)
    if isinstance(structured, dict):
        return structured
    data = getattr(res, "data", None)
    if isinstance(data, dict):
        return data
    for block in getattr(res, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
    raise AssertionError(f"Unable to parse FastMCP tool result: {res!r}")


async def _call(mcp: FastMCP, name: str, args: dict[str, Any]) -> dict[str, Any]:
    async with Client(mcp) as client:
        res = await client.call_tool(name, args)
        return _parse_tool_result(res)


def _make_raw_mcp() -> FastMCP:
    mcp = FastMCP("runtime-weather-runs-test", strict_input_validation=True)
    register_tools(mcp)
    return mcp


def _chicago_weather_paths() -> tuple[Path, Path, Path | None]:
    base = _REPO_ROOT / "resources" / "dragonfly-energy" / "tests" / "epw"
    stat = base / "chicago.stat"
    return base / "chicago.epw", base / "chicago.ddy", stat if stat.is_file() else None


def _setup_box_garden(tmp_path: Path, name: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    g_path = (tmp_path / name).resolve()
    gr = g_path.as_posix()
    raw_mcp = _make_raw_mcp()

    async def _prep() -> tuple[dict[str, Any], dict[str, Any]]:
        async with Client(raw_mcp) as client:
            await client.call_tool("GD_Create", {"name": name, "root_dir": gr})
            m_res = _parse_tool_result(
                await client.call_tool(
                    "HB_Create_Model",
                    {"garden_root": gr, "identifier": "Office_Model"},
                )
            )
            await client.call_tool(
                "HB_Create_Objects",
                {
                    "garden_root": gr,
                    "object_type": "room",
                    "identifier": "Room_1",
                    "x_dim": 6.0,
                    "y_dim": 5.0,
                    "height": 3.0,
                },
            )
            epw, ddy, stat = _chicago_weather_paths()
            wx_dir = tmp_path / f"{name}_wx_src"
            wx_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(epw, wx_dir / "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw")
            shutil.copy2(ddy, wx_dir / "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.ddy")
            if stat is not None:
                shutil.copy2(stat, wx_dir / "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.stat")
            w_res = _parse_tool_result(
                await client.call_tool(
                    "LB_Manage_Weather",
                    {"garden_root": gr, "action": "import", "source_path": str(wx_dir)},
                )
            )
            return m_res["target"], w_res["target"]

    model_target, weather_target = asyncio.run(_prep())
    return g_path, model_target, weather_target


# ===========================================================================
# 1. P0-1: Monty multiline call_tool error recovery
# ===========================================================================


def test_monty_multiline_call_tool_error_recovery() -> None:
    """Multiline await call_tool(...) exceptions surface the real inner tool error instead of Monty protocol crashes."""
    provider = PreviewMontySandboxProvider()

    async def failing_call_tool(tool_name: str, arguments: Any = None) -> Any:
        del arguments
        raise ValueError(f"bad argument for {tool_name}")

    multiline_code = (
        'res = await call_tool(\n'
        '    "HB_Create_Model",\n'
        '    {"garden_root": "missing"}\n'
        ')\n'
        'return res'
    )

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(
            provider.run(
                multiline_code,
                external_functions={"call_tool": failing_call_tool},
            )
        )
    message = str(exc_info.value)
    assert "monty worker protocol error" not in message.lower()
    assert "Error calling tool 'HB_Create_Model'" in message
    assert "bad argument for HB_Create_Model" in message
    assert isinstance(exc_info.value.__cause__, ValueError)

    # Normal non-protocol exceptions (no failing inner call_tool) remain untouched.
    non_tool_multiline = "x = (\n    1 / 0\n)\nreturn x"
    with pytest.raises(Exception) as non_tool_exc:
        asyncio.run(
            provider.run(
                non_tool_multiline,
                external_functions={"call_tool": failing_call_tool},
            )
        )
    assert "Error calling tool" not in str(non_tool_exc.value)
    assert "ZeroDivisionError" in repr(non_tool_exc.value) or "division by zero" in str(non_tool_exc.value).lower()

    # End-to-end Code Mode execute() check with multiline call_tool raising in a real tool.
    mcp = create_mcp()

    async def _run_execute() -> None:
        async with Client(mcp) as client:
            with pytest.raises(ToolError) as tool_err:
                await client.call_tool(
                    "execute",
                    {
                        "code": (
                            'return await call_tool(\n'
                            '    "GD_Get",\n'
                            '    {"garden_root": "D:/definitely_missing_garden_xyz_999"}\n'
                            ')'
                        )
                    },
                )
            err_text = str(tool_err.value)
            assert "monty worker protocol error" not in err_text.lower()
            assert "GD_Get" in err_text or "garden" in err_text.lower()

    asyncio.run(_run_execute())


# ===========================================================================
# 2. P0-2: Weather TLS, retries, remote search, ambiguity, OSS cap, metadata
# ===========================================================================


def test_weather_tls_retries_remote_search_ambiguity_and_sha256(tmp_path: Path) -> None:
    """Verify HTTPS URL, resilient SSLContext, retry on URLError/TimeoutError, remote search, ambiguity, and epw_sha256."""
    assert weather_download.EPW_API_URL == "https://epwapi.greensimhub.com.cn"

    # SSL context always enforces verified TLS (never CERT_NONE).
    weather_download._build_ssl_context.cache_clear()
    ctx = weather_download._build_ssl_context()
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True

    # Test Windows fallback when truststore and certifi are unavailable.
    weather_download._build_ssl_context.cache_clear()
    real_import = __import__

    def _no_truststore_no_certifi(name: str, *args: Any, **kwargs: Any) -> Any:
        if name in {"truststore", "certifi"}:
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    with mock.patch("builtins.__import__", side_effect=_no_truststore_no_certifi):
        fallback_ctx = weather_download._build_ssl_context()
        assert fallback_ctx.verify_mode == ssl.CERT_REQUIRED
        assert fallback_ctx.check_hostname is True
    weather_download._build_ssl_context.cache_clear()

    # Retry loop handles URLError and TimeoutError, and fast-fails on 404.
    class _FakeResp:
        def __init__(self, payload: bytes) -> None:
            self._buf = io.BytesIO(payload)

        def read(self, n: int = -1) -> bytes:
            return self._buf.read(n)

        def __enter__(self) -> _FakeResp:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

    attempts: list[int] = []

    def _flaky_urlopen(req: Any, timeout: int = 10, context: Any = None) -> _FakeResp:
        del req, timeout, context
        attempts.append(1)
        if len(attempts) == 1:
            raise URLError("transient dns failure")
        if len(attempts) == 2:
            raise TimeoutError("transient read timeout")
        return _FakeResp(b'{"ok": true}')

    with (
        mock.patch.object(weather_download, "urlopen", side_effect=_flaky_urlopen),
        mock.patch.object(weather_download.time, "sleep"),
    ):
        assert weather_download._request_bytes("https://example.test/ping", timeout=5) == b'{"ok": true}'
    assert len(attempts) == 3

    dl_attempts: list[int] = []

    def _flaky_dl_urlopen(req: Any, timeout: int = 10, context: Any = None) -> _FakeResp:
        del req, timeout, context
        dl_attempts.append(1)
        if len(dl_attempts) == 1:
            raise TimeoutError("chunk timeout")
        return _FakeResp(b"EPW_BYTES")

    dest_file = tmp_path / "retry_dl.epw"
    with (
        mock.patch.object(weather_download, "urlopen", side_effect=_flaky_dl_urlopen),
        mock.patch.object(weather_download.time, "sleep"),
    ):
        weather_download._download_url("https://example.test/file.epw", dest_file)
    assert dest_file.read_bytes() == b"EPW_BYTES"
    assert len(dl_attempts) == 2

    def _http_404(req: Any, timeout: int = 10, context: Any = None) -> Any:
        del timeout, context
        raise HTTPError(req.full_url, 404, "Not Found", {}, None)

    with (
        mock.patch.object(weather_download, "urlopen", side_effect=_http_404),
        mock.patch.object(weather_download.time, "sleep") as sleep_mock,
    ):
        with pytest.raises(HTTPError):
            weather_download._request_bytes("https://example.test/missing", timeout=5)
        sleep_mock.assert_not_called()

    # Build a sample weather ZIP from Chicago EPW/DDY/STAT with realistic OneBuilding name.
    epw_src, ddy_src, stat_src = _chicago_weather_paths()
    epw_bytes = epw_src.read_bytes()
    expected_sha256 = hashlib.sha256(epw_bytes).hexdigest()
    sample_stem = "CHN_BJ_Beijing-Capital.Intl.AP.545110_TMYx.2004-2018"
    sample_zip_bytes = io.BytesIO()
    with zipfile.ZipFile(sample_zip_bytes, "w") as zf:
        zf.writestr(f"{sample_stem}.epw", epw_bytes)
        zf.writestr(f"{sample_stem}.ddy", ddy_src.read_bytes())
        if stat_src is not None:
            zf.writestr(f"{sample_stem}.stat", stat_src.read_bytes())
    zip_payload = sample_zip_bytes.getvalue()

    g_path = (tmp_path / "wx_remote_g").resolve()
    gr = g_path.as_posix()
    create_garden(name="wx_remote_g", root_dir=gr)
    raw_mcp = _make_raw_mcp()

    sample_items = [
        {
            "id": "id_bj_2004",
            "name": f"{sample_stem}.zip",
            "format": "zip",
            "station_name": sample_stem,
            "wmo_station": "545110",
            "region": "WMO_Region_2_Asia",
            "country": "CHN_China",
            "admin_region": "BJ_Beijing",
        },
        {
            "id": "id_bj_2007",
            "name": "CHN_BJ_Beijing-Capital.Intl.AP.545110_TMYx.2007-2021.zip",
            "format": "zip",
            "station_name": "CHN_BJ_Beijing-Capital.Intl.AP.545110_TMYx.2007-2021",
            "wmo_station": "545110",
            "region": "WMO_Region_2_Asia",
            "country": "CHN_China",
            "admin_region": "BJ_Beijing",
        },
    ]

    def _fake_request_bytes(url: str, *, timeout: int) -> bytes:
        del timeout
        if "/v1/health" in url:
            return json.dumps(
                {"status": "ok", "api_version": "v1", "data_source": "aliyun-oss", "prefix": "epwfile"}
            ).encode("utf-8")
        if "/v1/files?" in url:
            if "Beijing" in url or "545110" in url or "2004-2018" in url:
                return json.dumps({"items": sample_items, "page": 1, "pages": 1}).encode("utf-8")
            return json.dumps({"items": [], "page": 1, "pages": 1}).encode("utf-8")
        if "/v1/files/id_bj_2004" in url:
            return json.dumps(
                {
                    **sample_items[0],
                    "object_key": f"epwfile/WMO_Region_2_Asia/CHN_China/BJ_Beijing/{sample_stem}.zip",
                }
            ).encode("utf-8")
        raise AssertionError(f"Unexpected URL: {url}")

    def _fake_download_url(url: str, destination: Path) -> None:
        del url
        destination.write_bytes(zip_payload)

    with (
        mock.patch.object(weather_download, "_request_bytes", side_effect=_fake_request_bytes),
        mock.patch.object(weather_download, "_download_url", side_effect=_fake_download_url),
    ):
        # 1. action="search_remote" and action="search", scope="remote"
        remote_a = asyncio.run(
            _call(
                raw_mcp,
                "LB_Manage_Weather",
                {"garden_root": gr, "action": "search_remote", "query": "Beijing"},
            )
        )
        assert remote_a["report"]["status"] == "ok"
        assert len(remote_a["matches"]) == 2
        first_cand = remote_a["matches"][0]
        assert set(first_cand) >= {
            "file_id",
            "file_name",
            "station",
            "region",
            "country",
            "admin_region",
            "object_key",
            "format",
        }
        assert first_cand["file_id"] == "id_bj_2004"

        remote_b = asyncio.run(
            _call(
                raw_mcp,
                "LB_Manage_Weather",
                {"garden_root": gr, "action": "search", "scope": "remote", "query": "Beijing"},
            )
        )
        assert remote_b["matches"] == remote_a["matches"]

        # Backwards-compatible default action="search" (scope="local") still works cleanly.
        local_empty = asyncio.run(
            _call(raw_mcp, "LB_Manage_Weather", {"garden_root": gr, "action": "search"})
        )
        assert local_empty["matches"] == []
        assert local_empty["report"]["status"] == "ok"

        # 2. Ambiguous query on action="download" returns structured MutationResultModel response.
        ambig = asyncio.run(
            _call(
                raw_mcp,
                "LB_Manage_Weather",
                {"garden_root": gr, "action": "download", "query": "Beijing"},
            )
        )
        MutationResultModel.model_validate(ambig)
        assert ambig["status"] == "ambiguous"
        assert len(ambig["matches"]) == 2
        assert ambig["summary_view"]["status"] == "ambiguous"
        assert ambig["summary_view"]["blocker"] == "ambiguous_weather_query"
        assert ambig["report"]["status"] == "blocked"

        # 3. Station not found blocker is distinct from network_error.
        not_found = asyncio.run(
            _call(
                raw_mcp,
                "LB_Manage_Weather",
                {"garden_root": gr, "action": "download", "query": "Atlantis_Missing"},
            )
        )
        assert not_found["report"]["status"] == "blocked"
        assert not_found["summary_view"]["blocker"] == "station_not_found"

        # 4. Exact download by file_id succeeds and records station, dataset_version, source, epw_sha256.
        dl_res = asyncio.run(
            _call(
                raw_mcp,
                "LB_Manage_Weather",
                {"garden_root": gr, "action": "download", "file_id": "id_bj_2004"},
            )
        )
        assert dl_res["report"]["status"] == "ok"
        w_target = dl_res["target"]
        assert w_target["epw_sha256"] == expected_sha256
        assert w_target["dataset_version"] == "TMYx.2004-2018"
        assert w_target["station"]
        assert w_target["source"] == "epwfile"
        assert dl_res["summary_view"]["epw_sha256"] == expected_sha256

    # Local search still finds the newly downloaded weather target.
    local_found = asyncio.run(
        _call(raw_mcp, "LB_Manage_Weather", {"garden_root": gr, "action": "search", "query": "Beijing"})
    )
    assert len(local_found["matches"]) == 1
    assert local_found["matches"][0]["epw_sha256"] == expected_sha256

    # 5. OSS fallback: ambiguous response, capped unscoped scan, and network_error distinction.
    oss_calls: list[str] = []

    def _fake_oss_xml_factory(*, truncated: bool) -> Any:
        def _fake_oss_xml(url: str, *, timeout: int) -> bytes:
            del timeout
            if "epwapi" in url:
                raise URLError("epwapi unreachable")
            oss_calls.append(url)
            token = (
                f"<NextContinuationToken>tok_{len(oss_calls)}</NextContinuationToken>"
                if truncated
                else ""
            )
            return (
                '<?xml version="1.0" encoding="UTF-8"?>'
                "<ListBucketResult>"
                f"<IsTruncated>{'true' if truncated else 'false'}</IsTruncated>"
                f"{token}"
                "<Contents><Key>epwfile/WMO_Region_2_Asia/CHN_China/BJ_Beijing/Beijing_A_TMYx.2004-2018.zip</Key><Size>100</Size></Contents>"
                "<Contents><Key>epwfile/WMO_Region_2_Asia/CHN_China/BJ_Beijing/Beijing_B_TMYx.2007-2021.zip</Key><Size>100</Size></Contents>"
                "</ListBucketResult>"
            ).encode()

        return _fake_oss_xml

    with mock.patch.object(
        weather_download, "_request_bytes", side_effect=_fake_oss_xml_factory(truncated=False)
    ):
        oss_ambig = weather_download.download_weather(garden_root=gr, query="Beijing")
        assert oss_ambig["status"] == "ambiguous"
        assert oss_ambig["summary_view"]["blocker"] == "ambiguous_weather_query"
        assert len(oss_ambig["matches"]) == 2

    with mock.patch.object(
        weather_download, "_request_bytes", side_effect=_fake_oss_xml_factory(truncated=True)
    ):
        oss_calls.clear()
        oss_capped = weather_download.download_weather(garden_root=gr, query="NoMatchStation")
        assert oss_capped["summary_view"]["blocker"] == "station_not_found"
        assert len(oss_calls) == weather_download._MAX_OSS_PAGES_UNSCOPED

    with mock.patch.object(
        weather_download, "_request_bytes", side_effect=URLError("offline")
    ):
        net_blocked = weather_download.download_weather(garden_root=gr, query="Beijing")
        assert net_blocked["report"]["status"] == "blocked"
        assert net_blocked["summary_view"]["blocker"] == "network_error"

    # 6. config.import_local_weather_folder records station, dataset_version, source, epw_sha256.
    local_src = tmp_path / "local_epw_src"
    local_src.mkdir()
    shutil.copy2(epw_src, local_src / f"{sample_stem}.epw")
    shutil.copy2(ddy_src, local_src / f"{sample_stem}.ddy")
    imported = weather_config.import_local_weather_folder(
        garden_root=gr, source_path=str(local_src), identifier="local_bj_test"
    )
    imp_target = imported["target"]
    assert imp_target["epw_sha256"] == expected_sha256
    assert imp_target["dataset_version"] == "TMYx.2004-2018"
    assert imp_target["source"] == "local_weather"
    assert imp_target["station"] == "Chicago Ohare Intl Ap"


# ===========================================================================
# 3. P0-3: EnergyPlus run_id directory isolation & stage statuses
# ===========================================================================


def test_expand_objects_errors_block_clean_simulation_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    GardenManifest.new("ExpandObjects diagnostics").write(tmp_path)
    (tmp_path / "eplusout.err").write_text("EnergyPlus Completed Successfully-- 0 Severe Errors\n", encoding="utf-8")
    (tmp_path / "expandedidf.err").write_text(
        "ExpandObjects: SEVERE: Too many fields for Chiller:Electric:EIR\n", encoding="utf-8"
    )
    (tmp_path / "eui.json").write_text('{"eui":42.0}', encoding="utf-8")
    record = {
        "status": "completed",
        "stage_statuses": {"energyplus": {"status": "completed"}},
        "outputs": [
            {"name": name, "path": path, "exists": True}
            for name, path in (("err", "eplusout.err"), ("eui", "eui.json"), ("sql", "eplusout.sql"))
        ],
    }
    monkeypatch.setattr(annual, "_run_record_by_id", lambda *_: record)
    errors = asyncio.run(_call(_make_raw_mcp(), "EP_Read_Errors", {
        "garden_root": str(tmp_path), "run_id": "run_with_preprocessing_errors",
    }))
    assert errors["report"]["status"] == "blocked"
    assert errors["summary_view"]["severe_count"] == 0
    assert errors["summary_view"]["expand_objects"]["severe_count"] == 1
    assert errors["summary_view"]["expand_objects"]["path"] == "expandedidf.err"

    evidence = annual._energy_run_result_evidence(
        garden_root=tmp_path, run_id="run_with_preprocessing_errors", record=record,
    )
    assert evidence["energyplus_succeeded"] is True
    assert evidence["final_answer_ready"] is False
    assert "ExpandObjects" in evidence["final_answer_guidance"]


def test_energyplus_run_id_isolation_and_stage_statuses(tmp_path: Path) -> None:
    """Verify run_id isolates run directories on the same model and stage_statuses distinguishes ReportingMeasures failure."""
    g_path, model_target, weather_target = _setup_box_garden(tmp_path, "ep_iso_g")
    gr = g_path.as_posix()
    res_dir = _REPO_ROOT / "resources" / "honeybee-energy" / "tests" / "result"
    sql_fixture = res_dir / "single_family_home_eplusout.sql"
    err_fixture = res_dir / "eplusout_normal.err"

    # Run 1 succeeds on Office Model.
    def _cli_run1_success(**kwargs: Any) -> tuple[int, int]:
        run_dir = Path(kwargs["run_dir"])
        os_dir = run_dir / "openstudio"
        sim_dir = os_dir / "run"
        reports_dir = os_dir / "reports"
        sim_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)
        (os_dir / "in.osm").write_text("OS:Version,3.10.0;\n", encoding="utf-8")
        (sim_dir / "in.idf").write_text("Version,24.2;\n", encoding="utf-8")
        shutil.copy2(sql_fixture, sim_dir / "eplusout.sql")
        shutil.copy2(err_fixture, sim_dir / "eplusout.err")
        (os_dir / "eui.json").write_text(
            json.dumps({"eui": 111.5, "total_floor_area": 30.0, "end_uses": {"heating": 50.0, "cooling": 61.5}}),
            encoding="utf-8",
        )
        (reports_dir / "openstudio_results_report.html").write_text("<html>ok</html>", encoding="utf-8")
        (os_dir / "out.osw").write_text(
            json.dumps(
                {
                    "completed_status": "Success",
                    "steps": [
                        {
                            "measure_dir_name": "from_honeybee_model",
                            "result": {"measure_type": "ModelMeasure", "step_result": "Success", "step_errors": []},
                        },
                        {
                            "measure_dir_name": "openstudio_results",
                            "result": {"measure_type": "ReportingMeasure", "step_result": "Success", "step_errors": []},
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        return 0, 0

    with mock.patch.object(annual, "_run_honeybee_energy_cli", side_effect=_cli_run1_success):
        run1 = annual.run_energy(
            garden_root=gr,
            model_target=model_target,
            weather_target=weather_target,
            run_id="run_one_ok",
            validate_weather=False,
        )
    assert run1["status"] == "completed"
    run1_target = run1["run_target"]
    assert run1["summary_view"]["run_folder"] == "runs/energy/run_one_ok"
    assert run1["stage_statuses"]["osm_load"]["status"] == "completed"
    assert run1["stage_statuses"]["forward_translator"]["status"] == "completed"
    assert run1["stage_statuses"]["energyplus"]["status"] == "completed"
    assert run1["stage_statuses"]["reporting_measures"]["status"] == "completed"

    # Run 2 fails early (at ForwardTranslator) on the EXACT SAME model; Run 1 outputs must survive!
    def _cli_run2_fail(**kwargs: Any) -> tuple[int, int]:
        run_dir = Path(kwargs["run_dir"])
        os_dir = run_dir / "openstudio"
        os_dir.mkdir(parents=True, exist_ok=True)
        (os_dir / "in.osm").write_text("OS:Version,3.10.0;\n", encoding="utf-8")
        (os_dir / "out.osw").write_text(
            json.dumps(
                {
                    "completed_status": "Fail",
                    "steps": [
                        {
                            "measure_dir_name": "from_honeybee_model",
                            "result": {"measure_type": "ModelMeasure", "step_result": "Success", "step_errors": []},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return 1, 1

    with mock.patch.object(annual, "_run_honeybee_energy_cli", side_effect=_cli_run2_fail):
        run2 = annual.run_energy(
            garden_root=gr,
            model_target=model_target,
            weather_target=weather_target,
            run_id="run_two_fail",
            validate_weather=False,
        )
    assert run2["status"] == "failed"
    assert run2["summary_view"]["run_folder"] == "runs/energy/run_two_fail"
    assert run2["stage_statuses"]["osm_load"]["status"] == "completed"
    assert run2["stage_statuses"]["forward_translator"]["status"] == "failed"
    assert run2["stage_statuses"]["energyplus"]["status"] == "not_started"

    # Run 1's SQL, ERR, and EUI remain intact and readable via Run 1's run_target!
    assert (g_path / "runs/energy/run_one_ok/openstudio/run/eplusout.sql").is_file()
    assert (g_path / "runs/energy/run_one_ok/openstudio/run/eplusout.err").is_file()
    assert (g_path / "runs/energy/run_one_ok/openstudio/eui.json").is_file()

    eui1 = annual.read_energy_eui(garden_root=gr, run_target=run1_target)
    assert eui1["eui"]["eui"] == 111.5
    err1 = annual.read_energy_errors(garden_root=gr, run_target=run1_target)
    assert err1["fatal_count"] == 0
    assert err1["path"] == "runs/energy/run_one_ok/openstudio/run/eplusout.err"

    raw_mcp = _make_raw_mcp()
    sum1 = asyncio.run(
        _call(raw_mcp, "EP_Summarize_Results", {"garden_root": gr, "run_target": run1_target, "summary_kind": "energy_use"})
    )
    assert sum1["report"]["status"] == "ok"

    # Run 3: EnergyPlus succeeds cleanly, but OpenStudio ReportingMeasure fails!
    def _cli_run3_reporting_fail(**kwargs: Any) -> tuple[int, int]:
        run_dir = Path(kwargs["run_dir"])
        os_dir = run_dir / "openstudio"
        sim_dir = os_dir / "run"
        sim_dir.mkdir(parents=True, exist_ok=True)
        (os_dir / "in.osm").write_text("OS:Version,3.10.0;\n", encoding="utf-8")
        (sim_dir / "in.idf").write_text("Version,24.2;\n", encoding="utf-8")
        shutil.copy2(sql_fixture, sim_dir / "eplusout.sql")
        shutil.copy2(err_fixture, sim_dir / "eplusout.err")
        (os_dir / "eui.json").write_text(
            json.dumps({"eui": 99.0, "total_floor_area": 30.0}),
            encoding="utf-8",
        )
        (os_dir / "out.osw").write_text(
            json.dumps(
                {
                    "completed_status": "Fail",
                    "steps": [
                        {
                            "measure_dir_name": "from_honeybee_model",
                            "result": {"measure_type": "ModelMeasure", "step_result": "Success", "step_errors": []},
                        },
                        {
                            "measure_dir_name": "openstudio_results",
                            "result": {
                                "measure_type": "ReportingMeasure",
                                "step_result": "Fail",
                                "step_errors": ["Ruby NoMethodError in openstudio_results"],
                            },
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        return 1, 0

    with mock.patch.object(annual, "_run_honeybee_energy_cli", side_effect=_cli_run3_reporting_fail):
        run3 = annual.run_energy(
            garden_root=gr,
            model_target=model_target,
            weather_target=weather_target,
            run_id="run_three_rep_fail",
            validate_weather=False,
        )
    assert run3["status"] == "failed"
    st3 = run3["stage_statuses"]
    assert st3["osm_load"]["status"] == "completed"
    assert st3["forward_translator"]["status"] == "completed"
    assert st3["energyplus"]["status"] == "completed"
    assert st3["reporting_measures"]["status"] == "failed"
    assert st3["reporting_measures"]["failed_measures"] == ["openstudio_results"]

    polled3 = asyncio.run(_call(raw_mcp, "GD_Poll_Run", {"garden_root": gr, "run_target": run3["run_target"]}))
    assert polled3["summary_view"]["run"]["stage_statuses"]["energyplus"]["status"] == "completed"
    assert polled3["summary_view"]["run"]["stage_statuses"]["reporting_measures"]["status"] == "failed"
    eui3 = annual.read_energy_eui(garden_root=gr, run_target=run3["run_target"])
    assert eui3["eui"]["eui"] == 99.0

    # Legacy model-name folder record still resolves cleanly for backwards compatibility.
    legacy_dir = g_path / "runs" / "energy" / "Legacy_Office_Model"
    (legacy_dir / "openstudio" / "run").mkdir(parents=True, exist_ok=True)
    shutil.copy2(err_fixture, legacy_dir / "openstudio" / "run" / "eplusout.err")
    (legacy_dir / "openstudio" / "eui.json").write_text(json.dumps({"eui": 77.7}), encoding="utf-8")
    manifest = GardenManifest.read(g_path)
    legacy_target = annual._run_target(manifest.garden_id, "legacy_run_1")
    annual._upsert_record(
        g_path,
        {
            "run_id": "legacy_run_1",
            "target": legacy_target,
            "recipe": annual.ENERGY_RUN_RECIPE,
            "status": "completed",
            "model_display_name": "Legacy Office Model",
            "run_folder": "runs/energy/Legacy_Office_Model",
            "outputs": annual._recipe_outputs(garden_root_path=g_path, run_dir=legacy_dir, warnings=[]),
        },
    )
    legacy_eui = annual.read_energy_eui(garden_root=gr, run_target=legacy_target)
    assert legacy_eui["eui"]["eui"] == 77.7
    legacy_err = annual.read_energy_errors(garden_root=gr, run_target=legacy_target)
    assert legacy_err["path"] == "runs/energy/Legacy_Office_Model/openstudio/run/eplusout.err"


# ===========================================================================
# 4. P0-5 / Wave 2: EP_Start_Simulation units & EP_Create_Simulation_Parameter schema
# ===========================================================================


def test_units_aliases_and_slim_sim_par_schema(tmp_path: Path) -> None:
    """Verify EP_Start_Simulation friendly units and slimmed EP_Create_Simulation_Parameter schema."""
    raw_mcp = _make_raw_mcp()
    tools = {t.name: t for t in asyncio.run(raw_mcp.list_tools())}
    sim_par_tool = tools["EP_Create_Simulation_Parameter"]
    raw_schema_bytes = len(json.dumps(sim_par_tool.parameters).encode("utf-8"))
    assert raw_schema_bytes < 4800, f"Expected slimmed EP_Create_Simulation_Parameter schema < 4800B, got {raw_schema_bytes}B"

    cm_mcp = create_mcp()

    async def _get_cm_full() -> int:
        async with Client(cm_mcp) as client:
            r = await client.call_tool(
                "get_schema",
                {"tools": ["EP_Create_Simulation_Parameter"], "detail": "full"},
            )
            txt = r.data if isinstance(r.data, str) else r.content[0].text
            return len(txt.encode("utf-8"))

    cm_full_bytes = asyncio.run(_get_cm_full())
    assert cm_full_bytes < 13000, f"Expected slimmed Code Mode full schema < 13000B, got {cm_full_bytes}B"

    g_path, model_target, weather_target = _setup_box_garden(tmp_path, "units_g")
    gr = g_path.as_posix()

    # Check EP_Create_Simulation_Parameter preserves all existing params & case-insensitive normalizers.
    sp_res = asyncio.run(
        _call(
            raw_mcp,
            "EP_Create_Simulation_Parameter",
            {
                "garden_root": gr,
                "identifier": "sp_slim_check",
                "terrain_type": "urban",
                "reporting_frequency": "monthly",
                "presets": ["zone_energy_use"],
                "run_period": {"start_month": 1, "start_day": 1, "end_month": 1, "end_day": 3},
                "design_days": ["99.6/0.4"],
                "weather_target": weather_target,
            },
        )
    )
    assert sp_res["report"]["status"] == "ok"
    assert sp_res["summary_view"]["terrain_type"] == "Urban"

    # Reject unknown output_request keys via _schemas.py validation.
    with pytest.raises(ToolError, match="unsupported field"):
        asyncio.run(
            _call(
                raw_mcp,
                "EP_Create_Simulation_Parameter",
                {
                    "garden_root": gr,
                    "output_request": {"presets": ["zone_energy_use"], "bogus_key": 1},
                },
            )
        )

    # Check EP_Start_Simulation friendly units aliases.
    unit_cases = [
        ("Meters", "si"),
        ("meters", "si"),
        ("metric", "si"),
        ("Feet", "ip"),
        ("feet", "ip"),
        ("imperial", "ip"),
        ("si", "si"),
        ("IP", "ip"),
    ]
    with mock.patch(
        "garden.run_energy.annual.submit_worker_process",
        return_value=SimpleNamespace(pid=51515),
    ):
        for idx, (raw_unit, expected_canonical) in enumerate(unit_cases):
            run_id = f"unit_case_{idx}"
            res = asyncio.run(
                _call(
                    raw_mcp,
                    "EP_Start_Simulation",
                    {
                        "garden_root": gr,
                        "model_target": model_target,
                        "weather_target": weather_target,
                        "simulation_parameter_target": sp_res["target"],
                        "units": raw_unit,
                        "run_id": run_id,
                        "validate_weather": False,
                    },
                )
            )
            assert res["status"] == "running"
            stored = annual._run_record_by_id(g_path, run_id)
            assert stored["units"] == expected_canonical

    with pytest.raises(ToolError, match="Unsupported units"):
        asyncio.run(
            _call(
                raw_mcp,
                "EP_Start_Simulation",
                {
                    "garden_root": gr,
                    "model_target": model_target,
                    "weather_target": weather_target,
                    "units": "kelvin",
                },
            )
        )
