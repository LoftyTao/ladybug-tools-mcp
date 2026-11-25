use std::collections::BTreeMap;
use std::env;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode};

enum JsonVal {
    Object(BTreeMap<String, JsonVal>),
    Str(String),
    Other,
}

struct JsonParser<'a> {
    bytes: &'a [u8],
    pos: usize,
}

impl<'a> JsonParser<'a> {
    fn new(input: &'a str) -> Self {
        let mut s = input;
        if let Some(stripped) = s.strip_prefix('\u{feff}') {
            s = stripped;
        }
        Self {
            bytes: s.as_bytes(),
            pos: 0,
        }
    }

    fn skip_ws(&mut self) {
        while self.pos < self.bytes.len() {
            match self.bytes[self.pos] {
                b' ' | b'\t' | b'\r' | b'\n' => self.pos += 1,
                _ => break,
            }
        }
    }

    fn peek(&mut self) -> Option<u8> {
        self.skip_ws();
        self.bytes.get(self.pos).copied()
    }

    fn parse_value(&mut self) -> Result<JsonVal, String> {
        match self.peek() {
            Some(b'{') => self.parse_object(),
            Some(b'[') => self.parse_array(),
            Some(b'"') => self.parse_string().map(JsonVal::Str),
            Some(b't') => self.expect_literal(b"true").map(|_| JsonVal::Other),
            Some(b'f') => self.expect_literal(b"false").map(|_| JsonVal::Other),
            Some(b'n') => self.expect_literal(b"null").map(|_| JsonVal::Other),
            Some(c) if c == b'-' || c.is_ascii_digit() => self.parse_number().map(|_| JsonVal::Other),
            Some(c) => Err(format!("unexpected JSON token byte 0x{c:02x} at {}", self.pos)),
            None => Err("unexpected end of JSON".to_string()),
        }
    }

    fn expect_literal(&mut self, lit: &[u8]) -> Result<(), String> {
        self.skip_ws();
        if self.bytes[self.pos..].starts_with(lit) {
            self.pos += lit.len();
            Ok(())
        } else {
            Err(format!("invalid JSON literal at {}", self.pos))
        }
    }

    fn parse_number(&mut self) -> Result<(), String> {
        self.skip_ws();
        let start = self.pos;
        while self.pos < self.bytes.len() {
            match self.bytes[self.pos] {
                b'-' | b'+' | b'.' | b'e' | b'E' | b'0'..=b'9' => self.pos += 1,
                _ => break,
            }
        }
        if self.pos == start {
            return Err(format!("invalid JSON number at {}", self.pos));
        }
        Ok(())
    }

    fn parse_hex4(&mut self) -> Result<u16, String> {
        if self.pos + 4 > self.bytes.len() {
            return Err("truncated unicode escape in JSON".to_string());
        }
        let hex = std::str::from_utf8(&self.bytes[self.pos..self.pos + 4])
            .map_err(|_| "invalid UTF-8 in unicode escape".to_string())?;
        self.pos += 4;
        u16::from_str_radix(hex, 16).map_err(|_| format!("invalid hex escape \\u{hex}"))
    }

    fn parse_string(&mut self) -> Result<String, String> {
        self.skip_ws();
        if self.bytes.get(self.pos) != Some(&b'"') {
            return Err(format!("expected '\"' at {}", self.pos));
        }
        self.pos += 1;
        let mut out = String::new();
        while self.pos < self.bytes.len() {
            let b = self.bytes[self.pos];
            if b == b'"' {
                self.pos += 1;
                return Ok(out);
            }
            if b == b'\\' {
                self.pos += 1;
                if self.pos >= self.bytes.len() {
                    return Err("unterminated JSON escape".to_string());
                }
                let esc = self.bytes[self.pos];
                self.pos += 1;
                match esc {
                    b'"' => out.push('"'),
                    b'\\' => out.push('\\'),
                    b'/' => out.push('/'),
                    b'b' => out.push('\u{0008}'),
                    b'f' => out.push('\u{000c}'),
                    b'n' => out.push('\n'),
                    b'r' => out.push('\r'),
                    b't' => out.push('\t'),
                    b'u' => {
                        let code = self.parse_hex4()?;
                        if (0xD800..=0xDBFF).contains(&code) {
                            if self.bytes.get(self.pos..self.pos + 2) != Some(b"\\u") {
                                return Err("unpaired UTF-16 high surrogate in JSON".to_string());
                            }
                            self.pos += 2;
                            let low = self.parse_hex4()?;
                            if !(0xDC00..=0xDFFF).contains(&low) {
                                return Err("invalid UTF-16 low surrogate in JSON".to_string());
                            }
                            let cp = 0x10000 + (((code as u32 - 0xD800) << 10) | (low as u32 - 0xDC00));
                            let ch = char::from_u32(cp)
                                .ok_or_else(|| "invalid unicode scalar value".to_string())?;
                            out.push(ch);
                        } else {
                            let ch = char::from_u32(code as u32)
                                .ok_or_else(|| "invalid unicode escape".to_string())?;
                            out.push(ch);
                        }
                    }
                    other => return Err(format!("unsupported escape \\{}", other as char)),
                }
            } else {
                let rest = std::str::from_utf8(&self.bytes[self.pos..])
                    .map_err(|_| "invalid UTF-8 in JSON string".to_string())?;
                let ch = rest.chars().next().ok_or_else(|| "unexpected EOF".to_string())?;
                self.pos += ch.len_utf8();
                out.push(ch);
            }
        }
        Err("unterminated JSON string".to_string())
    }

    fn parse_array(&mut self) -> Result<JsonVal, String> {
        self.skip_ws();
        self.pos += 1; // '['
        if self.peek() == Some(b']') {
            self.pos += 1;
            return Ok(JsonVal::Other);
        }
        loop {
            let _ = self.parse_value()?;
            match self.peek() {
                Some(b',') => self.pos += 1,
                Some(b']') => {
                    self.pos += 1;
                    return Ok(JsonVal::Other);
                }
                _ => return Err(format!("expected ',' or ']' at {}", self.pos)),
            }
        }
    }

    fn parse_object(&mut self) -> Result<JsonVal, String> {
        self.skip_ws();
        self.pos += 1; // '{'
        let mut map = BTreeMap::new();
        if self.peek() == Some(b'}') {
            self.pos += 1;
            return Ok(JsonVal::Object(map));
        }
        loop {
            let key = self.parse_string()?;
            if self.peek() != Some(b':') {
                return Err(format!("expected ':' at {}", self.pos));
            }
            self.pos += 1;
            let val = self.parse_value()?;
            map.insert(key, val);
            match self.peek() {
                Some(b',') => self.pos += 1,
                Some(b'}') => {
                    self.pos += 1;
                    return Ok(JsonVal::Object(map));
                }
                _ => return Err(format!("expected ',' or '}}' at {}", self.pos)),
            }
        }
    }
}

fn parse_json_object(raw: &str) -> Result<BTreeMap<String, JsonVal>, String> {
    let mut parser = JsonParser::new(raw);
    match parser.parse_value()? {
        JsonVal::Object(map) => Ok(map),
        _ => Err("current.json root must be a JSON object".to_string()),
    }
}

fn get_str_field<'a>(map: &'a BTreeMap<String, JsonVal>, key: &str) -> Option<&'a str> {
    match map.get(key) {
        Some(JsonVal::Str(s)) if !s.trim().is_empty() => Some(s.trim()),
        _ => None,
    }
}

fn resolve_under_home(home: &Path, raw: &str) -> PathBuf {
    let mut normalized = raw.to_string();
    if cfg!(windows) {
        normalized = normalized.replace('/', "\\");
    }
    let p = Path::new(&normalized);
    if p.is_absolute() {
        p.to_path_buf()
    } else {
        home.join(p)
    }
}

fn python_exe_name() -> &'static str {
    if cfg!(windows) {
        "python.exe"
    } else {
        "python"
    }
}

fn find_bundled_python_home(home: &Path, meta: &BTreeMap<String, JsonVal>) -> Option<PathBuf> {
    if let Some(raw) = get_str_field(meta, "python_home") {
        let candidate = resolve_under_home(home, raw);
        if candidate.join(python_exe_name()).is_file() {
            return Some(candidate);
        }
    }
    let py_root = home.join("runtimes").join("python");
    if py_root.join(python_exe_name()).is_file() {
        return Some(py_root);
    }
    if let Ok(entries) = fs::read_dir(&py_root) {
        let mut candidates: Vec<PathBuf> = entries
            .filter_map(|e| e.ok().map(|item| item.path()))
            .filter(|p| p.is_dir() && p.join(python_exe_name()).is_file())
            .collect();
        candidates.sort();
        if let Some(first) = candidates.into_iter().next() {
            return Some(first);
        }
    }
    None
}

fn normalize_path_cmp(p: &str) -> String {
    let trimmed = p.trim();
    if cfg!(windows) {
        trimmed.replace('/', "\\").to_ascii_lowercase()
    } else {
        trimmed.to_string()
    }
}

fn ensure_relocated_pyvenv_cfg(home: &Path, python_path: &Path, meta: &BTreeMap<String, JsonVal>) {
    let Some(scripts_dir) = python_path.parent() else {
        return;
    };
    let Some(venv_dir) = scripts_dir.parent() else {
        return;
    };
    if !venv_dir.starts_with(home) {
        return;
    }
    let cfg_path = venv_dir.join("pyvenv.cfg");
    if !cfg_path.is_file() {
        return;
    }
    let Some(target_py_home) = find_bundled_python_home(home, meta) else {
        return;
    };
    let target_py_exe = target_py_home.join(python_exe_name());
    let Ok(content) = fs::read_to_string(&cfg_path) else {
        return;
    };

    let target_home_str = target_py_home.to_string_lossy().into_owned();
    let target_exe_str = target_py_exe.to_string_lossy().into_owned();

    let mut changed = false;
    let mut saw_home = false;
    let mut saw_exe = false;
    let mut lines: Vec<String> = Vec::new();
    for line in content.lines() {
        if let Some((k, v)) = line.split_once('=') {
            let key_trim = k.trim();
            if key_trim == "home" {
                saw_home = true;
                if normalize_path_cmp(v) != normalize_path_cmp(&target_home_str) {
                    changed = true;
                }
                lines.push(format!("home = {target_home_str}"));
                continue;
            }
            if key_trim == "executable" {
                saw_exe = true;
                if normalize_path_cmp(v) != normalize_path_cmp(&target_exe_str) {
                    changed = true;
                }
                lines.push(format!("executable = {target_exe_str}"));
                continue;
            }
        }
        lines.push(line.to_string());
    }
    if !saw_home {
        changed = true;
        lines.insert(0, format!("home = {target_home_str}"));
    }
    if !saw_exe {
        changed = true;
        lines.push(format!("executable = {target_exe_str}"));
    }
    if !changed {
        return;
    }

    let mut updated = lines.join("\n");
    updated.push('\n');
    let tmp_path = venv_dir.join(".pyvenv.cfg.tmp");
    if let Ok(mut file) = fs::File::create(&tmp_path) {
        if file.write_all(updated.as_bytes()).is_ok() && file.sync_all().is_ok() {
            drop(file);
            let _ = fs::rename(&tmp_path, &cfg_path);
        } else {
            let _ = fs::remove_file(&tmp_path);
        }
    }
}

fn resolve_target_python(home: &Path, meta: &BTreeMap<String, JsonVal>) -> Option<PathBuf> {
    if let Some(raw) = get_str_field(meta, "python") {
        let p = resolve_under_home(home, raw);
        if p.is_file() {
            return Some(p);
        }
    }
    if let Some(rel) = get_str_field(meta, "release_dir") {
        let base = resolve_under_home(home, rel);
        for candidate in [
            base.join("venv").join("Scripts").join("python.exe"),
            base.join("venv").join("bin").join("python"),
        ] {
            if candidate.is_file() {
                return Some(candidate);
            }
        }
    }
    if let Some(ver) = get_str_field(meta, "version") {
        let base = home.join("app").join("releases").join(ver);
        for candidate in [
            base.join("venv").join("Scripts").join("python.exe"),
            base.join("venv").join("bin").join("python"),
        ] {
            if candidate.is_file() {
                return Some(candidate);
            }
        }
    }
    None
}

fn run() -> Result<i32, String> {
    let exe = env::current_exe().map_err(|e| format!("failed to locate launcher executable: {e}"))?;
    let bin_dir = exe
        .parent()
        .ok_or_else(|| "launcher executable has no parent directory".to_string())?;
    let home = bin_dir
        .parent()
        .ok_or_else(|| "launcher bin directory has no parent home directory".to_string())?
        .to_path_buf();

    let current_json_path = home.join("app").join("current.json");
    let raw = fs::read_to_string(&current_json_path).map_err(|e| {
        format!(
            "failed to read {}: {e}",
            current_json_path.to_string_lossy()
        )
    })?;
    let meta = parse_json_object(&raw)?;
    let python = resolve_target_python(&home, &meta).ok_or_else(|| {
        format!(
            "target python executable missing from {}",
            current_json_path.to_string_lossy()
        )
    })?;

    ensure_relocated_pyvenv_cfg(&home, &python, &meta);

    let mut cmd = Command::new(&python);
    cmd.arg("-I")
        .arg("-m")
        .arg("ladybug_tools_mcp_cli")
        .args(env::args_os().skip(1));

    cmd.env("LADYBUG_TOOLS_MCP_HOME", &home);
    cmd.env("PYTHONUTF8", "1");
    cmd.env("PYTHONNOUSERSITE", "1");
    cmd.env_remove("PYTHONHOME");

    let has_installation_env = env::var_os("LADYBUG_TOOLS_MCP_INSTALLATION")
        .map(|v| !v.is_empty())
        .unwrap_or(false);
    if !has_installation_env {
        cmd.env(
            "LADYBUG_TOOLS_MCP_INSTALLATION",
            home.join("config").join("installation.json"),
        );
    }

    let status = cmd
        .status()
        .map_err(|e| format!("failed to spawn {}: {e}", python.to_string_lossy()))?;
    Ok(status.code().unwrap_or(1))
}

fn main() -> ExitCode {
    match run() {
        Ok(code) => {
            let clamped = if (0..=255).contains(&code) {
                code as u8
            } else {
                1
            };
            ExitCode::from(clamped)
        }
        Err(err) => {
            eprintln!("lbt-mcp: {err}");
            ExitCode::from(1)
        }
    }
}
