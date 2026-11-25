//! Minimal, distraction-free `rune-kit` + Rune 3D Honeybee model viewer and property inspector.
//!
//! Architecture:
//! - Root: `rune_kit::root(SplitView, overlay_layer)` so `Menu`, `Popover`, and error `ToastRegion`
//!   mount cleanly above the WebGPU/WebGL2 viewport.
//! - Minimal `Toolbar`: leading Honeybee brand icon + clean model name; trailing 3 controls only:
//!   `ColorBy` dropdown (`Select` trigger + full-width `Menu`, 7 Honeybee SDK presets),
//!   `View` `Popover` (Camera / Projection / Section Slider / Display), and Inspector `IconButton`.
//! - Left `Sidebar`: purely the direct Honeybee Schema Model Tree (`SidebarRow` + official Ladybug
//!   Tools Artwork icons, display names only, zero synthetic folders, zero tabs).
//! - Right `SplitView::inspector`: clean read-only Honeybee Object Property Inspector (official
//!   Artwork header, populated genuine SDK properties + color swatch only, zero action buttons).
//! - 3D Viewport: authentic Honeybee/Ladybug SDK colors (zero forced validation/highlight tints),
//!   Room-first picking, double-click Room Edit Mode breadcrumb, live Axis HUD, and authentic
//!   borderless Ladybug Tools 2D Legend.

use std::time::Duration;

use lbt_scene::{CameraPreset, ObjectKind, SectionAxis, build_legend};
use rune::color::srgb_decode;
use rune::{
    Color, Cursor, Cx, Drag, El, Key, KeyEvent, LineCap, MagnifyEvent, Phase, PointerButton,
    ScrollSpec, Shape, TextStyle, Tx, WheelEvent, canvas, col, el, icon, row, text,
};
use rune_kit::shell::{Sidebar, SidebarRow, SidebarToggle, SplitView, Toolbar};
use rune_kit::{
    Badge, BadgeVariant, Button, ButtonVariant, ControlSize, Divider, IconButton,
    IconButtonVariant, Kit, Menu, MenuItem, Placement, Popover, SegmentedControl, Select,
    SelectAppearance, Slider, Switch, Toast, ToastRegion, TooltipAppearance, TooltipStyle,
};

use crate::i18n::{
    ALL_COLOR_BYS, Locale, camera_short, color_by_full, object_kind_label, orientation_label, tr,
    translate_display_category,
};
use crate::icons::{StudioIcon, icon_el, lbt_object_icon, lbt_record_icon, tinted_icon_el};
use crate::outliner::{
    FaceNode, ShadeNode, SubfaceNode, average_object_normal, orientation_from_normal,
};
use crate::state::{TopMenu, ViewerState};
use crate::theme::{CARDINAL_CAMERA_BUTTONS, PRIMARY_CAMERA_BUTTONS, studio_kit, viewport_bg};

fn rgba8(r: u8, g: u8, b: u8, a: u8) -> Color {
    Color {
        r: srgb_decode(f32::from(r) / 255.0),
        g: srgb_decode(f32::from(g) / 255.0),
        b: srgb_decode(f32::from(b) / 255.0),
        a: f32::from(a) / 255.0,
    }
}

fn srgb_rgba_to_color(rgba: [f32; 4]) -> Color {
    Color {
        r: srgb_decode(rgba[0].clamp(0.0, 1.0)),
        g: srgb_decode(rgba[1].clamp(0.0, 1.0)),
        b: srgb_decode(rgba[2].clamp(0.0, 1.0)),
        a: rgba[3].clamp(0.0, 1.0),
    }
}

/// Convert an sRGB color into a crisp opaque `Color` (`alpha = 1.0`), matching `ladybug/legend.py`.
fn srgb_rgb_opaque(rgba: [f32; 4]) -> Color {
    Color {
        r: srgb_decode(rgba[0].clamp(0.0, 1.0)),
        g: srgb_decode(rgba[1].clamp(0.0, 1.0)),
        b: srgb_decode(rgba[2].clamp(0.0, 1.0)),
        a: 1.0,
    }
}

// ============================================================================
// Top Toolbar (`ColorBy` Dropdown, `View` Popover, Inspector Toggle)
// ============================================================================

fn view_popover_body(s: &ViewerState, k: &Kit) -> El {
    let l = tr(s.locale);
    let is_ortho = s.renderer.is_orthographic();
    let axis_idx = match s.section.axis {
        SectionAxis::X => 0,
        SectionAxis::Y => 1,
        SectionAxis::Z => 2,
    };
    let (sec_min, sec_max) = s.section_axis_bounds(s.section.axis);
    let sec_val = s.section_current_value();

    let mut cam_primary = row().w_full().gap(4.0);
    for &(preset, key) in &PRIMARY_CAMERA_BUTTONS {
        cam_primary = cam_primary.child(
            Button::new(camera_short(s.locale, preset))
                .variant(ButtonVariant::Neutral)
                .control_size(ControlSize::Small)
                .on_press(move |st: &mut ViewerState| st.apply_camera_preset(preset))
                .build(k)
                .key(key)
                .grow(1.0),
        );
    }

    let mut cam_cardinals = row().w_full().gap(4.0);
    for &(preset, key) in &CARDINAL_CAMERA_BUTTONS {
        cam_cardinals = cam_cardinals.child(
            Button::new(camera_short(s.locale, preset))
                .variant(ButtonVariant::Neutral)
                .control_size(ControlSize::Small)
                .on_press(move |st: &mut ViewerState| st.apply_camera_preset(preset))
                .build(k)
                .key(key)
                .grow(1.0),
        );
    }

    let camera_group = col()
        .w_full()
        .gap(6.0)
        .child(
            text(l.view_camera)
                .font(k.ty.small_medium)
                .color(k.c.text_faint),
        )
        .child(cam_primary)
        .child(cam_cardinals);

    let projection_group = col()
        .w_full()
        .gap(6.0)
        .child(
            text(l.view_projection)
                .font(k.ty.small_medium)
                .color(k.c.text_faint),
        )
        .child(
            SegmentedControl::new(
                &[l.proj_perspective, l.proj_orthographic],
                Some(usize::from(is_ortho)),
            )
            .label(l.view_projection)
            .width(None)
            .on_pick(|st: &mut ViewerState, idx, _| st.set_orthographic(idx == 1))
            .build(k)
            .key("seg-projection"),
        );

    let mut section_group = col().w_full().gap(8.0).child(
        row()
            .w_full()
            .justify_between()
            .center_y()
            .child(
                text(l.view_section)
                    .font(k.ty.small_medium)
                    .color(k.c.text_faint),
            )
            .child(
                Switch::new(s.section.enabled)
                    .label(l.view_section)
                    .hide_label()
                    .on_toggle(|st: &mut ViewerState| st.toggle_section())
                    .build(k)
                    .key("switch-section"),
            ),
    );

    if s.section.enabled {
        section_group = section_group
            .child(
                SegmentedControl::new(&["X", "Y", "Z"], Some(axis_idx))
                    .label(l.section_axis)
                    .width(None)
                    .on_pick(|st: &mut ViewerState, idx, _| {
                        let next = match idx {
                            0 => SectionAxis::X,
                            1 => SectionAxis::Y,
                            _ => SectionAxis::Z,
                        };
                        st.set_section_axis(next);
                    })
                    .build(k)
                    .key("seg-section-axis"),
            )
            .child(
                col()
                    .w_full()
                    .gap(4.0)
                    .child(
                        row()
                            .w_full()
                            .justify_between()
                            .center_y()
                            .child(
                                text(l.section_position)
                                    .font(k.ty.small)
                                    .color(k.c.text_muted),
                            )
                            .child(
                                text(format!("{sec_val:.1} m"))
                                    .key("section-value-text")
                                    .font(k.ty.small_medium)
                                    .color(k.c.text_base),
                            ),
                    )
                    .child(
                        Slider::new("slider-section", sec_val)
                            .range(sec_min..=sec_max)
                            .step(0.1)
                            .width(248.0)
                            .label(l.section_position)
                            .hide_label()
                            .value_text(format!("{sec_val:.1} m"))
                            .on_change(|st: &mut ViewerState, val, done| {
                                st.set_section_value(val, done);
                            })
                            .build(k),
                    ),
            )
            .child(
                row()
                    .w_full()
                    .justify_between()
                    .center_y()
                    .child(
                        text(l.section_invert)
                            .font(k.ty.small)
                            .color(k.c.text_muted),
                    )
                    .child(
                        Switch::new(s.section.invert)
                            .label(l.section_invert)
                            .hide_label()
                            .on_toggle(|st: &mut ViewerState| {
                                st.set_section_invert(!st.section.invert);
                            })
                            .build(k)
                            .key("switch-section-invert"),
                    ),
            );
    }

    let display_group = col()
        .w_full()
        .gap(8.0)
        .child(
            text(l.view_display)
                .font(k.ty.small_medium)
                .color(k.c.text_faint),
        )
        .child(
            row()
                .w_full()
                .justify_between()
                .center_y()
                .child(
                    text(l.display_legend)
                        .font(k.ty.ui_compact)
                        .color(k.c.text_base),
                )
                .child(
                    Switch::new(s.show_legend)
                        .label(l.display_legend)
                        .hide_label()
                        .on_toggle(|st: &mut ViewerState| st.set_show_legend(!st.show_legend))
                        .build(k)
                        .key("switch-legend"),
                ),
        )
        .child(
            row()
                .w_full()
                .justify_between()
                .center_y()
                .child(
                    text(l.display_edges)
                        .font(k.ty.ui_compact)
                        .color(k.c.text_base),
                )
                .child(
                    Switch::new(s.show_edges)
                        .label(l.display_edges)
                        .hide_label()
                        .on_toggle(|st: &mut ViewerState| st.set_show_edges(!st.show_edges))
                        .build(k)
                        .key("switch-edges"),
                ),
        )
        .child(
            SegmentedControl::new(
                &[l.theme_dark, l.theme_light],
                Some(usize::from(!s.dark_mode)),
            )
            .label(l.toggle_theme_label)
            .width(None)
            .on_pick(|st: &mut ViewerState, idx, _| st.set_dark_mode(idx == 0))
            .build(k)
            .key("seg-theme"),
        )
        .child(
            SegmentedControl::new(
                &[l.lang_zh, l.lang_en],
                Some(usize::from(!s.locale.is_zh())),
            )
            .label(l.toggle_locale_label)
            .width(None)
            .on_pick(|st: &mut ViewerState, idx, _| {
                st.set_locale(if idx == 0 { Locale::ZhCn } else { Locale::EnUs });
            })
            .build(k)
            .key("seg-locale"),
        );

    col()
        .key("view-settings-body")
        .w(248.0)
        .gap(10.0)
        .child(camera_group)
        .child(Divider::horizontal().build(k))
        .child(projection_group)
        .child(Divider::horizontal().build(k))
        .child(section_group)
        .child(Divider::horizontal().build(k))
        .child(display_group)
}

fn build_toolbar(s: &ViewerState, k: &Kit, layer: &mut Vec<El>) -> Toolbar {
    let l = tr(s.locale);

    // Leading: Honeybee brand icon (15pt) + clean model title
    let brand = row()
        .key("toolbar-brand")
        .gap(6.0)
        .center_y()
        .shrink()
        .min_w(0.0)
        .child(icon_el(StudioIcon::LbtHoneybee, 15.0))
        .child(
            text(&s.model_label)
                .key("toolbar-title")
                .font(k.ty.ui_medium)
                .color(k.c.text_base)
                .truncate()
                .shrink(),
        );

    // Trailing 1: ColorBy inline Select trigger paired with full-width Menu (7 Honeybee SDK presets)
    let color_options: Vec<&'static str> = ALL_COLOR_BYS
        .into_iter()
        .map(|m| color_by_full(s.locale, m))
        .collect();
    let color_open = s.open_menu == Some(TopMenu::ColorBy);
    let color_trigger = Select::new("color-by-field", &color_options)
        .appearance(SelectAppearance::Inline)
        .step_closed(true)
        .label(l.color_by_label)
        .current(Some(color_by_full(s.locale, s.color_by)))
        .open(color_open)
        .on_toggle(|st: &mut ViewerState| st.toggle_top_menu(TopMenu::ColorBy))
        .on_choose(|st: &mut ViewerState, val: &str, _| st.set_color_by_label(val))
        .trigger(k);
    let mut color_menu = Menu::new("color-by")
        .trigger(color_trigger)
        .label(l.color_by_label)
        .placement(Placement::BottomEnd)
        .min_width(184.0)
        .open(color_open)
        .on_close(|st: &mut ViewerState| st.close_top_menu(TopMenu::ColorBy));
    for (i, mode) in ALL_COLOR_BYS.into_iter().enumerate() {
        color_menu = color_menu.item(
            MenuItem::new(color_by_full(s.locale, mode))
                .key(format!("color-by-opt-{i}"))
                .checked(mode == s.color_by)
                .on_select(move |st: &mut ViewerState| st.set_color_by(mode)),
        );
    }
    let color_select = color_menu.build(k, layer);

    // Trailing 2: View Popover (Camera, Projection, Section Slider, Display)
    let view_open = s.open_menu == Some(TopMenu::View);
    let view_trigger = Button::new(l.view_menu_btn)
        .variant(ButtonVariant::Ghost)
        .expanded(view_open)
        .on_press(|st: &mut ViewerState| st.toggle_top_menu(TopMenu::View))
        .build(k)
        .key("btn-view-menu");
    let view_popover = Popover::new("view-settings")
        .trigger(view_trigger)
        .label(l.view_menu_btn)
        .placement(Placement::BottomEnd)
        .padding(12.0)
        .open(view_open)
        .on_close(|st: &mut ViewerState| st.close_top_menu(TopMenu::View))
        .child(view_popover_body(s, k))
        .build(k, layer);

    // Trailing 3: Inspector Toggle IconButton
    let inspector_toggle = IconButton::new(&rune_kit::shell::INSPECTOR)
        .variant(IconButtonVariant::GhostMuted)
        .label(l.toggle_inspector_label)
        .expanded(s.inspector_pane.is_open())
        .on_press(|st: &mut ViewerState| {
            st.open_menu = None;
            st.inspector_pane.toggle();
        })
        .build(k)
        .key("btn-inspector-toggle");

    Toolbar::new()
        .leading(brand)
        .trailing(color_select)
        .trailing(view_popover)
        .trailing(inspector_toggle)
}

// ============================================================================
// Left Sidebar — Pure Direct Honeybee Schema Model Tree (`Sidebar` + `SidebarRow`)
// ============================================================================

fn disclosure_slot(s: &ViewerState, k: &Kit, toggle: Option<(String, String, bool)>) -> El {
    let l = tr(s.locale);
    if let Some((toggle_key, node_key, expanded)) = toggle {
        IconButton::new(if expanded {
            k.glyph.chevron_down
        } else {
            k.glyph.caret_right
        })
        .control_size(ControlSize::Mini)
        .variant(IconButtonVariant::GhostMuted)
        .label(if expanded {
            l.collapse_node_label
        } else {
            l.expand_node_label
        })
        .on_press(move |st: &mut ViewerState| st.toggle_node_expanded(&node_key))
        .build(k)
        .key(toggle_key)
        .focusable(false)
    } else {
        el().size(16.0, 16.0).a11y_hidden()
    }
}

#[allow(clippy::too_many_arguments)]
fn tree_group_row(
    s: &ViewerState,
    k: &Kit,
    row_key: String,
    node_key: String,
    icon_kind: StudioIcon,
    label: String,
    depth: u8,
    expanded: bool,
) -> El {
    let toggle_key = format!("toggle-{row_key}");
    let row_node_key = node_key.clone();
    let sb_row = SidebarRow::new(label)
        .avatar(icon_el(icon_kind, 15.0))
        .height(26.0)
        .on_select(move |st: &mut ViewerState, _| {
            st.toggle_node_expanded(&row_node_key);
        })
        .build(k)
        .key(row_key)
        .pl(4.0)
        .pr(6.0)
        .grow(1.0)
        .shrink()
        .min_w(0.0);

    row()
        .key(format!("wrap-group-{node_key}"))
        .w_full()
        .pl(depth as f32 * 14.0)
        .gap(2.0)
        .center_y()
        .child(disclosure_slot(s, k, Some((toggle_key, node_key, expanded))))
        .child(sb_row)
}

#[allow(clippy::too_many_arguments)]
fn outliner_object_row(
    s: &ViewerState,
    k: &Kit,
    object_id: u32,
    icon_kind: StudioIcon,
    label: &str,
    depth: u8,
    disclosure: Option<(String, bool)>,
    is_room: bool,
) -> El {
    let l = tr(s.locale);
    let selected = s.selected_ids.contains(&object_id);
    let is_editing = is_room && s.editing_room_id == Some(object_id);

    let mut sb = SidebarRow::new(label)
        .avatar(icon_el(icon_kind, 15.0))
        .height(26.0)
        .selected(selected)
        .on_select(move |st: &mut ViewerState, tx: &mut Tx| {
            st.select_object(object_id, tx.mods().shift, true);
        });
    if is_room {
        sb = sb.on_double_click(move |st: &mut ViewerState, _| {
            st.enter_room_edit_mode(object_id);
        });
    }
    if is_editing {
        sb = sb.badge(l.editing_badge);
    }

    let sb_el = sb
        .build(k)
        .key(format!("outliner-obj-{object_id}"))
        .pl(4.0)
        .pr(6.0)
        .grow(1.0)
        .shrink()
        .min_w(0.0);

    let slot =
        disclosure.map(|(node_key, expanded)| (format!("toggle-obj-{object_id}"), node_key, expanded));

    row()
        .key(format!("wrap-obj-{object_id}"))
        .w_full()
        .pl(depth as f32 * 14.0)
        .gap(2.0)
        .center_y()
        .child(disclosure_slot(s, k, slot))
        .child(sb_el)
}

fn append_shade_row(rows: &mut Vec<El>, s: &ViewerState, k: &Kit, sh: &ShadeNode, depth: u8) {
    let ic = s
        .scene
        .object_by_id(sh.object_id)
        .map_or(StudioIcon::LbtShade, lbt_record_icon);
    rows.push(outliner_object_row(
        s,
        k,
        sh.object_id,
        ic,
        &sh.label,
        depth,
        None,
        false,
    ));
}

fn append_subface_subtree(
    rows: &mut Vec<El>,
    s: &ViewerState,
    k: &Kit,
    sub: &SubfaceNode,
    depth: u8,
) {
    let node_key = format!("subface:{}", sub.object_id);
    let expanded = sub.has_children() && s.is_node_expanded(&node_key);
    let ic = lbt_object_icon(sub.kind);

    rows.push(outliner_object_row(
        s,
        k,
        sub.object_id,
        ic,
        &sub.label,
        depth,
        sub.has_children().then_some((node_key, expanded)),
        false,
    ));

    if expanded {
        for sh in &sub.shades {
            append_shade_row(rows, s, k, sh, depth + 1);
        }
    }
}

fn append_face_subtree(
    rows: &mut Vec<El>,
    s: &ViewerState,
    k: &Kit,
    face: &FaceNode,
    depth: u8,
) {
    let node_key = format!("face:{}", face.object_id);
    let expanded = face.has_children() && s.is_node_expanded(&node_key);

    rows.push(outliner_object_row(
        s,
        k,
        face.object_id,
        StudioIcon::LbtFace,
        &face.label,
        depth,
        face.has_children().then_some((node_key, expanded)),
        false,
    ));

    if expanded {
        // Strict direct child ordering under Face: Doors, then Apertures, then Shades.
        for dr in &face.doors {
            append_subface_subtree(rows, s, k, dr, depth + 1);
        }
        for ap in &face.apertures {
            append_subface_subtree(rows, s, k, ap, depth + 1);
        }
        for sh in &face.shades {
            append_shade_row(rows, s, k, sh, depth + 1);
        }
    }
}

fn build_model_tree_rows(s: &ViewerState, k: &Kit) -> Vec<El> {
    let mut rows = Vec::new();
    if s.outliner.is_empty() {
        return rows;
    }

    let l = tr(s.locale);
    let model_open = s.is_node_expanded("model");
    let model_label = s
        .outliner
        .model_name
        .as_deref()
        .unwrap_or(l.node_model)
        .to_owned();

    rows.push(tree_group_row(
        s,
        k,
        "tree-model".to_owned(),
        "model".to_owned(),
        StudioIcon::LbtModel,
        model_label,
        0,
        model_open,
    ));

    if !model_open {
        return rows;
    }

    // Direct Room children under Model
    for room in &s.outliner.rooms {
        let rid = room.object_id;
        let room_key = format!("room:{rid}");
        let room_open = room.has_children() && s.is_node_expanded(&room_key);

        rows.push(outliner_object_row(
            s,
            k,
            rid,
            StudioIcon::LbtRoom,
            &room.label,
            1,
            room.has_children().then_some((room_key, room_open)),
            true,
        ));

        if room_open {
            // Strict direct child ordering under Room: Faces, then Room Shades.
            for face in &room.faces {
                append_face_subtree(&mut rows, s, k, face, 2);
            }
            for sh in &room.shades {
                append_shade_row(&mut rows, s, k, sh, 2);
            }
        }
    }

    // Optional top-level orphaned groups under Model (shown ONLY when non-empty)
    if !s.outliner.orphaned_shades.is_empty() {
        let open = s.is_node_expanded("orphaned:shades");
        rows.push(tree_group_row(
            s,
            k,
            "tree-shades".to_owned(),
            "orphaned:shades".to_owned(),
            StudioIcon::LbtContextShade,
            l.node_shades.to_owned(),
            1,
            open,
        ));
        if open {
            for sh in &s.outliner.orphaned_shades {
                append_shade_row(&mut rows, s, k, sh, 2);
            }
        }
    }

    if !s.outliner.orphaned_faces.is_empty() {
        let open = s.is_node_expanded("orphaned:faces");
        rows.push(tree_group_row(
            s,
            k,
            "tree-faces".to_owned(),
            "orphaned:faces".to_owned(),
            StudioIcon::LbtFace,
            l.node_faces.to_owned(),
            1,
            open,
        ));
        if open {
            for face in &s.outliner.orphaned_faces {
                append_face_subtree(&mut rows, s, k, face, 2);
            }
        }
    }

    if !s.outliner.orphaned_apertures.is_empty() {
        let open = s.is_node_expanded("orphaned:apertures");
        rows.push(tree_group_row(
            s,
            k,
            "tree-apertures".to_owned(),
            "orphaned:apertures".to_owned(),
            StudioIcon::LbtAperture,
            l.node_apertures.to_owned(),
            1,
            open,
        ));
        if open {
            for ap in &s.outliner.orphaned_apertures {
                append_subface_subtree(&mut rows, s, k, ap, 2);
            }
        }
    }

    if !s.outliner.orphaned_doors.is_empty() {
        let open = s.is_node_expanded("orphaned:doors");
        rows.push(tree_group_row(
            s,
            k,
            "tree-doors".to_owned(),
            "orphaned:doors".to_owned(),
            StudioIcon::LbtDoor,
            l.node_doors.to_owned(),
            1,
            open,
        ));
        if open {
            for dr in &s.outliner.orphaned_doors {
                append_subface_subtree(&mut rows, s, k, dr, 2);
            }
        }
    }

    rows
}

fn build_sidebar(s: &ViewerState, k: &Kit) -> El {
    let l = tr(s.locale);
    let mut sb = Sidebar::new().label(l.node_model).row_gap(1.0);
    for item in build_model_tree_rows(s, k) {
        sb = sb.child(item);
    }
    sb.build(k)
}

// ============================================================================
// Right Inspector — Clean Read-Only Honeybee Object Property Inspector
// ============================================================================

fn prop_row(label: &str, value: String, k: &Kit) -> El {
    row()
        .w_full()
        .justify_between()
        .center_y()
        .gap(8.0)
        .child(text(label).font(k.ty.small).color(k.c.text_muted))
        .child(
            text(value)
                .font(k.ty.ui)
                .color(k.c.text_base)
                .truncate()
                .shrink(),
        )
}

fn build_inspector(s: &ViewerState, k: &Kit) -> El {
    let Some(rec) = s.primary_selected() else {
        return col()
            .key("right-inspector")
            .w_full()
            .h_full()
            .fill(k.c.bg_deep);
    };
    let l = tr(s.locale);

    let title = rec
        .display_name
        .as_deref()
        .filter(|n| !n.trim().is_empty())
        .unwrap_or(&rec.identifier);

    let mut header = row()
        .w_full()
        .gap(8.0)
        .center_y()
        .child(icon_el(lbt_record_icon(rec), 16.0))
        .child(
            text(title)
                .key("inspector-title")
                .font(k.ty.ui_medium)
                .color(k.c.text_base)
                .truncate()
                .grow(1.0)
                .shrink(),
        )
        .child(
            Badge::new(object_kind_label(s.locale, rec.kind))
                .variant(BadgeVariant::Subtle)
                .build(k),
        );
    if s.selected_ids.len() > 1 {
        header = header.child(
            Badge::new(format!("+{}", s.selected_ids.len() - 1))
                .variant(BadgeVariant::Accent)
                .build(k),
        );
    }

    let mut props = col()
        .key("inspector-props")
        .w_full()
        .grow(1.0)
        .min_h(0.0)
        .scroll(ScrollSpec::default())
        .padding(12.0)
        .gap(8.0)
        .child(header)
        .child(Divider::horizontal().build(k));

    // Only genuine populated Honeybee SDK properties (zero blank "—" fields, zero "ID xx")
    if let Some(parent_room) = s.parent_room_label(rec) {
        props = props.child(prop_row(l.prop_room, parent_room, k));
    }
    if let Some(area) = rec.area {
        props = props.child(prop_row(l.prop_area, format!("{area:.2} m²"), k));
    }
    if rec.kind != ObjectKind::Room
        && let Some(raw_orient) =
            average_object_normal(&s.scene, rec.object_id).map(orientation_from_normal)
        && let Some(orient) = orientation_label(s.locale, raw_orient)
    {
        props = props.child(prop_row(l.prop_orientation, orient.to_owned(), k));
    }
    if let Some(bc) = rec
        .boundary_condition
        .as_deref()
        .filter(|v| !v.trim().is_empty())
    {
        props = props.child(prop_row(
            l.prop_boundary,
            translate_display_category(s.locale, bc, bc).into_owned(),
            k,
        ));
    }
    if let Some(ft) = rec.face_type.as_deref().filter(|v| !v.trim().is_empty()) {
        props = props.child(prop_row(
            l.prop_face_type,
            translate_display_category(s.locale, ft, ft).into_owned(),
            k,
        ));
    }
    if let Some(story) = rec.story.as_deref().filter(|v| !v.trim().is_empty()) {
        props = props.child(prop_row(l.prop_story, story.to_owned(), k));
    }
    if let Some(zone) = rec.zone.as_deref().filter(|v| !v.trim().is_empty()) {
        props = props.child(prop_row(l.prop_zone, zone.to_owned(), k));
    }
    if let Some(program) = rec.program_type.as_deref().filter(|v| !v.trim().is_empty()) {
        props = props.child(prop_row(l.prop_program, program.to_owned(), k));
    }
    if let Some(constr) = rec
        .construction_set
        .as_deref()
        .filter(|v| !v.trim().is_empty())
    {
        props = props.child(prop_row(l.prop_construction, constr.to_owned(), k));
    }
    if let Some(hvac) = rec.hvac.as_deref().filter(|v| !v.trim().is_empty()) {
        props = props.child(prop_row(l.prop_hvac, hvac.to_owned(), k));
    }
    if rec.kind == ObjectKind::Door {
        props = props.child(prop_row(
            l.prop_glazing,
            if rec.is_glass {
                l.val_glass
            } else {
                l.val_opaque
            }
            .to_owned(),
            k,
        ));
    }
    if rec.kind == ObjectKind::Shade {
        let placement = if rec.is_indoor_shade {
            l.val_indoor
        } else if rec.is_detached_shade {
            l.val_context
        } else {
            l.val_outdoor
        };
        props = props.child(prop_row(l.prop_shade_placement, placement.to_owned(), k));
    }
    if rec.is_orphaned {
        props = props.child(prop_row(l.prop_hierarchy, l.val_orphaned.to_owned(), k));
    }

    let child_shades = s
        .scene
        .objects
        .iter()
        .filter(|o| o.kind == ObjectKind::Shade && o.parent_object_id == Some(rec.object_id))
        .count();
    if child_shades > 0 {
        props = props.child(prop_row(l.prop_shades, child_shades.to_string(), k));
    }

    let swatch = srgb_rgba_to_color(lbt_scene::color_for_object_in_scene(
        &s.scene, rec, s.color_by,
    ));
    props = props.child(
        row()
            .w_full()
            .justify_between()
            .center_y()
            .child(text(l.prop_color).font(k.ty.small).color(k.c.text_muted))
            .child(
                el().size(28.0, 12.0)
                    .radius(k.radius.xs)
                    .fill(swatch)
                    .border(0.5, k.c.border_strong),
            ),
    );

    col()
        .key("right-inspector")
        .w_full()
        .h_full()
        .min_h(0.0)
        .fill(k.c.bg_deep)
        .child(props)
}

// ============================================================================
// 3D Viewport, Room Edit Breadcrumb, Axis HUD, and Authentic Ladybug 2D Legend
// ============================================================================

fn axis_hud(s: &ViewerState, k: &Kit) -> El {
    let (r, u, _f) = s.renderer.camera_basis();
    let project_axis = |axis: [f32; 3]| -> [f32; 2] {
        let sx = axis[0] * r[0] + axis[1] * r[1] + axis[2] * r[2];
        let sy = -(axis[0] * u[0] + axis[1] * u[1] + axis[2] * u[2]);
        [24.0 + sx * 15.0, 24.0 + sy * 15.0]
    };
    let origin = [24.0, 24.0];
    let ax_x = project_axis([1.0, 0.0, 0.0]);
    let ax_y = project_axis([0.0, 1.0, 0.0]);
    let ax_z = project_axis([0.0, 0.0, 1.0]);

    let shape = Shape::new()
        .line(origin, ax_x, 1.7, LineCap::Round, rgba8(230, 86, 86, 255))
        .line(origin, ax_y, 2.1, LineCap::Round, rgba8(72, 200, 130, 255))
        .line(origin, ax_z, 1.7, LineCap::Round, rgba8(90, 155, 245, 255));

    let north_pos = [
        (ax_y[0] - 4.0).clamp(2.0, 38.0),
        (ax_y[1] - 6.0).clamp(1.0, 36.0),
    ];

    el().key("axis-hud")
        .size(48.0, 48.0)
        .radius(24.0)
        .fill(k.c.layer_01.alpha(0.88))
        .border(1.0, k.c.border_base)
        .pin(None, Some(12.0), Some(12.0), None)
        .child(
            tinted_icon_el(StudioIcon::LbtCompass, 36.0, k.c.text_faint.alpha(0.18))
                .absolute(6.0, 6.0),
        )
        .child(canvas(shape).size(48.0, 48.0))
        .child(
            text("N")
                .font(TextStyle::new(9.0, 800.0))
                .color(rgba8(82, 215, 140, 255))
                .absolute(north_pos[0], north_pos[1]),
        )
}

/// Clean `rune-kit` SketchUp/OpenStudio-style Room Edit Mode breadcrumb bar (top-left of viewport).
fn room_edit_breadcrumb(s: &ViewerState, k: &Kit) -> Option<El> {
    let room = s.editing_room()?;
    let l = tr(s.locale);
    let room_name = room
        .display_name
        .as_deref()
        .filter(|n| !n.trim().is_empty())
        .unwrap_or(&room.identifier);

    let model_crumb = k.interactive(
        row()
            .key("btn-breadcrumb-model")
            .role("button")
            .label(l.node_model)
            .h(22.0)
            .px(6.0)
            .gap(5.0)
            .center_y()
            .radius(k.radius.sm)
            .cursor(Cursor::Pointer)
            .on_press(|st: &mut ViewerState| st.exit_room_edit_mode())
            .child(icon_el(StudioIcon::LbtModel, 14.0))
            .child(
                text(l.node_model)
                    .font(k.ty.ui_compact)
                    .color(k.c.text_muted),
            ),
    );

    let exit_btn = Button::new(l.exit_breadcrumb_btn)
        .variant(ButtonVariant::Contrast)
        .control_size(ControlSize::Small)
        .on_press(|st: &mut ViewerState| st.exit_room_edit_mode())
        .build(k)
        .key("btn-exit-room-edit");

    let bar = row()
        .key("room-edit-breadcrumb")
        .h(32.0)
        .px(8.0)
        .gap(6.0)
        .center_y()
        .radius(k.radius.md)
        .fill(k.c.layer_01)
        .child(model_crumb)
        .child(icon(k.glyph.caret_right, 12.0).color(k.c.icon_faint))
        .child(icon_el(StudioIcon::LbtRoom, 14.0))
        .child(
            text(room_name)
                .key("room-edit-name")
                .font(k.ty.ui_medium)
                .color(k.c.text_base)
                .truncate()
                .max_w(180.0),
        )
        .child(el().h(14.0).child(Divider::vertical().build(k)))
        .child(exit_btn);

    Some(
        k.elevate(bar, &k.elevation.floating)
            .pin(Some(12.0), Some(12.0), None, None),
    )
}

/// Authentic Ladybug Tools 2D Legend overlay — faithful to `ladybug/legend.py`
/// (`Legend2DParameters`, `color_map_2d`, `segment_text_location_2d`, `title_location_2d`)
/// and `ladybug_display/analysis.py` (`legend_2d_to_svg`).
fn ladybug_legend_widget(s: &ViewerState) -> Option<El> {
    let legend = build_legend(&s.scene, s.color_by);
    if legend.entries.is_empty() {
        return None;
    }

    let [_vw, vh] = s.viewport_pts;
    let avail_h = (vh - 120.0).max(80.0);
    let seg_h = (avail_h / legend.entries.len() as f32).clamp(18.0, 26.0);

    let (legend_fg, bar_border) = if s.dark_mode {
        (rgba8(232, 236, 242, 255), rgba8(140, 150, 168, 255))
    } else {
        (rgba8(17, 24, 39, 255), rgba8(17, 24, 39, 255))
    };

    let title_text = color_by_full(s.locale, s.color_by);

    let mut color_bar = col()
        .key("legend-color-bar")
        .w(24.0)
        .padding(1.0)
        .gap(0.0)
        .radius(0.0)
        .fill(bar_border);

    let mut label_col = col().gap(0.0).py(1.0);

    for (idx, entry) in legend.entries.iter().enumerate() {
        let seg_fill = srgb_rgb_opaque(entry.color_srgb);
        let display_label =
            translate_display_category(s.locale, &entry.key, &entry.label).into_owned();

        color_bar = color_bar.child(
            el().key(format!("legend-seg-{idx}"))
                .w_full()
                .h(seg_h)
                .radius(0.0)
                .fill(seg_fill),
        );

        label_col = label_col.child(
            row()
                .key(format!("legend-entry-{idx}"))
                .h(seg_h)
                .items_center()
                .child(
                    text(display_label)
                        .font(TextStyle::new(11.5, 400.0))
                        .color(legend_fg),
                ),
        );
    }

    Some(
        col()
            .key("ladybug-legend")
            .gap(6.0)
            .items_start()
            .pin(None, None, Some(16.0), Some(18.0))
            .child(
                text(title_text)
                    .key("legend-title")
                    .font(TextStyle::new(12.0, 600.0))
                    .color(legend_fg),
            )
            .child(
                row()
                    .gap(7.0)
                    .items_start()
                    .child(color_bar)
                    .child(label_col),
            ),
    )
}

fn viewport_pane(s: &ViewerState, k: &Kit) -> El {
    let mut stack = el()
        .key("viewport-pane")
        .w_full()
        .h_full()
        .min_w(0.0)
        .min_h(0.0)
        .fill(viewport_bg(s.dark_mode))
        .clip_rounded(0.0);

    let viewport_surface = if s.use_compositor {
        el().effect(crate::compositor::VIEWPORT_EFFECT_MARK)
    } else {
        el().pixels(&s.viewport_pixels)
    };
    let pixel_canvas = viewport_surface
        .key("viewport-canvas")
        .w_full()
        .h_full()
        .cursor(if s.drag_moved {
            Cursor::Grabbing
        } else {
            Cursor::Grab
        })
        .pointer_buttons([PointerButton::Secondary, PointerButton::Middle])
        .on_layout_tx(|st: &mut ViewerState, rect: [f32; 4], tx: &mut Tx| {
            st.on_viewport_layout(rect[2], rect[3], tx.scale());
        })
        .on_drag(|st: &mut ViewerState, d: &mut Drag, tx: &mut Tx| match d.phase {
            Phase::Down => {
                st.open_menu = None;
                st.drag_prev_xy = [d.x, d.y];
                st.drag_start_pose = Some(st.renderer.camera_pose());
                st.drag_moved = false;
                let btn = tx.button();
                st.drag_pan = btn == PointerButton::Secondary
                    || btn == PointerButton::Middle
                    || tx.mods().shift;
            }
            Phase::Move => {
                let step_dx = d.x - st.drag_prev_xy[0];
                let step_dy = d.y - st.drag_prev_xy[1];
                st.drag_prev_xy = [d.x, d.y];
                if d.dx * d.dx + d.dy * d.dy > 9.0 {
                    st.drag_moved = true;
                }
                if step_dx.abs() > 0.0 || step_dy.abs() > 0.0 {
                    if st.drag_pan {
                        st.renderer.pan_pixels(
                            step_dx,
                            step_dy,
                            st.viewport_pts[1].round().max(1.0) as u32,
                        );
                    } else {
                        st.renderer.orbit_pixels(step_dx, step_dy, 0.008);
                    }
                    st.render_viewport_now();
                }
            }
            Phase::Up => {
                if d.cancelled() {
                    if let Some(pose) = st.drag_start_pose.take() {
                        st.renderer.apply_camera_pose(&pose);
                        st.render_viewport_now();
                    }
                } else {
                    st.drag_start_pose = None;
                    if st.drag_moved {
                        st.flush_interaction_state();
                    }
                }
                st.drag_moved = false;
                st.drag_pan = false;
            }
        })
        .on_background_press_tx(|st: &mut ViewerState, tx: &mut Tx| {
            if let Some(pt) = tx.press_point() {
                st.handle_viewport_click(pt.x, pt.y, tx.mods().shift);
            }
        })
        .on_double_press_tx(|st: &mut ViewerState, tx: &mut Tx| {
            if let Some(pt) = tx.press_point() {
                st.handle_viewport_double_click(pt.x, pt.y);
            }
        })
        .on_wheel(|st: &mut ViewerState, ev: WheelEvent, tx: &mut Tx| {
            let divisor = if ev.precise {
                60.0
            } else if cfg!(target_os = "linux") {
                120.0
            } else {
                40.0
            };
            st.renderer.zoom_wheel(ev.dy / divisor);
            st.render_viewport_now();
            st.camera_flush_due = Some(0.0);
            tx.wake_after(Duration::from_millis(260));
            true
        })
        .on_magnify(|st: &mut ViewerState, ev: MagnifyEvent, tx: &mut Tx| {
            let factor = 1.0 / (1.0 + ev.delta).clamp(0.5, 2.0);
            st.renderer.zoom_factor(factor);
            st.render_viewport_now();
            st.camera_flush_due = Some(0.0);
            tx.wake_after(Duration::from_millis(260));
            true
        });

    stack = stack.child(pixel_canvas);

    // Room Edit Mode Breadcrumb Bar (top-left)
    if let Some(crumb) = room_edit_breadcrumb(s, k) {
        stack = stack.child(crumb);
    }

    // Live 3D North & XYZ Axis HUD (top-right)
    stack = stack.child(axis_hud(s, k));

    // Authentic borderless Ladybug Tools 2D Legend (bottom-right)
    if s.show_legend
        && let Some(legend_el) = ladybug_legend_widget(s)
    {
        stack = stack.child(legend_el);
    }

    stack
}

// ============================================================================
// Root Error Toast (Only shown if a runtime load/render error occurs)
// ============================================================================

fn mount_status_toast(s: &ViewerState, k: &Kit, layer: &mut Vec<El>) {
    let Some(msg) = &s.status_banner else {
        return;
    };
    let toast = Toast::new("status-toast", msg)
        .on_close(|st: &mut ViewerState| st.status_banner = None)
        .build(k);
    layer.push(ToastRegion::new().toast(toast).build(k));
}

// ============================================================================
// Primary Rune View & Window Key Handler
// ============================================================================

/// Primary Rune + `rune-kit` view builder for `lbt-rune-viewer`.
pub fn view(s: &ViewerState, cx: &mut Cx<ViewerState>) -> El {
    let k = studio_kit(s.dark_mode);
    let l = tr(s.locale);
    cx.foreground(k.c.text_base);
    cx.press_cursor(Cursor::Pointer);
    cx.focus_ring(2.0, 2.0, k.c.border_focus);
    cx.help_look(TooltipStyle::from_kit(&k, TooltipAppearance::Compact).help_look());

    let mut layer = Vec::new();
    let toolbar = build_toolbar(s, &k, &mut layer);
    let sidebar_el = build_sidebar(s, &k);
    let inspector_el = build_inspector(s, &k);
    let viewport_el = viewport_pane(s, &k);

    let shell_el = SplitView::new(viewport_el)
        .sidebar(
            &s.sidebar_pane,
            |st: &mut ViewerState| &mut st.sidebar_pane,
            sidebar_el,
        )
        .inspector(
            &s.inspector_pane,
            |st: &mut ViewerState| &mut st.inspector_pane,
            inspector_el,
        )
        .toolbar(toolbar)
        .flat_main(true)
        .titlebar_inset(cx.titlebar_inset())
        .sidebar_toggle(SidebarToggle::new().labels(l.show_sidebar, l.hide_sidebar))
        .reduced_motion(cx.is_reduced_motion())
        .build(&k);

    mount_status_toast(s, &k, &mut layer);

    rune_kit::root(shell_el, layer)
}

/// Window-level keyboard shortcuts when no text input handles the key.
pub fn on_window_key(s: &mut ViewerState, ev: &KeyEvent, _tx: &mut Tx) -> bool {
    if rune_kit::shell::is_sidebar_toggle(ev) {
        s.sidebar_pane.toggle();
        return true;
    }

    match &ev.key {
        Key::Escape => {
            if s.open_menu.is_some() {
                s.open_menu = None;
                return true;
            }
            if s.editing_room_id.is_some() {
                s.exit_room_edit_mode();
                return true;
            }
            if !s.selected_ids.is_empty() {
                s.clear_selection();
                return true;
            }
            false
        }
        Key::Text(ch) if !ev.mods.cmd && !ev.mods.ctrl && !ev.mods.alt => match ch.as_str() {
            "f" | "F" => {
                s.apply_camera_preset(CameraPreset::Fit);
                true
            }
            "l" | "L" => {
                s.toggle_legend();
                true
            }
            _ => false,
        },
        _ => false,
    }
}

#[cfg(test)]
mod tests {
    use lbt_scene::{
        Bounds3, Callout, ColorBy, IsolationMode, MeshVertex, ObjectKind, ObjectRecord,
        ObjectTargetRef, PinStatus, SceneData, SpatialPin, ValidationIssue,
    };
    use rune::{Env, Key, KeyEvent, Runtime};

    use super::*;
    use crate::engine::{CpuCameraBackend, ViewerPickHit};

    fn sample_scene_with_room_and_orphan() -> SceneData {
        let wall_normal = [0.0, -1.0, 0.0];
        let v = |pos: [f32; 3], oid: u32, kind: ObjectKind| MeshVertex {
            position: pos,
            normal: wall_normal,
            object_id: oid,
            kind_code: kind.kind_code(),
        };
        let mut face_target =
            ObjectTargetRef::new(None, "OfficeModel", ObjectKind::Face, "Wall_South");
        face_target
            .parent
            .insert("room".to_owned(), "Room_South_1".to_owned());
        let mut ap_target =
            ObjectTargetRef::new(None, "OfficeModel", ObjectKind::Aperture, "Window_South");
        ap_target
            .parent
            .insert("room".to_owned(), "Room_South_1".to_owned());
        ap_target
            .parent
            .insert("face".to_owned(), "Wall_South".to_owned());
        let mut door_target =
            ObjectTargetRef::new(None, "OfficeModel", ObjectKind::Door, "Glass_Patio_Door");
        door_target
            .parent
            .insert("room".to_owned(), "Room_South_1".to_owned());
        door_target
            .parent
            .insert("face".to_owned(), "Wall_South".to_owned());

        SceneData {
            model_identifier: "OfficeModel".to_owned(),
            display_name: Some("South Office Model".to_owned()),
            units: Some("Meters".to_owned()),
            source_path: Some("office.hbjson".to_owned()),
            bounds: Bounds3::new([0.0, 0.0, 0.0], [10.0, 8.0, 4.0]),
            vertices: vec![
                v([0.0, 0.0, 0.0], 2, ObjectKind::Face),
                v([10.0, 0.0, 0.0], 2, ObjectKind::Face),
                v([10.0, 0.0, 4.0], 2, ObjectKind::Face),
                v([2.0, 0.0, 1.0], 3, ObjectKind::Aperture),
                v([8.0, 0.0, 1.0], 3, ObjectKind::Aperture),
                v([8.0, 0.0, 3.0], 3, ObjectKind::Aperture),
                v([0.0, -2.0, 3.0], 5, ObjectKind::Shade),
                v([4.0, -2.0, 3.0], 5, ObjectKind::Shade),
                v([4.0, -3.0, 3.0], 5, ObjectKind::Shade),
            ],
            indices: vec![0, 1, 2, 3, 4, 5, 6, 7, 8],
            edge_vertices: Vec::new(),
            objects: vec![
                ObjectRecord {
                    object_id: 1,
                    kind: ObjectKind::Room,
                    identifier: "Room_South_1".to_owned(),
                    display_name: Some("South Office".to_owned()),
                    target: ObjectTargetRef::new(
                        None,
                        "OfficeModel",
                        ObjectKind::Room,
                        "Room_South_1",
                    ),
                    parent_object_id: None,
                    owner_room_id: Some(1),
                    is_orphaned: false,
                    is_glass: false,
                    is_indoor_shade: false,
                    is_detached_shade: false,
                    is_shade_mesh: false,
                    bounds: Bounds3::new([0.0, 0.0, 0.0], [10.0, 8.0, 4.0]),
                    centroid: [5.0, 4.0, 2.0],
                    face_type: None,
                    boundary_condition: None,
                    area: Some(80.0),
                    wwr: None,
                    story: Some("Level 1".to_owned()),
                    zone: Some("CoreSouth".to_owned()),
                    program_type: Some("Generic Office".to_owned()),
                    construction_set: Some("ASHRAE 90.1".to_owned()),
                    hvac: Some("VAV Reheat".to_owned()),
                },
                ObjectRecord {
                    object_id: 2,
                    kind: ObjectKind::Face,
                    identifier: "Wall_South".to_owned(),
                    display_name: None,
                    target: face_target,
                    parent_object_id: Some(1),
                    owner_room_id: Some(1),
                    is_orphaned: false,
                    is_glass: false,
                    is_indoor_shade: false,
                    is_detached_shade: false,
                    is_shade_mesh: false,
                    bounds: Bounds3::new([0.0, 0.0, 0.0], [10.0, 0.0, 4.0]),
                    centroid: [5.0, 0.0, 2.0],
                    area: Some(40.0),
                    face_type: Some("Wall".to_owned()),
                    boundary_condition: Some("Outdoors".to_owned()),
                    wwr: None,
                    story: Some("Level 1".to_owned()),
                    zone: Some("CoreSouth".to_owned()),
                    program_type: Some("Generic Office".to_owned()),
                    construction_set: Some("ASHRAE 90.1".to_owned()),
                    hvac: Some("VAV Reheat".to_owned()),
                },
                ObjectRecord {
                    object_id: 3,
                    kind: ObjectKind::Aperture,
                    identifier: "Window_South".to_owned(),
                    display_name: None,
                    target: ap_target,
                    parent_object_id: Some(2),
                    owner_room_id: Some(1),
                    is_orphaned: false,
                    is_glass: false,
                    is_indoor_shade: false,
                    is_detached_shade: false,
                    is_shade_mesh: false,
                    bounds: Bounds3::new([2.0, 0.0, 1.0], [8.0, 0.0, 3.0]),
                    centroid: [5.0, 0.0, 2.0],
                    face_type: None,
                    area: Some(12.0),
                    boundary_condition: Some("Outdoors".to_owned()),
                    wwr: None,
                    story: Some("Level 1".to_owned()),
                    zone: Some("CoreSouth".to_owned()),
                    program_type: Some("Generic Office".to_owned()),
                    construction_set: Some("ASHRAE 90.1".to_owned()),
                    hvac: Some("VAV Reheat".to_owned()),
                },
                ObjectRecord {
                    object_id: 4,
                    kind: ObjectKind::Door,
                    identifier: "Glass_Patio_Door".to_owned(),
                    display_name: None,
                    target: door_target,
                    parent_object_id: Some(2),
                    owner_room_id: Some(1),
                    is_orphaned: false,
                    is_glass: true,
                    is_indoor_shade: false,
                    is_detached_shade: false,
                    is_shade_mesh: false,
                    bounds: Bounds3::new([0.5, 0.0, 0.0], [1.5, 0.0, 2.2]),
                    centroid: [1.0, 0.0, 1.1],
                    face_type: None,
                    area: Some(2.2),
                    boundary_condition: Some("Outdoors".to_owned()),
                    wwr: None,
                    story: Some("Level 1".to_owned()),
                    zone: Some("CoreSouth".to_owned()),
                    program_type: Some("Generic Office".to_owned()),
                    construction_set: Some("ASHRAE 90.1".to_owned()),
                    hvac: Some("VAV Reheat".to_owned()),
                },
                ObjectRecord {
                    object_id: 5,
                    kind: ObjectKind::Shade,
                    identifier: "Context_Canopy".to_owned(),
                    display_name: Some("Context Canopy".to_owned()),
                    target: ObjectTargetRef::new(
                        None,
                        "OfficeModel",
                        ObjectKind::Shade,
                        "Context_Canopy",
                    ),
                    parent_object_id: None,
                    owner_room_id: None,
                    is_orphaned: true,
                    is_glass: false,
                    is_indoor_shade: false,
                    is_detached_shade: true,
                    is_shade_mesh: false,
                    bounds: Bounds3::new([0.0, -3.0, 3.0], [4.0, -2.0, 3.0]),
                    centroid: [2.0, -2.5, 3.0],
                    face_type: Some("ContextShade".to_owned()),
                    boundary_condition: None,
                    area: Some(4.0),
                    wwr: None,
                    story: None,
                    zone: None,
                    program_type: None,
                    construction_set: None,
                    hvac: None,
                },
            ],
            stories: vec!["Level 1".to_owned()],
        }
    }

    fn step_frames(rt: &mut Runtime<ViewerState>) {
        for _ in 0..8 {
            rt.frame(0.05);
        }
    }

    fn click_key(rt: &mut Runtime<ViewerState>, key: &str) {
        let (x, y) = rt
            .find(key)
            .unwrap_or_else(|| panic!("missing key {key:?}"));
        rt.pointer_move(x, y);
        rt.pointer_down(x, y);
        rt.pointer_up(x, y);
        step_frames(rt);
    }

    fn click_label(rt: &mut Runtime<ViewerState>, label: &str) {
        let info = rt
            .elements()
            .into_iter()
            .find(|e| e.label.as_deref() == Some(label))
            .unwrap_or_else(|| panic!("missing element with label {label:?}"));
        let x = info.rect[0] + info.rect[2] * 0.5;
        let y = info.rect[1] + info.rect[3] * 0.5;
        rt.pointer_move(x, y);
        rt.pointer_down(x, y);
        rt.pointer_up(x, y);
        step_frames(rt);
    }

    fn double_click_xy(rt: &mut Runtime<ViewerState>, x: f32, y: f32) {
        for _ in 0..12 {
            rt.frame(0.1);
        }
        rt.pointer_move(x, y);
        for _ in 0..2 {
            rt.pointer_down(x, y);
            rt.frame(1.0 / 120.0);
            rt.pointer_up(x, y);
            rt.frame(1.0 / 120.0);
        }
        step_frames(rt);
    }

    #[test]
    fn pure_model_tree_three_control_toolbar_view_popover_and_readonly_inspector_work() {
        let mut state = ViewerState::new(sample_scene_with_room_and_orphan(), "South Office", None);
        state.present_title = Some("Live Inspection".to_owned());
        state.present_note = Some("Do not render instructional notes in sidebar.".to_owned());
        // Even if present.json includes validation issues, pins, and highlight targets,
        // none of them render UI chrome or force tint overrides!
        state.highlight_ids = vec![2, 3];
        state.isolation_mode = IsolationMode::GhostContext;
        state.validation_issues.push(ValidationIssue {
            code: Some("HB_WARN".to_owned()),
            severity: Some("warning".to_owned()),
            message: "Check floor area".to_owned(),
            element_id: vec!["Wall_South".to_owned()],
            target: Some(state.scene.objects[1].target.clone()),
            ..Default::default()
        });
        state.annotations.push(SpatialPin {
            id: "pin_hidden_1".to_owned(),
            status: PinStatus::Open,
            target: Some(state.scene.objects[2].target.clone()),
            world_point: Some([5.0, 0.0, 2.0]),
            comment: "Hidden protocol pin".to_owned(),
            ..Default::default()
        });
        state.callouts.push(Callout {
            id: Some("callout_1".to_owned()),
            target: Some(state.scene.objects[1].target.clone()),
            world_point: Some([5.0, 0.0, 2.0]),
            label: "South Wall Check".to_owned(),
            detail: None,
            severity: Some("warning".to_owned()),
            color: None,
        });

        // Verify zero forced coloring overrides in current_render_state()
        let rs = state.current_render_state();
        assert!(rs.highlighted_ids.is_empty());
        assert!(rs.validation_error_ids.is_empty());
        assert!(rs.validation_warning_ids.is_empty());
        assert_eq!(rs.isolation_mode, IsolationMode::Highlight);

        let mut rt = Runtime::new(state, view, (1280.0, 800.0), Env::new(true, 1.0));
        rt.on_key = Some(on_window_key);
        step_frames(&mut rt);

        // Removed features MUST NOT exist anywhere in the UI tree
        for forbidden_key in [
            "sidebar-tabs",
            "btn-tools-menu",
            "tools-menu-menu",
            "pin-dialog",
            "pin-mode-badge",
            "pin-mode-banner",
            "pin-item-pin_hidden_1",
            "issue-item-0",
            "inspector-actions",
            "btn-edit-room",
            "btn-isolate",
            "btn-select-similar",
            "btn-pin-here",
            "btn-clear-sel",
            "status-toast",
        ] {
            assert!(
                rt.find(forbidden_key).is_none(),
                "Removed element {forbidden_key:?} must not render!"
            );
        }
        for e in rt.elements() {
            if let Some(lbl) = &e.label {
                assert!(
                    !matches!(
                        lbl.as_str(),
                        "Pins" | "Issues" | "Tools" | "标注" | "问题" | "工具"
                    ) && !lbl.contains("Do not render instructional notes")
                        && !lbl.contains("(Esc)"),
                    "Unexpected removed label found: {lbl:?}"
                );
            }
            assert!(
                !e.key
                    .as_deref()
                    .is_some_and(|k| k.starts_with("pin-badge-") || k.starts_with("callout-")),
                "Found unexpected floating 3D pill!"
            );
        }

        // Authentic Ladybug Legend visible; SplitView sidebar open at 260pt, inspector collapsed
        assert!(rt.state.show_legend);
        assert!(rt.state.sidebar_pane.is_open());
        assert!((rt.state.sidebar_pane.width() - 260.0).abs() < 0.5);
        assert!(!rt.state.inspector_pane.is_open());
        assert!(rt.find("ladybug-legend").is_some());
        assert!(rt.find("legend-color-bar").is_some());
        assert!(rt.find("legend-entry-0").is_some());

        // Direct Honeybee Schema tree with SidebarRow inside 260pt sidebar: zero synthetic folders
        assert!(rt.find("tree-model").is_some());
        assert!(rt.find("tree-rooms").is_none());
        assert!(rt.find("tree-orphaned").is_none());
        assert!(rt.find("outliner-obj-1").is_some());
        assert!(rt.find("outliner-obj-2").is_some());
        assert!(rt.find("tree-shades").is_some());

        let elems_tree = rt.elements();
        let obj1 = elems_tree
            .iter()
            .find(|e| e.key.as_deref() == Some("outliner-obj-1"))
            .unwrap();
        let tog2 = elems_tree
            .iter()
            .find(|e| e.key.as_deref() == Some("toggle-obj-2"))
            .unwrap();
        let obj2 = elems_tree
            .iter()
            .find(|e| e.key.as_deref() == Some("outliner-obj-2"))
            .unwrap();
        assert!(
            obj1.rect[0] + obj1.rect[2] <= 260.5 && obj2.rect[0] + obj2.rect[2] <= 260.5,
            "SidebarRow overflowed 260px sidebar: obj1={:?} obj2={:?}",
            obj1.rect,
            obj2.rect
        );
        assert!(
            tog2.rect[0] + tog2.rect[2] <= obj2.rect[0] + 0.5,
            "Disclosure chevron overlapped SidebarRow: tog2={:?} obj2={:?}",
            tog2.rect,
            obj2.rect
        );

        // Expand Face 2 -> direct children Door 4, Aperture 3 (Doors precede Apertures)
        click_key(&mut rt, "toggle-obj-2");
        assert!(rt.find("outliner-obj-4").is_some());
        assert!(rt.find("outliner-obj-3").is_some());
        let (_, door_y) = rt.find("outliner-obj-4").unwrap();
        let (_, ap_y) = rt.find("outliner-obj-3").unwrap();
        assert!(door_y < ap_y, "Doors must precede Apertures under Face");

        // Expand top-level Shades -> Context_Canopy (5)
        click_key(&mut rt, "tree-shades");
        assert!(rt.find("outliner-obj-5").is_some());

        // Collapse Model root hides descendants; re-expanding restores them
        click_key(&mut rt, "tree-model");
        assert!(rt.find("outliner-obj-1").is_none());
        click_key(&mut rt, "tree-model");
        assert!(rt.find("outliner-obj-1").is_some());

        // ColorBy Select trigger + full-width Menu: strictly 7 Honeybee SDK presets (no WWR)
        click_key(&mut rt, "color-by-trigger");
        assert_eq!(rt.state.open_menu, Some(TopMenu::ColorBy));
        assert!(rt.find("color-by-menu").is_some());
        let elems_menu = rt.elements();
        let cb_menu = elems_menu
            .iter()
            .find(|e| e.key.as_deref() == Some("color-by-menu"))
            .expect("color-by-menu surface");
        assert!(
            cb_menu.rect[2] >= 180.0,
            "color-by-menu collapsed too narrow: {:?}",
            cb_menu.rect
        );
        for i in 0..ALL_COLOR_BYS.len() {
            let opt_key = format!("color-by-opt-{i}");
            let opt = elems_menu
                .iter()
                .find(|e| e.key.as_deref() == Some(opt_key.as_str()))
                .unwrap_or_else(|| panic!("missing {opt_key}"));
            assert!(
                opt.rect[2] >= 160.0,
                "{opt_key} collapsed too narrow: {:?}",
                opt.rect
            );
        }
        assert!(elems_menu.iter().all(|e| e.label.as_deref() != Some("WWR")));
        click_label(&mut rt, "Story");
        assert_eq!(rt.state.color_by, ColorBy::Story);
        assert_eq!(rt.state.open_menu, None);

        // Open View Popover: Camera, Projection, Section + Slider + Invert, Legend, Edges, Theme, Language
        click_key(&mut rt, "btn-view-menu");
        assert_eq!(rt.state.open_menu, Some(TopMenu::View));
        assert!(rt.find("view-settings-content").is_some());
        click_key(&mut rt, "cam-top");
        click_label(&mut rt, "Orthographic");
        assert!(rt.state.renderer.is_orthographic());
        click_key(&mut rt, "switch-section");
        assert!(rt.state.section.enabled);
        assert!(rt.find("slider-section").is_some());
        click_label(&mut rt, "X");
        assert_eq!(rt.state.section.axis, SectionAxis::X);
        click_key(&mut rt, "switch-section-invert");
        assert!(rt.state.section.invert);
        click_key(&mut rt, "switch-legend");
        assert!(!rt.state.show_legend);
        assert!(rt.find("ladybug-legend").is_none());
        click_key(&mut rt, "switch-legend");
        assert!(rt.state.show_legend);
        click_key(&mut rt, "switch-edges");
        assert!(!rt.state.show_edges);
        click_label(&mut rt, "Light");
        assert!(!rt.state.dark_mode);
        click_label(&mut rt, "中文");
        assert_eq!(rt.state.locale, Locale::ZhCn);
        click_label(&mut rt, "EN");
        assert_eq!(rt.state.locale, Locale::EnUs);

        // Escape closes View Popover
        rt.key(KeyEvent::from(Key::Escape));
        step_frames(&mut rt);
        assert_eq!(rt.state.open_menu, None);

        // Selecting Room 1 opens clean read-only Property Inspector with ZERO bottom action buttons
        click_key(&mut rt, "outliner-obj-1");
        assert_eq!(rt.state.selected_ids, vec![1]);
        assert!(rt.state.inspector_pane.is_open());
        assert!(rt.find("right-inspector").is_some());
        assert!(rt.find("inspector-title").is_some());
        assert!(rt.find("inspector-actions").is_none());
        assert!(rt.find("btn-edit-room").is_none());
        assert!(rt.find("btn-isolate").is_none());
        assert!(rt.find("btn-select-similar").is_none());
        assert!(rt.find("btn-pin-here").is_none());
        assert!(rt.find("btn-clear-sel").is_none());

        // Sidebar toggle collapses/expands SplitView sidebar
        click_key(&mut rt, "sidebar-toggle");
        assert!(!rt.state.sidebar_pane.is_open());
        click_key(&mut rt, "sidebar-toggle");
        assert!(rt.state.sidebar_pane.is_open());
    }

    #[test]
    fn room_first_picking_double_click_room_edit_mode_and_esc_exit_work() {
        let backend = CpuCameraBackend {
            mock_pick: Some(ViewerPickHit {
                object_id: 3,
                world_point: [5.0, 0.0, 2.0],
            }),
            ..Default::default()
        };
        let state = ViewerState::new(
            sample_scene_with_room_and_orphan(),
            "South Office",
            Some(Box::new(backend)),
        );
        let mut rt = Runtime::new(state, view, (1280.0, 800.0), Env::new(true, 1.0));
        rt.on_key = Some(on_window_key);
        step_frames(&mut rt);

        // 1) Model mode single-click on child window 3 -> MUST select owning Room 1 & open inspector
        let (vx, vy) = rt.find("viewport-canvas").unwrap();
        rt.pointer_move(vx, vy);
        rt.pointer_down(vx, vy);
        rt.frame(1.0 / 120.0);
        rt.pointer_up(vx, vy);
        step_frames(&mut rt);
        assert_eq!(rt.state.editing_room_id, None);
        assert_eq!(rt.state.selected_ids, vec![1]);
        assert!(rt.state.inspector_pane.is_open());
        assert!(rt.find("room-edit-breadcrumb").is_none());

        // 2) Double-click on Room geometry enters Room Edit Mode + shows breadcrumb
        double_click_xy(&mut rt, vx, vy);
        assert_eq!(rt.state.editing_room_id, Some(1));
        assert_eq!(rt.state.selected_ids, vec![1]);
        assert_eq!(rt.state.current_render_state().editing_room_id, Some(1));
        assert!(rt.find("room-edit-breadcrumb").is_some());
        assert!(rt.find("btn-exit-room-edit").is_some());

        // 3) Single-click inside Room Edit Mode selects child Window 3 directly
        for _ in 0..12 {
            rt.frame(0.1);
        }
        rt.pointer_move(vx, vy);
        rt.pointer_down(vx, vy);
        rt.frame(1.0 / 120.0);
        rt.pointer_up(vx, vy);
        step_frames(&mut rt);
        assert_eq!(rt.state.editing_room_id, Some(1));
        assert_eq!(rt.state.selected_ids, vec![3]);

        // 4) Pressing Escape exits Room Edit Mode cleanly & collapses inspector
        rt.key(KeyEvent::from(Key::Escape));
        step_frames(&mut rt);
        assert_eq!(rt.state.editing_room_id, None);
        assert!(!rt.state.inspector_pane.is_open());
        assert!(rt.find("room-edit-breadcrumb").is_none());

        // 5) Double-click Room 1 in Outliner also enters Room Edit Mode; Exit button leaves it
        let (rx, ry) = rt.find("outliner-obj-1").unwrap();
        double_click_xy(&mut rt, rx, ry);
        assert_eq!(rt.state.editing_room_id, Some(1));
        assert!(rt.find("room-edit-breadcrumb").is_some());
        click_key(&mut rt, "btn-exit-room-edit");
        assert_eq!(rt.state.editing_room_id, None);
        assert!(rt.find("room-edit-breadcrumb").is_none());

        // 6) Clicking empty background or outside active room exits Room Edit Mode cleanly
        rt.state.enter_room_edit_mode(1);
        assert_eq!(rt.state.editing_room_id, Some(1));
        rt.state.renderer = Box::new(CpuCameraBackend {
            mock_pick: None,
            ..Default::default()
        });
        rt.state.handle_viewport_click(100.0, 100.0, false);
        assert_eq!(rt.state.editing_room_id, None);

        rt.state.enter_room_edit_mode(1);
        assert_eq!(rt.state.editing_room_id, Some(1));
        rt.state.renderer = Box::new(CpuCameraBackend {
            mock_pick: Some(ViewerPickHit {
                object_id: 5,
                world_point: [2.0, -2.5, 3.0],
            }),
            ..Default::default()
        });
        rt.state.handle_viewport_click(100.0, 100.0, false);
        assert_eq!(rt.state.editing_room_id, None);
    }

    #[test]
    fn orphaned_geometry_selects_directly_and_deselects_on_empty_click() {
        let backend = CpuCameraBackend {
            mock_pick: Some(ViewerPickHit {
                object_id: 5,
                world_point: [2.0, -2.5, 3.0],
            }),
            ..Default::default()
        };
        let state = ViewerState::new(
            sample_scene_with_room_and_orphan(),
            "South Office",
            Some(Box::new(backend)),
        );
        let mut rt = Runtime::new(state, view, (1280.0, 800.0), Env::new(true, 1.0));
        rt.on_key = Some(on_window_key);
        step_frames(&mut rt);

        let (vx, vy) = rt.find("viewport-canvas").unwrap();
        rt.pointer_move(vx, vy);
        rt.pointer_down(vx, vy);
        rt.frame(1.0 / 120.0);
        rt.pointer_up(vx, vy);
        step_frames(&mut rt);
        assert_eq!(rt.state.selected_ids, vec![5]);
        assert!(rt.state.inspector_pane.is_open());
        assert_eq!(rt.state.editing_room_id, None);
        assert!(rt.find("axis-hud").is_some());
        assert!(rt.find("ladybug-legend").is_some());

        // Clicking empty canvas clears selection and auto-collapses inspector
        rt.state.renderer = Box::new(CpuCameraBackend {
            mock_pick: None,
            ..Default::default()
        });
        rt.state.handle_viewport_click(100.0, 100.0, false);
        assert!(rt.state.selected_ids.is_empty());
        assert!(!rt.state.inspector_pane.is_open());
    }

    #[test]
    fn minimal_three_control_toolbar_stays_clean_at_480px_in_en_and_zh() {
        let mut state = ViewerState::new(
            sample_scene_with_room_and_orphan(),
            "MultiZoneOfficeLongTitle",
            None,
        );
        state.sidebar_pane.set_open(false);
        let mut rt = Runtime::new(state, view, (480.0, 640.0), Env::new(true, 1.0));
        step_frames(&mut rt);

        for locale in [Locale::EnUs, Locale::ZhCn] {
            rt.update(|s, _| s.set_locale(locale));
            step_frames(&mut rt);

            let elems = rt.elements();
            let bar = elems
                .iter()
                .find(|e| e.key.as_deref() == Some("toolbar"))
                .expect("toolbar exists");
            assert!(
                (bar.rect[3] - 48.0).abs() <= 1.0,
                "toolbar height: {:?}",
                bar.rect
            );

            assert!(rt.find("btn-tools-menu").is_none());
            for key in [
                "sidebar-toggle",
                "color-by-trigger",
                "btn-view-menu",
                "btn-inspector-toggle",
            ] {
                let info = elems
                    .iter()
                    .find(|e| e.key.as_deref() == Some(key))
                    .unwrap_or_else(|| panic!("missing toolbar control {key}"));
                assert!(
                    info.rect[0] >= 0.0 && info.rect[0] + info.rect[2] <= 480.5,
                    "{key} overflowed 480px ({locale:?}): {:?}",
                    info.rect
                );
                assert!(
                    info.rect[1] >= 0.0 && info.rect[1] + info.rect[3] <= 48.5,
                    "{key} wrapped off 48px toolbar ({locale:?}): {:?}",
                    info.rect
                );
            }
        }
    }
}
