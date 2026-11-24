"""Contract tests for bundled pyHygroThermFEM-Fairyfly native solver, provenance, and Gmsh mesher."""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import zipfile

from ladybug_geometry.geometry3d import Face3D, LineSegment3D, Point3D


class HygroThermSolverContractTests(unittest.TestCase):
    def test_verified_kernel_commit_and_extension_registration(self) -> None:
        import fairyfly
        import fairyfly_hygrotherm  # noqa: F401
        import garden.fairyfly.availability as avail
        from pyhygrothermfem_fairyfly._build_source import verified_kernel_commit

        commit = verified_kernel_commit()
        self.assertRegex(commit, r"^[0-9a-f]{40}$")
        self.assertNotEqual(commit, "0" * 40)
        self.assertIn("fairyfly_hygrotherm", fairyfly.extensions)

        with mock.patch.object(avail, "is_windows_platform", return_value=False):
            cfg = avail.therm_engine_config()
        self.assertTrue(cfg["available"])
        self.assertTrue(cfg["platform_supported"])
        self.assertEqual(cfg["mesher"], "gmsh")
        self.assertEqual(cfg["kernel_commit"], commit)

    def test_gmsh_steady_analytical_slab_roundtrip(self) -> None:
        import fairyfly_hygrotherm  # noqa: F401
        from fairyfly.boundary import Boundary
        from fairyfly.model import Model
        from fairyfly.shape import Shape
        from fairyfly_next_therm.condition.steadystate import SteadyState
        from fairyfly_next_therm.material.solid import SolidMaterial
        from fairyfly_next_therm.result import THMZResult
        from fairyfly_next_therm.run import run_thmz
        from fairyfly_next_therm.writer import model_to_thmz
        from garden.fairyfly.mesher import gmsh_mesh_to_xml

        mat = SolidMaterial(1.0)
        mat.display_name = "ContractSlab"
        shape = Shape(Face3D([Point3D(0, 0), Point3D(100, 0), Point3D(100, 100), Point3D(0, 100)]))
        shape.properties.therm.material = mat
        b_int = Boundary([LineSegment3D.from_end_points(Point3D(0, 0), Point3D(0, 100))])
        b_int.properties.therm.condition = SteadyState(20.0, 8.0, emissivity=0.0)
        b_int.properties.therm.u_factor_tag = "UF1"
        b_ext = Boundary([LineSegment3D.from_end_points(Point3D(100, 0), Point3D(100, 100))])
        b_ext.properties.therm.condition = SteadyState(0.0, 25.0, emissivity=0.0)
        model = Model([shape], [b_int, b_ext], units="Millimeters")

        with tempfile.TemporaryDirectory() as tmpdir:
            thmz_path = Path(tmpdir) / "slab.thmz"
            model_to_thmz(model, str(thmz_path), mesh_generator=gmsh_mesh_to_xml)
            run_thmz(str(thmz_path), silent=True)
            result = THMZResult(str(thmz_path))
            self.assertIsNotNone(result.u_factors)
            self.assertEqual(len(result.u_factors), 1)
            expected_u = 1.0 / (1.0 / 8.0 + 0.1 / 1.0 + 1.0 / 25.0)
            self.assertAlmostEqual(result.u_factors[0].total_u_factor, expected_u, delta=expected_u * 0.02)

    def test_gmsh_hygrothermal_transient_roundtrip(self) -> None:
        import fairyfly_hygrotherm  # noqa: F401
        from fairyfly.boundary import Boundary
        from fairyfly.model import Model
        from fairyfly.shape import Shape
        from fairyfly_next_therm.condition.transient import Transient
        from fairyfly_next_therm.material.hygrothermal import HygrothermalMaterial
        from fairyfly_next_therm.run import run_thmz
        from fairyfly_next_therm.simulation.mesh import MeshControl
        from fairyfly_next_therm.simulation.parameter import SimulationParameter
        from fairyfly_next_therm.simulation.transient import TransientCalculation
        from fairyfly_next_therm.writer import model_to_thmz
        from garden.fairyfly.mesher import gmsh_mesh_to_xml
        from pyhygrothermfem_fairyfly.transient_results import read_transient_series

        mat = HygrothermalMaterial(
            conductivity=0.8,
            density=1800.0,
            porosity=0.25,
            specific_heat=850.0,
            vapor_diffusion_resistance=12.0,
            moisture_storage_function=[(0.0, 0.0), (0.5, 45.0), (1.0, 130.0)],
        )
        mat.display_name = "ContractBrick"
        shape = Shape(Face3D([Point3D(0, 0), Point3D(100, 0), Point3D(100, 100), Point3D(0, 100)]))
        shape.properties.therm.material = mat

        b_int = Boundary([LineSegment3D.from_end_points(Point3D(0, 0), Point3D(0, 100))])
        b_int.display_name = "IntTransient"
        cond_int = Transient(
            bc_type="Transient",
            bc_model="Neumann",
            convection_model="Fixed Convection Coefficient",
            timesteps={
                1: {"temperature": 20.0, "humidity": 0.5, "film_coefficient": 8.0},
                2: {"temperature": 21.0, "humidity": 0.55, "film_coefficient": 8.0},
            },
        )
        cond_int.display_name = "IntTransientCond"
        b_int.properties.therm.condition = cond_int

        b_ext = Boundary([LineSegment3D.from_end_points(Point3D(100, 0), Point3D(100, 100))])
        b_ext.display_name = "ExtTransient"
        cond_ext = Transient(
            bc_type="Transient",
            bc_model="Neumann",
            convection_model="Fixed Convection Coefficient",
            timesteps={
                1: {"temperature": 5.0, "humidity": 0.8, "film_coefficient": 25.0},
                2: {"temperature": 4.0, "humidity": 0.85, "film_coefficient": 25.0},
            },
        )
        cond_ext.display_name = "ExtTransientCond"
        b_ext.properties.therm.condition = cond_ext

        model = Model([shape], [b_int, b_ext], units="Millimeters")
        sim_par = SimulationParameter(
            mesh=MeshControl(parameter=12, run_error_estimator=False),
            transient=TransientCalculation(
                timestep=3600,
                number_of_timesteps=2,
                initial_temperature=15.0,
                initial_humidity=0.5,
                simulate_moisture=True,
            ),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            thmz_path = Path(tmpdir) / "hygro.thmz"
            model_to_thmz(model, str(thmz_path), simulation_par=sim_par, mesh_generator=gmsh_mesh_to_xml)
            run_thmz(str(thmz_path), silent=True)

            with zipfile.ZipFile(thmz_path, "r") as archive:
                provenance = json.loads(archive.read("pyHygroTherm.json").decode("utf-8"))
                self.assertEqual(provenance["mode"], "hygrothermal-transient")
                hum = read_transient_series(archive.read("transient results/Humidities.csv"))
                water = read_transient_series(archive.read("transient results/WaterContent.csv"))
                self.assertEqual(len(hum["times"]), 3)
                self.assertEqual(len(water["times"]), 3)
                self.assertTrue(len(hum["entities"]) >= 4)


if __name__ == "__main__":
    unittest.main()
