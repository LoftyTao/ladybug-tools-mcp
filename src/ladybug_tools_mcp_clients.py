"""MCP configuration fragments and import instructions; rendering never edits clients."""

from copy import deepcopy
import json
from pathlib import Path

SERVER_NAME = "lbt-mcp"

CLIENTS = {
    "codex": {
        "label": "Codex",
        "format": "toml",
        "docs": "https://learn.chatgpt.com/docs/extend/mcp?surface=cli",
        "instructions": "Merge mcp_servers.lbt-mcp into $CODEX_HOME/config.toml (default ~/.codex/config.toml). The installer can configure Codex and its local Skill with backups and conflict protection."
    },
    "claude-code": {
        "label": "Claude Code",
        "format": "json",
        "docs": "https://code.claude.com/docs/en/mcp",
        "instructions": "Merge mcpServers.lbt-mcp into project .mcp.json, or pass ONLY its inner server object to claude mcp add-json --scope user lbt-mcp. Do not replace ~/.claude.json. Copy the bundled Skill to ~/.claude/skills if needed."
    },
    "gemini": {
        "label": "Gemini CLI",
        "format": "json",
        "docs": "https://geminicli.com/docs/tools/mcp-server/",
        "instructions": "Merge the mcpServers entry into ~/.gemini/settings.json for user scope, or .gemini/settings.json for a project. The official gemini mcp add command can perform the import."
    },
    "opencode": {
        "label": "OpenCode 1",
        "format": "json",
        "docs": "https://opencode.ai/docs/mcp-servers/",
        "instructions": "Merge mcp.lbt-mcp into the active OpenCode 1 config (normally ~/.config/opencode/opencode.json or opencode.jsonc). Append skills.paths to existing paths. OpenCode generations may share a file; do not overwrite other servers or convert the whole file."
    },
    "opencode2": {
        "label": "OpenCode 2",
        "format": "json",
        "docs": "https://opencode.ai/v2/docs/mcp-servers",
        "instructions": "Tested @opencode/cli 2.0.12 format: merge mcp.lbt-mcp into the active OpenCode 2 config and append the supplied skills entry. OpenCode generations may share a file. Use opencode2-native only after verifying that client's native V2 schema."
    },
    "opencode2-native": {
        "label": "OpenCode 2 (native schema, experimental)",
        "format": "json",
        "docs": "https://opencode.ai/v2/docs/mcp-servers",
        "instructions": "Experimental export only. The fragment follows the current mcp.servers schema, but this repository has not verified it against every OpenCode 2 release. Inspect the installed schema and merge it manually before use."
    },
    "hermes": {
        "label": "Hermes Agent",
        "format": "yaml",
        "docs": "https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/mcp.md",
        "instructions": "Merge mcp_servers.lbt-mcp into the active Hermes config.yaml (default ~/.hermes/config.yaml). Connect with hermes mcp test lbt-mcp. Copy the bundled Skill to the selected profile's skills directory, normally ~/.hermes/skills."
    },
    "deepseek-harness": {
        "label": "DeepSeek Harness",
        "format": "yaml",
        "docs": "https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md",
        "instructions": "Merge this insert row into $DSH_HOME/cordis.patch.yml (default ~/.dsh/cordis.patch.yml), or the active profile's cordis.patch.yml. Confirm the profile resolves @deepseek-ai/dsh-mcp-client, then restart that profile. Its filesystem Skill provider scans ~/.agents/skills by default; copy the bundled Skill there if needed."
    },
    "openclaw": {
        "label": "OpenClaw",
        "format": "json",
        "docs": "https://docs.openclaw.ai/tools/mcp",
        "instructions": "Merge mcp.servers.lbt-mcp into the file reported by openclaw config file --json (normally ~/.openclaw/openclaw.json). Run openclaw mcp doctor lbt-mcp --probe; static status is not a connection test. Use the active state-dir/skills for the bundled Skill. Do not also register it in mcporter."
    },
    "zcode": {
        "label": "ZCode",
        "format": "json",
        "docs": "https://zcode.z.ai/en/docs/mcp-services",
        "instructions": "Merge mcp.servers.lbt-mcp into ~/.zcode/cli/config.json. For the desktop import dialog, paste ONLY the inner mcp.servers map. Check that native configuration does not hide existing .agents/mcp.json servers. Copy the bundled Skill to ~/.zcode/skills."
    },
    "kimi-code": {
        "label": "Kimi Code",
        "format": "json",
        "docs": "https://moonshotai.github.io/kimi-code/en/customization/mcp.html",
        "instructions": "Merge this mcpServers fragment into $KIMI_CODE_HOME/mcp.json (normally ~/.kimi-code/mcp.json). Use the current Kimi Code /mcp-config and /mcp checks; do not write the archived ~/.kimi configuration."
    },
    "devin-cli": {
        "label": "Devin CLI",
        "format": "json",
        "docs": "https://docs.devin.ai/cli/extensibility/mcp/configuration",
        "instructions": "Merge mcpServers.lbt-mcp into user mcp_config.json: %APPDATA%/devin/mcp_config.json on Windows, ~/.config/devin/mcp_config.json on macOS/Linux. Older clients used config.json; verify the version. The CLI alternative is devin mcp add -s user lbt-mcp -- <python> -I -m ladybug_tools_mcp.server with the supplied environment."
    },
    "devin-cloud": {
        "label": "Devin Cloud",
        "format": "text",
        "docs": "https://docs.devin.ai/work-with-devin/mcp",
        "instructions": "Cloud setup guide only. In Devin Cloud open Customize > MCPs, choose STDIO, and install lbt-mcp inside the Devin runtime with its own paths and credentials. A local absolute Python path and localhost do not refer to the cloud runtime; this preset never submits or writes cloud settings."
    },
    "qoder": {
        "label": "Qoder",
        "format": "json",
        "docs": "https://docs.qoder.com/cli/mcp-reference",
        "instructions": "Merge this mcpServers fragment into the Qoder CLI user settings.json (normally ~/.qoder/settings.json), or use the Qoder MCP import/deeplink. Keep trust and permission fields from the existing configuration."
    },
    "qoder-cn": {
        "label": "Qoder CN",
        "format": "json",
        "docs": "https://docs.qoder.cn/en/cli/settings-reference",
        "instructions": "Merge this mcpServers fragment into the Qoder CN user settings.json (normally ~/.qoder-cn/settings.json) only after checking that the installed client is the CN variant. Do not write both regional configuration files."
    },
    "codebuddy": {
        "label": "CodeBuddy Code CLI",
        "format": "json",
        "docs": "https://www.codebuddy.cn/docs/cli/mcp",
        "instructions": "Merge mcpServers.lbt-mcp into the active user config (preferred ~/.codebuddy/.mcp.json, older ~/.codebuddy/mcp.json or ~/.codebuddy.json). A new higher-priority file can hide old servers. For codebuddy mcp add-json --scope user, pass ONLY the inner server object. Copy the bundled Skill to ~/.codebuddy/skills."
    },
    "codebuddy-ide": {
        "label": "CodeBuddy IDE",
        "format": "json",
        "docs": "https://www.codebuddy.ai/docs/ide/User-guide/MCP",
        "instructions": "Use Settings > MCP in CodeBuddy IDE and import this mcpServers fragment. A stable IDE configuration file path was not verified, so this preset does not edit CodeBuddy CLI files."
    },
    "workbuddy": {
        "label": "WorkBuddy",
        "format": "json",
        "docs": "https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/MCP-Guide",
        "instructions": "Merge this mcpServers fragment into ~/.workbuddy/mcp.json or the selected project's .workbuddy/mcp.json. Open 插件 > MCP 服务器 > 配置 MCP and verify the connection; WorkBuddy Skills are managed separately through its supported import or marketplace flow."
    },
    "cline": {
        "label": "Cline",
        "format": "json",
        "docs": "https://docs.cline.bot/mcp/mcp-overview",
        "instructions": "Open the installed Cline client's MCP settings and merge mcpServers.lbt-mcp there. CLI and extension profiles have different storage paths; use the client to locate its configuration. Copy the bundled Skill to ~/.cline/skills if supported."
    },
    "cursor": {
        "label": "Cursor",
        "format": "json",
        "docs": "https://cursor.com/help/customization/mcp",
        "instructions": "Merge this mcpServers fragment into ~/.cursor/mcp.json for user scope or .cursor/mcp.json for a project, then reload Cursor. Preserve existing servers and project overrides."
    },
    "vscode": {
        "label": "Visual Studio Code",
        "format": "json",
        "docs": "https://code.visualstudio.com/docs/agents/reference/mcp-configuration",
        "instructions": "Use VS Code's MCP: Open User Configuration command or merge servers.lbt-mcp into .vscode/mcp.json. This is an MCP file, not the editor's settings.json. Other Copilot hosts may use a different schema."
    },
    "generic": {
        "label": "Generic MCP client",
        "format": "json",
        "docs": "https://modelcontextprotocol.io/docs",
        "instructions": "Merge the mcpServers fragment into the target client's stdio configuration. Confirm its top-level key, scope, and command schema before importing; this generic export does not claim to cover every client."
    }
}


def render_client(client_id: str, server: dict, skill_source: Path) -> str:
    """Render one preset from the installed runtime's command and Skills root."""
    if client_id not in CLIENTS:
        raise ValueError(f"Unknown MCP client preset: {client_id}")
    if client_id == "devin-cloud":
        return (
            "# Devin Cloud setup\n\n"
            "1. Open Customize > MCPs in the target organization and choose STDIO.\n"
            "2. Prepare uv and the chosen fixed lbt-mcp release inside Devin's runtime.\n"
            "3. Use that runtime's Python with -I -m ladybug_tools_mcp.server, and set\n"
            "   LADYBUG_TOOLS_GARDENS_ROOT and LADYBUG_TOOLS_MCP_INSTALLATION to its paths.\n"
            "4. Test the MCP tools from a Devin session.\n\n"
            "Local Python paths, localhost previews and Grasshopper are not cloud paths.\n"
            "This guide does not create cloud settings or expose a network endpoint.\n"
        )
    if client_id == "codex":
        import tomlkit
        return tomlkit.dumps({"mcp_servers": {SERVER_NAME: deepcopy(server)}})

    # Only shared stdio fields cross client boundaries; Codex flags stay in Codex.
    entry = {key: deepcopy(server[key]) for key in ("command", "args", "env")}
    if client_id in {"opencode", "opencode2", "opencode2-native"}:
        local = {
            "type": "local",
            "command": [entry["command"], *entry["args"]],
            "environment": entry["env"],
            "timeout": 120000,
        }
        skills = [str(skill_source)]
        if client_id == "opencode2-native":
            local["timeout"] = {"catalog": 120000, "execution": 120000}
            config = {"mcp": {"servers": {SERVER_NAME: local}}, "skills": skills}
        else:
            config = {"mcp": {SERVER_NAME: local},
                      "skills": {"paths": skills} if client_id == "opencode" else skills}
    elif client_id == "hermes":
        import yaml
        return yaml.safe_dump({"mcp_servers": {SERVER_NAME: entry}},
                              allow_unicode=True, sort_keys=False)
    elif client_id == "deepseek-harness":
        import yaml
        return yaml.safe_dump([{"insert": [{"id": "mcp-lbt-mcp",
                                           "name": "@deepseek-ai/dsh-mcp-client",
                                           "config": {"serverName": SERVER_NAME,
                                                      "transport": "stdio", **entry}}]}],
                              allow_unicode=True, sort_keys=False)
    elif client_id in {"openclaw", "zcode"}:
        if client_id == "zcode":
            entry["type"] = "stdio"
        config = {"mcp": {"servers": {SERVER_NAME: entry}}}
    elif client_id == "vscode":
        config = {"servers": {SERVER_NAME: {"type": "stdio", **entry}}}
    else:
        config = {"mcpServers": {SERVER_NAME: entry}}
    return json.dumps(config, ensure_ascii=False, indent=2) + "\n"
