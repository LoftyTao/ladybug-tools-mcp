"""Simulation subprocess runner that backports OpenStudio OSM files when needed.

When Python ``openstudio`` (bundled with ``honeybee-openstudio``) is newer than
the locally installed OpenStudio CLI / C# bindings (used by external
``Ironbug.Console.exe`` and ``openstudio.exe``), temporary OSM files are
automatically backported in-place via ``openstudiobackporter`` immediately
before invoking external executables.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


def _parse_version_tuple(version_str: str) -> tuple[int, int, int] | None:
    """Parse a semantic version string such as '3.11.0+abc' into a 3-tuple."""
    core = str(version_str or "").strip().split("+", 1)[0].split("-", 1)[0]
    parts = core.split(".")
    if len(parts) < 2:
        return None
    try:
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2]) if len(parts) > 2 else 0
    except ValueError:
        return None
    return (major, minor, patch)


def _resolve_backport_target() -> str | None:
    """Return target X.Y.0 OpenStudio version string if desktop OS is older than Python SDK."""
    import openstudio
    from honeybee_energy.config import folders as hbe_folders
    from openstudiobackporter.backporter import KNOWN_TO_VERSIONS

    py_ver = _parse_version_tuple(openstudio.openStudioVersion())
    cli_ver = getattr(hbe_folders, "openstudio_version", None)
    if py_ver is None or not cli_ver or len(cli_ver) < 2:
        return None

    cli_tuple = (int(cli_ver[0]), int(cli_ver[1]), int(cli_ver[2]) if len(cli_ver) > 2 else 0)
    if py_ver <= cli_tuple:
        return None

    candidate = f"{cli_tuple[0]}.{cli_tuple[1]}.0"
    return candidate if candidate in KNOWN_TO_VERSIONS else None


def _backport_osm_inplace(osm_path: Path, target_version: str) -> bool:
    """Backport *osm_path* in place if its file version exceeds *target_version*."""
    if not osm_path.is_file():
        return False

    import openstudio
    from openstudiobackporter.backporter import Backporter

    ver = openstudio.IdfFile.loadVersionOnly(osm_path)
    if not ver.is_initialized():
        return False
    if ver.get() <= openstudio.VersionString(target_version):
        return False

    backporter = Backporter(to_version=target_version, save_intermediate=False)
    with redirect_stdout(sys.stderr):
        idf_file = backporter.backport_file(osm_path)
    idf_file.save(osm_path, True)
    return True


def backport_osm_if_needed(osm_path: Path | str) -> dict[str, Any]:
    """Backport *osm_path* in place when Python OpenStudio exceeds CLI version."""
    path = Path(osm_path)
    if not path.is_file() or path.suffix.lower() != ".osm":
        return {"backported": False, "target_version": None, "warning": None}

    try:
        target = _resolve_backport_target()
    except Exception as exc:
        return {
            "backported": False,
            "target_version": None,
            "warning": f"Skipped OSM backport target resolution: {exc}",
        }

    if target is None:
        return {"backported": False, "target_version": None, "warning": None}

    try:
        changed = _backport_osm_inplace(path, target)
    except Exception as exc:
        return {
            "backported": False,
            "target_version": target,
            "warning": f"Failed to backport OSM {path.name} to OpenStudio {target}: {exc}",
        }

    return {"backported": changed, "target_version": target, "warning": None}


def _extract_tokens(args: Any) -> list[str]:
    if isinstance(args, (list, tuple)):
        return [str(part) for part in args]
    if isinstance(args, str):
        try:
            return shlex.split(args, posix=False)
        except ValueError:
            return args.split()
    return []


def _is_ironbug_osm_invocation(tokens: list[str], ironbug_exe: str | None) -> bool:
    if len(tokens) < 2:
        return False
    exe_token = tokens[0].strip().strip('"').strip("'")
    osm_token = tokens[1].strip().strip('"').strip("'")
    if not osm_token.lower().endswith(".osm"):
        return False
    if "ironbug" in Path(exe_token).name.lower():
        return True
    if ironbug_exe:
        try:
            return Path(exe_token).resolve() == Path(ironbug_exe).resolve()
        except OSError:
            return exe_token.lower() == str(ironbug_exe).lower()
    return False


class _WriterSubprocessProxy:
    """Proxy for ``honeybee_openstudio.writer.subprocess`` that backports OSM inputs."""

    def __init__(self, target_version: str, ironbug_exe: str | None) -> None:
        self._target_version = target_version
        self._ironbug_exe = ironbug_exe

    def _maybe_backport_args(self, args: Any) -> None:
        tokens = _extract_tokens(args)
        if _is_ironbug_osm_invocation(tokens, self._ironbug_exe):
            osm_arg = tokens[1].strip().strip('"').strip("'")
            _backport_osm_inplace(Path(osm_arg), self._target_version)

    def Popen(self, args: Any, *pargs: Any, **kwargs: Any) -> subprocess.Popen[Any]:
        self._maybe_backport_args(args)
        return subprocess.Popen(args, *pargs, **kwargs)

    def run(
        self, args: Any, *pargs: Any, **kwargs: Any
    ) -> subprocess.CompletedProcess[Any]:
        self._maybe_backport_args(args)
        return subprocess.run(args, *pargs, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(subprocess, name)


def _install_backport_hooks(target_version: str) -> None:
    """Patch Ironbug and OpenStudio CLI callers in this simulation subprocess."""
    from honeybee_energy import run as hb_run
    from honeybee_energy.cli import simulate as hb_simulate
    from honeybee_energy.config import folders as hbe_folders
    from honeybee_openstudio import writer as hb_writer

    hb_writer.subprocess = _WriterSubprocessProxy(
        target_version=target_version,
        ironbug_exe=getattr(hbe_folders, "ironbug_exe", None),
    )

    orig_run_osw = hb_run.run_osw

    def wrapped_run_osw(osw_json: str, *pargs: Any, **kwargs: Any) -> Any:
        try:
            osw_path = Path(osw_json)
            if osw_path.is_file():
                osw_data = json.loads(osw_path.read_text(encoding="utf-8"))
                seed_file = osw_data.get("seed_file")
                if isinstance(seed_file, str) and seed_file.strip():
                    seed_path = Path(seed_file.strip())
                    if not seed_path.is_absolute():
                        seed_path = osw_path.parent / seed_path
                    if seed_path.suffix.lower() == ".osm":
                        _backport_osm_inplace(seed_path, target_version)
        except Exception:
            # Fall back to upstream run_osw error reporting if OSW inspection fails.
            pass
        return orig_run_osw(osw_json, *pargs, **kwargs)

    hb_run.run_osw = wrapped_run_osw
    hb_simulate.run_osw = wrapped_run_osw


def _run_with_measures_or_mode(
    cli_args: list[str],
    *,
    measures_spec_json: str | None,
    measures_only: bool,
) -> int:
    """Execute EnergyPlus/OpenStudio simulation when ordered measures or measures_only are used."""
    import argparse

    from honeybee.config import folders as hb_folders
    from honeybee.model import Model
    from honeybee_energy import run as hb_run
    from honeybee_energy.measure import Measure
    from honeybee_energy.result.err import Err
    from honeybee_energy.simulation.parameter import SimulationParameter
    from ladybug.epw import EPW
    from ladybug.futil import preparedir
    from ladybug.stat import STAT

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("model_file")
    parser.add_argument("epw_file")
    parser.add_argument("--sim-par-json", "-sp", default=None)
    parser.add_argument("--measures", "-m", default=None)
    parser.add_argument("--additional-string", "-as", default=None)
    parser.add_argument("--additional-idf", "-ai", default=None)
    parser.add_argument("--report-units", "-r", default="none")
    parser.add_argument("--viz-variable", "-v", action="append", default=[])
    parser.add_argument("--folder", "-f", default=None)
    parser.add_argument("--enforce-rooms", action="store_true", default=True)
    parser.add_argument("--skip-no-rooms", "-sr", action="store_true", default=False)
    parser.add_argument("--log-file", "-log", default="-")
    parsed, unknown = parser.parse_known_args(cli_args)
    if unknown:
        raise ValueError(f"Unsupported simulate_runner arguments: {' '.join(unknown)}")

    model_file = str(Path(parsed.model_file).resolve())
    epw_file = str(Path(parsed.epw_file).resolve())
    epw_path = Path(epw_file)
    ddy_file = epw_path.with_suffix(".ddy")
    stat_file = epw_path.with_suffix(".stat")

    first_char = Path(model_file).read_text(encoding="utf-8", errors="replace")[:1]
    if first_char == "{":
        file_type = "hbjson"
    else:
        lines = Path(model_file).read_text(encoding="utf-8", errors="replace").splitlines()
        second_line = lines[1] if len(lines) > 1 else ""
        file_type = "osm" if "OS:Version," in second_line else "idf"

    folder = parsed.folder
    if not folder:
        proj_name = Path(model_file).stem.lower()
        base = Path(hb_folders.default_simulation_folder) / proj_name
        folder = str(base / ("energyplus/run" if file_type == "idf" else "openstudio"))
    elif file_type == "idf":
        folder = str(Path(folder) / "run")
    preparedir(folder, remove_content=False)

    sim_par: SimulationParameter | None = None
    if file_type == "hbjson":
        if not parsed.sim_par_json or not Path(parsed.sim_par_json).is_file():
            sim_par = SimulationParameter()
            sim_par.output.add_zone_energy_use()
            sim_par.output.add_hvac_energy_use()
            sim_par.output.add_electricity_generation()
            sim_par.output.reporting_frequency = "Monthly"
        else:
            sim_par = SimulationParameter.from_dict(
                json.loads(Path(parsed.sim_par_json).read_text(encoding="utf-8"))
            )
        if not sim_par.sizing_parameter.design_days:
            if ddy_file.is_file():
                try:
                    sim_par.sizing_parameter.add_from_ddy_996_004(str(ddy_file))
                except AssertionError:
                    epw_obj = EPW(epw_file)
                    sim_par.sizing_parameter.design_days = [
                        epw_obj.approximate_design_day("WinterDesignDay"),
                        epw_obj.approximate_design_day("SummerDesignDay"),
                    ]
            else:
                epw_obj = EPW(epw_file)
                sim_par.sizing_parameter.design_days = [
                    epw_obj.approximate_design_day("WinterDesignDay"),
                    epw_obj.approximate_design_day("SummerDesignDay"),
                ]
        if sim_par.sizing_parameter.climate_zone is None and stat_file.is_file():
            sim_par.sizing_parameter.climate_zone = STAT(str(stat_file)).ashrae_climate_zone

    base_osw: str | None = None
    if parsed.measures and Path(parsed.measures).is_dir():
        measures_dir = Path(parsed.measures)
        for child in sorted(measures_dir.iterdir()):
            if child.is_file() and child.suffix.lower() == ".osw":
                base_osw = str(child)
                osw_dict = json.loads(child.read_text(encoding="utf-8"))
                osw_dict["measure_paths"] = [str(measures_dir.resolve())]
                child.write_text(json.dumps(osw_dict), encoding="utf-8")
                break

    additional_measures: list[Measure] | None = None
    if measures_spec_json:
        raw_specs = json.loads(Path(measures_spec_json).read_text(encoding="utf-8"))
        additional_measures = []
        for spec in raw_specs:
            measure = Measure(str(spec["folder"]))
            args_by_id = {arg.identifier: arg for arg in measure.arguments}
            for key, value in dict(spec.get("arguments") or {}).items():
                if key not in args_by_id:
                    raise ValueError(f"Unknown measure argument {key!r} for {measure.identifier}.")
                args_by_id[key].value = value
            measure.validate(raise_exception=True)
            additional_measures.append(measure)

    strings_to_inject = parsed.additional_string or ""
    if parsed.additional_idf and Path(parsed.additional_idf).is_file():
        strings_to_inject = (
            strings_to_inject + "\n" + Path(parsed.additional_idf).read_text(encoding="utf-8")
        )

    if file_type not in ("hbjson", "osm"):
        if additional_measures or measures_only:
            raise ValueError("OpenStudio measures and measures_only require HBJSON or OSM input.")

    skip_no_rooms = bool(parsed.skip_no_rooms)
    model_input: Any = model_file
    if file_type == "hbjson":
        model_input = Model.from_hbjson(model_file)
        if skip_no_rooms and not model_input.rooms:
            return 0

    report_units = None if measures_only else parsed.report_units
    viz_vars = parsed.viz_variable or None
    osm, osw, idf = hb_run.to_openstudio_sim_folder(
        model_input,
        folder,
        epw_file=epw_file,
        sim_par=sim_par,
        enforce_rooms=True,
        additional_measures=additional_measures,
        base_osw=base_osw,
        strings_to_inject=strings_to_inject,
        report_units=report_units,
        viz_variables=viz_vars,
        print_progress=True,
    )

    gen_files: list[str | None] = []
    if osw is not None:
        gen_files.append(osw)
        out_osm, out_idf = hb_run.run_osw(osw, measures_only=measures_only, silent=True)
        if measures_only:
            if out_osm and Path(out_osm).is_file():
                gen_files.append(out_osm)
            out_osw = Path(folder) / "out.osw"
            if out_osw.is_file():
                from honeybee_energy.result.osw import OSW

                osw_res = OSW(str(out_osw))
                if osw_res.errors:
                    raise RuntimeError("Failed to run OpenStudio measures:\n" + "\n".join(osw_res.errors))
        else:
            if out_idf and Path(out_idf).is_file():
                gen_files.extend([out_osm, out_idf])
            else:
                hb_run._parse_os_cli_failure(folder)
            sql, zsz, rdd, html, err = hb_run.output_energyplus_files(str(Path(out_idf).parent))
            if err and Path(err).is_file():
                gen_files.extend([sql, zsz, rdd, html, err])
                err_obj = Err(err)
                for error in err_obj.fatal_errors:
                    raise RuntimeError(error)
            else:
                raise RuntimeError("Running EnergyPlus failed.")
    elif measures_only:
        if osm:
            gen_files.append(osm)
    elif idf is not None:
        gen_files.extend([osm, idf] if osm else [idf])
        sql, zsz, rdd, html, err = hb_run.run_idf(idf, epw_file)
        if err and Path(err).is_file():
            gen_files.extend([sql, zsz, rdd, html, err])
            err_obj = Err(err)
            for error in err_obj.fatal_errors:
                raise RuntimeError(error)
        else:
            raise RuntimeError("Running EnergyPlus failed.")

    payload = json.dumps(gen_files, indent=4)
    if parsed.log_file and parsed.log_file != "-":
        Path(parsed.log_file).write_text(payload, encoding="utf-8")
    else:
        print(payload)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run ``honeybee_energy.cli.simulate.simulate_model_cli`` with OSM backporting."""
    from honeybee_energy.cli.simulate import simulate_model_cli

    target = _resolve_backport_target()
    if target is not None:
        _install_backport_hooks(target)

    raw_args = list(sys.argv[1:] if argv is None else argv)
    measures_spec_json: str | None = None
    measures_only = False
    cli_args: list[str] = []
    index = 0
    while index < len(raw_args):
        token = raw_args[index]
        if token == "--measures-spec-json":
            if index + 1 >= len(raw_args):
                raise ValueError("--measures-spec-json requires a file path.")
            measures_spec_json = raw_args[index + 1]
            index += 2
            continue
        if token.startswith("--measures-spec-json="):
            measures_spec_json = token.split("=", 1)[1]
            index += 1
            continue
        if token == "--measures-only":
            measures_only = True
            index += 1
            continue
        cli_args.append(token)
        index += 1

    if measures_spec_json is not None or measures_only:
        return _run_with_measures_or_mode(
            cli_args,
            measures_spec_json=measures_spec_json,
            measures_only=measures_only,
        )

    simulate_model_cli.main(args=cli_args, standalone_mode=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
