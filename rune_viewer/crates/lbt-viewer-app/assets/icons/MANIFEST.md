# Rune viewer icons

Official Ladybug Tools artwork (`lbt/`) is used everywhere an Artwork icon exists:
brand badges (`lbt/honeybee.png`, `lbt/ladybug.svg`), North compass (`lbt/compass.svg`),
all Honeybee Schema tree/inspector/breadcrumb objects (`lbt/model.png`, `lbt/room.png`,
`lbt/face.png`, `lbt/aperture.png`, `lbt/door.png`, `lbt/shade.png`, `lbt/context_shade.png`),
all 7 ColorBy attribute modes (`lbt/viz_by_type.png`, `lbt/viz_by_bc.png`, `lbt/story.png`,
`lbt/zone.png`, `lbt/program.png`, `lbt/construction_set.png`, `lbt/hvac.png`), and
matching studio tools (`lbt/section_view.png`, `lbt/legend.png`, `lbt/capture_view.png`,
`lbt/validation.png`, `lbt/color_by.png`, `lbt/color_room_attr.png`).

Custom monochrome-white (`#FFFFFF`) SVGs (`custom/`) are used solely for generic UI controls
that have no Ladybug Tools Artwork equivalent (panel toggle, camera presets, ortho/persp,
section up/down, pin, copy AI, theme toggle, language toggle, isolate/similar/clear, exit room,
tree chevrons, and severity badges).

Render `multicolor` assets as-is (downsampled with linear-light area filtering to 64×64 for PNGs).
Use the alpha of `monochrome-white` assets for tinting via `El::pixels_tint`.

The official artwork repository asks users to request permission before use.
See its [copyright notice](https://github.com/ladybug-tools/artwork#copyright-notice).

| Relative path | Origin | Rendering |
| --- | --- | --- |
| `lbt/honeybee.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_bugs/png/honeybee.png) (600×600) | multicolor |
| `lbt/ladybug.svg` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_bugs/svg/ladybug.svg) | multicolor |
| `lbt/compass.svg` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/ladybug/svg/compass.svg) | multicolor |
| `lbt/model.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/model.png) (450×450) | multicolor |
| `lbt/room.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/room.png) (450×450) | multicolor |
| `lbt/face.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/face.png) (450×450) | multicolor |
| `lbt/aperture.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/aperture.png) (450×450) | multicolor |
| `lbt/door.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/door.png) (450×450) | multicolor |
| `lbt/shade.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/shade.png) (450×450) | multicolor |
| `lbt/context_shade.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/contextshade.png) (450×450) | multicolor |
| `lbt/viz_by_type.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/vizbytype.png) (450×450) | multicolor |
| `lbt/viz_by_bc.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/vizbybc.png) (450×450) | multicolor |
| `lbt/color_by.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/colorfaceattr.png) (450×450) | multicolor |
| `lbt/color_room_attr.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/colorroomattr.png) (450×450) | multicolor |
| `lbt/story.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/setstory.png) (450×450) | multicolor |
| `lbt/zone.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/setzone.png) (450×450) | multicolor |
| `lbt/program.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/program.png) (450×450) | multicolor |
| `lbt/construction_set.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/constructionset.png) (450×450) | multicolor |
| `lbt/hvac.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/allairhvac.png) (450×450) | multicolor |
| `lbt/section_view.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/sectionview.png) (450×450) | multicolor |
| `lbt/legend.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/ladybug/png/createlegend.png) (450×450) | multicolor |
| `lbt/capture_view.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/ladybug/png/captureview.png) (450×450) | multicolor |
| `lbt/validation.png` | [Official](https://raw.githubusercontent.com/ladybug-tools/artwork/master/icons_components/honeybee/png/validatehb.png) (450×450) | multicolor |
| `custom/panel.svg` | Custom SVG | monochrome-white |
| `custom/cam_axon.svg` | Custom SVG | monochrome-white |
| `custom/cam_top.svg` | Custom SVG | monochrome-white |
| `custom/cam_fit.svg` | Custom SVG | monochrome-white |
| `custom/proj_ortho.svg` | Custom SVG | monochrome-white |
| `custom/proj_persp.svg` | Custom SVG | monochrome-white |
| `custom/section_up.svg` | Custom SVG | monochrome-white |
| `custom/section_down.svg` | Custom SVG | monochrome-white |
| `custom/pin.svg` | Custom SVG | monochrome-white |
| `custom/copy_context.svg` | Custom SVG | monochrome-white |
| `custom/theme_dark.svg` | Custom SVG | monochrome-white |
| `custom/theme_light.svg` | Custom SVG | monochrome-white |
| `custom/lang.svg` | Custom SVG | monochrome-white |
| `custom/isolate.svg` | Custom SVG | monochrome-white |
| `custom/similar.svg` | Custom SVG | monochrome-white |
| `custom/clear.svg` | Custom SVG | monochrome-white |
| `custom/exit_room.svg` | Custom SVG | monochrome-white |
| `custom/chevron_right.svg` | Custom SVG | monochrome-white |
| `custom/chevron_down.svg` | Custom SVG | monochrome-white |
| `custom/issue_error.svg` | Custom SVG | monochrome-white |
| `custom/issue_warn.svg` | Custom SVG | monochrome-white |
