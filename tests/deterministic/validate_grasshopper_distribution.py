"""Run in Rhino MCP's Python 3 after validate_distribution.py --keep.

Call validate(installation_record, evidence_directory). Uses a private canvas;
the existing document is restored and no user canvas is saved or edited.
"""

import json
import os
from pathlib import Path

import Grasshopper
import System
from Grasshopper.Kernel import GH_Document, GH_DocumentIO, GH_RuntimeMessageLevel
from Grasshopper.Kernel.Data import GH_Path
from Grasshopper.Kernel.Types import GH_Boolean, GH_String


def set_input(component, index, value):
    param = component.Params.Input[index]
    param.PersistentData.Clear()
    param.PersistentData.Append(value, GH_Path(0))
    param.ExpireSolution(False)
    component.ExpireSolution(False)


def values(component, index):
    return list(component.Params.Output[index].VolatileData.AllData(True))


def validate(record_path, evidence_directory):
    record_path = Path(record_path).resolve()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    evidence = Path(evidence_directory).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    assets = Path(record["grasshopper_dir"])
    manifest = json.loads((assets / "manifest.json").read_text(encoding="utf-8"))
    original = Grasshopper.Instances.ActiveCanvas.Document
    original_environment = System.Environment.GetEnvironmentVariable("LADYBUG_TOOLS_MCP_INSTALLATION")
    doc = GH_Document()
    loaded = None
    try:
        System.Environment.SetEnvironmentVariable("LADYBUG_TOOLS_MCP_INSTALLATION", str(record_path))
        Grasshopper.Instances.ActiveCanvas.Document = doc
        components = {}
        discovered = []
        for entry in manifest["components"]:
            matches = [proxy for proxy in Grasshopper.Instances.ComponentServer.ObjectProxies
                       if proxy.Desc.Name == entry["name"]
                       and Path(str(proxy.Location)).resolve() == (assets / entry["file"]).resolve()]
            assert len(matches) == 1, "Start Grasshopper after installation: " + entry["name"]
            component = matches[0].CreateInstance()
            discovered.append({"name": entry["name"], "location": str(matches[0].Location)})
            component.CreateAttributes()
            assert [p.NickName for p in component.Params.Input] == entry["inputs"]
            assert [p.NickName for p in component.Params.Output] == entry["outputs"]
            components[entry["name"]] = component
            doc.AddObject(component, False)
        create = components["FP Create Garden"]
        garden_path = Path(record["gardens_root"]) / "GH Native Verified"
        set_input(create, 0, GH_String("GH native verified"))
        set_input(create, 1, GH_String(str(garden_path)))
        set_input(create, 2, GH_Boolean(True))
        lister = components["FP Garden List"]
        set_input(lister, 0, GH_String(record["gardens_root"]))
        set_input(lister, 1, GH_Boolean(True))
        link = components["FP Honeybee Link"]
        link.Params.Input[0].AddSource(lister.Params.Output[0])
        # The prebuilt optional _write must already contain False.
        assert link.Params.Input[2].PersistentData.DataCount == 1
        doc.NewSolution(False)
        for component in (create, lister, link):
            assert not list(component.RuntimeMessages(GH_RuntimeMessageLevel.Error)), component.Name
        assert (garden_path / "garden.json").is_file()
        assert str(garden_path) == str(values(create, 1)[0])
        assert "Distribution acceptance" in [str(value) for value in values(lister, 2)]
        assert any("package_model" in str(value) for value in values(link, 0)), values(link, 0)

        proof = Grasshopper.Instances.ComponentServer.EmitObjectProxy(
            System.Guid("410755b1-224a-4c1e-a407-bf32fb45ea7e")).CreateInstance()
        proof.CreateAttributes()
        for param in proof.Params.Input:
            param.Optional = True
        proof.Params.Input[0].AddSource(link.Params.Output[0])
        proof.Code = '''import json
if x is not None:
    a=json.dumps({'identifier':x.identifier,'rooms':len(x.rooms),'area':x.floor_area,'volume':x.volume})
'''
        doc.AddObject(proof, False)
        doc.NewSolution(False)
        assert not list(proof.RuntimeMessages(GH_RuntimeMessageLevel.Error))
        readbacks = [json.loads(str(value)) for value in values(proof, 1)]
        model = next(item for item in readbacks if item["identifier"] == "package_model")
        assert model["rooms"] == 1 and model["area"] == 30 and model["volume"] == 90
        saved = evidence / "installed-components.gh"
        assert GH_DocumentIO(doc).SaveQuiet(str(saved))
        restored = GH_DocumentIO()
        assert restored.Open(str(saved))
        loaded = restored.Document
        for entry in manifest["components"]:
            component = next(obj for obj in loaded.Objects if obj.Name == entry["name"])
            assert [p.NickName for p in component.Params.Input] == entry["inputs"]
        Grasshopper.Instances.ActiveCanvas.Document = loaded
        loaded.Enabled = True
        loaded.NewSolution(True)
        restored_proof = next(obj for obj in loaded.Objects if obj.Code == proof.Code)
        restored_values = values(restored_proof, 1)
        assert any(json.loads(str(value)) == model for value in restored_values), {
            "values": [str(value) for value in restored_values],
            "errors": [str(message) for obj in loaded.Objects for message in obj.RuntimeMessages(GH_RuntimeMessageLevel.Error)],
        }
        result = {"status": "passed", "components": len(components), "garden": str(garden_path),
                  "readback": model, "saved_canvas": str(saved), "reopened": True,
                  "discovered_user_objects": discovered}
        (evidence / "grasshopper.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result))
        return result
    finally:
        Grasshopper.Instances.ActiveCanvas.Document = original
        System.Environment.SetEnvironmentVariable("LADYBUG_TOOLS_MCP_INSTALLATION", original_environment)
        if loaded is not None:
            loaded.Dispose()
        doc.Dispose()
