"""Bounded EnergyPlus results retain paging and source references."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from garden.manifest import GardenManifest
from garden.run_energy import results


def test_energy_results_limit_inline_samples_without_truncating_saved_series(tmp_path: Path, monkeypatch):
    manifest = GardenManifest.new("Result budgets")
    manifest.write(tmp_path)
    collection = SimpleNamespace(values=list(range(8760)), header=None)
    outputs = {name: [collection] * 30 for name in ("Heating", "Cooling")}
    sql = SimpleNamespace(
        available_outputs=list(outputs),
        data_collections_by_output_name=lambda name: outputs[name],
        data_collections_by_output_name_run_period=lambda name, period: outputs[name],
    )
    record = {"run_id": "run", "target": {"garden_id": manifest.garden_id}}
    monkeypatch.setattr(results, "_sql_result", lambda **kwargs: ("run", tmp_path / "run.sql", sql, record))
    saves = {}

    def save(*, data_collection, identifier, source, **kwargs):
        saves[identifier] = (len(data_collection.values), source)
        return {"target": {"identifier": identifier}, "persistence_receipt": {}}

    monkeypatch.setattr(results, "save_data_collection", save)
    page = results.read_energy_result_data(
        garden_root=str(tmp_path),
        output_names=["Heating", "Cooling"],
        include_values=True,
        max_values=8760,
        max_collections=100,
    )
    assert len(page["data_collections"]) == 50
    assert sum(len(series["values"]) for series in page["data_collections"]) == 1024
    assert all(series["values_truncated"] for series in page["data_collections"])
    cooling = page["summary_view"]["collections_by_output"][1]
    assert cooling["next_collection_offset"] == 20

    for period in (0, 1):
        next_page = results.read_energy_result_data(
            garden_root=str(tmp_path),
            output_name="Cooling",
            collection_offset=cooling["next_collection_offset"],
            max_collections=1,
            run_period_index=period,
            save_data_collections=True,
        )
        first = next_page["data_collections"][0]
        assert "values" not in first
        assert first["result_context"]["collection_index"] == 20
        assert first["result_context"]["run_period_index"] == period
    assert len(saves) == 2
    assert all(count == 8760 for count, _ in saves.values())
    assert {source["run_period_index"] for _, source in saves.values()} == {0, 1}


@pytest.mark.parametrize("match_to", ["rooms", "faces"])
def test_geometry_results_stay_within_inline_budget_and_report_next_page(tmp_path: Path, monkeypatch, match_to):
    GardenManifest.new("Geometry budget").write(tmp_path)
    collection = SimpleNamespace(values=list(range(600)), header=None)
    sql = SimpleNamespace(
        available_outputs=["Cooling"],
        data_collections_by_output_name=lambda name: [collection] * 60,
    )
    monkeypatch.setattr(results, "_sql_result", lambda **kwargs: ("sim", tmp_path / "run.sql", sql, {}))
    model = SimpleNamespace(identifier="model", rooms=[], faces=[], orphaned_apertures=[], orphaned_doors=[])
    monkeypatch.setattr(results, "_resolve_honeybee_model_for_run", lambda *args: model)
    objects = [
        SimpleNamespace(identifier=f"object_{index}", display_name=f"Object {index}", zone=None,
                        story=None, floor_area=10, multiplier=1)
        for index in range(60)
    ]
    monkeypatch.setattr(results, "match_rooms_to_data", lambda *a, **kw: [(obj, collection, 1) for obj in objects])
    monkeypatch.setattr(results, "match_faces_to_data", lambda *a, **kw: [(obj, collection) for obj in objects])
    page = results.read_energy_result_data(
        garden_root=str(tmp_path),
        output_name="Cooling",
        match_to=match_to,
        include_values=True,
        max_values=1000,
        max_collections=100,
        collection_offset=2,
    )
    matched = page["geometry_matches"][f"matched_{match_to}"]
    assert len(matched) == 50
    assert page["geometry_matches"]["matches_by_output"][0]["next_collection_offset"] == 52
    identifier_field = "room_identifier" if match_to == "rooms" else "face_identifier"
    assert matched[0][identifier_field] == "object_2"
    assert matched[0]["result_context"]["run_id"] == "sim"
    assert sum(len(item["values"]) for item in matched + page["data_collections"]) == 1024
