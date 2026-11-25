//! Shared `wgpu` architectural scene core: styles textures, globals uniform, section-plane
//! resolution, room descendant expansion, coplanar pair anti-ghosting, and passes 0..4c
//! shared by native and embedded renderers.

use std::collections::{HashMap, HashSet};
use std::mem::{offset_of, size_of};

use bytemuck::{Pod, Zeroable};
use lbt_scene::{
    Bounds3, ColorBy, EdgeVertex, IsolationMode, MeshVertex, ObjectKind, ObjectRecord, SceneData,
    SectionAxis, SectionSpec,
};
use wgpu::util::DeviceExt;

use crate::camera::OrbitCamera;
use crate::error::RendererError;
use crate::palette::{resolve_scene_colors, srgb_to_linear};

pub const COLOR_FORMAT: wgpu::TextureFormat = wgpu::TextureFormat::Rgba8UnormSrgb;
pub const DEPTH_FORMAT: wgpu::TextureFormat = wgpu::TextureFormat::Depth32Float;
pub const STYLE_TEX_WIDTH: u32 = 256;

const FLAG_SELECTED: u32 = 1 << 0;
const FLAG_HIGHLIGHTED: u32 = 1 << 1;
const FLAG_ERROR: u32 = 1 << 2;
const FLAG_WARNING: u32 = 1 << 3;
const FLAG_GHOST: u32 = 1 << 4;
const FLAG_HIDDEN: u32 = 1 << 5;
const FLAG_TRANSLUCENT: u32 = 1 << 6;
const FLAG_CULL_BACK: u32 = 1 << 7;

/// Subtle positive bias on opaque surfaces so wireframe edges and coplanar glazing stay crisp.
const OPAQUE_DEPTH_BIAS: wgpu::DepthBiasState = wgpu::DepthBiasState {
    constant: 1,
    slope_scale: 0.75,
    clamp: 0.0,
};

/// Subtle negative bias on active glazing so apertures/glass doors never z-fight with host frames.
const GLAZING_DEPTH_BIAS: wgpu::DepthBiasState = wgpu::DepthBiasState {
    constant: -2,
    slope_scale: -1.0,
    clamp: 0.0,
};

/// Stronger positive bias on ghosted context shells so adjacent ghost rooms stay strictly behind
/// active edited-room surfaces and allow clean ghost silhouette edges.
const GHOST_DEPTH_BIAS: wgpu::DepthBiasState = wgpu::DepthBiasState {
    constant: 6,
    slope_scale: 2.0,
    clamp: 0.0,
};

/// Successful pick result containing the object ID, room ownership, ghost state, and world point.
#[derive(Copy, Clone, Debug, PartialEq)]
pub struct PickHit {
    /// Non-zero [`ObjectRecord::object_id`] under the picked pixel.
    pub object_id: u32,
    /// Owning Room [`ObjectRecord::object_id`] (`Some(room_id)` for a Room and all its
    /// descendants; `None` for orphaned geometry and `ShadeMesh`es).
    pub owner_room_id: Option<u32>,
    /// `true` when the picked object is currently rendered as ghosted context (e.g., outside
    /// [`RenderState::editing_room_id`] or non-highlighted under [`IsolationMode::GhostContext`]).
    pub is_ghosted: bool,
    /// Exact world-space XYZ intersection point.
    pub world_point: [f32; 3],
}

/// Interactive visual styling, isolation, Room Edit Mode, validation, and section-cut state.
#[derive(Clone, Debug, PartialEq)]
pub struct RenderState {
    pub color_by: ColorBy,
    pub selected_ids: Vec<u32>,
    pub highlighted_ids: Vec<u32>,
    pub isolation_mode: IsolationMode,
    /// Active SketchUp/OpenStudio-style Room Edit Mode target (`Some(room_id)` fades rest of model).
    pub editing_room_id: Option<u32>,
    pub validation_error_ids: Vec<u32>,
    pub validation_warning_ids: Vec<u32>,
    pub section: Option<SectionSpec>,
    pub dark_mode: bool,
    pub show_edges: bool,
}

impl Default for RenderState {
    fn default() -> Self {
        Self {
            color_by: ColorBy::Type,
            selected_ids: Vec::new(),
            highlighted_ids: Vec::new(),
            isolation_mode: IsolationMode::Highlight,
            editing_room_id: None,
            validation_error_ids: Vec::new(),
            validation_warning_ids: Vec::new(),
            section: None,
            dark_mode: true,
            show_edges: true,
        }
    }
}

#[repr(C)]
#[derive(Copy, Clone, Debug, Pod, Zeroable)]
pub(crate) struct GlobalsUniform {
    pub view_proj: [[f32; 4]; 4],
    pub camera_pos: [f32; 4],
    pub camera_forward: [f32; 4],
    pub section_plane: [f32; 4],
    pub bg_bottom: [f32; 4],
    pub bg_top: [f32; 4],
    pub accent_selected: [f32; 4],
    pub accent_highlight: [f32; 4],
    pub flags: [u32; 4],
}

const _: () = {
    assert!(size_of::<GlobalsUniform>() == 192);
    assert!(size_of::<MeshVertex>() == 32);
    assert!(size_of::<EdgeVertex>() == 16);
};

pub(crate) struct ColorTargets {
    pub width: u32,
    pub height: u32,
    pub color_msaa_view: Option<wgpu::TextureView>,
    #[cfg_attr(target_arch = "wasm32", allow(dead_code))]
    pub color_resolve_tex: wgpu::Texture,
    pub color_resolve_view: wgpu::TextureView,
    pub depth_view: wgpu::TextureView,
}

/// Shared GPU state for rendering Honeybee geometry with WebGPU/WebGL2/DX12/Metal/Vulkan.
pub(crate) struct SceneGpuCore {
    pub device: wgpu::Device,
    pub queue: wgpu::Queue,
    pub sample_count: u32,
    pub bind_group_layout: wgpu::BindGroupLayout,
    #[cfg_attr(target_arch = "wasm32", allow(dead_code))]
    pub pipeline_layout: wgpu::PipelineLayout,

    pub globals_buffer: wgpu::Buffer,
    pub style_tex_height: u32,
    pub style_color_tex: wgpu::Texture,
    pub style_color_view: wgpu::TextureView,
    pub style_flags_tex: wgpu::Texture,
    pub style_flags_view: wgpu::TextureView,
    pub bind_group: wgpu::BindGroup,

    pub bg_pipeline: wgpu::RenderPipeline,
    pub opaque_pipeline: wgpu::RenderPipeline,
    pub edge_pipeline: wgpu::RenderPipeline,
    pub translucent_back_pipeline: wgpu::RenderPipeline,
    pub translucent_front_pipeline: wgpu::RenderPipeline,
    pub ghost_depth_pipeline: wgpu::RenderPipeline,
    pub ghost_color_pipeline: wgpu::RenderPipeline,
    pub ghost_edge_pipeline: wgpu::RenderPipeline,

    pub vertex_buffer: Option<wgpu::Buffer>,
    pub index_buffer: Option<wgpu::Buffer>,
    pub index_count: u32,
    pub edge_buffer: Option<wgpu::Buffer>,
    pub edge_vertex_count: u32,

    pub scene_meta: SceneData,
    pub owner_room_map: HashMap<u32, Option<u32>>,
    pub coplanar_surface_pairs: Vec<(u32, u32)>,
    pub ghosted_ids: HashSet<u32>,
    pub has_active_translucent: bool,
    pub has_ghost: bool,
    pub max_object_id: u32,
    pub state: RenderState,
    pub camera: OrbitCamera,
    pub targets: Option<ColorTargets>,
}

impl SceneGpuCore {
    pub fn new(device: wgpu::Device, queue: wgpu::Queue, sample_count: u32) -> Self {
        let shader_module = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("lbt_building_shader"),
            source: wgpu::ShaderSource::Wgsl(include_str!("shader.wgsl").into()),
        });

        let bind_group_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("lbt_globals_styles_layout"),
            entries: &[
                wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::VERTEX_FRAGMENT,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Uniform,
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 1,
                    visibility: wgpu::ShaderStages::VERTEX_FRAGMENT,
                    ty: wgpu::BindingType::Texture {
                        sample_type: wgpu::TextureSampleType::Float { filterable: false },
                        view_dimension: wgpu::TextureViewDimension::D2,
                        multisampled: false,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 2,
                    visibility: wgpu::ShaderStages::VERTEX_FRAGMENT,
                    ty: wgpu::BindingType::Texture {
                        sample_type: wgpu::TextureSampleType::Float { filterable: false },
                        view_dimension: wgpu::TextureViewDimension::D2,
                        multisampled: false,
                    },
                    count: None,
                },
            ],
        });

        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: Some("lbt_pipeline_layout"),
            bind_group_layouts: &[Some(&bind_group_layout)],
            immediate_size: 0,
        });

        let globals_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("lbt_globals_uniform"),
            size: size_of::<GlobalsUniform>() as u64,
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });

        let style_tex_height = 1u32;
        let (style_color_tex, style_color_view) =
            create_style_texture(&device, "lbt_style_color_tex", style_tex_height);
        let (style_flags_tex, style_flags_view) =
            create_style_texture(&device, "lbt_style_flags_tex", style_tex_height);
        write_style_row_fallback(&queue, &style_color_tex, &style_flags_tex, style_tex_height);

        let bind_group = create_bind_group(
            &device,
            &bind_group_layout,
            &globals_buffer,
            &style_color_view,
            &style_flags_view,
        );

        let mesh_layout = mesh_vertex_layout();
        let edge_layout = edge_vertex_layout();
        let color_multisample = wgpu::MultisampleState {
            count: sample_count,
            mask: !0,
            alpha_to_coverage_enabled: false,
        };

        let bg_pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("lbt_bg_pipeline"),
            layout: Some(&pipeline_layout),
            vertex: wgpu::VertexState {
                module: &shader_module,
                entry_point: Some("vs_bg"),
                compilation_options: Default::default(),
                buffers: &[],
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader_module,
                entry_point: Some("fs_bg"),
                compilation_options: Default::default(),
                targets: &[Some(wgpu::ColorTargetState {
                    format: COLOR_FORMAT,
                    blend: None,
                    write_mask: wgpu::ColorWrites::ALL,
                })],
            }),
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleList,
                ..Default::default()
            },
            depth_stencil: Some(wgpu::DepthStencilState {
                format: DEPTH_FORMAT,
                depth_write_enabled: Some(false),
                depth_compare: Some(wgpu::CompareFunction::Always),
                stencil: Default::default(),
                bias: Default::default(),
            }),
            multisample: color_multisample,
            multiview_mask: None,
            cache: None,
        });

        let opaque_pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("lbt_opaque_pipeline"),
            layout: Some(&pipeline_layout),
            vertex: wgpu::VertexState {
                module: &shader_module,
                entry_point: Some("vs_opaque"),
                compilation_options: Default::default(),
                buffers: &mesh_layout,
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader_module,
                entry_point: Some("fs_solid"),
                compilation_options: Default::default(),
                targets: &[Some(wgpu::ColorTargetState {
                    format: COLOR_FORMAT,
                    blend: None,
                    write_mask: wgpu::ColorWrites::ALL,
                })],
            }),
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleList,
                cull_mode: None,
                ..Default::default()
            },
            depth_stencil: Some(wgpu::DepthStencilState {
                format: DEPTH_FORMAT,
                depth_write_enabled: Some(true),
                depth_compare: Some(wgpu::CompareFunction::LessEqual),
                stencil: Default::default(),
                bias: OPAQUE_DEPTH_BIAS,
            }),
            multisample: color_multisample,
            multiview_mask: None,
            cache: None,
        });

        let edge_pipeline = create_edge_pipeline(
            &device,
            &pipeline_layout,
            &shader_module,
            &edge_layout,
            color_multisample,
            "vs_edge",
            "fs_edge",
            "lbt_edge_pipeline",
        );

        let translucent_back_pipeline = create_translucent_pipeline(
            &device,
            &pipeline_layout,
            &shader_module,
            &mesh_layout,
            color_multisample,
            Some(wgpu::Face::Front),
            "lbt_translucent_back_pipeline",
        );
        let translucent_front_pipeline = create_translucent_pipeline(
            &device,
            &pipeline_layout,
            &shader_module,
            &mesh_layout,
            color_multisample,
            Some(wgpu::Face::Back),
            "lbt_translucent_front_pipeline",
        );

        let ghost_depth_pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("lbt_ghost_depth_pipeline"),
            layout: Some(&pipeline_layout),
            vertex: wgpu::VertexState {
                module: &shader_module,
                entry_point: Some("vs_ghost"),
                compilation_options: Default::default(),
                buffers: &mesh_layout,
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader_module,
                entry_point: Some("fs_ghost_depth"),
                compilation_options: Default::default(),
                targets: &[Some(wgpu::ColorTargetState {
                    format: COLOR_FORMAT,
                    blend: None,
                    write_mask: wgpu::ColorWrites::empty(),
                })],
            }),
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleList,
                cull_mode: None,
                ..Default::default()
            },
            depth_stencil: Some(wgpu::DepthStencilState {
                format: DEPTH_FORMAT,
                depth_write_enabled: Some(true),
                depth_compare: Some(wgpu::CompareFunction::LessEqual),
                stencil: Default::default(),
                bias: GHOST_DEPTH_BIAS,
            }),
            multisample: color_multisample,
            multiview_mask: None,
            cache: None,
        });

        let ghost_color_pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("lbt_ghost_color_pipeline"),
            layout: Some(&pipeline_layout),
            vertex: wgpu::VertexState {
                module: &shader_module,
                entry_point: Some("vs_ghost"),
                compilation_options: Default::default(),
                buffers: &mesh_layout,
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader_module,
                entry_point: Some("fs_ghost_color"),
                compilation_options: Default::default(),
                targets: &[Some(wgpu::ColorTargetState {
                    format: COLOR_FORMAT,
                    blend: Some(wgpu::BlendState::ALPHA_BLENDING),
                    write_mask: wgpu::ColorWrites::ALL,
                })],
            }),
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleList,
                cull_mode: None,
                ..Default::default()
            },
            depth_stencil: Some(wgpu::DepthStencilState {
                format: DEPTH_FORMAT,
                depth_write_enabled: Some(false),
                depth_compare: Some(wgpu::CompareFunction::LessEqual),
                stencil: Default::default(),
                bias: GHOST_DEPTH_BIAS,
            }),
            multisample: color_multisample,
            multiview_mask: None,
            cache: None,
        });

        let ghost_edge_pipeline = create_edge_pipeline(
            &device,
            &pipeline_layout,
            &shader_module,
            &edge_layout,
            color_multisample,
            "vs_ghost_edge",
            "fs_ghost_edge",
            "lbt_ghost_edge_pipeline",
        );

        Self {
            device,
            queue,
            sample_count,
            bind_group_layout,
            pipeline_layout,
            globals_buffer,
            style_tex_height,
            style_color_tex,
            style_color_view,
            style_flags_tex,
            style_flags_view,
            bind_group,
            bg_pipeline,
            opaque_pipeline,
            edge_pipeline,
            translucent_back_pipeline,
            translucent_front_pipeline,
            ghost_depth_pipeline,
            ghost_color_pipeline,
            ghost_edge_pipeline,
            vertex_buffer: None,
            index_buffer: None,
            index_count: 0,
            edge_buffer: None,
            edge_vertex_count: 0,
            scene_meta: SceneData::default(),
            owner_room_map: HashMap::new(),
            coplanar_surface_pairs: Vec::new(),
            ghosted_ids: HashSet::new(),
            has_active_translucent: false,
            has_ghost: false,
            max_object_id: 0,
            state: RenderState::default(),
            camera: OrbitCamera::new(),
            targets: None,
        }
    }

    pub fn set_scene(&mut self, scene: &SceneData) {
        if !scene.vertices.is_empty() && !scene.indices.is_empty() {
            self.vertex_buffer = Some(self.device.create_buffer_init(
                &wgpu::util::BufferInitDescriptor {
                    label: Some("lbt_mesh_vertices"),
                    contents: bytemuck::cast_slice(&scene.vertices),
                    usage: wgpu::BufferUsages::VERTEX,
                },
            ));
            self.index_buffer = Some(self.device.create_buffer_init(
                &wgpu::util::BufferInitDescriptor {
                    label: Some("lbt_mesh_indices"),
                    contents: bytemuck::cast_slice(&scene.indices),
                    usage: wgpu::BufferUsages::INDEX,
                },
            ));
            self.index_count = scene.indices.len() as u32;
        } else {
            self.vertex_buffer = None;
            self.index_buffer = None;
            self.index_count = 0;
        }

        if !scene.edge_vertices.is_empty() {
            self.edge_buffer = Some(self.device.create_buffer_init(
                &wgpu::util::BufferInitDescriptor {
                    label: Some("lbt_edge_vertices"),
                    contents: bytemuck::cast_slice(&scene.edge_vertices),
                    usage: wgpu::BufferUsages::VERTEX,
                },
            ));
            self.edge_vertex_count = scene.edge_vertices.len() as u32;
        } else {
            self.edge_buffer = None;
            self.edge_vertex_count = 0;
        }

        self.scene_meta = SceneData {
            model_identifier: scene.model_identifier.clone(),
            display_name: scene.display_name.clone(),
            units: scene.units.clone(),
            source_path: scene.source_path.clone(),
            bounds: scene.bounds,
            vertices: Vec::new(),
            indices: Vec::new(),
            edge_vertices: Vec::new(),
            objects: scene.objects.clone(),
            stories: scene.stories.clone(),
        };
        self.owner_room_map = resolve_owner_room_map(&self.scene_meta.objects);
        self.coplanar_surface_pairs = find_coplanar_surface_pairs(&self.scene_meta.objects);
        self.max_object_id = scene
            .objects
            .iter()
            .map(|o| o.object_id)
            .max()
            .unwrap_or(0);

        self.upload_styles();
    }

    pub fn set_render_state(&mut self, state: &RenderState) {
        let styles_changed = self.state.color_by != state.color_by
            || self.state.selected_ids != state.selected_ids
            || self.state.highlighted_ids != state.highlighted_ids
            || self.state.isolation_mode != state.isolation_mode
            || self.state.editing_room_id != state.editing_room_id
            || self.state.validation_error_ids != state.validation_error_ids
            || self.state.validation_warning_ids != state.validation_warning_ids;
        self.state = state.clone();
        if styles_changed {
            self.upload_styles();
        }
    }

    /// Active validated editing room ID (only `Some` when the room exists in the loaded scene).
    #[cfg_attr(target_arch = "wasm32", allow(dead_code))]
    pub fn active_editing_room_id(&self) -> Option<u32> {
        active_editing_room_in_scene(&self.scene_meta.objects, &self.owner_room_map, self.state.editing_room_id)
    }

    /// Return `(owner_room_id, is_ghosted)` for a picked `object_id`.
    #[cfg_attr(target_arch = "wasm32", allow(dead_code))]
    pub fn object_pick_meta(&self, object_id: u32) -> (Option<u32>, bool) {
        let owner = self.owner_room_map.get(&object_id).copied().flatten();
        let ghosted = self.ghosted_ids.contains(&object_id);
        (owner, ghosted)
    }

    pub fn upload_styles(&mut self) {
        let len = (self.max_object_id as usize) + 1;
        let tex_height = (len as u32).div_ceil(STYLE_TEX_WIDTH).max(1);
        let texel_count = (STYLE_TEX_WIDTH * tex_height) as usize;

        let mut color_rgba = vec![0u8; texel_count * 4];
        let mut flags_rgba = vec![0u8; texel_count * 4];
        // Initialize slot 0 and padding slots to opaque mid-gray fallback.
        for px in color_rgba.chunks_exact_mut(4) {
            px.copy_from_slice(&[128, 128, 128, 255]);
        }
        for px in flags_rgba.chunks_exact_mut(4) {
            px.copy_from_slice(&[0, 0, 0, 255]);
        }

        let base_srgb = resolve_scene_colors(&self.scene_meta, self.state.color_by);
        let selected_set = expand_room_descendants_with_map(
            &self.scene_meta.objects,
            &self.owner_room_map,
            &self.state.selected_ids,
        );
        let highlighted_set = expand_room_descendants_with_map(
            &self.scene_meta.objects,
            &self.owner_room_map,
            &self.state.highlighted_ids,
        );
        let error_set = expand_room_descendants_with_map(
            &self.scene_meta.objects,
            &self.owner_room_map,
            &self.state.validation_error_ids,
        );
        let warning_set = expand_room_descendants_with_map(
            &self.scene_meta.objects,
            &self.owner_room_map,
            &self.state.validation_warning_ids,
        );

        let isolation_active = !highlighted_set.is_empty()
            && matches!(
                self.state.isolation_mode,
                IsolationMode::GhostContext | IsolationMode::Isolate
            );
        let active_edit_room = active_editing_room_in_scene(
            &self.scene_meta.objects,
            &self.owner_room_map,
            self.state.editing_room_id,
        );

        let mut per_id_flags = vec![0u32; len];
        let mut has_active_translucent = false;
        let mut has_ghost = false;
        self.ghosted_ids.clear();

        for record in &self.scene_meta.objects {
            let id = record.object_id as usize;
            if id >= texel_count || id >= len {
                continue;
            }
            let srgb = base_srgb.get(id).copied().unwrap_or([0.6, 0.6, 0.6, 1.0]);

            let mut flags = 0u32;
            let is_selected = selected_set.contains(&record.object_id);
            let is_highlighted = highlighted_set.contains(&record.object_id);
            let is_error = error_set.contains(&record.object_id);
            let is_warning = warning_set.contains(&record.object_id);
            let owner_room = self.owner_room_map.get(&record.object_id).copied().flatten();

            if is_selected {
                flags |= FLAG_SELECTED;
            }
            if is_highlighted {
                flags |= FLAG_HIGHLIGHTED;
            }
            if is_error {
                flags |= FLAG_ERROR;
            }
            if is_warning {
                flags |= FLAG_WARNING;
            }

            let is_translucent = is_record_translucent(record, srgb[3]);
            if is_translucent {
                flags |= FLAG_TRANSLUCENT;
            }

            if isolation_active && !is_highlighted {
                match self.state.isolation_mode {
                    IsolationMode::GhostContext => {
                        flags |= FLAG_GHOST;
                    }
                    IsolationMode::Isolate => {
                        flags |= FLAG_HIDDEN;
                    }
                    IsolationMode::Highlight => {}
                }
            } else if let Some(edit_rid) = active_edit_room
                && owner_room != Some(edit_rid)
            {
                flags |= FLAG_GHOST;
            }

            if (flags & FLAG_HIDDEN) == 0 {
                if (flags & FLAG_GHOST) != 0 {
                    has_ghost = true;
                    self.ghosted_ids.insert(record.object_id);
                } else if (flags & FLAG_TRANSLUCENT) != 0 {
                    has_active_translucent = true;
                }
            }

            per_id_flags[id] = flags;

            let off = id * 4;
            color_rgba[off] = to_u8(srgb[0]);
            color_rgba[off + 1] = to_u8(srgb[1]);
            color_rgba[off + 2] = to_u8(srgb[2]);
            color_rgba[off + 3] = to_u8(srgb[3]);
        }

        // Prevent double-blending on coplanar opposite-normal Surface-BC pairs (e.g. shared
        // interior Air Boundaries / interior Apertures, or ghosted adjacent room walls) whenever
        // BOTH faces in the pair are drawn in the same translucent/ghost pass.
        for &(id_a, id_b) in &self.coplanar_surface_pairs {
            let (ia, ib) = (id_a as usize, id_b as usize);
            if ia >= len || ib >= len {
                continue;
            }
            let fa = per_id_flags[ia];
            let fb = per_id_flags[ib];
            if ((fa | fb) & FLAG_HIDDEN) != 0 {
                continue;
            }
            let both_active_translucent = (fa & FLAG_GHOST) == 0
                && (fb & FLAG_GHOST) == 0
                && (fa & FLAG_TRANSLUCENT) != 0
                && (fb & FLAG_TRANSLUCENT) != 0;
            let both_ghost = (fa & FLAG_GHOST) != 0 && (fb & FLAG_GHOST) != 0;
            if both_active_translucent || both_ghost {
                per_id_flags[ia] |= FLAG_CULL_BACK;
                per_id_flags[ib] |= FLAG_CULL_BACK;
            }
        }

        for record in &self.scene_meta.objects {
            let id = record.object_id as usize;
            if id >= texel_count || id >= len {
                continue;
            }
            let off = id * 4;
            flags_rgba[off] = (per_id_flags[id] & 0xff) as u8;
            flags_rgba[off + 1] = 0;
            flags_rgba[off + 2] = 0;
            flags_rgba[off + 3] = 255;
        }

        self.has_active_translucent = has_active_translucent;
        self.has_ghost = has_ghost;

        if tex_height > self.style_tex_height {
            self.style_tex_height = tex_height.next_power_of_two().max(1);
            let (ct, cv) =
                create_style_texture(&self.device, "lbt_style_color_tex", self.style_tex_height);
            let (ft, fv) =
                create_style_texture(&self.device, "lbt_style_flags_tex", self.style_tex_height);
            self.style_color_tex = ct;
            self.style_color_view = cv;
            self.style_flags_tex = ft;
            self.style_flags_view = fv;
            self.bind_group = create_bind_group(
                &self.device,
                &self.bind_group_layout,
                &self.globals_buffer,
                &self.style_color_view,
                &self.style_flags_view,
            );
        }

        let extent = wgpu::Extent3d {
            width: STYLE_TEX_WIDTH,
            height: tex_height,
            depth_or_array_layers: 1,
        };
        let layout = wgpu::TexelCopyBufferLayout {
            offset: 0,
            bytes_per_row: Some(STYLE_TEX_WIDTH * 4),
            rows_per_image: Some(tex_height),
        };
        self.queue.write_texture(
            wgpu::TexelCopyTextureInfo {
                texture: &self.style_color_tex,
                mip_level: 0,
                origin: wgpu::Origin3d::ZERO,
                aspect: wgpu::TextureAspect::All,
            },
            &color_rgba,
            layout,
            extent,
        );
        self.queue.write_texture(
            wgpu::TexelCopyTextureInfo {
                texture: &self.style_flags_tex,
                mip_level: 0,
                origin: wgpu::Origin3d::ZERO,
                aspect: wgpu::TextureAspect::All,
            },
            &flags_rgba,
            layout,
            extent,
        );
    }

    pub fn write_globals(&self, width: u32, height: u32) {
        let aspect = width.max(1) as f32 / height.max(1) as f32;
        let view_proj = self.camera.view_projection_matrix(aspect).to_cols_array_2d();
        let eye = self.camera.eye_position();
        let fwd = self.camera.forward();
        let is_ortho = self.camera.is_orthographic();
        let (section_enabled, section_plane) =
            resolve_section_plane(&self.scene_meta, self.state.section.as_ref());

        let (bg_bottom, bg_top) = if self.state.dark_mode {
            (
                srgb_to_linear([0.072, 0.088, 0.118, 1.0]),
                srgb_to_linear([0.122, 0.146, 0.188, 1.0]),
            )
        } else {
            (
                srgb_to_linear([0.896, 0.916, 0.944, 1.0]),
                srgb_to_linear([0.972, 0.980, 0.992, 1.0]),
            )
        };

        let accent_selected = if self.state.dark_mode {
            srgb_to_linear([0.22, 0.74, 0.97, 1.0])
        } else {
            srgb_to_linear([0.02, 0.50, 0.84, 1.0])
        };
        let accent_highlight = srgb_to_linear([0.98, 0.74, 0.16, 1.0]);

        let globals = GlobalsUniform {
            view_proj,
            camera_pos: [eye[0], eye[1], eye[2], if is_ortho { 1.0 } else { 0.0 }],
            camera_forward: [fwd[0], fwd[1], fwd[2], self.camera.ortho_height],
            section_plane,
            bg_bottom,
            bg_top,
            accent_selected,
            accent_highlight,
            flags: [
                u32::from(section_enabled),
                u32::from(self.state.dark_mode),
                u32::from(is_ortho),
                self.max_object_id,
            ],
        };
        self.queue
            .write_buffer(&self.globals_buffer, 0, bytemuck::bytes_of(&globals));
    }

    pub fn ensure_color_targets(
        &mut self,
        width: u32,
        height: u32,
        resolve_usage: wgpu::TextureUsages,
    ) -> Result<bool, RendererError> {
        let max_dim = self.device.limits().max_texture_dimension_2d;
        if width == 0 || height == 0 || width > max_dim || height > max_dim {
            return Err(RendererError::InvalidDimensions { width, height });
        }
        if let Some(existing) = &self.targets
            && existing.width == width
            && existing.height == height
        {
            return Ok(false);
        }

        let size = wgpu::Extent3d {
            width,
            height,
            depth_or_array_layers: 1,
        };

        let color_msaa_view = if self.sample_count > 1 {
            let tex = self.device.create_texture(&wgpu::TextureDescriptor {
                label: Some("lbt_color_msaa"),
                size,
                mip_level_count: 1,
                sample_count: self.sample_count,
                dimension: wgpu::TextureDimension::D2,
                format: COLOR_FORMAT,
                usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
                view_formats: &[],
            });
            Some(tex.create_view(&Default::default()))
        } else {
            None
        };

        let color_resolve_tex = self.device.create_texture(&wgpu::TextureDescriptor {
            label: Some("lbt_color_resolve"),
            size,
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: COLOR_FORMAT,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT | resolve_usage,
            view_formats: &[],
        });
        let color_resolve_view = color_resolve_tex.create_view(&Default::default());

        let depth_tex = self.device.create_texture(&wgpu::TextureDescriptor {
            label: Some("lbt_color_depth"),
            size,
            mip_level_count: 1,
            sample_count: self.sample_count,
            dimension: wgpu::TextureDimension::D2,
            format: DEPTH_FORMAT,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
            view_formats: &[],
        });
        let depth_view = depth_tex.create_view(&Default::default());

        self.targets = Some(ColorTargets {
            width,
            height,
            color_msaa_view,
            color_resolve_tex,
            color_resolve_view,
            depth_view,
        });
        Ok(true)
    }

    pub fn encode_scene_pass(
        &self,
        encoder: &mut wgpu::CommandEncoder,
        width: u32,
        height: u32,
    ) {
        self.write_globals(width, height);
        let targets = self.targets.as_ref().expect("color targets ensured");

        let (color_view, resolve_target) = match &targets.color_msaa_view {
            Some(msaa_view) => (msaa_view, Some(&targets.color_resolve_view)),
            None => (&targets.color_resolve_view, None),
        };

        let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            label: Some("lbt_color_pass"),
            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                view: color_view,
                depth_slice: None,
                resolve_target,
                ops: wgpu::Operations {
                    load: wgpu::LoadOp::Clear(wgpu::Color::BLACK),
                    store: wgpu::StoreOp::Store,
                },
            })],
            depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment {
                view: &targets.depth_view,
                depth_ops: Some(wgpu::Operations {
                    load: wgpu::LoadOp::Clear(1.0),
                    store: wgpu::StoreOp::Discard,
                }),
                stencil_ops: None,
            }),
            ..Default::default()
        });

        pass.set_bind_group(0, &self.bind_group, &[]);
        // Pass 0: Studio gradient background
        pass.set_pipeline(&self.bg_pipeline);
        pass.draw(0..3, 0..1);

        if let (Some(vb), Some(ib)) = (&self.vertex_buffer, &self.index_buffer)
            && self.index_count > 0
        {
            // Pass 1: Opaque active architectural surfaces
            pass.set_pipeline(&self.opaque_pipeline);
            pass.set_vertex_buffer(0, vb.slice(..));
            pass.set_index_buffer(ib.slice(..), wgpu::IndexFormat::Uint32);
            pass.draw_indexed(0..self.index_count, 0, 0..1);
        }

        if self.state.show_edges
            && let Some(eb) = &self.edge_buffer
            && self.edge_vertex_count > 0
        {
            // Pass 2: Active architectural crease & boundary edges
            pass.set_pipeline(&self.edge_pipeline);
            pass.set_vertex_buffer(0, eb.slice(..));
            pass.draw(0..self.edge_vertex_count, 0..1);
        }

        if self.has_active_translucent
            && let (Some(vb), Some(ib)) = (&self.vertex_buffer, &self.index_buffer)
            && self.index_count > 0
        {
            // Pass 3: Active translucent glass apertures & air boundaries (back-to-front)
            pass.set_vertex_buffer(0, vb.slice(..));
            pass.set_index_buffer(ib.slice(..), wgpu::IndexFormat::Uint32);
            pass.set_pipeline(&self.translucent_back_pipeline);
            pass.draw_indexed(0..self.index_count, 0, 0..1);
            pass.set_pipeline(&self.translucent_front_pipeline);
            pass.draw_indexed(0..self.index_count, 0, 0..1);
        }

        if self.has_ghost
            && let (Some(vb), Some(ib)) = (&self.vertex_buffer, &self.index_buffer)
            && self.index_count > 0
        {
            // Pass 4a + 4b: Ghost context single-layer shell (depth pre-pass then color pass)
            // eliminates muddy overlapping interior wall ghosting in Room Edit Mode & GhostContext.
            pass.set_vertex_buffer(0, vb.slice(..));
            pass.set_index_buffer(ib.slice(..), wgpu::IndexFormat::Uint32);
            pass.set_pipeline(&self.ghost_depth_pipeline);
            pass.draw_indexed(0..self.index_count, 0, 0..1);
            pass.set_pipeline(&self.ghost_color_pipeline);
            pass.draw_indexed(0..self.index_count, 0, 0..1);

            if self.state.show_edges
                && let Some(eb) = &self.edge_buffer
                && self.edge_vertex_count > 0
            {
                // Pass 4c: Visible ghost silhouette & crease edges tested against Pass 4a shell
                pass.set_pipeline(&self.ghost_edge_pipeline);
                pass.set_vertex_buffer(0, eb.slice(..));
                pass.draw(0..self.edge_vertex_count, 0..1);
            }
        }
    }
}

pub(crate) fn mesh_vertex_layout() -> [Option<wgpu::VertexBufferLayout<'static>>; 1] {
    [Some(wgpu::VertexBufferLayout {
        array_stride: size_of::<MeshVertex>() as wgpu::BufferAddress,
        step_mode: wgpu::VertexStepMode::Vertex,
        attributes: &[
            wgpu::VertexAttribute {
                format: wgpu::VertexFormat::Float32x3,
                offset: offset_of!(MeshVertex, position) as wgpu::BufferAddress,
                shader_location: 0,
            },
            wgpu::VertexAttribute {
                format: wgpu::VertexFormat::Float32x3,
                offset: offset_of!(MeshVertex, normal) as wgpu::BufferAddress,
                shader_location: 1,
            },
            wgpu::VertexAttribute {
                format: wgpu::VertexFormat::Uint32,
                offset: offset_of!(MeshVertex, object_id) as wgpu::BufferAddress,
                shader_location: 2,
            },
            wgpu::VertexAttribute {
                format: wgpu::VertexFormat::Uint32,
                offset: offset_of!(MeshVertex, kind_code) as wgpu::BufferAddress,
                shader_location: 3,
            },
        ],
    })]
}

pub(crate) fn edge_vertex_layout() -> [Option<wgpu::VertexBufferLayout<'static>>; 1] {
    [Some(wgpu::VertexBufferLayout {
        array_stride: size_of::<EdgeVertex>() as wgpu::BufferAddress,
        step_mode: wgpu::VertexStepMode::Vertex,
        attributes: &[
            wgpu::VertexAttribute {
                format: wgpu::VertexFormat::Float32x3,
                offset: offset_of!(EdgeVertex, position) as wgpu::BufferAddress,
                shader_location: 0,
            },
            wgpu::VertexAttribute {
                format: wgpu::VertexFormat::Uint32,
                offset: offset_of!(EdgeVertex, object_id) as wgpu::BufferAddress,
                shader_location: 1,
            },
        ],
    })]
}

pub(crate) fn choose_msaa_sample_count(adapter: &wgpu::Adapter) -> u32 {
    // WebGL2 downlevel contexts often have MSAA sRGB resolve quirks; stick to 1x on GLES/WebGL.
    if adapter.get_info().backend == wgpu::Backend::Gl {
        return 1;
    }
    let color_flags = adapter.get_texture_format_features(COLOR_FORMAT).flags;
    let depth_flags = adapter.get_texture_format_features(DEPTH_FORMAT).flags;
    let need_color = wgpu::TextureFormatFeatureFlags::MULTISAMPLE_X4
        | wgpu::TextureFormatFeatureFlags::MULTISAMPLE_RESOLVE;
    let need_depth = wgpu::TextureFormatFeatureFlags::MULTISAMPLE_X4;
    if color_flags.contains(need_color) && depth_flags.contains(need_depth) {
        4
    } else {
        1
    }
}

/// Resolve each `object_id` to its owning Room's `object_id` (`None` for orphaned geometry and
/// `ShadeMesh`es). Uses `ObjectRecord::owner_room_id` directly and falls back to walking
/// `parent_object_id` for hand-constructed synthetic test scenes.
pub(crate) fn resolve_owner_room_map(objects: &[ObjectRecord]) -> HashMap<u32, Option<u32>> {
    let by_id: HashMap<u32, &ObjectRecord> = objects
        .iter()
        .filter(|o| o.object_id != 0)
        .map(|o| (o.object_id, o))
        .collect();

    let mut map = HashMap::with_capacity(by_id.len());
    for (&id, &rec) in &by_id {
        let owner = if rec.owner_room_id.is_some() {
            rec.owner_room_id
        } else if rec.is_orphaned || rec.is_shade_mesh {
            None
        } else if rec.kind == ObjectKind::Room {
            Some(id)
        } else {
            let mut cur = rec.parent_object_id;
            let mut found = None;
            for _ in 0..8 {
                let Some(pid) = cur else {
                    break;
                };
                let Some(&parent) = by_id.get(&pid) else {
                    break;
                };
                if let Some(rid) = parent.owner_room_id {
                    found = Some(rid);
                    break;
                }
                if parent.kind == ObjectKind::Room {
                    found = Some(parent.object_id);
                    break;
                }
                cur = parent.parent_object_id;
            }
            found
        };
        map.insert(id, owner);
    }
    map
}

/// Validate that `editing_room_id` refers to an existing Room (or owner room) in `objects`.
pub(crate) fn active_editing_room_in_scene(
    objects: &[ObjectRecord],
    owner_room_map: &HashMap<u32, Option<u32>>,
    editing_room_id: Option<u32>,
) -> Option<u32> {
    let rid = editing_room_id.filter(|&id| id != 0)?;
    let exists = objects
        .iter()
        .any(|o| o.object_id == rid || owner_room_map.get(&o.object_id).copied().flatten() == Some(rid));
    exists.then_some(rid)
}

pub(crate) fn expand_room_descendants_with_map(
    objects: &[ObjectRecord],
    owner_room_map: &HashMap<u32, Option<u32>>,
    ids: &[u32],
) -> HashSet<u32> {
    let mut expanded: HashSet<u32> = ids.iter().copied().filter(|&id| id != 0).collect();
    if expanded.is_empty() {
        return expanded;
    }

    let mut room_ids = HashSet::new();
    for record in objects {
        if record.kind == ObjectKind::Room && expanded.contains(&record.object_id) {
            room_ids.insert(record.object_id);
        }
    }
    if room_ids.is_empty() {
        return expanded;
    }

    for record in objects {
        if owner_room_map
            .get(&record.object_id)
            .copied()
            .flatten()
            .is_some_and(|rid| room_ids.contains(&rid))
        {
            expanded.insert(record.object_id);
        }
    }
    expanded
}

fn is_air_boundary_type(face_type: Option<&str>) -> bool {
    face_type.is_some_and(|ft| {
        let norm = ft.trim();
        norm.eq_ignore_ascii_case("AirBoundary")
            || norm.eq_ignore_ascii_case("air_boundary")
            || norm.eq_ignore_ascii_case("air boundary")
    })
}

fn is_record_translucent(record: &ObjectRecord, srgb_alpha: f32) -> bool {
    if srgb_alpha < 0.99 {
        return true;
    }
    match record.kind {
        ObjectKind::Aperture => true,
        ObjectKind::Door => {
            record.is_glass
                || record.face_type.as_deref().is_some_and(|ft| {
                    ft.eq_ignore_ascii_case("GlassDoor") || ft.eq_ignore_ascii_case("glass_door")
                })
        }
        ObjectKind::Face => is_air_boundary_type(record.face_type.as_deref()),
        _ => false,
    }
}

/// Detect paired coplanar `Surface`-BC (or `AirBoundary`) faces/subfaces across adjacent rooms
/// so translucent & ghost passes can back-face cull paired twins and eliminate double-blending.
fn find_coplanar_surface_pairs(objects: &[ObjectRecord]) -> Vec<(u32, u32)> {
    const CELL_M: f32 = 0.05;
    const CENTROID_TOL_SQ: f32 = 0.025 * 0.025;
    const BOUNDS_TOL: f32 = 0.03;

    let candidates: Vec<&ObjectRecord> = objects
        .iter()
        .filter(|o| {
            o.object_id != 0
                && o.kind != ObjectKind::Room
                && o.bounds.is_valid()
                && (o.boundary_condition
                    .as_deref()
                    .is_some_and(|bc| bc.trim().eq_ignore_ascii_case("Surface"))
                    || is_air_boundary_type(o.face_type.as_deref()))
        })
        .collect();

    if candidates.len() < 2 {
        return Vec::new();
    }

    let quant = |c: [f32; 3]| -> (i32, i32, i32) {
        (
            (c[0] / CELL_M).floor() as i32,
            (c[1] / CELL_M).floor() as i32,
            (c[2] / CELL_M).floor() as i32,
        )
    };

    let mut grid: HashMap<(i32, i32, i32), Vec<usize>> = HashMap::with_capacity(candidates.len());
    for (idx, rec) in candidates.iter().enumerate() {
        grid.entry(quant(rec.centroid)).or_default().push(idx);
    }

    let mut pairs = Vec::new();
    for (i, a) in candidates.iter().enumerate() {
        let (gx, gy, gz) = quant(a.centroid);
        for dx in -1..=1 {
            for dy in -1..=1 {
                for dz in -1..=1 {
                    let Some(bucket) = grid.get(&(gx + dx, gy + dy, gz + dz)) else {
                        continue;
                    };
                    for &j in bucket {
                        if j <= i {
                            continue;
                        }
                        let b = candidates[j];
                        if a.kind != b.kind {
                            continue;
                        }
                        if a.owner_room_id.is_some() && a.owner_room_id == b.owner_room_id {
                            continue;
                        }
                        let d0 = a.centroid[0] - b.centroid[0];
                        let d1 = a.centroid[1] - b.centroid[1];
                        let d2 = a.centroid[2] - b.centroid[2];
                        if d0 * d0 + d1 * d1 + d2 * d2 > CENTROID_TOL_SQ {
                            continue;
                        }
                        let bounds_match = (0..3).all(|k| {
                            (a.bounds.min[k] - b.bounds.min[k]).abs() <= BOUNDS_TOL
                                && (a.bounds.max[k] - b.bounds.max[k]).abs() <= BOUNDS_TOL
                        });
                        if bounds_match {
                            pairs.push((a.object_id, b.object_id));
                        }
                    }
                }
            }
        }
    }
    pairs
}

pub(crate) fn resolve_section_plane(
    scene: &SceneData,
    section: Option<&SectionSpec>,
) -> (bool, [f32; 4]) {
    let Some(sec) = section else {
        return (false, [0.0, 0.0, 1.0, 0.0]);
    };
    if !sec.enabled {
        return (false, [0.0, 0.0, 1.0, 0.0]);
    }

    let axis_idx = match sec.axis {
        SectionAxis::X => 0,
        SectionAxis::Y => 1,
        SectionAxis::Z => 2,
    };

    let cut_val = if let Some(v) = sec.value.filter(|v| v.is_finite()) {
        v
    } else if let Some(story) = sec.story.as_deref() {
        story_section_value(scene, story, axis_idx)
            .unwrap_or_else(|| default_axis_midpoint(&scene.bounds, axis_idx))
    } else {
        default_axis_midpoint(&scene.bounds, axis_idx)
    };

    let sign = if sec.invert { -1.0 } else { 1.0 };
    let mut normal = [0.0_f32; 3];
    normal[axis_idx] = sign;
    (true, [normal[0], normal[1], normal[2], sign * cut_val])
}

fn story_section_value(scene: &SceneData, story: &str, axis_idx: usize) -> Option<f32> {
    let mut bounds = Bounds3::empty();
    for record in &scene.objects {
        if record.story.as_deref() == Some(story) && record.bounds.is_valid() {
            bounds.merge(&record.bounds);
        }
    }
    if !bounds.is_valid() {
        return None;
    }
    let min_v = bounds.min[axis_idx];
    let max_v = bounds.max[axis_idx];
    if axis_idx == 2 {
        let span = max_v - min_v;
        if span > 1.5 {
            Some((min_v + 1.2).min(max_v - 0.15))
        } else {
            Some(0.5 * (min_v + max_v))
        }
    } else {
        Some(0.5 * (min_v + max_v))
    }
}

fn default_axis_midpoint(bounds: &Bounds3, axis_idx: usize) -> f32 {
    if bounds.is_valid() {
        0.5 * (bounds.min[axis_idx] + bounds.max[axis_idx])
    } else if axis_idx == 2 {
        1.5
    } else {
        0.0
    }
}

#[inline]
fn to_u8(v: f32) -> u8 {
    (v.clamp(0.0, 1.0) * 255.0).round() as u8
}

fn create_style_texture(
    device: &wgpu::Device,
    label: &'static str,
    height: u32,
) -> (wgpu::Texture, wgpu::TextureView) {
    let tex = device.create_texture(&wgpu::TextureDescriptor {
        label: Some(label),
        size: wgpu::Extent3d {
            width: STYLE_TEX_WIDTH,
            height: height.max(1),
            depth_or_array_layers: 1,
        },
        mip_level_count: 1,
        sample_count: 1,
        dimension: wgpu::TextureDimension::D2,
        format: wgpu::TextureFormat::Rgba8Unorm,
        usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
        view_formats: &[],
    });
    let view = tex.create_view(&Default::default());
    (tex, view)
}

fn write_style_row_fallback(
    queue: &wgpu::Queue,
    color_tex: &wgpu::Texture,
    flags_tex: &wgpu::Texture,
    height: u32,
) {
    let texel_count = (STYLE_TEX_WIDTH * height.max(1)) as usize;
    let mut color_rgba = vec![0u8; texel_count * 4];
    for px in color_rgba.chunks_exact_mut(4) {
        px.copy_from_slice(&[128, 128, 128, 255]);
    }
    let mut flags_rgba = vec![0u8; texel_count * 4];
    for px in flags_rgba.chunks_exact_mut(4) {
        px.copy_from_slice(&[0, 0, 0, 255]);
    }
    let extent = wgpu::Extent3d {
        width: STYLE_TEX_WIDTH,
        height: height.max(1),
        depth_or_array_layers: 1,
    };
    let layout = wgpu::TexelCopyBufferLayout {
        offset: 0,
        bytes_per_row: Some(STYLE_TEX_WIDTH * 4),
        rows_per_image: Some(height.max(1)),
    };
    queue.write_texture(
        wgpu::TexelCopyTextureInfo {
            texture: color_tex,
            mip_level: 0,
            origin: wgpu::Origin3d::ZERO,
            aspect: wgpu::TextureAspect::All,
        },
        &color_rgba,
        layout,
        extent,
    );
    queue.write_texture(
        wgpu::TexelCopyTextureInfo {
            texture: flags_tex,
            mip_level: 0,
            origin: wgpu::Origin3d::ZERO,
            aspect: wgpu::TextureAspect::All,
        },
        &flags_rgba,
        layout,
        extent,
    );
}

fn create_bind_group(
    device: &wgpu::Device,
    layout: &wgpu::BindGroupLayout,
    globals_buffer: &wgpu::Buffer,
    style_color_view: &wgpu::TextureView,
    style_flags_view: &wgpu::TextureView,
) -> wgpu::BindGroup {
    device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some("lbt_globals_styles_group"),
        layout,
        entries: &[
            wgpu::BindGroupEntry {
                binding: 0,
                resource: globals_buffer.as_entire_binding(),
            },
            wgpu::BindGroupEntry {
                binding: 1,
                resource: wgpu::BindingResource::TextureView(style_color_view),
            },
            wgpu::BindGroupEntry {
                binding: 2,
                resource: wgpu::BindingResource::TextureView(style_flags_view),
            },
        ],
    })
}

#[allow(clippy::too_many_arguments)]
fn create_edge_pipeline(
    device: &wgpu::Device,
    layout: &wgpu::PipelineLayout,
    shader: &wgpu::ShaderModule,
    edge_layout: &[Option<wgpu::VertexBufferLayout<'_>>],
    multisample: wgpu::MultisampleState,
    vs_entry: &str,
    fs_entry: &str,
    label: &str,
) -> wgpu::RenderPipeline {
    device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
        label: Some(label),
        layout: Some(layout),
        vertex: wgpu::VertexState {
            module: shader,
            entry_point: Some(vs_entry),
            compilation_options: Default::default(),
            buffers: edge_layout,
        },
        fragment: Some(wgpu::FragmentState {
            module: shader,
            entry_point: Some(fs_entry),
            compilation_options: Default::default(),
            targets: &[Some(wgpu::ColorTargetState {
                format: COLOR_FORMAT,
                blend: Some(wgpu::BlendState::ALPHA_BLENDING),
                write_mask: wgpu::ColorWrites::ALL,
            })],
        }),
        primitive: wgpu::PrimitiveState {
            topology: wgpu::PrimitiveTopology::LineList,
            cull_mode: None,
            ..Default::default()
        },
        depth_stencil: Some(wgpu::DepthStencilState {
            format: DEPTH_FORMAT,
            depth_write_enabled: Some(false),
            depth_compare: Some(wgpu::CompareFunction::LessEqual),
            stencil: Default::default(),
            bias: Default::default(),
        }),
        multisample,
        multiview_mask: None,
        cache: None,
    })
}

fn create_translucent_pipeline(
    device: &wgpu::Device,
    layout: &wgpu::PipelineLayout,
    shader: &wgpu::ShaderModule,
    mesh_layout: &[Option<wgpu::VertexBufferLayout<'_>>],
    multisample: wgpu::MultisampleState,
    cull_mode: Option<wgpu::Face>,
    label: &str,
) -> wgpu::RenderPipeline {
    device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
        label: Some(label),
        layout: Some(layout),
        vertex: wgpu::VertexState {
            module: shader,
            entry_point: Some("vs_translucent"),
            compilation_options: Default::default(),
            buffers: mesh_layout,
        },
        fragment: Some(wgpu::FragmentState {
            module: shader,
            entry_point: Some("fs_translucent"),
            compilation_options: Default::default(),
            targets: &[Some(wgpu::ColorTargetState {
                format: COLOR_FORMAT,
                blend: Some(wgpu::BlendState::ALPHA_BLENDING),
                write_mask: wgpu::ColorWrites::ALL,
            })],
        }),
        primitive: wgpu::PrimitiveState {
            topology: wgpu::PrimitiveTopology::TriangleList,
            cull_mode,
            ..Default::default()
        },
        depth_stencil: Some(wgpu::DepthStencilState {
            format: DEPTH_FORMAT,
            depth_write_enabled: Some(false),
            depth_compare: Some(wgpu::CompareFunction::LessEqual),
            stencil: Default::default(),
            bias: GLAZING_DEPTH_BIAS,
        }),
        multisample,
        multiview_mask: None,
        cache: None,
    })
}
