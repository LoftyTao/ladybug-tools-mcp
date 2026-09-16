"""FP Detail HVAC worker handoff checks."""

import hashlib
from pathlib import Path

from honeybee.model import Model
from honeybee.room import Room
from flowerpot.registry import create_flowerpot
from flowerpot import worker_cli
from flowerpot.worker_cli import _dispatch
from garden.honeybee_core.model_io import save_honeybee_model
from garden.ironbug_core.model_io import save_ironbug_model
from garden.ironbug_core.models import create_ironbug_model
from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    add_ironbug_thermal_zone_equipment,
    set_ironbug_ptac_children,
)
from garden.manifest import GardenManifest
from garden.store import create_garden
from ironbug.hvac import (
    IB_ElectricLoadCenter,
    IB_EnergyManagementSystem,
    IB_HVACSystem,
    IB_Model,
    IB_NoAirLoop,
    IB_ThermalZone,
)


def _save_model(garden_root, identifier, display_name=None):
    hvac = IB_HVACSystem(AirLoops=[], PlantLoops=[], VariableRefrigerantFlows=[])
    save_ironbug_model(
        garden_root,
        GardenManifest.read(garden_root),
        IB_Model(
            identifier=identifier,
            display_name=display_name,
            HVACSystem=hvac,
        ),
        identifier=identifier,
    )


def test_worker_prepares_unique_ironbug_model_without_exposing_spec_in_report(
    tmp_path,
):
    garden = create_garden(name="detail-hvac", root_dir=str(tmp_path / "garden"))
    hvac = IB_HVACSystem(
        AirLoops=[], PlantLoops=[], VariableRefrigerantFlows=[]
    )
    hvac.AirLoops.append(
        IB_NoAirLoop(
            identifier="no_air_loop",
            ThermalZones=[IB_ThermalZone(identifier="Room1")],
        )
    )
    save_ironbug_model(
        tmp_path / "garden",
        GardenManifest.read(tmp_path / "garden"),
        IB_Model(
            identifier="system_one",
            display_name="System One",
            HVACSystem=hvac,
        ),
        identifier="system_one",
    )
    flowerpot = create_flowerpot(
        garden_root=garden["garden_root"], source="garden"
    )["flowerpot"]

    result = _dispatch(
        "ironbug_hvac_specification", {"flowerpot": flowerpot}
    )

    assert result["report"]["status"] == "ok", result["report"]["message"]
    assert result["metadata"]["model_identifier"] == "system_one"
    assert result["specification"]["DisplayName"] == "System One"
    assert result["allowlist"]
    assert result["follow_path"].endswith("system_one.ibjson")
    assert "specification" not in result["report"]["details"]
    assert result["report"]["details"]["room_binding"]["status"] == "not_checked"


def test_worker_reports_no_ironbug_models(tmp_path):
    garden = create_garden(name="empty", root_dir=str(tmp_path / "garden"))
    flowerpot = create_flowerpot(
        garden_root=garden["garden_root"], source="garden"
    )["flowerpot"]

    result = _dispatch(
        "ironbug_hvac_specification", {"flowerpot": flowerpot}
    )

    assert result["specification"] is None
    assert result["report"]["status"] == "error"
    assert result["report"]["details"]["failed_gate"] == "selection"


def test_worker_materializes_source_backed_ptac_graph(tmp_path):
    garden = create_garden(name="ptac", root_dir=str(tmp_path / "garden"))
    model_target = create_ironbug_model(
        garden_root=garden["garden_root"], identifier="ptac"
    )["target"]

    def create(source_class, identifier, **kwargs):
        return create_source_backed_ironbug_object(
            garden_root=garden["garden_root"],
            ironbug_model_target=model_target,
            source_class=source_class,
            identifier=identifier,
            **kwargs,
        )["target"]

    zone = create(
        "IB_ThermalZone",
        "Room1",
        source_fields={"Name": "Room1"},
        source_properties={"IsAirTerminalBeforeZoneEquipments": False},
    )
    ptac = create("IB_ZoneHVACPackagedTerminalAirConditioner", "ptac")
    fan = create("IB_FanOnOff", "fan")
    heating = create("IB_CoilHeatingElectric", "heating")
    cooling = create("IB_CoilCoolingDXSingleSpeed", "cooling")
    set_ironbug_ptac_children(
        garden_root=garden["garden_root"],
        ironbug_model_target=model_target,
        ptac_target=ptac,
        fan_target=fan,
        heating_coil_target=heating,
        cooling_coil_target=cooling,
    )
    add_ironbug_thermal_zone_equipment(
        garden_root=garden["garden_root"],
        ironbug_model_target=model_target,
        thermal_zone_target=zone,
        zone_equipment_target=ptac,
    )
    flowerpot = create_flowerpot(
        garden_root=garden["garden_root"], source="garden"
    )["flowerpot"]

    result = _dispatch("ironbug_hvac_specification", {"flowerpot": flowerpot})

    assert result["report"]["status"] == "ok"
    assert "IB_ZoneHVACPackagedTerminalAirConditioner" in str(
        result["specification"]
    )


def test_worker_selects_exact_identifier_and_reports_ambiguous_candidates(tmp_path):
    garden = create_garden(name="multiple", root_dir=str(tmp_path / "garden"))
    _save_model(tmp_path / "garden", "system_one", "System One")
    _save_model(tmp_path / "garden", "system_two", "System Two")
    flowerpot = create_flowerpot(
        garden_root=garden["garden_root"], source="garden"
    )["flowerpot"]

    selected = _dispatch(
        "ironbug_hvac_specification",
        {"flowerpot": flowerpot, "model_identifier": "system_two"},
    )
    assert selected["report"]["status"] == "ok"
    assert selected["metadata"]["model_identifier"] == "system_two"
    assert selected["specification"]["DisplayName"] == "System Two"

    ambiguous = _dispatch("ironbug_hvac_specification", {"flowerpot": flowerpot})
    assert ambiguous["specification"] is None
    assert ambiguous["report"]["status"] == "error"
    assert ambiguous["report"]["details"]["candidate_identifiers"] == [
        "system_one",
        "system_two",
    ]

    missing = _dispatch(
        "ironbug_hvac_specification",
        {"flowerpot": flowerpot, "model_identifier": "missing"},
    )
    assert missing["specification"] is None
    assert missing["report"]["status"] == "error"
    assert missing["report"]["details"]["candidate_identifiers"] == [
        "system_one",
        "system_two",
    ]


def test_worker_specification_is_detached_from_garden_file(tmp_path):
    garden = create_garden(name="detached", root_dir=str(tmp_path / "garden"))
    _save_model(tmp_path / "garden", "system_one", "System One")
    flowerpot = create_flowerpot(
        garden_root=garden["garden_root"], source="garden"
    )["flowerpot"]

    result = _dispatch("ironbug_hvac_specification", {"flowerpot": flowerpot})
    model_path = Path(result["follow_path"])
    before = hashlib.sha256(model_path.read_bytes()).digest()
    result["specification"]["DisplayName"] = "Edited Snapshot"
    result["specification"]["AirLoops"].append({"edited": True})

    assert hashlib.sha256(model_path.read_bytes()).digest() == before


def test_worker_rejects_invalid_root_type_before_removal(tmp_path, monkeypatch):
    garden = create_garden(name="invalid-root", root_dir=str(tmp_path / "garden"))
    _save_model(tmp_path / "garden", "system_one")
    flowerpot = create_flowerpot(
        garden_root=garden["garden_root"], source="garden"
    )["flowerpot"]
    monkeypatch.setattr(worker_cli, "_ironbug_hvac_type_allowlist", lambda: set())

    result = _dispatch("ironbug_hvac_specification", {"flowerpot": flowerpot})

    assert result["specification"] is None
    assert result["report"]["status"] == "error"
    assert result["report"]["details"]["failed_gate"] == "allowlist"
    assert "disallowed $type" in result["report"]["message"]
    assert "IB_HVACSystem" in result["report"]["message"]


def test_worker_rejects_null_type_metadata_with_allowlist_gate(tmp_path, monkeypatch):
    garden = create_garden(name="null-type", root_dir=str(tmp_path / "garden"))
    _save_model(tmp_path / "garden", "system_one")
    flowerpot = create_flowerpot(
        garden_root=garden["garden_root"], source="garden"
    )["flowerpot"]
    monkeypatch.setattr(
        worker_cli,
        "_ironbug_console_spec_value",
        lambda value: {"$type": None, "AirLoops": []},
    )

    result = _dispatch("ironbug_hvac_specification", {"flowerpot": flowerpot})

    assert result["specification"] is None
    assert result["report"]["status"] == "error"
    assert result["report"]["details"]["failed_gate"] == "allowlist"
    assert "disallowed $type: None" in result["report"]["message"]


def _flowerpot_with_hvac(tmp_path, *, room_identifier=None, zone_identifier="Room1", roots=False):
    garden = create_garden(name="detail-hvac", root_dir=str(tmp_path / "garden"))
    garden_root = Path(garden["garden_root"])
    if room_identifier is not None:
        save_honeybee_model(
            garden_root,
            GardenManifest.read(garden_root),
            Model("base", [Room.from_box(room_identifier)]),
            name="base",
            set_base=True,
        )
    hvac = IB_HVACSystem(AirLoops=[], PlantLoops=[], VariableRefrigerantFlows=[])
    hvac.AirLoops.append(
        IB_NoAirLoop(
            identifier="no_air_loop",
            ThermalZones=[IB_ThermalZone(identifier=zone_identifier)],
        )
    )
    model = IB_Model(identifier="system_one", HVACSystem=hvac)
    if roots:
        model.EnergyManagementSystem = IB_EnergyManagementSystem()
        model.ElectricLoadCenter = IB_ElectricLoadCenter()
    save_ironbug_model(
        garden_root,
        GardenManifest.read(garden_root),
        model,
        identifier="system_one",
    )
    return create_flowerpot(garden_root=str(garden_root), source="garden")["flowerpot"]


def test_worker_reports_matching_or_mismatched_base_room_ids(tmp_path):
    matching = _dispatch(
        "ironbug_hvac_specification",
        {"flowerpot": _flowerpot_with_hvac(tmp_path / "matching", room_identifier="Room1")},
    )
    assert matching["report"]["details"]["room_binding"]["status"] == "matched"

    mismatched = _dispatch(
        "ironbug_hvac_specification",
        {"flowerpot": _flowerpot_with_hvac(tmp_path / "mismatch", room_identifier="Room1", zone_identifier="Other")},
    )
    assert mismatched["report"]["status"] == "blocked"
    assert mismatched["specification"]
    assert mismatched["report"]["details"]["room_binding"]["missing_room_identifiers"] == ["Room1"]


def test_worker_excludes_model_level_ems_and_electric_load_center(tmp_path):
    result = _dispatch(
        "ironbug_hvac_specification",
        {"flowerpot": _flowerpot_with_hvac(tmp_path, roots=True)},
    )

    assert result["report"]["details"]["excluded_roots"] == [
        "EnergyManagementSystem",
        "ElectricLoadCenter",
    ]
    assert "EnergyManagementSystem" not in result["specification"]
    assert "ElectricLoadCenter" not in result["specification"]
