//! Bilingual Chinese (`ZhCn`) and English (`EnUs`) UI localization.
//!
//! Labels are intentionally terse (1–2 words) so layout and native `rune-kit` controls
//! communicate state without instructional blurbs or helper sentences.

use std::borrow::Cow;

use lbt_scene::{CameraPreset, ColorBy, ObjectKind};

/// All 7 genuine Honeybee SDK display coloring presets in display order.
pub const ALL_COLOR_BYS: [ColorBy; 7] = [
    ColorBy::Type,
    ColorBy::BoundaryCondition,
    ColorBy::Story,
    ColorBy::Zone,
    ColorBy::ProgramType,
    ColorBy::ConstructionSet,
    ColorBy::Hvac,
];

/// Supported studio UI locales.
#[derive(Copy, Clone, Debug, PartialEq, Eq, Hash, Default)]
pub enum Locale {
    #[default]
    EnUs,
    ZhCn,
}

impl Locale {
    /// Toggle between Simplified Chinese and English.
    pub const fn toggle(self) -> Self {
        match self {
            Self::EnUs => Self::ZhCn,
            Self::ZhCn => Self::EnUs,
        }
    }

    /// BCP 47 language tag passed to Rune's text engine for accurate CJK/Latin shaping.
    pub const fn bcp47(self) -> &'static str {
        match self {
            Self::EnUs => "en-US",
            Self::ZhCn => "zh-CN",
        }
    }

    /// Return `true` when Simplified Chinese is active.
    pub const fn is_zh(self) -> bool {
        matches!(self, Self::ZhCn)
    }
}

/// Parse `?lang=zh|en` (or `zh-CN` / `en-US`) from a URL query string.
pub fn parse_lang_query(search: &str) -> Option<Locale> {
    let query = search.strip_prefix('?').unwrap_or(search);
    for pair in query.split('&') {
        let Some((k, v)) = pair.split_once('=') else {
            continue;
        };
        if k.eq_ignore_ascii_case("lang") || k.eq_ignore_ascii_case("locale") {
            let norm = v.trim().to_ascii_lowercase();
            if norm.starts_with("zh") || norm == "cn" {
                return Some(Locale::ZhCn);
            }
            if norm.starts_with("en") {
                return Some(Locale::EnUs);
            }
        }
    }
    None
}

/// Detect locale from a browser `navigator.language` BCP-47 string.
pub fn locale_from_language_tag(tag: &str) -> Locale {
    if tag.trim().to_ascii_lowercase().starts_with("zh") {
        Locale::ZhCn
    } else {
        Locale::EnUs
    }
}

/// Detect the initial browser locale on `wasm32` (`?lang=zh|en` query override, then `navigator.language`).
#[cfg(target_arch = "wasm32")]
pub fn detect_browser_locale() -> Locale {
    if let Some(window) = web_sys::window() {
        if let Ok(search) = window.location().search()
            && let Some(override_locale) = parse_lang_query(&search)
        {
            return override_locale;
        }
        if let Some(lang) = window.navigator().language() {
            return locale_from_language_tag(&lang);
        }
    }
    Locale::EnUs
}

/// Synchronize Rune's global text language tag so CJK shaping prefers Simplified Chinese fonts.
pub fn apply_rune_language(locale: Locale) {
    rune::text::set_language(Some(locale.bcp47()));
}

/// Static typed UI string table for a [`Locale`].
#[derive(Copy, Clone, Debug)]
pub struct Strings {
    // App Shell & Toolbar
    pub app_title: &'static str,
    pub show_sidebar: &'static str,
    pub hide_sidebar: &'static str,
    pub toggle_inspector_label: &'static str,
    pub color_by_label: &'static str,
    pub view_menu_btn: &'static str,

    // View Popover Groups & Controls
    pub view_camera: &'static str,
    pub view_projection: &'static str,
    pub proj_perspective: &'static str,
    pub proj_orthographic: &'static str,
    pub view_section: &'static str,
    pub section_axis: &'static str,
    pub section_position: &'static str,
    pub section_invert: &'static str,
    pub view_display: &'static str,
    pub display_legend: &'static str,
    pub display_edges: &'static str,
    pub theme_dark: &'static str,
    pub theme_light: &'static str,
    pub toggle_theme_label: &'static str,
    pub toggle_locale_label: &'static str,
    pub lang_zh: &'static str,
    pub lang_en: &'static str,

    // Direct Honeybee Schema Tree
    pub node_model: &'static str,
    pub node_shades: &'static str,
    pub node_faces: &'static str,
    pub node_apertures: &'static str,
    pub node_doors: &'static str,
    pub expand_node_label: &'static str,
    pub collapse_node_label: &'static str,
    pub editing_badge: &'static str,

    // Room Edit Mode Breadcrumb
    pub exit_breadcrumb_btn: &'static str,

    // Property Inspector (Genuine Honeybee SDK fields only)
    pub prop_room: &'static str,
    pub prop_area: &'static str,
    pub prop_orientation: &'static str,
    pub prop_boundary: &'static str,
    pub prop_face_type: &'static str,
    pub prop_story: &'static str,
    pub prop_zone: &'static str,
    pub prop_hvac: &'static str,
    pub prop_program: &'static str,
    pub prop_construction: &'static str,
    pub prop_shades: &'static str,
    pub prop_glazing: &'static str,
    pub prop_shade_placement: &'static str,
    pub prop_hierarchy: &'static str,
    pub prop_color: &'static str,
    pub val_glass: &'static str,
    pub val_opaque: &'static str,
    pub val_indoor: &'static str,
    pub val_outdoor: &'static str,
    pub val_context: &'static str,
    pub val_orphaned: &'static str,
}

const EN_STRINGS: Strings = Strings {
    app_title: "Honeybee 3D Viewer",
    show_sidebar: "Show sidebar",
    hide_sidebar: "Hide sidebar",
    toggle_inspector_label: "Inspector",
    color_by_label: "Color By",
    view_menu_btn: "View",

    view_camera: "Camera",
    view_projection: "Projection",
    proj_perspective: "Perspective",
    proj_orthographic: "Orthographic",
    view_section: "Section",
    section_axis: "Axis",
    section_position: "Position",
    section_invert: "Invert",
    view_display: "Display",
    display_legend: "Legend",
    display_edges: "Edges",
    theme_dark: "Dark",
    theme_light: "Light",
    toggle_theme_label: "Theme",
    toggle_locale_label: "Language",
    lang_zh: "中文",
    lang_en: "EN",

    node_model: "Model",
    node_shades: "Shades",
    node_faces: "Faces",
    node_apertures: "Apertures",
    node_doors: "Doors",
    expand_node_label: "Expand",
    collapse_node_label: "Collapse",
    editing_badge: "EDIT",

    exit_breadcrumb_btn: "Exit",

    prop_room: "Room",
    prop_area: "Area",
    prop_orientation: "Orientation",
    prop_boundary: "Boundary",
    prop_face_type: "Face Type",
    prop_story: "Story",
    prop_zone: "Zone",
    prop_hvac: "HVAC",
    prop_program: "Program",
    prop_construction: "Construction",
    prop_shades: "Shades",
    prop_glazing: "Door",
    prop_shade_placement: "Shade",
    prop_hierarchy: "Scope",
    prop_color: "Color",
    val_glass: "Glass",
    val_opaque: "Opaque",
    val_indoor: "Indoor",
    val_outdoor: "Outdoor",
    val_context: "Context",
    val_orphaned: "Orphaned",
};

const ZH_STRINGS: Strings = Strings {
    app_title: "Honeybee 三维视图",
    show_sidebar: "显示侧边栏",
    hide_sidebar: "隐藏侧边栏",
    toggle_inspector_label: "属性面板",
    color_by_label: "着色模式",
    view_menu_btn: "视图",

    view_camera: "视角",
    view_projection: "投影",
    proj_perspective: "透视",
    proj_orthographic: "正交",
    view_section: "剖切",
    section_axis: "方向",
    section_position: "位置",
    section_invert: "反转",
    view_display: "显示",
    display_legend: "图例",
    display_edges: "线框边",
    theme_dark: "深色",
    theme_light: "浅色",
    toggle_theme_label: "主题",
    toggle_locale_label: "语言",
    lang_zh: "中文",
    lang_en: "EN",

    node_model: "模型",
    node_shades: "遮阳",
    node_faces: "表面",
    node_apertures: "洞口",
    node_doors: "门",
    expand_node_label: "展开",
    collapse_node_label: "折叠",
    editing_badge: "编辑中",

    exit_breadcrumb_btn: "退出",

    prop_room: "所属房间",
    prop_area: "面积",
    prop_orientation: "朝向",
    prop_boundary: "边界条件",
    prop_face_type: "表面类型",
    prop_story: "楼层",
    prop_zone: "热分区",
    prop_hvac: "暖通空调",
    prop_program: "房间功能",
    prop_construction: "围护构造",
    prop_shades: "附属遮阳",
    prop_glazing: "门类型",
    prop_shade_placement: "遮阳类型",
    prop_hierarchy: "层级",
    prop_color: "显示颜色",
    val_glass: "玻璃门",
    val_opaque: "不透明门",
    val_indoor: "室内",
    val_outdoor: "室外",
    val_context: "环境",
    val_orphaned: "独立",
};

/// Retrieve the static translation table for `locale`.
pub const fn tr(locale: Locale) -> &'static Strings {
    match locale {
        Locale::EnUs => &EN_STRINGS,
        Locale::ZhCn => &ZH_STRINGS,
    }
}

/// Full human-readable label for a Honeybee SDK `ColorBy` mode.
pub const fn color_by_full(locale: Locale, mode: ColorBy) -> &'static str {
    match (locale, mode) {
        (Locale::EnUs, ColorBy::Type) => "Face Type",
        (Locale::EnUs, ColorBy::BoundaryCondition) => "Boundary Condition",
        (Locale::EnUs, ColorBy::Story) => "Story",
        (Locale::EnUs, ColorBy::Zone) => "Zone",
        (Locale::EnUs, ColorBy::ProgramType) => "Program Type",
        (Locale::EnUs, ColorBy::ConstructionSet) => "Construction Set",
        (Locale::EnUs, ColorBy::Hvac) => "HVAC",
        (Locale::ZhCn, ColorBy::Type) => "构件类型",
        (Locale::ZhCn, ColorBy::BoundaryCondition) => "边界条件",
        (Locale::ZhCn, ColorBy::Story) => "建筑楼层",
        (Locale::ZhCn, ColorBy::Zone) => "热分区",
        (Locale::ZhCn, ColorBy::ProgramType) => "房间功能",
        (Locale::ZhCn, ColorBy::ConstructionSet) => "围护构造集",
        (Locale::ZhCn, ColorBy::Hvac) => "暖通空调",
    }
}

/// Resolve a localized `Select` option label back to its `ColorBy` variant.
pub fn parse_color_by_label(label: &str) -> Option<ColorBy> {
    ALL_COLOR_BYS.into_iter().find(|&mode| {
        color_by_full(Locale::EnUs, mode) == label || color_by_full(Locale::ZhCn, mode) == label
    })
}

/// Compact camera preset label for the `View` popover button rows.
pub const fn camera_short(locale: Locale, preset: CameraPreset) -> &'static str {
    match (locale, preset) {
        (Locale::EnUs, CameraPreset::Axon) => "Axon",
        (Locale::EnUs, CameraPreset::Top) => "Top",
        (Locale::EnUs, CameraPreset::North) => "N",
        (Locale::EnUs, CameraPreset::South) => "S",
        (Locale::EnUs, CameraPreset::East) => "E",
        (Locale::EnUs, CameraPreset::West) => "W",
        (Locale::EnUs, CameraPreset::Fit) => "Fit",
        (Locale::EnUs, CameraPreset::FitHighlights) => "Focus",
        (Locale::EnUs, CameraPreset::Keep) => "Keep",
        (Locale::ZhCn, CameraPreset::Axon) => "轴测",
        (Locale::ZhCn, CameraPreset::Top) => "顶视",
        (Locale::ZhCn, CameraPreset::North) => "北",
        (Locale::ZhCn, CameraPreset::South) => "南",
        (Locale::ZhCn, CameraPreset::East) => "东",
        (Locale::ZhCn, CameraPreset::West) => "西",
        (Locale::ZhCn, CameraPreset::Fit) => "适配",
        (Locale::ZhCn, CameraPreset::FitHighlights) => "聚焦",
        (Locale::ZhCn, CameraPreset::Keep) => "保持",
    }
}

/// Localized label for a Honeybee `ObjectKind`.
pub const fn object_kind_label(locale: Locale, kind: ObjectKind) -> &'static str {
    match (locale, kind) {
        (Locale::EnUs, ObjectKind::Room) => "Room",
        (Locale::EnUs, ObjectKind::Face) => "Face",
        (Locale::EnUs, ObjectKind::Aperture) => "Aperture",
        (Locale::EnUs, ObjectKind::Door) => "Door",
        (Locale::EnUs, ObjectKind::Shade) => "Shade",
        (Locale::ZhCn, ObjectKind::Room) => "房间",
        (Locale::ZhCn, ObjectKind::Face) => "表面",
        (Locale::ZhCn, ObjectKind::Aperture) => "洞口/窗",
        (Locale::ZhCn, ObjectKind::Door) => "门",
        (Locale::ZhCn, ObjectKind::Shade) => "遮阳",
    }
}

/// Localized orientation cardinal/tilt string from a canonical English orientation tag.
pub fn orientation_label(locale: Locale, raw: &str) -> Option<&'static str> {
    let translated = match (locale, raw) {
        (Locale::EnUs, "Horizontal Up") => "Horizontal Up",
        (Locale::EnUs, "Horizontal Down") => "Horizontal Down",
        (Locale::EnUs, "N") => "N",
        (Locale::EnUs, "NE") => "NE",
        (Locale::EnUs, "E") => "E",
        (Locale::EnUs, "SE") => "SE",
        (Locale::EnUs, "S") => "S",
        (Locale::EnUs, "SW") => "SW",
        (Locale::EnUs, "W") => "W",
        (Locale::EnUs, "NW") => "NW",
        (Locale::ZhCn, "Horizontal Up") => "水平朝上",
        (Locale::ZhCn, "Horizontal Down") => "水平朝下",
        (Locale::ZhCn, "N") => "北 (N)",
        (Locale::ZhCn, "NE") => "东北 (NE)",
        (Locale::ZhCn, "E") => "东 (E)",
        (Locale::ZhCn, "SE") => "东南 (SE)",
        (Locale::ZhCn, "S") => "南 (S)",
        (Locale::ZhCn, "SW") => "西南 (SW)",
        (Locale::ZhCn, "W") => "西 (W)",
        (Locale::ZhCn, "NW") => "西北 (NW)",
        _ => return None,
    };
    Some(translated)
}

/// Translate official `honeybee-display` FaceType, BoundaryCondition, and Legend category labels.
///
/// Unknown / user-authored identifiers (story names, zone names, program types, construction sets)
/// pass through unchanged. Unassigned room attributes display as `"None"` (EN, matching official
/// Honeybee SDK `ColorRoom`) or `"无"` (ZH).
pub fn translate_display_category<'a>(
    locale: Locale,
    key: &'a str,
    fallback_label: &'a str,
) -> Cow<'a, str> {
    let norm = key.trim().to_ascii_lowercase().replace([' ', '-'], "_");
    match locale {
        Locale::EnUs => match norm.as_str() {
            "wall" => Cow::Borrowed("Wall"),
            "interior_wall" => Cow::Borrowed("Interior Wall"),
            "roof" => Cow::Borrowed("Roof"),
            "roofceiling" | "roof_ceiling" => Cow::Borrowed("Roof / Ceiling"),
            "ceiling" => Cow::Borrowed("Ceiling"),
            "floor" => Cow::Borrowed("Floor"),
            "interior_floor" => Cow::Borrowed("Interior Floor"),
            "air_boundary" | "airboundary" => Cow::Borrowed("Air Boundary"),
            "aperture" => Cow::Borrowed("Aperture"),
            "door" => Cow::Borrowed("Door"),
            "glass_door" | "glassdoor" => Cow::Borrowed("Glass Door"),
            "outdoor_shade" | "outdoorshade" => Cow::Borrowed("Outdoor Shade"),
            "indoor_shade" | "indoorshade" => Cow::Borrowed("Indoor Shade"),
            "context_shade" | "contextshade" => Cow::Borrowed("Context Shade"),
            "shade_mesh" | "shademesh" => Cow::Borrowed("Shade Mesh"),
            "outdoors" => Cow::Borrowed("Outdoors"),
            "surface" => Cow::Borrowed("Surface"),
            "ground" => Cow::Borrowed("Ground"),
            "adiabatic" => Cow::Borrowed("Adiabatic"),
            "other" | "othersidetemperature" | "other_side_temperature" => Cow::Borrowed("Other"),
            "unassigned" | "none" | "n/a" => Cow::Borrowed("None"),
            "room" => Cow::Borrowed("Room"),
            _ => Cow::Borrowed(if fallback_label.is_empty() {
                key
            } else {
                fallback_label
            }),
        },
        Locale::ZhCn => match norm.as_str() {
            "wall" => Cow::Borrowed("外墙"),
            "interior_wall" => Cow::Borrowed("内墙"),
            "roof" => Cow::Borrowed("屋顶"),
            "roofceiling" | "roof_ceiling" => Cow::Borrowed("屋顶/天花板"),
            "ceiling" => Cow::Borrowed("天花板"),
            "floor" => Cow::Borrowed("楼板/地面"),
            "interior_floor" => Cow::Borrowed("室内楼板"),
            "air_boundary" | "airboundary" => Cow::Borrowed("空气边界"),
            "aperture" => Cow::Borrowed("外窗/洞口"),
            "door" => Cow::Borrowed("不透明门"),
            "glass_door" | "glassdoor" => Cow::Borrowed("玻璃门"),
            "outdoor_shade" | "outdoorshade" => Cow::Borrowed("室外遮阳"),
            "indoor_shade" | "indoorshade" => Cow::Borrowed("室内遮阳"),
            "context_shade" | "contextshade" => Cow::Borrowed("环境遮阳"),
            "shade_mesh" | "shademesh" => Cow::Borrowed("遮阳网格"),
            "outdoors" => Cow::Borrowed("室外"),
            "surface" => Cow::Borrowed("相邻面"),
            "ground" => Cow::Borrowed("地面"),
            "adiabatic" => Cow::Borrowed("绝热"),
            "other" | "othersidetemperature" | "other_side_temperature" => {
                Cow::Borrowed("其他边界")
            }
            "unassigned" | "none" | "n/a" => Cow::Borrowed("无"),
            "room" => Cow::Borrowed("房间"),
            _ => Cow::Borrowed(if fallback_label.is_empty() {
                key
            } else {
                fallback_label
            }),
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_query_override_and_browser_language() {
        assert_eq!(parse_lang_query("?lang=zh"), Some(Locale::ZhCn));
        assert_eq!(parse_lang_query("?foo=1&lang=zh-CN"), Some(Locale::ZhCn));
        assert_eq!(parse_lang_query("?lang=en-US"), Some(Locale::EnUs));
        assert_eq!(parse_lang_query("?foo=bar"), None);

        assert_eq!(locale_from_language_tag("zh-CN"), Locale::ZhCn);
        assert_eq!(locale_from_language_tag("zh-Hans"), Locale::ZhCn);
        assert_eq!(locale_from_language_tag("en-US"), Locale::EnUs);
        assert_eq!(locale_from_language_tag("fr-FR"), Locale::EnUs);
    }

    #[test]
    fn translates_display_categories_and_color_by_labels_in_zh_and_en() {
        assert_eq!(
            translate_display_category(Locale::EnUs, "Wall", "Wall"),
            "Wall"
        );
        assert_eq!(
            translate_display_category(Locale::EnUs, "unassigned", "None"),
            "None"
        );
        assert_eq!(
            translate_display_category(Locale::ZhCn, "unassigned", "None"),
            "无"
        );
        assert_eq!(
            translate_display_category(Locale::ZhCn, "Wall", "Wall"),
            "外墙"
        );
        assert_eq!(
            translate_display_category(Locale::ZhCn, "Glass Door", "Glass Door"),
            "玻璃门"
        );
        assert_eq!(
            translate_display_category(Locale::ZhCn, "Outdoors", "Outdoors"),
            "室外"
        );
        assert_eq!(
            translate_display_category(Locale::ZhCn, "Context Shade", "Context Shade"),
            "环境遮阳"
        );
        assert_eq!(
            translate_display_category(Locale::ZhCn, "Level_1", "Level_1"),
            "Level_1"
        );

        for mode in ALL_COLOR_BYS {
            assert_eq!(
                parse_color_by_label(color_by_full(Locale::EnUs, mode)),
                Some(mode)
            );
            assert_eq!(
                parse_color_by_label(color_by_full(Locale::ZhCn, mode)),
                Some(mode)
            );
        }
    }
}
