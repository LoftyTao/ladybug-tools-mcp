"""Run through Rhino MCP / Rhino Python 3 to build the six Flowerpot user objects.

No active document, canvas, or user-object installation is changed.
"""

import ast
import hashlib
import json
from pathlib import Path
import re

import System
import Grasshopper
from Grasshopper.Kernel import GH_UserObject, GH_Exposure, GH_ParamAccess
from Grasshopper.Kernel.Parameters import Param_GenericObject, Param_ScriptVariable
from Grasshopper.Kernel.Types import GH_Boolean
from Grasshopper.Kernel.Data import GH_Path


ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "src" / "grasshopper_components"
OUTPUT = SOURCES / "user_objects"
SCRIPT_GUID = System.Guid("410755b1-224a-4c1e-a407-bf32fb45ea7e")
VERSION = re.search(r'__version__ = "([^"]+)"', (ROOT / "src/ladybug_tools_mcp/__init__.py").read_text()).group(1)


def port_descriptions(text):
    result = []
    for line in text.splitlines():
        match = re.match(r"\s+([A-Za-z_]\w*):\s*(.*)", line)
        if match:
            result.append([match.group(1), match.group(2)])
        elif line.strip() and result:
            result[-1][1] += " " + line.strip()
    return result


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    entries = []
    for path in sorted(SOURCES.glob("FP *.py")):
        source = path.read_text(encoding="utf-8")
        module = ast.parse(source)
        doc = ast.get_docstring(module)
        arguments, returns = doc.split("Args:", 1)[1].split("Returns:", 1)
        inputs = port_descriptions(arguments)
        outputs = port_descriptions(returns)
        properties, optional = {}, {}
        for node in ast.walk(module):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = ast.unparse(node.targets[0])
            if target.startswith("ghenv.Component."):
                match = re.fullmatch(r"ghenv\.Component\.Params\.Input\[(\d+)\]\.Optional", target)
                if match:
                    optional[int(match.group(1))] = ast.literal_eval(node.value)
                elif target.count(".") == 2:
                    properties[target.rsplit(".", 1)[1]] = ast.literal_eval(node.value)
        component = Grasshopper.Instances.ComponentServer.EmitObjectProxy(SCRIPT_GUID).CreateInstance()
        component.CreateAttributes()
        component.HiddenCodeInput = True
        component.HiddenOutOutput = True
        for param in list(component.Params.Input):
            component.Params.UnregisterInputParameter(param, True)
        for param in list(component.Params.Output):
            component.Params.UnregisterOutputParameter(param, True)
        for index, (name, description) in enumerate(inputs):
            param = Param_ScriptVariable()
            param.Name = param.NickName = name
            param.Description = description
            param.Access = GH_ParamAccess.item
            param.Optional = optional[index]
            if optional[index] and name in {"_write", "follow_", "refresh_"}:
                param.PersistentData.Append(GH_Boolean(False), GH_Path(0))
            component.Params.RegisterInputParam(param)
        for name, description in outputs:
            param = Param_GenericObject()
            param.Name = param.NickName = name
            param.Description = description
            component.Params.RegisterOutputParam(param)
        component.Params.OnParametersChanged()
        component.Code = source
        component.Description = doc.split("Args:", 1)[0].strip()
        for key, value in properties.items():
            setattr(component, key, value)
        assert component.Message == VERSION
        user_object = GH_UserObject()
        user_object.BaseGuid = component.ComponentGuid
        user_object.Icon = component.Icon_24x24
        user_object.Exposure = GH_Exposure.primary
        user_object.Description.Name = component.Name
        user_object.Description.NickName = component.NickName
        user_object.Description.Description = component.Description
        user_object.Description.Category = component.Category
        user_object.Description.SubCategory = component.SubCategory
        user_object.SetDataFromObject(component)
        destination = OUTPUT / (path.stem + ".ghuser")
        user_object.Path = str(destination)
        assert user_object.SaveToFile(), destination
        restored = GH_UserObject(str(destination)).InstantiateObject()
        assert [p.NickName for p in restored.Params.Input] == [p[0] for p in inputs]
        assert [p.NickName for p in restored.Params.Output] == [p[0] for p in outputs]
        entries.append({
            "name": path.stem, "file": destination.name,
            "inputs": [p[0] for p in inputs], "outputs": [p[0] for p in outputs],
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        })
    assert len(entries) == 6
    (OUTPUT / "manifest.json").write_text(json.dumps({"version": VERSION, "components": entries}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"version": VERSION, "output": str(OUTPUT), "components": [entry["name"] for entry in entries]}))


if __name__ == "__main__":
    build()
