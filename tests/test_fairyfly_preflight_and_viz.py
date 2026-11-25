"""Tests for Fairyfly P0-6 fixes: Gmsh diagnostics, edit ergonomics, preflight, and heat_flux_vectors viz."""

from __future__ import annotations

import asyncio
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET
import zipfile

from fastmcp import FastMCP
import pytest

from garden.store import create_garden
from ladybug_tools_mcp.registry import register_tools


def _call_tool(mcp: FastMCP, tool_name: str, **kwargs):
    tool = asyncio.run(mcp.get_tool(tool_name))
    assert tool is not None, f"Expected registered MCP tool {tool_name}"
    return tool.fn(**kwargs)


@pytest.fixture()
def mcp_server() -> FastMCP:
    mcp = FastMCP("test-ff-p0-6")
    register_tools(mcp)
    return mcp


@pytest.fixture()
def garden_root(tmp_path: Path) -> str:
    created = create_garden(name="ff-preflight-viz", root_dir=str(tmp_path / "garden"))
    return str(created["garden_root"])


# ---------------------------------------------------------------------------
# P0-6a: mesh_type="auto" & actionable FEM/Gmsh boundary coverage errors
# ---------------------------------------------------------------------------


def test_mesh_control_accepts_auto_case_insensitive():
    from fairyfly_next_therm.simulation.mesh import MeshControl
    from garden.fairyfly.therm import _coerce_simulation_parameter

    for raw in ("auto", "AUTO", "Auto", "  auto  "):
        ctrl = MeshControl(mesh_type=raw, parameter=24)
        assert ctrl.mesh_type == "Simmetrix"

    from_dict = MeshControl.from_dict({"type": "MeshControl", "mesh_type": "AUTO", "parameter": 30})
    assert from_dict.mesh_type == "Simmetrix"

    sim_par = _coerce_simulation_parameter({"mesh": {"mesh_type": "auto", "parameter": 16}})
    assert sim_par is not None
    assert sim_par.mesh.mesh_type == "Simmetrix"
    assert sim_par.mesh.parameter == 16

    with pytest.raises(ValueError, match="not supported"):
        MeshControl(mesh_type="invalid_mesher")


def test_native_mesh_uncovered_boundary_reports_actionable_details():
    from fairyfly_next_therm.native_mesh import mesh_to_xml

    class _Vert:
        def __init__(self, x: float, y: float, z: float = 0.0) -> None:
            self.X, self.Y, self.Z = x, y, z

    class _Face:
        def __init__(self, a: int, b: int, c: int, d: int) -> None:
            self.A, self.B, self.C, self.D = a, b, c, d

    class _Mesh:
        Vertices = [_Vert(0, 0), _Vert(100, 0), _Vert(100, 100), _Vert(0, 100)]
        Faces = [_Face(0, 1, 2, 3)]

    model_xml = ET.fromstring(
        """
        <Model>
          <GlazingOrigin><x>0</x><y>0</y></GlazingOrigin>
          <Polygons>
            <Polygon>
              <Type>Material</Type>
              <MaterialUUID>mat-1</MaterialUUID>
              <Points>
                <Point><x>0</x><y>0</y></Point>
                <Point><x>100</x><y>0</y></Point>
                <Point><x>100</x><y>100</y></Point>
                <Point><x>0</x><y>100</y></Point>
              </Points>
            </Polygon>
          </Polygons>
          <Boundaries>
            <Boundary>
              <ID>11</ID><Name>IntBC</Name><Type>Boundary Condition</Type>
              <StartPoint><x>0</x><y>0</y></StartPoint><EndPoint><x>0</x><y>100</y></EndPoint>
            </Boundary>
            <Boundary>
              <ID>12</ID><Name>BottomBC</Name><Type>Boundary Condition</Type>
              <StartPoint><x>0</x><y>0</y></StartPoint><EndPoint><x>100</x><y>0</y></EndPoint>
            </Boundary>
            <Boundary>
              <ID>13</ID><Name>ExtBC</Name><Type>Boundary Condition</Type>
              <StartPoint><x>100</x><y>0</y></StartPoint><EndPoint><x>100</x><y>100</y></EndPoint>
            </Boundary>
            <Boundary>
              <ID>14</ID><Name>TopBC</Name><Type>Boundary Condition</Type>
              <StartPoint><x>0</x><y>100</y></StartPoint><EndPoint><x>100</x><y>100</y></EndPoint>
            </Boundary>
            <Boundary>
              <ID>15</ID><Name>MissingTopExtra</Name><Type>Boundary Condition</Type>
              <StartPoint><x>0</x><y>100</y></StartPoint><EndPoint><x>50</x><y>100</y></EndPoint>
            </Boundary>
          </Boundaries>
        </Model>
        """
    )
    # Wait: edge (0,100)-(100,100) matches TopBC only (MissingTopExtra does not match (100,100));
    # make MissingTopExtra lie along a separate uncovered span so exterior edges match 14 cleanly.
    for b in model_xml.findall("Boundaries/Boundary"):
        if b.findtext("ID") == "15":
            b.find("StartPoint/x").text = "200"
            b.find("StartPoint/y").text = "200"
            b.find("EndPoint/x").text = "250"
            b.find("EndPoint/y").text = "200"

    bcs_xml = ET.fromstring(
        """
        <BoundaryConditions>
          <BoundaryCondition><Name>IntBC</Name><Simplified><FilmCoefficient>8</FilmCoefficient><Temperature>20</Temperature></Simplified></BoundaryCondition>
          <BoundaryCondition><Name>BottomBC</Name><Simplified><FilmCoefficient>0</FilmCoefficient><Temperature>0</Temperature></Simplified></BoundaryCondition>
          <BoundaryCondition><Name>ExtBC</Name><Simplified><FilmCoefficient>25</FilmCoefficient><Temperature>0</Temperature></Simplified></BoundaryCondition>
          <BoundaryCondition><Name>TopBC</Name><Simplified><FilmCoefficient>0</FilmCoefficient><Temperature>0</Temperature></Simplified></BoundaryCondition>
          <BoundaryCondition><Name>MissingTopExtra</Name><Simplified><FilmCoefficient>8</FilmCoefficient><Temperature>15</Temperature></Simplified></BoundaryCondition>
        </BoundaryConditions>
        """
    )
    with pytest.raises(ValueError) as exc_info:
        mesh_to_xml(model_xml, bcs_xml, _Mesh())
    msg = str(exc_info.value)
    assert "FEM/Gmsh mesh" in msg
    assert "Rhino mesh" not in msg
    assert "15" in msg
    assert "MissingTopExtra" in msg
    assert "expected_length=50.000" in msg
    assert "covered_length=0.000" in msg
    assert "(200.000, 200.000)->(250.000, 200.000)" in msg


# ---------------------------------------------------------------------------
# P0-6b: FF_Edit_Model missing-key diagnostics & non-UUID condition auto-UUID
# ---------------------------------------------------------------------------


def test_edit_model_descriptive_errors_and_condition_uuid_conversion(
    mcp_server: FastMCP, garden_root: str
):
    from garden.fairyfly.model import coerce_fairyfly_condition, load_fairyfly_model

    m = _call_tool(mcp_server, "FF_Create_Model", garden_root=garden_root, identifier="ff_ergo")

    # Missing shape 'material' should give explicit ValueError instead of KeyError
    with pytest.raises(ValueError, match="material") as exc_mat:
        _call_tool(
            mcp_server,
            "FF_Edit_Model",
            garden_root=garden_root,
            model_target=m["target"],
            shapes=[{"vertices_2d": [[0, 0], [100, 0], [100, 100], [0, 100]]}],
        )
    assert "vertices_2d" in str(exc_mat.value)

    # Missing shape 'vertices_2d'
    with pytest.raises(ValueError, match="vertices_2d"):
        _call_tool(
            mcp_server,
            "FF_Edit_Model",
            garden_root=garden_root,
            model_target=m["target"],
            shapes=[{"material": {"conductivity": 1.0}}],
        )

    # Missing boundary 'line_segments_2d'
    with pytest.raises(ValueError, match="line_segments_2d"):
        _call_tool(
            mcp_server,
            "FF_Edit_Model",
            garden_root=garden_root,
            model_target=m["target"],
            boundaries=[{"temperature": 20.0, "film_coefficient": 8.0}],
        )

    # Missing 'identifier' and missing 'temperature' in SteadyState dict
    with pytest.raises(ValueError, match="temperature"):
        coerce_fairyfly_condition({"condition": {"type": "SteadyState", "film_coefficient": 8.0}})

    # SteadyState dict WITHOUT 'identifier' should auto-generate UUID instead of KeyError: 'identifier'
    no_id_cond = coerce_fairyfly_condition(
        {"condition": {"type": "SteadyState", "temperature": 20.0, "film_coefficient": 8.0}}
    )
    assert str(uuid.UUID(no_id_cond.identifier)) == no_id_cond.identifier

    # Non-UUID identifier converts deterministically via uuid5 and preserves display_name
    expected_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "lbt-mcp:therm-condition:int-iso-20"))
    cond_auto_name = coerce_fairyfly_condition(
        {
            "condition": {
                "type": "SteadyState",
                "identifier": "int-iso-20",
                "temperature": 20.0,
                "film_coefficient": 7.69,
            }
        }
    )
    assert cond_auto_name.identifier == expected_uuid
    assert cond_auto_name.display_name == "int-iso-20"

    # Explicit display_name is preserved when non-UUID identifier is converted
    cond_explicit_name = coerce_fairyfly_condition(
        {
            "condition": {
                "type": "SteadyState",
                "identifier": "int-iso-20",
                "display_name": "ISO 10211 Interior",
                "temperature": 20.0,
                "film_coefficient": 7.69,
            }
        }
    )
    assert cond_explicit_name.identifier == expected_uuid
    assert cond_explicit_name.display_name == "ISO 10211 Interior"

    # Non-UUID identifier also works in flat SteadyState and Transient specs via FF_Edit_Model
    edit_res = _call_tool(
        mcp_server,
        "FF_Edit_Model",
        garden_root=garden_root,
        model_target=m["target"],
        shapes=[
            {
                "name": "Wall",
                "vertices_2d": [[0, 0], [100, 0], [100, 100], [0, 100]],
                "material": {"name": "Concrete", "conductivity": 1.0},
            }
        ],
        boundaries=[
            {
                "name": "IntFace",
                "line_segments_2d": [[[0, 0], [0, 100]]],
                "condition": {
                    "type": "SteadyState",
                    "identifier": "int-iso-20",
                    "temperature": 20.0,
                    "film_coefficient": 7.69,
                },
                "u_factor_tag": "WallU",
            },
            {
                "name": "ExtFace",
                "line_segments_2d": [[[100, 0], [100, 100]]],
                "identifier": "ext-iso-0",
                "temperature": 0.0,
                "film_coefficient": 25.0,
            },
        ],
    )
    assert edit_res["report"]["status"] == "ok"
    loaded = load_fairyfly_model(Path(garden_root), edit_res["model_target"])
    assert loaded.boundaries[0].properties.therm.condition.identifier == expected_uuid
    assert loaded.boundaries[0].properties.therm.condition.display_name == "int-iso-20"
    assert loaded.boundaries[1].properties.therm.condition.identifier == str(
        uuid.uuid5(uuid.NAMESPACE_DNS, "lbt-mcp:therm-condition:ext-iso-0")
    )
    assert loaded.boundaries[1].properties.therm.condition.display_name == "ext-iso-0"


# ---------------------------------------------------------------------------
# P0-6c: validate_fairyfly_model + THMZ preflight + pre-solve fail-fast
# ---------------------------------------------------------------------------


def test_validate_fairyfly_model_detects_missing_material_empty_and_misaligned_boundaries(
    mcp_server: FastMCP, garden_root: str, monkeypatch: pytest.MonkeyPatch
):
    from fairyfly.boundary import Boundary
    from fairyfly.model import Model
    from fairyfly.shape import Shape
    from fairyfly_next_therm.condition.steadystate import SteadyState
    from fairyfly_next_therm.material.solid import SolidMaterial
    from ladybug_geometry.geometry3d import Face3D, LineSegment3D, Point3D

    import garden.fairyfly.model as ff_model
    from garden.fairyfly.model import save_fairyfly_model, validate_fairyfly_model
    from garden.manifest import GardenManifest

    garden_path = Path(garden_root)
    manifest = GardenManifest.read(garden_path)

    # 1. Valid 2-shape model with a boundary spanning across collinear exterior edges
    mat = SolidMaterial(1.0)
    s1 = Shape(Face3D([Point3D(0, 0), Point3D(50, 0), Point3D(50, 100), Point3D(0, 100)]))
    s1.display_name = "LeftLayer"
    s1.properties.therm.material = mat
    s2 = Shape(Face3D([Point3D(50, 0), Point3D(100, 0), Point3D(100, 100), Point3D(50, 100)]))
    s2.display_name = "RightLayer"
    s2.properties.therm.material = mat
    b_bottom = Boundary([LineSegment3D.from_end_points(Point3D(0, 0), Point3D(100, 0))])
    b_bottom.display_name = "SpanningBottom"
    b_bottom.properties.therm.condition = SteadyState(20.0, 8.0)
    valid_model = Model([s1, s2], [b_bottom], units="Millimeters")
    valid_target, _ = save_fairyfly_model(
        garden_path, manifest, valid_model, name="valid_spanning", set_base=False
    )
    val_ok = validate_fairyfly_model(garden_root=garden_root, model_target=valid_target)
    assert val_ok["valid"] is True
    assert val_ok["issues"] == []

    # 2. Missing material + empty boundary geometry + misaligned floating boundary + interior edge
    s_no_mat = Shape(Face3D([Point3D(0, 0), Point3D(50, 0), Point3D(50, 100), Point3D(0, 100)]))
    s_no_mat.display_name = "UnassignedShape"
    s_with_mat = Shape(Face3D([Point3D(50, 0), Point3D(100, 0), Point3D(100, 100), Point3D(50, 100)]))
    s_with_mat.display_name = "AssignedShape"
    s_with_mat.properties.therm.material = mat

    b_floating = Boundary([LineSegment3D.from_end_points(Point3D(-10, 0), Point3D(-10, 100))])
    b_floating.display_name = "FloatingLeft"
    b_floating.properties.therm.condition = SteadyState(20.0, 8.0)

    b_interior = Boundary([LineSegment3D.from_end_points(Point3D(50, 0), Point3D(50, 100))])
    b_interior.display_name = "InteriorJoint"
    b_interior.properties.therm.condition = SteadyState(0.0, 25.0)

    b_empty = Boundary([LineSegment3D.from_end_points(Point3D(0, 0), Point3D(0, 100))])
    b_empty.display_name = "EmptyBoundary"

    bad_model = Model([s_no_mat, s_with_mat], [b_floating, b_interior, b_empty], units="Millimeters")
    bad_target, _ = save_fairyfly_model(
        garden_path, manifest, bad_model, name="bad_checks", set_base=False
    )
    orig_load = ff_model.load_fairyfly_model

    def _load_with_empty_boundary(gr_path, mt):
        loaded = orig_load(gr_path, mt)
        loaded.boundaries[-1]._geometry = ()
        return loaded

    monkeypatch.setattr(ff_model, "load_fairyfly_model", _load_with_empty_boundary)
    val_bad = validate_fairyfly_model(garden_root=garden_root, model_target=bad_target)
    assert val_bad["valid"] is False
    joined = "\n".join(val_bad["issues"])
    assert "UnassignedShape" in joined
    assert "EmptyBoundary" in joined
    assert "FloatingLeft" in joined
    assert "min_distance=10.0000" in joined
    assert "[-10.0, 0.0, 0.0]" in joined
    assert "InteriorJoint" in joined
    assert val_bad["summary_view"]["missing_material_count"] == 1
    assert val_bad["summary_view"]["empty_boundary_count"] == 1
    assert val_bad["summary_view"]["misaligned_boundary_count"] == 2


def test_preflight_export_and_presolve_fail_fast(
    mcp_server: FastMCP, garden_root: str, monkeypatch: pytest.MonkeyPatch
):
    import garden.fairyfly.therm as ff_therm

    # Valid model with export_only=True, include_mesh=True populates preflight fields
    m_ok = _call_tool(mcp_server, "FF_Create_Model", garden_root=garden_root, identifier="ff_pre_ok")
    _call_tool(
        mcp_server,
        "FF_Edit_Model",
        garden_root=garden_root,
        model_target=m_ok["target"],
        shapes=[
            {
                "name": "Slab",
                "vertices_2d": [[0, 0], [100, 0], [100, 100], [0, 100]],
                "material": {"name": "SlabMat", "conductivity": 1.0},
            }
        ],
        boundaries=[
            {
                "name": "Int",
                "line_segments_2d": [[[0, 0], [0, 100]]],
                "temperature": 20.0,
                "film_coefficient": 8.0,
                "u_factor_tag": "UF_Slab",
            },
            {
                "name": "Ext",
                "line_segments_2d": [[[100, 0], [100, 100]]],
                "temperature": 0.0,
                "film_coefficient": 25.0,
            },
        ],
    )
    exported = _call_tool(
        mcp_server,
        "FF_Start_Simulation",
        garden_root=garden_root,
        model_target=m_ok["target"],
        export_only=True,
        include_mesh=True,
        run_id="ff_preflight_export",
        simulation_parameter={"mesh": {"mesh_type": "auto", "parameter": 16}},
    )
    sv = exported["summary_view"]
    preflight = sv["preflight"]
    for key in (
        "boundary_count",
        "boundary_labels",
        "boundary_coverage_lengths",
        "unmatched_boundaries",
        "mesh_element_count",
        "mesh_node_count",
    ):
        assert key in sv
        assert key in preflight
    assert preflight["boundary_count"] == 4  # 2 user BCs + 2 Adiabatic edges
    assert preflight["unmatched_boundaries"] == []
    assert preflight["mesh_element_count"] > 0
    assert preflight["mesh_node_count"] > 0
    assert any(item.get("flux_tag") == "UF_Slab" for item in preflight["boundary_labels"])
    assert all(entry["covered"] is True for entry in preflight["boundary_coverage_lengths"].values())

    # Guard: submit_worker_process must NEVER be invoked when pre-solve validation fails
    submit_calls: list[dict] = []

    def fail_if_called(**kwargs):
        submit_calls.append(kwargs)
        raise AssertionError("submit_worker_process should not be called on invalid preflight")

    monkeypatch.setattr(ff_therm, "submit_worker_process", fail_if_called)

    # 1. Misaligned boundary fails fast before launching worker
    m_bad_b = _call_tool(mcp_server, "FF_Create_Model", garden_root=garden_root, identifier="ff_pre_bad_b")
    _call_tool(
        mcp_server,
        "FF_Edit_Model",
        garden_root=garden_root,
        model_target=m_bad_b["target"],
        shapes=[
            {
                "name": "Wall",
                "vertices_2d": [[0, 0], [100, 0], [100, 100], [0, 100]],
                "material": {"name": "Mat", "conductivity": 1.0},
            }
        ],
        boundaries=[
            {
                "name": "OffsetBoundary",
                "line_segments_2d": [[[-5, 0], [-5, 100]]],
                "temperature": 20.0,
                "film_coefficient": 8.0,
            }
        ],
    )
    with pytest.raises(ValueError, match="OffsetBoundary"):
        _call_tool(
            mcp_server,
            "FF_Start_Simulation",
            garden_root=garden_root,
            model_target=m_bad_b["target"],
            run_id="ff_fail_bad_b",
        )
    assert submit_calls == []

    # 2. Missing boundaries fails fast before launching solver
    m_no_b = _call_tool(mcp_server, "FF_Create_Model", garden_root=garden_root, identifier="ff_pre_no_b")
    _call_tool(
        mcp_server,
        "FF_Edit_Model",
        garden_root=garden_root,
        model_target=m_no_b["target"],
        shapes=[
            {
                "name": "Wall",
                "vertices_2d": [[0, 0], [100, 0], [100, 100], [0, 100]],
                "material": {"name": "Mat", "conductivity": 1.0},
            }
        ],
    )
    with pytest.raises(ValueError, match="no boundaries"):
        _call_tool(
            mcp_server,
            "FF_Start_Simulation",
            garden_root=garden_root,
            model_target=m_no_b["target"],
            run_id="ff_fail_no_b",
        )
    assert submit_calls == []

    # 3. Corrupted premeshed THMZ with 0 mesh elements fails fast before launching worker
    thmz_zero_path = Path(garden_root) / "zero_mesh.thmz"
    src_thmz = Path(garden_root) / sv["path"]
    with zipfile.ZipFile(src_thmz, "r") as zin, zipfile.ZipFile(thmz_zero_path, "w") as zout:
        for name in zin.namelist():
            if name == "Mesh.xml":
                zout.writestr(
                    "Mesh.xml",
                    "<Mesh><Version>1</Version><Case><Nodes/><Elements/><BCSegments/></Case></Mesh>",
                )
            else:
                zout.writestr(name, zin.read(name))
    with pytest.raises(ValueError, match="zero elements or nodes"):
        _call_tool(
            mcp_server,
            "FF_Start_Simulation",
            garden_root=garden_root,
            thmz_path=str(thmz_zero_path),
            run_id="ff_fail_zero_mesh",
        )
    assert submit_calls == []


# ---------------------------------------------------------------------------
# P0-6d: heat_flux_vectors VisualizationSet + source_run_id provenance
# ---------------------------------------------------------------------------


def test_heat_flux_vectors_visualization_and_run_id_provenance(
    mcp_server: FastMCP, garden_root: str
):
    m = _call_tool(mcp_server, "FF_Create_Model", garden_root=garden_root, identifier="ff_viz_vec")
    _call_tool(
        mcp_server,
        "FF_Edit_Model",
        garden_root=garden_root,
        model_target=m["target"],
        shapes=[
            {
                "name": "Slab",
                "vertices_2d": [[0, 0], [100, 0], [100, 100], [0, 100]],
                "material": {"name": "Concrete", "conductivity": 1.0},
            }
        ],
        boundaries=[
            {
                "name": "Interior",
                "line_segments_2d": [[[0, 0], [0, 100]]],
                "temperature": 20.0,
                "film_coefficient": 8.0,
                "emissivity": 0.0,
                "u_factor_tag": "SlabU",
            },
            {
                "name": "Exterior",
                "line_segments_2d": [[[100, 0], [100, 100]]],
                "temperature": 0.0,
                "film_coefficient": 25.0,
                "emissivity": 0.0,
            },
        ],
    )
    run_id = "ff_vec_run_01"
    run_res = _call_tool(
        mcp_server,
        "FF_Start_Simulation",
        garden_root=garden_root,
        model_target=m["target"],
        run_id=run_id,
        simulation_parameter={"mesh": {"mesh_type": "auto", "parameter": 16, "run_error_estimator": False}},
        wait_seconds=60.0,
    )
    assert run_res["status"] == "completed", run_res.get("error")
    assert run_res["summary_view"]["preflight"]["mesh_element_count"] > 0

    # Inline VisualizationSet with heat_flux_vectors
    vis_inline = _call_tool(
        mcp_server,
        "FF_To_Visualization_Set",
        garden_root=garden_root,
        source_kind="result",
        run_target=run_res["run_target"],
        data_type="heat_flux_vectors",
        return_visualization_set=True,
    )
    assert vis_inline["report"]["status"] == "ok"
    assert vis_inline["summary_view"]["source_run_id"] == run_id
    assert vis_inline["summary_view"]["vector_arrow_count"] > 0
    vs_dict = vis_inline["visualization_set"]
    assert vs_dict["user_data"]["source_run_id"] == run_id
    assert vs_dict["user_data"]["data_type"] == "heat_flux_vectors"
    layer_ids = [layer["identifier"] for layer in vs_dict["geometry"]]
    assert "Fairyfly_Mesh_Outline" in layer_ids
    assert "Fairyfly_Heat_Flux_Vectors" in layer_ids
    vec_layer = next(
        layer for layer in vs_dict["geometry"] if layer["identifier"] == "Fairyfly_Heat_Flux_Vectors"
    )
    assert vec_layer["geometry"]
    assert vec_layer["geometry"][0]["type"] == "DisplayLineSegment3D"

    # Persisted VisualizationSet target + export to HTML, SVG, PNG, VTKJS
    vis_saved = _call_tool(
        mcp_server,
        "FF_To_Visualization_Set",
        garden_root=garden_root,
        source_kind="result",
        run_target=run_res["run_target"],
        data_type="heat_flux_vectors",
        name="slab_flux_vectors",
        return_visualization_set=False,
    )
    assert vis_saved["summary_view"]["source_run_id"] == run_id
    assert vis_saved["persistence_receipt"]["source"]["source_run_id"] == run_id
    assert vis_saved["persistence_receipt"]["source"]["data_type"] == "heat_flux_vectors"

    for fmt in ("html", "svg", "png", "vtkjs"):
        exp = _call_tool(
            mcp_server,
            "LB_Export_Visualization_Set",
            garden_root=garden_root,
            export_format=fmt,
            visualization_set_target=vis_saved["visualization_set_target"],
            name=f"slab_flux_vectors_{fmt}",
        )
        assert exp["report"]["status"] == "ok"
        out_path = Path(exp["artifact_receipt"]["absolute_path"])
        assert out_path.is_file()
        assert out_path.stat().st_size > 0

    # Scalar result also propagates source_run_id
    vis_temp = _call_tool(
        mcp_server,
        "FF_To_Visualization_Set",
        garden_root=garden_root,
        source_kind="result",
        run_id=run_id,
        data_type="temperature",
        return_visualization_set=True,
    )
    assert vis_temp["visualization_set"]["user_data"]["source_run_id"] == run_id
    assert vis_temp["summary_view"]["source_run_id"] == run_id
