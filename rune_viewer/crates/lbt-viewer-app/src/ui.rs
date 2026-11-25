//! Responsive Dark/Light AEC Studio UI built with Rune.

use std::time::Duration;

use lbt_scene::{CameraPreset, ColorBy, ObjectKind, PinStatus, ValidationIssue};
use rune::tok::TextStyle;
use rune::{
    Color, ColorScheme, Cursor, Cx, Drag, El, Key, KeyEvent, LineCap, MagnifyEvent, Phase,
    PointerButton, ScrollSpec, Shape, Tx, WheelEvent, canvas, col, el, row, spacer, text,
    text_input,
};

use crate::outliner::{average_object_normal, issue_object_ids, orientation_from_normal};
use crate::state::{ViewerState, TopMenu, object_kind_label};
use crate::theme::{
    CAMERA_BUTTONS, StudioTheme, color_by_full_label, color_by_short_label, kind_badge,
    studio_theme,
};

const ALL_COLOR_BYS: [ColorBy; 8] = [
    ColorBy::Type,
    ColorBy::BoundaryCondition,
    ColorBy::Story,
    ColorBy::Zone,
    ColorBy::ProgramType,
    ColorBy::ConstructionSet,
    ColorBy::Hvac,
    ColorBy::Wwr,
];

fn color_by_key(mode: ColorBy) -> &'static str {
    match mode {
        ColorBy::Type => "color-by-type",
        ColorBy::BoundaryCondition => "color-by-bc",
        ColorBy::Story => "color-by-story",
        ColorBy::Zone => "color-by-zone",
        ColorBy::ProgramType => "color-by-program",
        ColorBy::ConstructionSet => "color-by-constr",
        ColorBy::Hvac => "color-by-hvac",
        ColorBy::Wwr => "color-by-wwr",
    }
}

fn rgba8(r: u8, g: u8, b: u8, a: u8) -> Color {
    Color {
        r: rune::color::srgb_decode(r as f32 / 255.0),
        g: rune::color::srgb_decode(g as f32 / 255.0),
        b: rune::color::srgb_decode(b as f32 / 255.0),
        a: a as f32 / 255.0,
    }
}

fn srgb_rgba_to_color(c: [f32; 4]) -> Color {
    Color {
        r: rune::color::srgb_decode(c[0].clamp(0.0, 1.0)),
        g: rune::color::srgb_decode(c[1].clamp(0.0, 1.0)),
        b: rune::color::srgb_decode(c[2].clamp(0.0, 1.0)),
        a: c[3].clamp(0.0, 1.0),
    }
}

fn toolbar_btn(label: &str, active: bool, key: &'static str, t: &StudioTheme) -> El {
    let fg = if active { t.accent_text } else { t.text };
    let bg = if active { t.accent } else { Color::TRANSPARENT };
    let hover = if active { t.accent } else { t.hover };
    el().key(key)
        .role("button")
        .label(label)
        .h(26.0)
        .px(6.0)
        .center()
        .radius(5.0)
        .fill(bg)
        .border(t.hairline, if active { t.accent } else { t.border })
        .hover(hover)
        .press(t.press)
        .cursor(Cursor::Pointer)
        .child(
            text(label)
                .font(TextStyle::new(11.0, if active { 600.0 } else { 500.0 }))
                .color(fg),
        )
}

fn compact_btn(label: &str, active: bool, key: impl Into<String>, t: &StudioTheme) -> El {
    let fg = if active { t.accent_text } else { t.text };
    let bg = if active { t.accent } else { Color::TRANSPARENT };
    el().key(key)
        .role("button")
        .label(label)
        .h(24.0)
        .px(5.0)
        .center()
        .radius(4.0)
        .fill(bg)
        .border(t.hairline, if active { t.accent } else { t.border })
        .hover(if active { t.accent } else { t.hover })
        .press(t.press)
        .cursor(Cursor::Pointer)
        .child(text(label).font(TextStyle::new(10.5, 500.0)).color(fg))
}

fn top_bar(
    s: &ViewerState,
    t: &StudioTheme,
    compact: bool,
    drawer_effective: bool,
) -> El {
    let live = s.garden_root.is_some();
    let sync_dot_color = if live { t.live_dot } else { t.offline_dot };
    let model_text = if live && s.present_revision > 0 {
        format!("{} · r{}", s.model_label, s.present_revision)
    } else {
        s.model_label.clone()
    };

    let drawer_btn = compact_btn(if compact { "≡" } else { "Panel" }, drawer_effective, "btn-drawer", t)
        .checked(drawer_effective)
        .on_press(move |st: &mut ViewerState| {
            st.drawer_open = !drawer_effective;
            st.drawer_user_toggled = true;
            st.open_menu = None;
        });

    let model_badge = row()
        .key("model-badge")
        .grow(1.0)
        .shrink()
        .min_w(18.0)
        .max_w(if compact { 120.0 } else { 220.0 })
        .h(26.0)
        .px(5.0)
        .gap(5.0)
        .items_center()
        .radius(5.0)
        .fill(t.card)
        .border(t.hairline, t.border)
        .child(
            el().key("live-sync-dot")
                .size(7.0, 7.0)
                .radius(4.0)
                .fill(sync_dot_color),
        )
        .child(
            text(model_text)
                .key("model-label")
                .font(TextStyle::new(11.0, 600.0))
                .color(t.text)
                .truncate()
                .shrink(),
        );

    let color_label = format!("{} ▾", color_by_short_label(s.color_by));
    let color_btn = compact_btn(
        &color_label,
        s.open_menu == Some(TopMenu::ColorBy),
        "btn-color-by",
        t,
    )
    .label(format!("Color By: {}", color_by_full_label(s.color_by)))
    .on_press(|st: &mut ViewerState| {
        st.open_menu = if st.open_menu == Some(TopMenu::ColorBy) {
            None
        } else {
            Some(TopMenu::ColorBy)
        };
    });

    let mut cam_group = row().key("camera-group").gap(2.0).items_center();
    if compact {
        cam_group = cam_group.child(
            compact_btn(
                "View ▾",
                s.open_menu == Some(TopMenu::Camera),
                "btn-cam-menu",
                t,
            )
            .on_press(|st: &mut ViewerState| {
                st.open_menu = if st.open_menu == Some(TopMenu::Camera) {
                    None
                } else {
                    Some(TopMenu::Camera)
                };
            }),
        );
    } else {
        for &(preset, short, key) in &CAMERA_BUTTONS {
            cam_group = cam_group.child(
                compact_btn(short, false, key, t).on_press(move |st: &mut ViewerState| {
                    st.apply_camera_preset(preset);
                }),
            );
        }
    }

    let ortho_on = s.renderer.is_orthographic();
    let ortho_btn = compact_btn(if ortho_on { "Ort" } else { "3D" }, ortho_on, "btn-ortho", t)
        .role("switch")
        .checked(ortho_on)
        .label("Toggle Perspective / Orthographic")
        .on_press(|st: &mut ViewerState| {
            st.open_menu = None;
            st.toggle_orthographic();
        });

    let sec_z = s
        .section
        .value
        .unwrap_or_else(|| if s.scene.bounds.is_valid() { s.scene.bounds.center()[2] } else { 3.0 });
    let sec_label = if s.section.enabled {
        format!("{:.1}m", sec_z)
    } else {
        "Cut".to_owned()
    };
    let section_group = row()
        .key("section-group")
        .gap(1.0)
        .items_center()
        .child(
            compact_btn("-", false, "btn-sec-down", t)
                .label("Lower section cut 0.5m")
                .on_press(|st: &mut ViewerState| {
                    st.open_menu = None;
                    st.step_section_z(-0.5);
                }),
        )
        .child(
            compact_btn(&sec_label, s.section.enabled, "btn-section", t)
                .role("switch")
                .checked(s.section.enabled)
                .label("Toggle Z Section Cut")
                .on_press(|st: &mut ViewerState| {
                    st.open_menu = None;
                    st.toggle_section();
                }),
        )
        .child(
            compact_btn("+", false, "btn-sec-up", t)
                .label("Raise section cut 0.5m")
                .on_press(|st: &mut ViewerState| {
                    st.open_menu = None;
                    st.step_section_z(0.5);
                }),
        );

    let pin_btn = el()
        .key("btn-pin-mode")
        .role("switch")
        .checked(s.pin_mode)
        .label("Toggle 3D Spatial Pin Mode")
        .h(24.0)
        .px(6.0)
        .center()
        .radius(4.0)
        .fill(if s.pin_mode { t.pin_color } else { Color::TRANSPARENT })
        .border(t.hairline, if s.pin_mode { t.pin_color } else { t.border })
        .hover(if s.pin_mode { t.pin_color } else { t.hover })
        .press(t.press)
        .cursor(Cursor::Pointer)
        .child(
            text("Pin")
                .font(TextStyle::new(10.5, if s.pin_mode { 700.0 } else { 500.0 }))
                .color(if s.pin_mode { Color::BLACK } else { t.text }),
        )
        .on_press(|st: &mut ViewerState| {
            st.open_menu = None;
            st.pin_mode = !st.pin_mode;
            if !st.pin_mode {
                st.pin_draft = None;
            }
        });

    let copy_label = if compact { "Copy AI" } else { "Copy AI Context" };
    let copy_btn = compact_btn(copy_label, false, "btn-copy-context", t)
        .label("Copy AI Context")
        .on_press_tx(|st: &mut ViewerState, tx: &mut Tx| {
            st.open_menu = None;
            let prompt = st.copy_ai_context();
            tx.copy(prompt);
        });

    let capture_btn = compact_btn(if compact { "Snap" } else { "Capture" }, false, "btn-capture", t)
        .label("Capture PNG")
        .on_press(|st: &mut ViewerState| {
            st.open_menu = None;
            st.capture_current_png();
        });

    let theme_btn = compact_btn(if s.dark_mode { "Lt" } else { "Dk" }, false, "btn-theme", t)
        .role("switch")
        .checked(s.dark_mode)
        .label("Toggle Dark / Light Studio Theme")
        .on_press_tx(|st: &mut ViewerState, tx: &mut Tx| {
            st.open_menu = None;
            st.dark_mode = !st.dark_mode;
            st.sync_render_state();
            st.render_viewport_now();
            tx.set_color_scheme(if st.dark_mode {
                ColorScheme::Dark
            } else {
                ColorScheme::Light
            });
        });

    col()
        .key("top-bar")
        .w_full()
        .h(40.0)
        .fill(t.topbar)
        .child(
            row()
                .w_full()
                .grow(1.0)
                .px(4.0)
                .gap(if compact { 2.5 } else { 4.0 })
                .items_center()
                .child(drawer_btn)
                .child(model_badge)
                .child(spacer().grow(1.0))
                .child(color_btn)
                .child(cam_group)
                .child(ortho_btn)
                .child(section_group)
                .child(pin_btn)
                .child(copy_btn)
                .child(capture_btn)
                .child(theme_btn),
        )
        .child(el().w_full().h(t.hairline).fill(t.border))
}

fn section_header(title: &str, count: usize, open: bool, key: &'static str, t: &StudioTheme) -> El {
    row()
        .key(key)
        .role("button")
        .label(title)
        .w_full()
        .h(26.0)
        .px(8.0)
        .justify_between()
        .items_center()
        .fill(t.card)
        .hover(t.hover)
        .cursor(Cursor::Pointer)
        .child(
            text(format!("{} {title}", if open { "▾" } else { "▸" }))
                .font(TextStyle::new(11.0, 600.0))
                .color(t.text),
        )
        .child(
            el().px(6.0)
                .py(1.0)
                .radius(8.0)
                .fill(t.accent_soft)
                .child(text(format!("{count}")).font(TextStyle::new(10.0, 600.0)).color(t.accent)),
        )
}

fn outliner_leaf_row(
    object_id: u32,
    kind: ObjectKind,
    label: &str,
    indent: f32,
    selected: bool,
    t: &StudioTheme,
) -> El {
    let badge = kind_badge(kind);
    let fg = if selected { t.accent_text } else { t.text_muted };
    row()
        .key(format!("outliner-obj-{object_id}"))
        .role("button")
        .label(label)
        .w_full()
        .h(22.0)
        .pl(indent)
        .pr(6.0)
        .gap(5.0)
        .items_center()
        .radius(4.0)
        .fill(if selected { t.accent } else { Color::TRANSPARENT })
        .hover(if selected { t.accent } else { t.hover })
        .cursor(Cursor::Pointer)
        .on_press_tx(move |st: &mut ViewerState, tx: &mut Tx| {
            let additive = tx.mods().shift;
            st.select_object(object_id, additive, !additive);
        })
        .child(
            el().px(4.0)
                .py(1.0)
                .radius(3.0)
                .fill(if selected {
                    Color::WHITE.alpha(0.18)
                } else {
                    t.card_elevated
                })
                .child(text(badge).font(TextStyle::new(9.0, 700.0).mono()).color(fg)),
        )
        .child(
            text(label)
                .font(TextStyle::new(11.0, if selected { 600.0 } else { 400.0 }))
                .color(fg)
                .truncate()
                .shrink(),
        )
}

fn left_drawer(s: &ViewerState, t: &StudioTheme, floating: bool, max_h: f32) -> El {
    let mut inner = col()
        .key("drawer-scroll")
        .w_full()
        .grow(1.0)
        .min_h(0.0)
        .scroll(ScrollSpec::default())
        .p_gap_panel(t);

    if s.present_title.is_some() || s.present_note.is_some() {
        let mut note_card = col()
            .w_full()
            .padding(7.0)
            .gap(3.0)
            .radius(6.0)
            .fill(t.card_elevated)
            .border(t.hairline, t.border);
        if let Some(title) = &s.present_title {
            note_card = note_card.child(
                text(title)
                    .font(TextStyle::new(11.5, 600.0))
                    .color(t.text)
                    .wrap(),
            );
        }
        if let Some(note) = &s.present_note {
            note_card = note_card.child(
                text(note)
                    .font(TextStyle::new(10.5, 400.0))
                    .color(t.text_muted)
                    .wrap(),
            );
        }
        inner = inner.child(note_card);
    }

    // 1) Model Outliner (Story -> Room -> Face -> Aperture/Door/Shade)
    let object_count = s.scene.objects.len();
    inner = inner.child(
        section_header(
            "Outliner",
            object_count,
            s.outliner_section_open,
            "outliner-header",
            t,
        )
        .on_press(|st: &mut ViewerState| {
            st.outliner_section_open = !st.outliner_section_open;
        }),
    );
    if s.outliner_section_open {
        if s.outliner.stories.is_empty() && s.outliner.orphaned.is_empty() {
            inner = inner.child(
                text("No model objects loaded")
                    .font(TextStyle::new(11.0, 400.0))
                    .color(t.text_dim),
            );
        } else {
            for story in &s.outliner.stories {
                let story_name = story.name.clone();
                let story_open = s.outliner_expanded_stories.contains(&story_name);
                inner = inner.child(
                    row()
                        .key(format!("story-{}", story.name))
                        .role("button")
                        .w_full()
                        .h(22.0)
                        .px(6.0)
                        .gap(4.0)
                        .items_center()
                        .radius(4.0)
                        .hover(t.hover)
                        .cursor(Cursor::Pointer)
                        .on_press(move |st: &mut ViewerState| {
                            if st.outliner_expanded_stories.contains(&story_name) {
                                st.outliner_expanded_stories.remove(&story_name);
                            } else {
                                st.outliner_expanded_stories.insert(story_name.clone());
                            }
                        })
                        .child(
                            text(format!(
                                "{} {} ({})",
                                if story_open { "▾" } else { "▸" },
                                story.name,
                                story.rooms.len()
                            ))
                            .font(TextStyle::new(10.5, 600.0))
                            .color(t.text_muted)
                            .truncate(),
                        ),
                );
                if story_open {
                    for room in &story.rooms {
                        let room_id = room.object_id;
                        let room_open = s.outliner_expanded_rooms.contains(&room_id);
                        let room_sel = s.selected_ids.contains(&room_id);
                        inner = inner.child(
                            row()
                                .w_full()
                                .items_center()
                                .gap(2.0)
                                .child(
                                    el().key(format!("toggle-room-{room_id}"))
                                        .role("button")
                                        .label("Expand Room")
                                        .size(16.0, 22.0)
                                        .center()
                                        .radius(3.0)
                                        .hover(t.hover)
                                        .cursor(Cursor::Pointer)
                                        .on_press(move |st: &mut ViewerState| {
                                            if st.outliner_expanded_rooms.contains(&room_id) {
                                                st.outliner_expanded_rooms.remove(&room_id);
                                            } else {
                                                st.outliner_expanded_rooms.insert(room_id);
                                            }
                                        })
                                        .child(
                                            text(if room_open { "▾" } else { "▸" })
                                                .font(TextStyle::new(10.0, 500.0))
                                                .color(t.text_dim),
                                        ),
                                )
                                .child(
                                    outliner_leaf_row(
                                        room_id,
                                        ObjectKind::Room,
                                        &room.label,
                                        4.0,
                                        room_sel,
                                        t,
                                    )
                                    .grow(1.0)
                                    .shrink(),
                                ),
                        );
                        if room_open {
                            for face in &room.faces {
                                let fsel = s.selected_ids.contains(&face.object_id);
                                inner = inner.child(outliner_leaf_row(
                                    face.object_id,
                                    ObjectKind::Face,
                                    &face.label,
                                    24.0,
                                    fsel,
                                    t,
                                ));
                                for child in &face.children {
                                    let csel = s.selected_ids.contains(&child.object_id);
                                    inner = inner.child(outliner_leaf_row(
                                        child.object_id,
                                        child.kind,
                                        &child.label,
                                        36.0,
                                        csel,
                                        t,
                                    ));
                                }
                            }
                            for shade in &room.shades {
                                let ssel = s.selected_ids.contains(&shade.object_id);
                                inner = inner.child(outliner_leaf_row(
                                    shade.object_id,
                                    shade.kind,
                                    &shade.label,
                                    24.0,
                                    ssel,
                                    t,
                                ));
                            }
                        }
                    }
                }
            }
            for orphan in &s.outliner.orphaned {
                let osel = s.selected_ids.contains(&orphan.object_id);
                inner = inner.child(outliner_leaf_row(
                    orphan.object_id,
                    orphan.kind,
                    &orphan.label,
                    6.0,
                    osel,
                    t,
                ));
                for child in &orphan.children {
                    let csel = s.selected_ids.contains(&child.object_id);
                    inner = inner.child(outliner_leaf_row(
                        child.object_id,
                        child.kind,
                        &child.label,
                        18.0,
                        csel,
                        t,
                    ));
                }
            }
        }
    }

    // 2) Open Spatial Pins
    let open_pins = s.open_pins();
    inner = inner.child(
        section_header(
            "Spatial Pins",
            open_pins.len(),
            s.pins_section_open,
            "pins-header",
            t,
        )
        .on_press(|st: &mut ViewerState| {
            st.pins_section_open = !st.pins_section_open;
        }),
    );
    if s.pins_section_open {
        if s.annotations.is_empty() {
            inner = inner.child(
                text("No spatial pins yet. Enable Pin mode and click geometry.")
                    .font(TextStyle::new(10.5, 400.0))
                    .color(t.text_dim)
                    .wrap(),
            );
        } else {
            for pin in &s.annotations {
                let is_open = pin.status == PinStatus::Open;
                let pin_clone = pin.clone();
                let pin_id_res = pin.id.clone();
                let active = s.active_pin_id.as_deref() == Some(pin.id.as_str());
                let title = if pin.comment.is_empty() {
                    pin.target
                        .as_ref()
                        .map(|tgt| tgt.object_identifier.clone())
                        .unwrap_or_else(|| pin.id.clone())
                } else {
                    pin.comment.clone()
                };
                let target_sub = pin
                    .target
                    .as_ref()
                    .map(|tgt| format!("{} · {}", tgt.object_type.as_str(), tgt.object_identifier))
                    .unwrap_or_else(|| "World point".to_owned());

                let mut card = col()
                    .key(format!("pin-item-{}", pin.id))
                    .w_full()
                    .padding(6.0)
                    .gap(3.0)
                    .radius(5.0)
                    .fill(if active { t.accent_soft } else { t.card })
                    .border(t.hairline, if active { t.accent } else { t.border })
                    .hover(t.hover)
                    .cursor(Cursor::Pointer)
                    .on_press(move |st: &mut ViewerState| {
                        st.focus_on_pin(&pin_clone);
                    })
                    .child(
                        row()
                            .w_full()
                            .justify_between()
                            .items_center()
                            .gap(4.0)
                            .child(
                                el().px(5.0)
                                    .py(1.0)
                                    .radius(4.0)
                                    .fill(if is_open { t.pin_color } else { t.card_elevated })
                                    .child(
                                        text(if is_open { "OPEN" } else { "DONE" })
                                            .font(TextStyle::new(9.0, 700.0).mono())
                                            .color(if is_open { Color::BLACK } else { t.text_dim }),
                                    ),
                            )
                            .child(
                                text(target_sub)
                                    .font(TextStyle::new(9.5, 500.0))
                                    .color(t.text_dim)
                                    .truncate()
                                    .shrink(),
                            ),
                    )
                    .child(
                        text(title)
                            .font(TextStyle::new(11.0, 500.0))
                            .color(t.text)
                            .wrap(),
                    );

                if is_open {
                    card = card.child(
                        row().w_full().justify_between().child(spacer()).child(
                            compact_btn("Resolve", false, format!("resolve-pin-{}", pin.id), t)
                                .on_press(move |st: &mut ViewerState| {
                                    st.resolve_pin_local(&pin_id_res);
                                }),
                        ),
                    );
                }
                inner = inner.child(card);
            }
        }
    }

    // 3) Validation Issues
    inner = inner.child(
        section_header(
            "Validation Issues",
            s.validation_issues.len(),
            s.issues_section_open,
            "issues-header",
            t,
        )
        .on_press(|st: &mut ViewerState| {
            st.issues_section_open = !st.issues_section_open;
        }),
    );
    if s.issues_section_open {
        if s.validation_issues.is_empty() {
            inner = inner.child(
                text("No active validation issues")
                    .font(TextStyle::new(10.5, 400.0))
                    .color(t.text_dim),
            );
        } else {
            for (idx, issue) in s.validation_issues.iter().enumerate() {
                inner = inner.child(issue_card(s, issue, idx, t));
            }
        }
    }

    let panel = col()
        .key("left-drawer")
        .w(260.0)
        .min_h(0.0)
        .fill(t.panel)
        .child(inner);

    if floating {
        panel
            .max_h((max_h - 16.0).max(160.0))
            .radius(8.0)
            .border(t.hairline, t.border_strong)
            .pin(Some(8.0), Some(8.0), None, Some(8.0))
    } else {
        row()
            .key("left-drawer-wrap")
            .h_full()
            .min_h(0.0)
            .child(panel.h_full())
            .child(el().w(t.hairline).h_full().fill(t.border))
    }
}

trait DrawerLayoutExt {
    fn p_gap_panel(self, t: &StudioTheme) -> Self;
}

impl DrawerLayoutExt for El {
    fn p_gap_panel(self, _t: &StudioTheme) -> Self {
        self.padding(8.0).gap(6.0)
    }
}

fn issue_card(s: &ViewerState, issue: &ValidationIssue, idx: usize, t: &StudioTheme) -> El {
    let sev = issue
        .severity
        .as_deref()
        .unwrap_or("error")
        .to_ascii_lowercase();
    let is_warn = sev.contains("warn");
    let badge_bg = if is_warn { t.warning_color } else { t.error_color };
    let target_ids = issue_object_ids(&s.scene, issue);
    let first_id = target_ids.first().copied();
    let message = issue.message.clone();

    col()
        .key(format!("issue-item-{idx}"))
        .w_full()
        .padding(6.0)
        .gap(3.0)
        .radius(5.0)
        .fill(t.card)
        .border(t.hairline, t.border)
        .hover(t.hover)
        .cursor(Cursor::Pointer)
        .on_press(move |st: &mut ViewerState| {
            if !target_ids.is_empty() {
                st.selected_ids = target_ids.clone();
                if let Some(id) = first_id {
                    st.focus_on_object(id);
                }
                st.sync_render_state();
                st.render_viewport_now();
                st.flush_interaction_state();
            }
        })
        .child(
            row()
                .gap(5.0)
                .items_center()
                .child(
                    el().px(5.0)
                        .py(1.0)
                        .radius(4.0)
                        .fill(badge_bg)
                        .child(
                            text(if is_warn { "WARN" } else { "ERR" })
                                .font(TextStyle::new(9.0, 700.0).mono())
                                .color(Color::WHITE),
                        ),
                )
                .child(
                    text(issue.code.as_deref().unwrap_or("validation"))
                        .font(TextStyle::new(9.5, 600.0).mono())
                        .color(t.text_dim)
                        .truncate(),
                ),
        )
        .child(text(message).font(TextStyle::new(11.0, 400.0)).color(t.text).wrap())
}

fn prop_row(label: &str, value: String, t: &StudioTheme) -> El {
    row()
        .w_full()
        .justify_between()
        .items_center()
        .gap(6.0)
        .py(2.0)
        .child(
            text(label)
                .font(TextStyle::new(10.5, 500.0))
                .color(t.text_dim),
        )
        .child(
            text(value)
                .font(TextStyle::new(11.0, 500.0))
                .color(t.text)
                .truncate()
                .shrink(),
        )
}

fn right_inspector(s: &ViewerState, t: &StudioTheme, floating: bool, max_h: f32) -> El {
    let Some(rec) = s.primary_selected() else {
        return el().size(0.0, 0.0);
    };

    let parent_room = s.parent_room_label(rec).unwrap_or_else(|| "—".to_owned());
    let normal = average_object_normal(&s.scene, rec.object_id);
    let orient = normal
        .map(orientation_from_normal)
        .unwrap_or("—")
        .to_owned();
    let area = rec
        .area
        .map(|a| format!("{a:.2} m²"))
        .unwrap_or_else(|| "—".to_owned());
    let wwr = rec
        .wwr
        .map(|w| format!("{:.1}%", w * 100.0))
        .unwrap_or_else(|| "—".to_owned());

    let header = row()
        .w_full()
        .justify_between()
        .items_center()
        .gap(6.0)
        .child(
            el().px(6.0)
                .py(2.0)
                .radius(4.0)
                .fill(t.accent_soft)
                .child(
                    text(object_kind_label(rec.kind))
                        .font(TextStyle::new(10.0, 700.0))
                        .color(t.accent),
                ),
        )
        .child(
            text(if s.selected_ids.len() > 1 {
                format!("+{} selected", s.selected_ids.len() - 1)
            } else {
                format!("ID {}", rec.object_id)
            })
            .font(TextStyle::new(10.0, 500.0).mono())
            .color(t.text_dim),
        );

    let mut props = col()
        .w_full()
        .grow(1.0)
        .min_h(0.0)
        .scroll(ScrollSpec::default())
        .padding(8.0)
        .gap(6.0)
        .child(header)
        .child(
            text(&rec.identifier)
                .key("inspector-identifier")
                .font(TextStyle::new(12.5, 700.0))
                .color(t.text)
                .wrap(),
        );

    if let Some(dn) = &rec.display_name
        && dn != &rec.identifier
    {
        props = props.child(
            text(dn)
                .font(TextStyle::new(11.0, 400.0))
                .color(t.text_muted)
                .wrap(),
        );
    }

    let child_shades = s
        .scene
        .objects
        .iter()
        .filter(|o| o.parent_object_id == Some(rec.object_id) && o.kind == ObjectKind::Shade)
        .count();

    props = props
        .child(el().w_full().h(t.hairline).fill(t.border))
        .child(prop_row("Room", parent_room, t))
        .child(prop_row("Area", area, t))
        .child(prop_row("Orientation", orient, t))
        .child(prop_row(
            "Boundary",
            rec.boundary_condition.clone().unwrap_or_else(|| "—".to_owned()),
            t,
        ))
        .child(prop_row(
            "Face Type",
            rec.face_type.clone().unwrap_or_else(|| "—".to_owned()),
            t,
        ))
        .child(prop_row("WWR", wwr, t))
        .child(prop_row(
            "Story",
            rec.story.clone().unwrap_or_else(|| "—".to_owned()),
            t,
        ))
        .child(prop_row(
            "Zone",
            rec.zone.clone().unwrap_or_else(|| "—".to_owned()),
            t,
        ))
        .child(prop_row(
            "HVAC",
            rec.hvac.clone().unwrap_or_else(|| "—".to_owned()),
            t,
        ))
        .child(prop_row(
            "Program",
            rec.program_type.clone().unwrap_or_else(|| "—".to_owned()),
            t,
        ))
        .child(prop_row(
            "Construction",
            rec.construction_set.clone().unwrap_or_else(|| "—".to_owned()),
            t,
        ));

    if child_shades > 0 {
        props = props.child(prop_row("Shades", format!("{child_shades}"), t));
    }

    let swatch = srgb_rgba_to_color(lbt_scene::color_for_object(rec, s.color_by));
    props = props.child(
        row()
            .w_full()
            .justify_between()
            .items_center()
            .child(text("Color").font(TextStyle::new(10.5, 500.0)).color(t.text_dim))
            .child(
                el().size(36.0, 12.0)
                    .radius(3.0)
                    .fill(swatch)
                    .border(t.hairline, t.border_strong),
            ),
    );

    let actions = col()
        .w_full()
        .padding(8.0)
        .gap(5.0)
        .child(el().w_full().h(t.hairline).fill(t.border))
        .child(
            row()
                .w_full()
                .gap(5.0)
                .child(
                    toolbar_btn(
                        if s.local_isolate { "Unisolate" } else { "Isolate" },
                        s.local_isolate,
                        "btn-isolate",
                        t,
                    )
                    .grow(1.0)
                    .on_press(|st: &mut ViewerState| st.toggle_isolate_selection()),
                )
                .child(
                    toolbar_btn("Similar", false, "btn-select-similar", t)
                        .grow(1.0)
                        .on_press(|st: &mut ViewerState| st.select_similar()),
                ),
        )
        .child(
            row()
                .w_full()
                .gap(5.0)
                .child(
                    toolbar_btn("Pin Here", false, "btn-pin-here", t)
                        .grow(1.0)
                        .on_press(|st: &mut ViewerState| st.pin_selected_object()),
                )
                .child(
                    toolbar_btn("Clear", false, "btn-clear-sel", t)
                        .grow(1.0)
                        .on_press(|st: &mut ViewerState| st.clear_selection()),
                ),
        );

    let panel = col()
        .key("right-inspector")
        .w(248.0)
        .min_h(0.0)
        .fill(t.panel)
        .child(props)
        .child(actions);

    if floating {
        panel
            .max_h((max_h - 16.0).max(160.0))
            .radius(8.0)
            .border(t.hairline, t.border_strong)
            .pin(None, Some(8.0), Some(8.0), Some(8.0))
    } else {
        row()
            .key("right-inspector-wrap")
            .h_full()
            .min_h(0.0)
            .child(el().w(t.hairline).h_full().fill(t.border))
            .child(panel.h_full())
    }
}

fn axis_hud(s: &ViewerState, t: &StudioTheme) -> El {
    let (r, u, _f) = s.renderer.camera_basis();
    let project_axis = |axis: [f32; 3]| -> [f32; 2] {
        let sx = axis[0] * r[0] + axis[1] * r[1] + axis[2] * r[2];
        let sy = -(axis[0] * u[0] + axis[1] * u[1] + axis[2] * u[2]);
        [24.0 + sx * 16.0, 24.0 + sy * 16.0]
    };
    let origin = [24.0, 24.0];
    let ax_x = project_axis([1.0, 0.0, 0.0]);
    let ax_y = project_axis([0.0, 1.0, 0.0]);
    let ax_z = project_axis([0.0, 0.0, 1.0]);

    let shape = Shape::new()
        .line(origin, ax_x, 1.7, LineCap::Round, rgba8(230, 86, 86, 255))
        .line(origin, ax_y, 2.0, LineCap::Round, rgba8(72, 200, 130, 255))
        .line(origin, ax_z, 1.7, LineCap::Round, rgba8(90, 155, 245, 255));

    let north_pos = [
        (ax_y[0] - 4.0).clamp(2.0, 38.0),
        (ax_y[1] - 6.0).clamp(1.0, 36.0),
    ];

    el().key("axis-hud")
        .size(48.0, 48.0)
        .radius(24.0)
        .fill(t.badge_bg)
        .border(t.hairline, t.border)
        .pin(None, Some(10.0), Some(10.0), None)
        .child(canvas(shape).size(48.0, 48.0))
        .child(
            text("N")
                .font(TextStyle::new(9.0, 800.0))
                .color(rgba8(82, 215, 140, 255))
                .absolute(north_pos[0], north_pos[1]),
        )
}

fn viewport_pane(s: &ViewerState, t: &StudioTheme) -> El {
    let mut stack = el()
        .key("viewport-pane")
        .grow(1.0)
        .min_w(0.0)
        .min_h(0.0)
        .h_full()
        .fill(t.viewport_bg)
        .clip_rounded(0.0);

    let pixel_canvas = el()
        .key("viewport-canvas")
        .w_full()
        .h_full()
        .pixels(&s.viewport_pixels)
        .cursor(if s.pin_mode {
            Cursor::Crosshair
        } else if s.drag_moved {
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
                        st.renderer
                            .pan_pixels(step_dx, step_dy, st.viewport_pts[1].round().max(1.0) as u32);
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

    // Projected 3D Spatial Pin Badges
    let [vw, vh] = s.viewport_pts;
    for (idx, pin) in s.annotations.iter().enumerate() {
        let active = s.active_pin_id.as_deref() == Some(pin.id.as_str());
        if pin.status != PinStatus::Open && !active {
            continue;
        }
        let Some(pt) = s.pin_world_point(pin) else {
            continue;
        };
        let Some([px, py]) = s.project_world_pts(pt) else {
            continue;
        };
        if px < -8.0 || py < -8.0 || px > vw + 8.0 || py > vh + 8.0 {
            continue;
        }
        let pin_clone = pin.clone();
        let summary = if pin.comment.is_empty() {
            format!("Pin #{}", idx + 1)
        } else {
            pin.comment.clone()
        };
        let bx = (px - 10.0).clamp(4.0, (vw - 140.0).max(4.0));
        let by = (py - 12.0).clamp(4.0, (vh - 28.0).max(4.0));
        stack = stack.child(
            row()
                .key(format!("pin-badge-{}", pin.id))
                .role("button")
                .label(&summary)
                .h(22.0)
                .max_w(160.0)
                .px(6.0)
                .gap(5.0)
                .items_center()
                .radius(11.0)
                .fill(t.badge_bg)
                .border(t.hairline, if active { t.accent } else { t.pin_color })
                .cursor(Cursor::Pointer)
                .absolute(bx, by)
                .on_press(move |st: &mut ViewerState| st.focus_on_pin(&pin_clone))
                .child(el().size(7.0, 7.0).radius(4.0).fill(t.pin_color))
                .child(
                    text(summary)
                        .font(TextStyle::new(10.0, 600.0))
                        .color(t.text)
                        .truncate()
                        .shrink(),
                ),
        );
    }

    // Projected Agent Callouts
    for (idx, callout) in s.callouts.iter().enumerate() {
        let Some(pt) = s.callout_world_point(callout) else {
            continue;
        };
        let Some([px, py]) = s.project_world_pts(pt) else {
            continue;
        };
        if px < -8.0 || py < -8.0 || px > vw + 8.0 || py > vh + 8.0 {
            continue;
        }
        let sev = callout
            .severity
            .as_deref()
            .unwrap_or("info")
            .to_ascii_lowercase();
        let border_col = if sev.contains("err") {
            t.error_color
        } else if sev.contains("warn") {
            t.warning_color
        } else {
            t.info_color
        };
        let bx = (px - 10.0).clamp(4.0, (vw - 170.0).max(4.0));
        let by = (py - 12.0).clamp(4.0, (vh - 28.0).max(4.0));
        stack = stack.child(
            row()
                .key(format!("callout-{idx}"))
                .h(22.0)
                .max_w(180.0)
                .px(7.0)
                .gap(5.0)
                .items_center()
                .radius(6.0)
                .fill(t.badge_bg)
                .border(t.hairline, border_col)
                .absolute(bx, by)
                .child(el().size(6.0, 6.0).radius(3.0).fill(border_col))
                .child(
                    text(&callout.label)
                        .font(TextStyle::new(10.0, 600.0))
                        .color(t.text)
                        .truncate()
                        .shrink(),
                ),
        );
    }

    // Live 3D North & XYZ Axis HUD
    stack = stack.child(axis_hud(s, t));

    // Pin Mode hint pill
    if s.pin_mode && s.pin_draft.is_none() {
        stack = stack.child(
            row()
                .key("pin-mode-banner")
                .h(26.0)
                .px(10.0)
                .center()
                .radius(13.0)
                .fill(t.badge_bg)
                .border(t.hairline, t.pin_color)
                .pin(Some(10.0), Some(10.0), None, None)
                .child(
                    text("Pin Mode: click a surface to place a 3D pin (Esc to exit)")
                        .font(TextStyle::new(10.5, 600.0))
                        .color(t.pin_color),
                ),
        );
    }

    // Spatial Pin Comment Composer Popover
    if let Some(draft) = &s.pin_draft {
        let [px, py] = s
            .project_world_pts(draft.world_point)
            .unwrap_or([vw * 0.5, vh * 0.35]);
        let pop_w = (vw - 24.0).clamp(220.0, 270.0);
        let left = (px - pop_w * 0.5).clamp(12.0, (vw - pop_w - 12.0).max(12.0));
        let top = (py + 10.0).clamp(12.0, (vh - 148.0).max(12.0));

        let composer = col()
            .key("pin-composer")
            .role("dialog")
            .label("Add 3D Spatial Pin")
            .modal(true, |st: &mut ViewerState| {
                st.pin_draft = None;
            })
            .w(pop_w)
            .padding(10.0)
            .gap(7.0)
            .radius(8.0)
            .fill(t.card_elevated)
            .border(t.hairline, t.pin_color)
            .absolute(left, top)
            .child(
                row()
                    .w_full()
                    .justify_between()
                    .items_center()
                    .child(
                        text("New 3D Spatial Pin")
                            .font(TextStyle::new(11.5, 700.0))
                            .color(t.text),
                    )
                    .child(
                        text(&draft.target_label)
                            .font(TextStyle::new(10.0, 500.0))
                            .color(t.text_muted)
                            .truncate()
                            .shrink(),
                    ),
            )
            .child(
                text(format!(
                    "XYZ ({:.2}, {:.2}, {:.2}) m",
                    draft.world_point[0], draft.world_point[1], draft.world_point[2]
                ))
                .font(TextStyle::new(9.5, 400.0).mono())
                .color(t.text_dim),
            )
            .child(
                el().w_full()
                    .px(7.0)
                    .py(5.0)
                    .radius(5.0)
                    .fill(t.bg)
                    .border(t.hairline, t.border_strong)
                    .child(
                        text_input(&draft.comment_edit, TextStyle::new(11.5, 400.0))
                            .key("pin-comment-input")
                            .label("Pin annotation comment")
                            .single_line()
                            .w_full()
                            .color(t.text)
                            .placeholder("Enter issue or annotation...", t.text_dim)
                            .on_edit(|st: &mut ViewerState| {
                                &mut st
                                    .pin_draft
                                    .as_mut()
                                    .expect("pin draft active")
                                    .comment_edit
                            })
                            .on_submit(|st: &mut ViewerState, _| {
                                st.commit_pin_draft();
                            }),
                    ),
            )
            .child(
                row()
                    .w_full()
                    .gap(6.0)
                    .child(
                        toolbar_btn("Save Pin", true, "btn-pin-save", t)
                            .grow(1.0)
                            .on_press(|st: &mut ViewerState| st.commit_pin_draft()),
                    )
                    .child(
                        toolbar_btn("Cancel", false, "btn-pin-cancel", t)
                            .grow(1.0)
                            .on_press(|st: &mut ViewerState| st.pin_draft = None),
                    ),
            );
        stack = stack.child(composer);
    }

    // Status Toast
    if let Some(msg) = &s.status_banner {
        stack = stack.child(
            row()
                .key("status-toast")
                .max_w((vw - 24.0).max(160.0))
                .h(24.0)
                .px(8.0)
                .gap(6.0)
                .items_center()
                .radius(6.0)
                .fill(t.badge_bg)
                .border(t.hairline, t.border_strong)
                .pin(Some(10.0), None, None, Some(10.0))
                .child(
                    text(msg)
                        .font(TextStyle::new(10.5, 500.0))
                        .color(t.text)
                        .truncate()
                        .shrink(),
                )
                .child(
                    el().key("btn-dismiss-toast")
                        .role("button")
                        .label("Dismiss notification")
                        .px(4.0)
                        .cursor(Cursor::Pointer)
                        .on_press(|st: &mut ViewerState| st.status_banner = None)
                        .child(text("×").font(TextStyle::new(11.0, 600.0)).color(t.text_dim)),
                ),
        );
    }

    stack
}

fn menu_overlay(s: &ViewerState, t: &StudioTheme, win_w: f32) -> Option<El> {
    let menu = s.open_menu?;
    match menu {
        TopMenu::ColorBy => {
            let mut items = col()
                .key("menu-color-by")
                .role("menu")
                .label("Color By Modes")
                .modal(true, |st: &mut ViewerState| st.open_menu = None)
                .w(176.0)
                .padding(5.0)
                .gap(2.0)
                .radius(7.0)
                .fill(t.card_elevated)
                .border(t.hairline, t.border_strong)
                .pin(None, Some(42.0), Some((win_w - 280.0).clamp(8.0, 260.0)), None);

            for mode in ALL_COLOR_BYS {
                let selected = s.color_by == mode;
                items = items.child(
                    row()
                        .key(color_by_key(mode))
                        .role("menuitem")
                        .w_full()
                        .h(26.0)
                        .px(8.0)
                        .justify_between()
                        .items_center()
                        .radius(4.0)
                        .fill(if selected { t.accent_soft } else { Color::TRANSPARENT })
                        .hover(t.hover)
                        .cursor(Cursor::Pointer)
                        .on_press(move |st: &mut ViewerState| st.set_color_by(mode))
                        .child(
                            text(color_by_full_label(mode))
                                .font(TextStyle::new(11.5, if selected { 600.0 } else { 400.0 }))
                                .color(if selected { t.accent } else { t.text }),
                        )
                        .child(
                            text(if selected { "✓" } else { "" })
                                .font(TextStyle::new(11.0, 700.0))
                                .color(t.accent),
                        ),
                );
            }
            Some(items)
        }
        TopMenu::Camera => {
            let mut items = col()
                .key("menu-camera")
                .role("menu")
                .label("Camera Presets")
                .modal(true, |st: &mut ViewerState| st.open_menu = None)
                .w(140.0)
                .padding(5.0)
                .gap(2.0)
                .radius(7.0)
                .fill(t.card_elevated)
                .border(t.hairline, t.border_strong)
                .pin(None, Some(42.0), Some(110.0), None);

            for &(preset, short, key) in &CAMERA_BUTTONS {
                let title = match preset {
                    CameraPreset::Axon => "Axonometric",
                    CameraPreset::Top => "Top Plan",
                    CameraPreset::North => "North",
                    CameraPreset::South => "South",
                    CameraPreset::East => "East",
                    CameraPreset::West => "West",
                    CameraPreset::Fit => "Fit Model",
                    CameraPreset::FitHighlights => "Fit Highlights",
                    CameraPreset::Keep => "Keep",
                };
                items = items.child(
                    row()
                        .key(key)
                        .role("menuitem")
                        .w_full()
                        .h(26.0)
                        .px(8.0)
                        .justify_between()
                        .items_center()
                        .radius(4.0)
                        .hover(t.hover)
                        .cursor(Cursor::Pointer)
                        .on_press(move |st: &mut ViewerState| st.apply_camera_preset(preset))
                        .child(text(title).font(TextStyle::new(11.5, 500.0)).color(t.text))
                        .child(text(short).font(TextStyle::new(10.0, 600.0).mono()).color(t.text_dim)),
                );
            }
            Some(items)
        }
    }
}

/// Primary Rune view builder for `lbt-rune-viewer`.
pub fn view(s: &ViewerState, cx: &mut Cx<ViewerState>) -> El {
    let t = studio_theme(s.dark_mode, cx.env().scale);
    cx.foreground(t.text);
    cx.press_cursor(Cursor::Pointer);
    cx.focus_ring(2.0, 1.5, t.accent);

    let root_rect = cx.layout_with("root", |r| [r[2], r[3]]).unwrap_or([1280.0, 800.0]);
    let win_w = root_rect[0].max(320.0);
    let body_h = (root_rect[1] - 40.0).max(200.0);

    let compact_bar = win_w < 980.0;
    let overlay_panels = win_w < 760.0;
    let drawer_effective = if overlay_panels && !s.drawer_user_toggled {
        false
    } else {
        s.drawer_open
    };
    let has_selection = !s.selected_ids.is_empty();

    let mut body_row = row()
        .key("studio-body")
        .w_full()
        .grow(1.0)
        .min_h(0.0);

    if drawer_effective && !overlay_panels {
        body_row = body_row.child(left_drawer(s, &t, false, body_h));
    }

    let mut viewport = viewport_pane(s, &t);
    if drawer_effective && overlay_panels {
        viewport = viewport.child(left_drawer(s, &t, true, body_h));
    }
    if has_selection && overlay_panels {
        viewport = viewport.child(right_inspector(s, &t, true, body_h));
    }
    body_row = body_row.child(viewport);

    if has_selection && !overlay_panels {
        body_row = body_row.child(right_inspector(s, &t, false, body_h));
    }

    let mut root = col()
        .key("root")
        .w_full()
        .h_full()
        .fill(t.bg)
        .child(top_bar(s, &t, compact_bar, drawer_effective))
        .child(body_row);

    if let Some(menu_el) = menu_overlay(s, &t, win_w) {
        root = root.child(menu_el);
    }

    root
}

/// Window-level keyboard shortcuts when no text input handles the key.
pub fn on_window_key(s: &mut ViewerState, ev: &KeyEvent, _tx: &mut Tx) -> bool {
    match &ev.key {
        Key::Escape => {
            if s.open_menu.is_some() {
                s.open_menu = None;
                return true;
            }
            if s.pin_draft.is_some() {
                s.pin_draft = None;
                return true;
            }
            if s.pin_mode {
                s.pin_mode = false;
                return true;
            }
            if !s.selected_ids.is_empty() {
                s.clear_selection();
                return true;
            }
            false
        }
        Key::Text(ch) if !ev.mods.cmd && !ev.mods.ctrl && !ev.mods.alt => {
            match ch.as_str() {
                "f" | "F" => {
                    s.apply_camera_preset(CameraPreset::Fit);
                    true
                }
                "p" | "P" => {
                    s.pin_mode = !s.pin_mode;
                    if !s.pin_mode {
                        s.pin_draft = None;
                    }
                    true
                }
                "i" | "I" => {
                    if !s.selected_ids.is_empty() {
                        s.toggle_isolate_selection();
                        true
                    } else {
                        false
                    }
                }
                _ => false,
            }
        }
        _ => false,
    }
}

#[cfg(test)]
mod tests {
    use lbt_scene::{
        Bounds3, ColorBy, MeshVertex, ObjectKind, ObjectRecord, ObjectTargetRef, PinStatus,
        SceneData,
    };
    use rune::{Env, Key, KeyEvent, Runtime};

    use super::*;
    use crate::engine::CpuCameraBackend;

    fn sample_scene_with_room() -> SceneData {
        let wall_normal = [0.0, -1.0, 0.0];
        let v = |pos: [f32; 3], oid: u32, kind: ObjectKind| MeshVertex {
            position: pos,
            normal: wall_normal,
            object_id: oid,
            kind_code: kind.kind_code(),
        };
        let mut face_target = ObjectTargetRef::new(None, "OfficeModel", ObjectKind::Face, "Wall_South");
        face_target.parent.insert("room".to_owned(), "Room_South_1".to_owned());
        let mut ap_target = ObjectTargetRef::new(None, "OfficeModel", ObjectKind::Aperture, "Window_South");
        ap_target.parent.insert("room".to_owned(), "Room_South_1".to_owned());
        ap_target.parent.insert("face".to_owned(), "Wall_South".to_owned());

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
            ],
            indices: vec![0, 1, 2, 3, 4, 5],
            edge_vertices: Vec::new(),
            objects: vec![
                ObjectRecord {
                    object_id: 1,
                    kind: ObjectKind::Room,
                    identifier: "Room_South_1".to_owned(),
                    display_name: Some("South Office".to_owned()),
                    target: ObjectTargetRef::new(None, "OfficeModel", ObjectKind::Room, "Room_South_1"),
                    parent_object_id: None,
                    bounds: Bounds3::new([0.0, 0.0, 0.0], [10.0, 8.0, 4.0]),
                    centroid: [5.0, 4.0, 2.0],
                    face_type: None,
                    boundary_condition: None,
                    area: Some(80.0),
                    wwr: Some(0.32),
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
                    bounds: Bounds3::new([0.0, 0.0, 0.0], [10.0, 0.0, 4.0]),
                    centroid: [5.0, 0.0, 2.0],
                    area: Some(40.0),
                    face_type: Some("Wall".to_owned()),
                    boundary_condition: Some("Outdoors".to_owned()),
                    wwr: Some(0.45),
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
            ],
            stories: vec!["Level 1".to_owned()],
        }
    }

    fn step_frames(rt: &mut Runtime<ViewerState>) {
        for _ in 0..6 {
            rt.frame(0.05);
        }
    }

    fn click_key(rt: &mut Runtime<ViewerState>, key: &str) {
        let (x, y) = rt.find(key).unwrap_or_else(|| panic!("missing key {key:?}"));
        rt.pointer_move(x, y);
        rt.pointer_down(x, y);
        rt.pointer_up(x, y);
        step_frames(rt);
    }

    #[test]
    fn toolbar_theme_drawer_color_by_and_clipboard_work_in_rune_runtime() {
        let state = ViewerState::new(sample_scene_with_room(), "South Office", None);
        let mut rt = Runtime::new(state, view, (1280.0, 800.0), Env::new(true, 1.0));
        rt.on_key = Some(on_window_key);
        let clip = rune::clipboard::memory();
        rt.use_clipboard(&clip);
        rt.frame(0.0);
        rt.frame(0.0);

        // Theme toggle
        assert!(rt.state.dark_mode);
        click_key(&mut rt, "btn-theme");
        assert!(!rt.state.dark_mode);

        // Drawer toggle
        assert!(rt.state.drawer_open);
        click_key(&mut rt, "btn-drawer");
        assert!(!rt.state.drawer_open);
        assert!(rt.find("left-drawer").is_none());
        click_key(&mut rt, "btn-drawer");
        assert!(rt.state.drawer_open);

        // ColorBy popup menu -> switch to WWR
        click_key(&mut rt, "btn-color-by");
        assert_eq!(rt.state.open_menu, Some(TopMenu::ColorBy));
        click_key(&mut rt, "color-by-wwr");
        assert_eq!(rt.state.color_by, ColorBy::Wwr);
        assert_eq!(rt.state.open_menu, None);

        // Ortho & Section controls
        click_key(&mut rt, "btn-ortho");
        assert!(rt.state.renderer.is_orthographic());
        click_key(&mut rt, "btn-section");
        assert!(rt.state.section.enabled);
        let z0 = rt.state.section.value.unwrap();
        click_key(&mut rt, "btn-sec-up");
        assert!(rt.state.section.value.unwrap() > z0);

        // Outliner click selects aperture & opens Right Inspector
        click_key(&mut rt, "outliner-obj-3");
        assert_eq!(rt.state.selected_ids, vec![3]);
        assert!(rt.find("right-inspector").is_some());

        // Copy AI Context -> clipboard contains identifier + GD_Web_View_Get_Context
        click_key(&mut rt, "btn-copy-context");
        let pasted = clip.text().map(|z| z.to_string()).unwrap_or_default();
        assert!(pasted.contains("Window_South"), "clipboard: {pasted}");
        assert!(pasted.contains("GD_Web_View_Get_Context"), "clipboard: {pasted}");
    }

    #[test]
    fn viewport_pin_mode_draft_and_right_inspector_actions_work() {
        let mut backend = CpuCameraBackend::default();
        backend.mock_pick = Some(crate::engine::ViewerPickHit {
            object_id: 3,
            world_point: [5.0, 0.0, 2.0],
        });
        let state = ViewerState::new(
            sample_scene_with_room(),
            "South Office",
            Some(Box::new(backend)),
        );
        let mut rt = Runtime::new(state, view, (1280.0, 800.0), Env::new(true, 1.0));
        rt.on_key = Some(on_window_key);
        step_frames(&mut rt);

        // Click on viewport -> picks aperture 3 -> Right Inspector appears
        let (vx, vy) = rt.find("viewport-canvas").unwrap();
        rt.pointer_move(vx, vy);
        rt.pointer_down(vx, vy);
        rt.frame(1.0 / 120.0);
        rt.pointer_up(vx, vy);
        step_frames(&mut rt);
        assert_eq!(rt.state.selected_ids, vec![3]);
        assert!(rt.find("right-inspector").is_some());

        // Wait past double-click interval, then perform a fresh double-click to escalate Aperture 3 -> Room 1
        for _ in 0..12 {
            rt.frame(0.1);
        }
        rt.pointer_move(vx, vy);
        for _ in 0..2 {
            rt.pointer_down(vx, vy);
            rt.frame(1.0 / 120.0);
            rt.pointer_up(vx, vy);
            rt.frame(1.0 / 120.0);
        }
        step_frames(&mut rt);
        assert_eq!(rt.state.selected_ids, vec![1]);

        // Re-select aperture 3 via outliner, test Inspector Isolate + Pin Here
        click_key(&mut rt, "outliner-obj-3");
        assert_eq!(rt.state.selected_ids, vec![3]);
        click_key(&mut rt, "btn-isolate");
        assert!(rt.state.local_isolate);
        click_key(&mut rt, "btn-pin-here");
        assert!(rt.find("pin-composer").is_some());

        rt.key(KeyEvent::from(Key::Text("Check SHGC glazing".into())));
        step_frames(&mut rt);
        click_key(&mut rt, "btn-pin-save");
        assert!(rt.state.pin_draft.is_none());
        assert_eq!(rt.state.annotations.len(), 1);
        assert_eq!(rt.state.annotations[0].status, PinStatus::Open);
        assert_eq!(rt.state.annotations[0].comment, "Check SHGC glazing");
        assert!(rt.find("btn-pin-mode").is_some());
        assert!(rt.find("axis-hud").is_some());

        // Enter Pin Mode via toolbar & click open viewport area directly
        click_key(&mut rt, "btn-pin-mode");
        assert!(rt.state.pin_mode);
        let (vx2, vy2) = rt.find("viewport-canvas").unwrap();
        let (px, py) = (vx2 + 140.0, vy2 + 100.0);
        rt.pointer_move(px, py);
        rt.pointer_down(px, py);
        rt.frame(1.0 / 120.0);
        rt.pointer_up(px, py);
        step_frames(&mut rt);
        assert!(
            rt.state.pin_draft.is_some(),
            "pin_mode={} open_menu={:?} active_pin={:?} click=({px},{py})",
            rt.state.pin_mode,
            rt.state.open_menu,
            rt.state.active_pin_id
        );
    }

    #[test]
    fn narrow_480px_layout_stays_single_row_without_clipping() {
        let state = ViewerState::new(sample_scene_with_room(), "MultiZoneOfficeLongTitle", None);
        let mut rt = Runtime::new(state, view, (480.0, 640.0), Env::new(true, 1.0));
        rt.frame(0.0);
        rt.frame(0.0);
        rt.frame(0.0);

        let elems = rt.elements();
        let top = elems
            .iter()
            .find(|e| e.key.as_deref() == Some("top-bar"))
            .expect("top-bar exists");
        assert!((top.rect[3] - 40.0).abs() <= 1.0, "top-bar height: {:?}", top.rect);

        for key in [
            "btn-drawer",
            "btn-color-by",
            "btn-cam-menu",
            "btn-ortho",
            "btn-sec-down",
            "btn-section",
            "btn-sec-up",
            "btn-pin-mode",
            "btn-copy-context",
            "btn-capture",
            "btn-theme",
        ] {
            let info = elems
                .iter()
                .find(|e| e.key.as_deref() == Some(key))
                .unwrap_or_else(|| panic!("missing compact control {key}"));
            assert!(
                info.rect[0] >= 0.0 && info.rect[0] + info.rect[2] <= 480.5,
                "{key} overflowed 480px: {:?}",
                info.rect
            );
            assert!(
                info.rect[1] >= 0.0 && info.rect[1] + info.rect[3] <= 41.0,
                "{key} wrapped off 40px bar: {:?}",
                info.rect
            );
        }

        // Opening drawer at 480px floats it without crushing viewport below 400px
        click_key(&mut rt, "btn-drawer");
        let elems2 = rt.elements();
        let vp = elems2
            .iter()
            .find(|e| e.key.as_deref() == Some("viewport-canvas"))
            .expect("viewport exists");
        assert!(vp.rect[2] >= 470.0, "viewport squeezed at 480px: {:?}", vp.rect);
    }
}
