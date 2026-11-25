"""Contract tests for bundled honeybee-gbas native GBAS2026 DWG export."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dragonfly.building import Building
from dragonfly.model import Model as DragonflyModel
from honeybee.model import Model as HoneybeeModel
from honeybee.room import Room
from ladybug_geometry.geometry3d import Face3D, Point3D

from garden.dragonfly_core.model_io import save_dragonfly_model
from garden.honeybee_core.model_io import save_honeybee_model
from garden.manifest import GardenManifest
from garden.model_export import FORMAT_GBAS_DWG, export_model_file
from garden.store import create_garden


class GbasDwgExportContractTests(unittest.TestCase):
    def test_extension_registration_and_license_bundle(self) -> None:
        import honeybee
        import honeybee_gbas

        pkg_root = Path(honeybee_gbas.__file__).resolve().parent
        self.assertIn("honeybee_gbas", honeybee.extensions)
        self.assertTrue((pkg_root / "LICENSE").is_file())
        self.assertTrue((pkg_root / "dwg" / "LICENSE-ezdwg.txt").is_file())

        room = Room.from_box("Room_1", 5.0, 4.0, 3.0)
        model = HoneybeeModel("contract_hb", [room])
        self.assertTrue(callable(getattr(model.to, "dwg", None)))
        self.assertTrue(hasattr(model.properties, "gbas"))
        self.assertEqual(model.check_for_extension("gbas", raise_exception=False), "")

    def test_export_model_file_honeybee_and_dragonfly_gbas_dwg(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            g_root = tmp_path / "gbas_garden"
            create_garden(name="gbas_contract", root_dir=str(g_root))
            manifest = GardenManifest.read(g_root)

            room = Room.from_box("Office_1", 5.0, 4.0, 3.0)
            wall = next(face for face in room.faces if str(face.type) == "Wall")
            wall.apertures_by_ratio(0.35)
            hb_model = HoneybeeModel("hb_contract", [room])
            hb_target, _ = save_honeybee_model(
                g_root,
                manifest,
                hb_model,
                name="hb_contract",
                set_base=True,
            )

            empty_hb = HoneybeeModel("empty_hb", [])
            empty_hb_target, _ = save_honeybee_model(
                g_root,
                manifest,
                empty_hb,
                name="empty_hb",
                set_base=False,
            )

            footprint = Face3D(
                [
                    Point3D(0.0, 0.0, 0.0),
                    Point3D(8.0, 0.0, 0.0),
                    Point3D(8.0, 6.0, 0.0),
                    Point3D(0.0, 6.0, 0.0),
                ]
            )
            building = Building.from_footprint("Bldg_1", [footprint], [3.5])
            df_model = DragonflyModel("df_contract", [building])
            df_target, _ = save_dragonfly_model(
                g_root,
                manifest,
                df_model,
                name="df_contract",
                set_base=True,
            )

            hb_res = export_model_file(
                garden_root=str(g_root),
                export_format=FORMAT_GBAS_DWG,
                model_target=hb_target,
                name="hb_out",
                include_body=True,
                export_options={"write_report": True},
            )
            self.assertNotIn("file_body", hb_res)
            self.assertTrue(
                any("include_body" in warning for warning in hb_res["report"]["warnings"])
            )
            hb_dwg = g_root / hb_res["target"]["path"]
            self.assertTrue(hb_dwg.is_file())
            self.assertTrue(hb_dwg.read_bytes().startswith(b"AC1015"))
            self.assertTrue(hb_res["summary_view"]["self_check_passed"])
            self.assertEqual(hb_res["summary_view"]["counts"]["rooms"], 1)
            self.assertGreaterEqual(hb_res["summary_view"]["counts"]["native_openings"], 1)

            report_file = g_root / hb_res["summary_view"]["report_path"]
            self.assertTrue(report_file.is_file())
            report_payload = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(report_payload["status"], "translated")
            self.assertTrue(report_payload["self_check"]["passed"])

            custom_res = export_model_file(
                garden_root=str(g_root),
                export_format=FORMAT_GBAS_DWG,
                model_target=hb_target,
                name="hb_custom",
                export_options={"report_path": "artifacts/custom/custom_gbas.report.json"},
            )
            self.assertEqual(
                custom_res["summary_view"]["report_path"],
                "artifacts/custom/custom_gbas.report.json",
            )
            self.assertTrue((g_root / "artifacts/custom/custom_gbas.report.json").is_file())

            with self.assertRaises(RuntimeError):
                export_model_file(
                    garden_root=str(g_root),
                    export_format=FORMAT_GBAS_DWG,
                    model_target=hb_target,
                    name="hb_out",
                    export_options={"overwrite": False},
                )

            with self.assertRaises(ValueError):
                export_model_file(
                    garden_root=str(g_root),
                    export_format=FORMAT_GBAS_DWG,
                    model_target=hb_target,
                    export_options={"report_path": str(tmp_path / "outside.json")},
                )

            with self.assertRaises(ValueError):
                export_model_file(
                    garden_root=str(g_root),
                    export_format=FORMAT_GBAS_DWG,
                    model_target=hb_target,
                    export_options={"report_path": "../outside.json"},
                )

            with self.assertRaises(ValueError):
                export_model_file(
                    garden_root=str(g_root),
                    export_format=FORMAT_GBAS_DWG,
                    model_target=hb_target,
                    export_options={"report_path": "artifacts/bad.txt"},
                )

            with self.assertRaises(RuntimeError):
                export_model_file(
                    garden_root=str(g_root),
                    export_format=FORMAT_GBAS_DWG,
                    model_target=empty_hb_target,
                    name="empty_out",
                )

            df_res = export_model_file(
                garden_root=str(g_root),
                export_format=FORMAT_GBAS_DWG,
                model_target=df_target,
                name="df_out",
            )
            self.assertEqual(df_res["summary_view"]["model_domain"], "dragonfly")
            self.assertTrue(df_res["summary_view"]["self_check_passed"])
            df_dwg = g_root / df_res["target"]["path"]
            self.assertTrue(df_dwg.is_file())
            self.assertTrue(df_dwg.read_bytes().startswith(b"AC1015"))


if __name__ == "__main__":
    unittest.main()
