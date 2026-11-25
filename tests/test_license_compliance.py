"""License, packaging metadata, and corresponding-source compliance tests."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_root_license_is_verbatim_agplv3() -> None:
    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    fairyfly_license = (REPO_ROOT / "src" / "fairyfly_next_therm" / "LICENSE").read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in license_text
    assert "Version 3, 19 November 2007" in license_text
    assert "13. Remote Network Interaction; Use with the GNU General Public License." in license_text
    assert license_text.replace("\r\n", "\n") == fairyfly_license.replace("\r\n", "\n")


def test_pyproject_toml_license_and_modules() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project["license"] == "AGPL-3.0-only"
    assert project["license-files"] == ["LICENSE", "licenses/THIRD_PARTY_NOTICES.md"]
    assert data["tool"]["setuptools"]["py-modules"] == ["ladybug_tools_mcp_cli"]
    assert "ladybug_tools_mcp_clients" not in data["tool"]["setuptools"]["py-modules"]


def test_manifest_in_compliance() -> None:
    manifest = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    lines = [line.strip() for line in manifest.splitlines() if line.strip()]
    expected_lines = [
        "include LICENSE",
        "recursive-include licenses *",
        "recursive-include rune_viewer *",
        "prune rune_viewer/target",
        "recursive-include vendor/rune *",
        "prune vendor/rune/.git",
        "prune vendor/rune/target",
        "recursive-include scripts/distribution/launcher *",
        "prune scripts/distribution/launcher/target",
        "prune docs",
        "prune tests",
        "exclude CONTEXT.md",
        "global-exclude AGENTS.md",
    ]
    for expected in expected_lines:
        assert expected in lines, f"Missing MANIFEST.in directive: {expected}"
    assert "src/web_view/vendor" not in manifest


def test_generated_licenses_and_notices() -> None:
    licenses_dir = REPO_ROOT / "licenses"
    notices = (licenses_dir / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    corresponding = (licenses_dir / "CORRESPONDING_SOURCE.md").read_text(encoding="utf-8")

    # Radiance verbatim section 3 attribution & Qt5/rvu exclusion
    rad_attr = (
        "This product includes Radiance software (http://radsite.lbl.gov/) "
        "developed by the Lawrence Berkeley National Laboratory (http://www.lbl.gov/)."
    )
    assert rad_attr in notices
    rad_10 = (licenses_dir / "components" / "radiance" / "LICENSE-Radiance-1.0.txt").read_text(encoding="utf-8")
    assert "The Radiance Software License, Version 1.0" in rad_10
    assert "http://radsite.lbl.gov/" in rad_10
    assert (licenses_dir / "components" / "radiance" / "LICENSE-rad5R4.txt").is_file()
    assert "rvu.exe" in notices and "Qt5" in notices

    # Evalglare 2.0 attribution & license
    assert "This product includes the evalglare software, developed at Fraunhofer ISE and EPFL by J. Wienold" in notices
    evalglare_lic = (licenses_dir / "components" / "evalglare" / "LICENSE.txt").read_text(encoding="utf-8")
    assert "Evalglare Software License, Version 2.0" in evalglare_lic
    assert "Fraunhofer ISE" in evalglare_lic and "EPFL" in evalglare_lic

    # EnergyPlus version 25.2.0 naming, DOE NOTICE, and no-endorsement clause
    assert "EnergyPlus version 25.2.0" in notices
    assert "No endorsement by the U.S. Department of Energy" in notices
    assert "EnergyPlus / E+" in notices
    ep_lic = (licenses_dir / "components" / "energyplus" / "LICENSE.txt").read_text(encoding="utf-8")
    assert "NOTICE: This Software was developed under funding from the U.S. Department of Energy" in ep_lic
    assert (licenses_dir / "components" / "energyplus" / "NOTICE.txt").is_file()

    # OpenStudio(R) 3.11.0 naming, pruning transparency, and NuGet C# bindings
    assert "OpenStudio(R)" in notices
    for pruned in ("Python/", "Perl/", "Radiance/", "include/", "Examples/", "openstudiolib.lib", "Ruby/"):
        assert pruned in notices
    assert "NREL.OpenStudio.win" in notices
    os_lic = (licenses_dir / "components" / "openstudio" / "LICENSE.md").read_text(encoding="utf-8")
    assert "OpenStudio(R)" in os_lic
    assert (licenses_dir / "components" / "openstudio" / "copyright.txt").is_file()
    assert (licenses_dir / "components" / "openstudio" / "PRUNING_NOTICE.txt").is_file()

    # No stale GPL-3.0-only claim for lbt-mcp itself
    assert "`lbt-mcp` | `1.2.3` | `GPL-3.0-only`" not in notices

    # Verbatim extension licenses
    assert (licenses_dir / "components" / "fairyfly_next_therm" / "LICENSE").read_bytes() == (
        REPO_ROOT / "src" / "fairyfly_next_therm" / "LICENSE"
    ).read_bytes()
    assert (licenses_dir / "components" / "honeybee_gbas" / "LICENSE").read_bytes() == (
        REPO_ROOT / "src" / "honeybee_gbas" / "LICENSE"
    ).read_bytes()
    assert (licenses_dir / "components" / "honeybee_gbas" / "LICENSE-ezdwg.txt").read_bytes() == (
        REPO_ROOT / "src" / "honeybee_gbas" / "dwg" / "LICENSE-ezdwg.txt"
    ).read_bytes()

    # HygroThermFEM / Fairyfly native verbatim copies
    htfem_src = REPO_ROOT / "src" / "pyhygrothermfem_fairyfly"
    htfem_dst = licenses_dir / "components" / "hygrothermfem_fairyfly"
    assert (htfem_dst / "third_party_notices.txt").read_bytes() == (
        htfem_src / "third_party_notices.txt"
    ).read_bytes()
    for src_file in (htfem_src / "third_party_licenses").rglob("*"):
        if src_file.is_file():
            rel = src_file.relative_to(htfem_src)
            assert (htfem_dst / rel).read_bytes() == src_file.read_bytes()
    assert (htfem_dst / "libraryfemtherm" / "LICENSE").is_file()

    # Rune 3D Viewer verbatim copies + Cargo crate summary
    rune_src = REPO_ROOT / "vendor" / "rune"
    rune_dst = licenses_dir / "components" / "rune_viewer"
    assert (rune_dst / "LICENSE").read_bytes() == (rune_src / "LICENSE").read_bytes()
    assert (rune_dst / "THIRD_PARTY_NOTICES.md").read_bytes() == (rune_src / "THIRD_PARTY_NOTICES.md").read_bytes()
    assert (rune_dst / "OFL.txt").read_bytes() == (
        rune_src / "crates" / "rune-kit" / "assets" / "math" / "OFL.txt"
    ).read_bytes()
    cargo_summary = (rune_dst / "CARGO_CRATE_LICENSES.md").read_text(encoding="utf-8")
    assert "lbt-viewer-app" in cargo_summary
    assert "GPL-3.0-or-later" in cargo_summary

    # IronbugBridge / .NET, Python 3.12, and optional URBANopt
    assert "Newtonsoft.Json" in notices and "System.Security.Permissions" in notices
    assert "Self-Contained App Bundling Only" in notices
    assert (licenses_dir / "components" / "ironbug_bridge" / "MICROSOFT_DOTNET_LICENSE.txt").is_file()
    assert "PSF-2.0" in notices and "no GPL `readline` or `gdbm`" in notices
    assert (licenses_dir / "components" / "python" / "LICENSE.txt").is_file()
    for urbanopt_file in ("RUBY_LICENSE.txt", "RUBY_BSDL.txt", "URBANOPT_CLI_LICENSE.md", "OPENSTUDIO_GEMS_LICENSE.md"):
        assert (licenses_dir / "components" / "urbanopt" / urbanopt_file).is_file()

    # Corresponding source doc coverage
    for token in ("corresponding-source.tar.zst", "gmsh", "GEOS", "Ironbug", "dss_python_backend", "KLUSolveX"):
        assert token in corresponding


def test_corresponding_source_manifest() -> None:
    manifest = json.loads((REPO_ROOT / "licenses" / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["project"] == "lbt-mcp"
    assert manifest["license"] == "AGPL-3.0-only"

    by_id = {entry["id"]: entry for entry in manifest["entries"]}
    assert {"ladybug-tools-mcp", "lbt-rune-viewer", "gmsh", "geos", "ironbug", "dss_python_backend"} <= set(by_id)

    assert by_id["gmsh"]["version"] == "4.15.2"
    assert "GPL-2.0-or-later" in by_id["gmsh"]["license"]
    assert by_id["geos"]["version"] == "3.14.1"
    assert "LGPL-2.1-only" in by_id["geos"]["license"]
    assert by_id["ironbug"]["version"] == "1.26.1"
    assert "LGPL-3.0" in by_id["ironbug"]["license"]
    assert by_id["dss_python_backend"]["bundled_in_standard"] is False
    assert by_id["dss_python_backend"]["requires_corresponding_source_if_distributed"] is True
    assert "LGPL-3.0" in by_id["dss_python_backend"]["license"]

    for entry in manifest["entries"]:
        assert entry["requires_corresponding_source"] is True
        for lic_rel in entry["license_files"]:
            assert (REPO_ROOT / lic_rel).is_file(), f"Missing manifest license_file: {lic_rel}"


def test_generate_licenses_cli_staging_and_bundle_manifest(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "distribution" / "generate_licenses.py"
    custom_manifest = tmp_path / "bundle_manifest.json"
    fake_sha = "a" * 64
    custom_manifest.write_text(
        json.dumps(
            {
                "sources": {
                    "gmsh": {
                        "version": "4.15.2",
                        "archive": "gmsh-4.15.2-source.tgz",
                        "sha256": fake_sha,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    staging_dir = tmp_path / "staging"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--output-dir",
            str(staging_dir),
            "--bundle-manifest",
            str(custom_manifest),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["source_manifest_only"] is False
    assert (staging_dir / "LICENSE").read_bytes() == (REPO_ROOT / "LICENSE").read_bytes()
    assert (staging_dir / "licenses" / "THIRD_PARTY_NOTICES.md").is_file()
    assert (staging_dir / "licenses" / "CORRESPONDING_SOURCE.md").is_file()
    staged_manifest = json.loads((staging_dir / "licenses" / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in staged_manifest["entries"]}
    assert by_id["gmsh"]["sha256"] == fake_sha

    manifest_only_dir = tmp_path / "manifest_only"
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--output-dir",
            str(manifest_only_dir),
            "--source-manifest-only",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert (manifest_only_dir / "licenses" / "SOURCE_MANIFEST.json").is_file()
    assert not (manifest_only_dir / "licenses" / "THIRD_PARTY_NOTICES.md").exists()
    assert not (manifest_only_dir / "LICENSE").exists()
