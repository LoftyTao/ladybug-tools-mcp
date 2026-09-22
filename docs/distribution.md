# Local distribution

Version 1.2.1 adds a Python terminal installer, a persistent uv-managed runtime, bundled Skills/weather, and six prebuilt Flowerpot Grasshopper user objects. This branch has not been published to PyPI. Do not advertise its PyPI command as available until publication succeeds.

## Install and configure

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), reopen your terminal, then run the fixed release:

```text
uvx --isolated --python 3.12 --prerelease allow ladybug-tools-mcp@1.2.1 install
```

The same wizard supports Windows, Linux, and macOS. `--isolated` keeps the bootstrap process outside the environment being upgraded. `--prerelease allow` is required by the pinned FastMCP beta. The command installs all Python dependencies, including an automatic pure-Python Luigi wheel build, before a client starts MCP. Initial downloads can be large because the existing scientific SDK dependency set is retained.

Options are available with `install --help`: `--tool-dir`, `--garden-dir`, `--codex-config`, `--skills-dir`, `--grasshopper`, `--grasshopper-dir`, `--generate-config`, and `--yes`. Automated installation still refuses conflicts; `--replace` explicitly backs up and replaces only the conflicting managed entries/files.

Defaults:

| Item | Location / behavior |
| --- | --- |
| Runtime | Native `uv tool dir`; the client launches the environment's absolute Python path. |
| Gardens | `~/LadybugTools/Gardens`, separate from runtime and cache. Existing Gardens stay at their paths. |
| Installation record | `~/.ladybug-tools-mcp/installation.json` |
| Codex | `$CODEX_HOME/config.toml`, otherwise `~/.codex/config.toml`; only `mcp_servers.ladybug-tools-mcp` is managed. |
| Local Skill | `~/.agents/skills/ladybug-tools-mcp-use` |
| Optional Flowerpot | `%APPDATA%/Grasshopper/UserObjects/Flowerpot` on Windows with Rhino 8. |

The installer leaves the client's tool-approval policy in place. For unattended acceptance, explicitly authorize `execute` in the isolated test profile using `tools.execute.approval_mode = "approve"`; ordinary interactive users approve calls in their client.

The installer preserves comments/unrelated Codex entries and records hashes of installed assets. Existing files receive timestamped `.ladybug-backup-*` backups when changed. `--generate-config` installs the runtime and prints TOML without changing client settings or local Skills. `--state` selects an independent installation record for tests; Flowerpot must receive the matching `LADYBUG_TOOLS_MCP_INSTALLATION` environment variable when using a non-default record.

Restart the client after configuration. Codex waits for this required server to initialize, with a 60-second startup timeout, before the first turn. If startup fails, repair the installation or disable this server in the client configuration. Restart Rhino/Grasshopper after installing or upgrading Flowerpot, then search `FP` or open the Flowerpot category. The six assets retain their filenames and current port names. Grasshopper assigns session proxy GUIDs when loading user objects; saved canvases embed the GhPython component and its script. Grasshopper's Ladybug Tools and optional Ironbug installation are separate prerequisites for their respective workflows.

## Other clients

Use the Python path and environment returned in the generated Codex configuration. No source-directory `cwd` is required. Replace all angle-bracket placeholders with actual values; JSON Windows paths need doubled backslashes or forward slashes.

Clients that use `mcpServers`:

```json
{
  "mcpServers": {
    "ladybug-tools-mcp": {
      "command": "<installed-python>",
      "args": ["-I", "-m", "ladybug_tools_mcp.server"],
      "env": {
        "LADYBUG_TOOLS_GARDENS_ROOT": "<garden-directory>",
        "LADYBUG_TOOLS_MCP_INSTALLATION": "<installation-record>"
      }
    }
  }
}
```

[OpenCode V2](https://opencode.ai/v2/docs/mcp-servers/) uses a different shape:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "skills": ["<installed-skills-directory>"],
  "mcp": {
    "servers": {
      "ladybug-tools-mcp": {
        "type": "local",
        "command": ["<installed-python>", "-I", "-m", "ladybug_tools_mcp.server"],
        "environment": {
          "LADYBUG_TOOLS_GARDENS_ROOT": "<garden-directory>",
          "LADYBUG_TOOLS_MCP_INSTALLATION": "<installation-record>"
        },
        "codemode": false,
        "timeout": {"startup": 60000}
      }
    }
  }
}
```

The server already exposes FastMCP's `search`, `get_schema`, and `execute`; disabling the client's additional Code Mode layer exposes these directly. MCP also serves the bundled Skill as resources. Codex local Skill discovery follows the [official Skills locations](https://learn.chatgpt.com/docs/build-skills).

## Upgrade, recovery, and removal

Versions never update automatically. Close MCP clients and Rhino, then run the new fixed version's installer. Repeating the same version reuses a healthy runtime and preserves unchanged settings. A local test wheel is identified by its SHA-256 so rebuilding the same development version still refreshes it.

If uv fails, resolve its download/permission error, close processes using the runtime, and rerun the same command. Configuration and asset writes occur only after runtime verification and are backed up/rolled back on a local write error. A failed environment replacement may require retrying installation; it does not roll back Python dependencies. Gardens are never part of replacement or removal.

```text
uvx --isolated --python 3.12 --prerelease allow ladybug-tools-mcp@1.2.1 status
uvx --isolated --python 3.12 --prerelease allow ladybug-tools-mcp@1.2.1 uninstall
```

Uninstall removes only unchanged managed integration files and restores the original Codex server entry where possible. Edited files/settings and Gardens remain. To relocate the runtime, uninstall first; Garden relocation is a separate explicit file-management operation. After `--generate-config`, manually copied client entries are user-managed.

## Platform and runtime boundary

The release targets Python 3.12, Windows x86_64, Linux x86_64, and macOS Apple Silicon for basic MCP/Garden/modeling/localhost preview. Windows is the primary native acceptance platform. Dependency wheel resolution alone is not native acceptance; inspect the three-platform Distribution CI results before publishing.

Flowerpot's first native matrix is Windows, Rhino 8 and Grasshopper 1 / IronPython 2. Fairyfly/THERM remains Windows-gated. Git is optional for creating Gardens and needed for Garden version history. External simulation engines are prepared per workflow; `LB_get_runtime_config` reports availability. Existing simulation tools remain in the MCP catalog.

Preview binds to localhost and keeps the existing vtk.js CDN dependency. Opening a viewer needs CDN access; keeping the MCP client connected keeps its preview server alive.

## Build and release

Build from a clean checkout with `uv build --sdist` and `uv build --wheel`. On Windows, building the wheel directly avoids a nested source-extraction path exceeding the Windows path limit; CI on Linux also rebuilds it from the source distribution. `setup.py` checks component versions and source/binary hashes, copies the canonical Skill and generated Grasshopper assets into the wheel, and rejects stale component builds. After editing component source, run `scripts/distribution/build_grasshopper.py` through Rhino MCP / Rhino Python 3 and commit all six `.ghuser` files plus `manifest.json` together. This generator leaves the current document/canvas untouched.

Resolve dependencies with:

```text
uv pip compile --universal --python-version 3.12 --prerelease allow requirements.in -o requirements.txt
```

Review the complete pinned graph when changing dependencies. The current FastMCP prereleases are intentional; avoid unrelated prerelease upgrades. Installation CI requires binary distributions for native dependencies and permits only the known pure-Python Luigi source build.

For a local, unpublished wheel, the same uvx bootstrap accepts its absolute path:

```text
uvx --isolated --python 3.12 --prerelease allow --from <absolute-wheel-path> ladybug-tools-mcp install --wheel <absolute-wheel-path>
```

For maintaining a reusable test runner, use a separate bootstrap environment:

```text
uv venv --python 3.12 .distribution-runner
uv pip install --python <bootstrap-python> --prerelease allow dist/ladybug_tools_mcp-1.2.1-py3-none-any.whl
<bootstrap-python> -I -m ladybug_tools_mcp_cli install --wheel dist/ladybug_tools_mcp-1.2.1-py3-none-any.whl
```

`<bootstrap-python>` is `.distribution-runner/Scripts/python.exe` on Windows or `.distribution-runner/bin/python` on POSIX. The deterministic check uses isolated client/Skill/state directories and real stdio:

```text
<bootstrap-python> -I tests/deterministic/validate_distribution.py --wheel dist/ladybug_tools_mcp-1.2.1-py3-none-any.whl --root <new-test-directory>
```

It checks package resources, generated configuration, repeat install, MCP discovery, Garden/model creation, validation, geometry readback, localhost HTTP, conflict protection, backup, and uninstall preservation. Native Grasshopper and natural-language Agent acceptance are additional release checks. Use OpenCode2's current listed free model, an explicit session title, and native JSON execution records; unavailable free models are a test-environment limitation and never trigger paid fallback. Use Codex for full Agent acceptance and independently inspect the persisted model.

`.github/workflows/distribution.yml` builds once, tests the same wheel on three OS runners, and publishes the downloaded artifact only for a version-matching tag after all checks pass. The GitHub `pypi` environment requires approval from `LoftyTao` and permits only `v*` tags. Confirm native Grasshopper and Agent evidence before approving that environment.

For the first publication, the PyPI account owner must sign in and add a [pending Trusted Publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) at [account publishing settings](https://pypi.org/manage/account/publishing/), using these exact public values:

| Field | Value |
| --- | --- |
| PyPI project name | `ladybug-tools-mcp` |
| GitHub owner | `LoftyTao` |
| Repository | `ladybug-tools-mcp` |
| Workflow filename | `distribution.yml` |
| Environment | `pypi` |

This configuration does not publish a package or reserve its name. No long-lived PyPI token is needed. Once acceptance and review are complete, merge the reviewed change, tag that commit `v1.2.1`, and approve its successful Distribution run's `pypi` job. Verify the published artifact's SHA-256 against the tested CI artifact, then perform a fresh PyPI install with the documented fixed-version command before marking the ADR delivered.

### 1.2.1 release notes

- Adds a unified terminal wizard and a persistent Python 3.12 runtime managed by uv.
- Bundles operation Skills, weather resources, and six prebuilt Flowerpot user objects; Grasshopper integration is optional and requires Windows/Rhino 8.
- Configures Codex and local Skills or prints configuration for manual setup. Existing user changes require explicit replacement and receive backups.
- Keeps Gardens outside the installation and preserves them during reinstall and uninstall. Upgrades are explicit and version-pinned.
- Keeps localhost preview and its vtk.js CDN requirement. Git history, simulation engines, Rhino, and Ironbug retain their documented prerequisites.

The support evidence and any remaining release conditions are recorded in [distribution acceptance](distribution-acceptance.md).

Legacy source-pasted canvases (1.2.0 and earlier) still require their existing `LADYBUG_TOOLS_MCP_SRC` source location. To migrate one, point that variable at the installed `package_root` from the installation record and restart Rhino, or replace the embedded components with the newly installed versions. Installing a `.ghuser` never silently rewrites scripts embedded in saved user canvases.
