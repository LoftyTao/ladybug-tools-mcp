//! Command-line parsing for `lbt-rune-viewer`.

use std::path::PathBuf;

use lbt_scene::{CameraPreset, ColorBy};

/// Parsed CLI options for `lbt-rune-viewer`.
#[derive(Clone, Debug, PartialEq)]
pub struct CliArgs {
    pub show_version: bool,
    pub show_help: bool,
    pub mcp_mode: bool,
    pub hbjson: Option<PathBuf>,
    pub garden: Option<PathBuf>,
    pub snap: Option<PathBuf>,
    pub view: Option<CameraPreset>,
    pub color_by: Option<ColorBy>,
    pub section_z: Option<f32>,
    pub width: u32,
    pub height: u32,
    /// Arguments following `--`, forwarded verbatim to Rune (`App::args`).
    pub rune_args: Vec<String>,
}

impl Default for CliArgs {
    fn default() -> Self {
        Self {
            show_version: false,
            show_help: false,
            mcp_mode: false,
            hbjson: None,
            garden: None,
            snap: None,
            view: None,
            color_by: None,
            section_z: None,
            width: 1280,
            height: 720,
            rune_args: Vec::new(),
        }
    }
}

/// Human-readable CLI help text.
pub fn usage_text() -> &'static str {
    "\
lbt-rune-viewer — Native GPU 3D Honeybee & Garden Viewer

USAGE:
  lbt-rune-viewer --version | -V
  lbt-rune-viewer --hbjson <path.hbjson> [-- <rune tooling flags>]
  lbt-rune-viewer --garden <garden_root> [-- <rune tooling flags>]
  lbt-rune-viewer --hbjson <path.hbjson> --snap <out.png> [OPTIONS]
  lbt-rune-viewer --garden <garden_root> --snap <out.png> [OPTIONS]
  lbt-rune-viewer --mcp [--hbjson <path.hbjson>]

OPTIONS:
  --hbjson <path>        Load a Honeybee Model .hbjson file
  --garden <dir>         Live-sync with <garden>/tmp/web_view/ protocol files
  --snap <out.png>       Render a fast headless GPU snapshot PNG and exit
  --view <preset>        Camera preset: axon|top|north|south|east|west|fit|fit_highlights|keep
  --color-by <mode>      Color mode: type|boundary_condition|story|zone|program_type|construction_set|hvac
  --section-z <meters>   Enable horizontal Z section cut at elevation (meters)
  --width <px>           Headless snapshot width in pixels (default: 1280)
  --height <px>          Headless snapshot height in pixels (default: 720)
  --mcp                  Run standalone stdio JSON-RPC MCP server
  -V, --version          Print version and protocol info
  -h, --help             Print this help message"
}

/// Parse CLI arguments before `--`, capturing everything after `--` as `rune_args`.
pub fn parse_args(args: &[String]) -> Result<CliArgs, String> {
    let mut out = CliArgs::default();
    let mut i = 0;

    while i < args.len() {
        let arg = args[i].as_str();
        if arg == "--" {
            out.rune_args = args[i + 1..].to_vec();
            break;
        }
        match arg {
            "-V" | "--version" => out.show_version = true,
            "-h" | "--help" => out.show_help = true,
            "--mcp" => out.mcp_mode = true,
            "--hbjson" => {
                i += 1;
                let val = args.get(i).ok_or_else(|| "--hbjson requires a file path".to_owned())?;
                out.hbjson = Some(PathBuf::from(val));
            }
            "--garden" => {
                i += 1;
                let val = args.get(i).ok_or_else(|| "--garden requires a directory path".to_owned())?;
                out.garden = Some(PathBuf::from(val));
            }
            "--snap" => {
                i += 1;
                let val = args.get(i).ok_or_else(|| "--snap requires an output PNG path".to_owned())?;
                out.snap = Some(PathBuf::from(val));
            }
            "--view" => {
                i += 1;
                let val = args.get(i).ok_or_else(|| "--view requires a preset name".to_owned())?;
                out.view = Some(parse_camera_preset(val)?);
            }
            "--color-by" => {
                i += 1;
                let val = args.get(i).ok_or_else(|| "--color-by requires a coloring mode".to_owned())?;
                out.color_by = Some(parse_color_by(val)?);
            }
            "--section-z" => {
                i += 1;
                let val = args.get(i).ok_or_else(|| "--section-z requires a float elevation".to_owned())?;
                let z = val
                    .trim()
                    .parse::<f32>()
                    .map_err(|_| format!("invalid --section-z float: {val}"))?;
                if !z.is_finite() {
                    return Err(format!("--section-z must be finite: {val}"));
                }
                out.section_z = Some(z);
            }
            "--width" => {
                i += 1;
                let val = args.get(i).ok_or_else(|| "--width requires a positive integer".to_owned())?;
                out.width = parse_positive_u32(val, "--width")?;
            }
            "--height" => {
                i += 1;
                let val = args.get(i).ok_or_else(|| "--height requires a positive integer".to_owned())?;
                out.height = parse_positive_u32(val, "--height")?;
            }
            other if !other.starts_with('-') && out.hbjson.is_none() && other.ends_with(".hbjson") => {
                out.hbjson = Some(PathBuf::from(other));
            }
            other => {
                return Err(format!("unknown argument: {other}\n\n{}", usage_text()));
            }
        }
        i += 1;
    }

    if out.snap.is_some() && out.hbjson.is_none() && out.garden.is_none() {
        return Err(
            "--snap requires --hbjson <path> or --garden <root> (or pass `-- --snap <out.png>` for Rune UI snapshot)".to_owned(),
        );
    }
    if out.hbjson.is_some() && out.garden.is_some() {
        return Err("cannot pass both --hbjson and --garden".to_owned());
    }

    Ok(out)
}

fn parse_positive_u32(raw: &str, flag: &str) -> Result<u32, String> {
    let val = raw
        .trim()
        .parse::<u32>()
        .map_err(|_| format!("invalid {flag} integer: {raw}"))?;
    if val == 0 {
        return Err(format!("{flag} must be > 0"));
    }
    Ok(val)
}

/// Parse a `ColorBy` mode from CLI strings.
pub fn parse_color_by(raw: &str) -> Result<ColorBy, String> {
    match raw.trim().to_ascii_lowercase().as_str() {
        "type" | "face_type" => Ok(ColorBy::Type),
        "boundary_condition" | "boundary" | "bc" => Ok(ColorBy::BoundaryCondition),
        "story" | "stories" => Ok(ColorBy::Story),
        "zone" | "zones" => Ok(ColorBy::Zone),
        "program_type" | "program" => Ok(ColorBy::ProgramType),
        "construction_set" | "construction" | "constr" => Ok(ColorBy::ConstructionSet),
        "hvac" => Ok(ColorBy::Hvac),
        other => Err(format!("unsupported --color-by value: {other}")),
    }
}

/// Parse a `CameraPreset` from CLI strings.
pub fn parse_camera_preset(raw: &str) -> Result<CameraPreset, String> {
    match raw.trim().to_ascii_lowercase().as_str() {
        "keep" => Ok(CameraPreset::Keep),
        "fit" => Ok(CameraPreset::Fit),
        "fit_highlights" | "highlights" => Ok(CameraPreset::FitHighlights),
        "axon" | "iso" | "ne" | "nw" | "se" | "sw" => Ok(CameraPreset::Axon),
        "top" | "plan" => Ok(CameraPreset::Top),
        "north" | "back" => Ok(CameraPreset::North),
        "south" | "front" => Ok(CameraPreset::South),
        "east" | "right" => Ok(CameraPreset::East),
        "west" | "left" => Ok(CameraPreset::West),
        other => Err(format!("unsupported --view preset: {other}")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn s(items: &[&str]) -> Vec<String> {
        items.iter().map(|v| (*v).to_owned()).collect()
    }

    #[test]
    fn parses_version_and_help() {
        assert!(parse_args(&s(&["--version"])).unwrap().show_version);
        assert!(parse_args(&s(&["-V"])).unwrap().show_version);
        assert!(parse_args(&s(&["--help"])).unwrap().show_help);
        assert!(parse_args(&s(&["-h"])).unwrap().show_help);
    }

    #[test]
    fn parses_hbjson_snap_options_and_rune_passthrough() {
        let parsed = parse_args(&s(&[
            "--hbjson",
            "model.hbjson",
            "--snap",
            "out.png",
            "--view",
            "axon",
            "--color-by",
            "boundary_condition",
            "--section-z",
            "4.25",
            "--width",
            "1600",
            "--height",
            "900",
        ]))
        .unwrap();
        assert_eq!(parsed.hbjson, Some(PathBuf::from("model.hbjson")));
        assert_eq!(parsed.snap, Some(PathBuf::from("out.png")));
        assert_eq!(parsed.view, Some(CameraPreset::Axon));
        assert_eq!(parsed.color_by, Some(ColorBy::BoundaryCondition));
        assert_eq!(parsed.section_z, Some(4.25));
        assert_eq!(parsed.width, 1600);
        assert_eq!(parsed.height, 900);

        let gui = parse_args(&s(&[
            "--hbjson",
            "model.hbjson",
            "--",
            "--snap",
            "window.png",
            "--settle",
        ]))
        .unwrap();
        assert_eq!(gui.hbjson, Some(PathBuf::from("model.hbjson")));
        assert!(gui.snap.is_none());
        assert_eq!(gui.rune_args, s(&["--snap", "window.png", "--settle"]));
    }

    #[test]
    fn parses_garden_and_mcp_modes_and_rejects_invalid_combinations() {
        let garden = parse_args(&s(&["--garden", "my_garden", "--snap", "g.png", "--view", "top"])).unwrap();
        assert_eq!(garden.garden, Some(PathBuf::from("my_garden")));
        assert_eq!(garden.view, Some(CameraPreset::Top));

        let mcp = parse_args(&s(&["--mcp", "--hbjson", "m.hbjson"])).unwrap();
        assert!(mcp.mcp_mode);
        assert_eq!(mcp.hbjson, Some(PathBuf::from("m.hbjson")));

        assert!(parse_args(&s(&["--snap", "only.png"])).is_err());
        assert!(parse_args(&s(&["--hbjson", "a.hbjson", "--garden", "g"])).is_err());
        assert!(parse_args(&s(&["--width", "0"])).is_err());
    }
}
