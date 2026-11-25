from __future__ import annotations

import hashlib
import os
from pathlib import Path
from unittest import mock

import pytest

from garden.manifest import GardenManifest
from garden.run_energy import config as weather_config
from garden.run_energy.config import import_local_weather_folder


def _write_weather_folder(
    folder: Path,
    *,
    epw_content: str,
    ddy_content: str = "DDY contents\n",
    stat_content: str = "STAT contents\n",
) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    epw_path = folder / "Chicago_TMY3.epw"
    epw_path.write_text(
        "LOCATION,Chicago O'Hare,IL,USA,TMY3,725300,41.98,-87.92,-6.0,201\n"
        f"{epw_content}",
        encoding="utf-8",
    )
    (folder / "Chicago_TMY3.ddy").write_text(ddy_content, encoding="utf-8")
    (folder / "Chicago_TMY3.stat").write_text(stat_content, encoding="utf-8")
    return epw_path


def _create_garden(root: Path) -> None:
    root.mkdir(parents=True)
    GardenManifest.new("Weather import transaction test").write(root)


def _weather_files(folder: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in folder.iterdir()
        if path.is_file()
    }


def test_overwrite_can_read_source_from_existing_weather_destination(
    tmp_path: Path,
) -> None:
    garden_root = tmp_path / "garden"
    source_folder = tmp_path / "source"
    _create_garden(garden_root)
    _write_weather_folder(source_folder, epw_content="old EPW data\n")

    import_local_weather_folder(
        garden_root=str(garden_root),
        source_path=str(source_folder),
        identifier="same_directory",
    )
    destination = garden_root / "imports" / "weather" / "same_directory"
    _write_weather_folder(
        destination,
        epw_content="replacement EPW data\n",
        ddy_content="replacement DDY data\n",
        stat_content="replacement STAT data\n",
    )

    result = import_local_weather_folder(
        garden_root=str(garden_root),
        source_path=str(destination),
        identifier="same_directory",
        overwrite=True,
    )

    epw_bytes = (destination / "Chicago_TMY3.epw").read_bytes()
    assert b"replacement EPW data" in epw_bytes
    assert (destination / "Chicago_TMY3.ddy").read_text(encoding="utf-8") == (
        "replacement DDY data\n"
    )
    assert (destination / "Chicago_TMY3.stat").read_text(encoding="utf-8") == (
        "replacement STAT data\n"
    )
    assert result["target"]["epw_sha256"] == hashlib.sha256(epw_bytes).hexdigest()
    assert result["target"]["ddy_path"] == (
        "imports/weather/same_directory/Chicago_TMY3.ddy"
    )


def test_manifest_failure_restores_previous_weather_and_manifest(
    tmp_path: Path,
) -> None:
    garden_root = tmp_path / "garden"
    original_source = tmp_path / "original"
    replacement_source = tmp_path / "replacement"
    _create_garden(garden_root)
    _write_weather_folder(
        original_source,
        epw_content="original EPW data\n",
        ddy_content="original DDY data\n",
        stat_content="original STAT data\n",
    )
    _write_weather_folder(
        replacement_source,
        epw_content="new EPW data\n",
        ddy_content="new DDY data\n",
        stat_content="new STAT data\n",
    )
    import_local_weather_folder(
        garden_root=str(garden_root),
        source_path=str(original_source),
        identifier="transactional_weather",
    )

    destination = garden_root / "imports" / "weather" / "transactional_weather"
    original_files = _weather_files(destination)
    manifest_path = garden_root / "garden.json"
    original_manifest = manifest_path.read_bytes()

    with mock.patch.object(
        GardenManifest, "write", side_effect=OSError("simulated manifest failure")
    ):
        with pytest.raises(OSError, match="simulated manifest failure"):
            import_local_weather_folder(
                garden_root=str(garden_root),
                source_path=str(replacement_source),
                identifier="transactional_weather",
                overwrite=True,
            )

    assert _weather_files(destination) == original_files
    assert manifest_path.read_bytes() == original_manifest
    assert list(destination.parent.glob(".weather-*")) == []
    assert list((garden_root / ".garden").glob("weather-import-*.manifest-backup")) == []


def test_failed_directory_rollback_keeps_recovery_backups(tmp_path: Path) -> None:
    garden_root = tmp_path / "garden"
    original_source = tmp_path / "original"
    replacement_source = tmp_path / "replacement"
    _create_garden(garden_root)
    _write_weather_folder(original_source, epw_content="original EPW data\n")
    _write_weather_folder(replacement_source, epw_content="new EPW data\n")
    import_local_weather_folder(
        garden_root=str(garden_root),
        source_path=str(original_source),
        identifier="rollback_backup",
    )

    destination = garden_root / "imports" / "weather" / "rollback_backup"
    original_manifest = (garden_root / "garden.json").read_bytes()
    real_replace = os.replace

    def fail_restoring_old_directory(source: str | Path, target: str | Path) -> None:
        if Path(source).name.startswith(".weather-backup-") and Path(target) == destination:
            raise PermissionError("simulated directory restore failure")
        real_replace(source, target)

    with (
        mock.patch.object(GardenManifest, "write", side_effect=OSError("manifest failure")),
        mock.patch.object(
            weather_config.os, "replace", side_effect=fail_restoring_old_directory
        ),
    ):
        with pytest.raises(RuntimeError, match="rollback was incomplete") as error:
            import_local_weather_folder(
                garden_root=str(garden_root),
                source_path=str(replacement_source),
                identifier="rollback_backup",
                overwrite=True,
            )

    recovery_paths = str(error.value)
    backup_directories = list(destination.parent.glob(".weather-backup-*"))
    assert len(backup_directories) == 1
    assert str(backup_directories[0]) in recovery_paths
    assert b"original EPW data" in _weather_files(backup_directories[0])["Chicago_TMY3.epw"]
    assert not destination.exists()
    assert (garden_root / "garden.json").read_bytes() == original_manifest
