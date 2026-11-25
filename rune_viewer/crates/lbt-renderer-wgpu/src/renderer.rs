//! Offscreen wgpu 3D architectural building renderer and picking pipeline.

use std::collections::HashSet;
use std::mem::{offset_of, size_of};
use std::sync::mpsc;

use bytemuck::{Pod, Zeroable};
use lbt_scene::{
    Bounds3, ColorBy, EdgeVertex, IsolationMode, MeshVertex, ObjectKind, ObjectRecord, SceneData,
    SectionAxis, SectionSpec,
};
use wgpu::util::DeviceExt;

use crate::camera::OrbitCamera;
use crate::error::RendererError;
use crate::palette::{resolve_scene_colors, srgb_to_linear};

const COLOR_FORMAT: wgpu::TextureFormat = wgpu::TextureFormat::Rgba8UnormSrgb;
const DEPTH_FORMAT: wgpu::TextureFormat = wgpu::TextureFormat::Depth32Float;
const PICK_FORMAT: wgpu::TextureFormat = wgpu::TextureFormat::R32Uint;

const FLAG_SELECTED: u32 = 1 << 0;
const FLAG_HIGHLIGHTED: u32 = 1 << 1;
const FLAG_ERROR: u32 = 1 << 2;
const FLAG_WARNING: u32 = 1 << 3;
const FLAG_GHOST: u32 = 1 << 4;
const FLAG_HIDDEN: u32 = 1 << 5;
const FLAG_TRANSLUCENT: u32 = 1 << 6;

/// Successful GPU pick result returned by [`BuildingRenderer::pick_at`].
#[derive(Copy, Clone, Debug, PartialEq)]
pub struct PickHit {
    /// Non-zero [`ObjectRecord::object_id`] under the picked pixel.
    pub object_id: u32,
    /// Exact world-space XYZ intersection point reconstructed from the pick depth sample.
    pub world_point: [f32; 3],
}

/// Interactive visual styling, isolation, validation, and section-cut state.
#[derive(Clone, Debug, PartialEq)]
pub struct RenderState {
    pub color_by: ColorBy,
    pub selected_ids: Vec<u32>,
    pub highlighted_ids: Vec<u32>,
    pub isolation_mode: IsolationMode,
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
struct GlobalsUniform {
    view_proj: [[f32; 4]; 4],
    camera_pos: [f32; 4],
    camera_forward: [f32; 4],
    section_plane: [f32; 4],
    bg_bottom: [f32; 4],
    bg_top: [f32; 4],
    accent_selected: [f32; 4],
    accent_highlight: [f32; 4],
    flags: [u32; 4],
}

#[repr(C)]
#[derive(Copy, Clone, Debug, Pod, Zeroable)]
struct GpuObjectStyle {
    color: [f32; 4],
    flags: u32,
    _pad: [u32; 3],
}

const _: () = {
    assert!(size_of::<GlobalsUniform>() == 192);
    assert!(size_of::<GpuObjectStyle>() == 32);
    assert!(size_of::<MeshVertex>() == 32);
    assert!(size_of::<EdgeVertex>() == 16);
};

struct RenderTargets {
    width: u32,
    height: u32,
    color_msaa_view: Option<wgpu::TextureView>,
    color_resolve_tex: wgpu::Texture,
    color_resolve_view: wgpu::TextureView,
    depth_view: wgpu::TextureView,
    pick_id_tex: wgpu::Texture,
    pick_id_view: wgpu::TextureView,
    pick_depth_tex: wgpu::Texture,
    pick_depth_view: wgpu::TextureView,
    pick_z_view: wgpu::TextureView,
    rgba_readback_buf: wgpu::Buffer,
    rgba_padded_row_bytes: u32,
    pick_readback_buf: wgpu::Buffer,
}

/// Standalone offscreen `wgpu` 3D architectural building renderer.
///
/// Renders Honeybee [`SceneData`] to RGBA8 pixel buffers, encoded PNG bytes, and `R32Uint`
/// picking targets without requiring a window or swapchain surface.
pub struct BuildingRenderer {
    device: wgpu::Device,
    queue: wgpu::Queue,
    adapter_info: wgpu::AdapterInfo,
    sample_count: u32,

    globals_buffer: wgpu::Buffer,
    styles_buffer: wgpu::Buffer,
    styles_capacity: usize,
    bind_group_layout: wgpu::BindGroupLayout,
    bind_group: wgpu::BindGroup,

    bg_pipeline: wgpu::RenderPipeline,
    opaque_pipeline: wgpu::RenderPipeline,
    edge_pipeline: wgpu::RenderPipeline,
    translucent_back_pipeline: wgpu::RenderPipeline,
    translucent_front_pipeline: wgpu::RenderPipeline,
    pick_pipeline: wgpu::RenderPipeline,

    vertex_buffer: Option<wgpu::Buffer>,
    index_buffer: Option<wgpu::Buffer>,
    index_count: u32,
    edge_buffer: Option<wgpu::Buffer>,
    edge_vertex_count: u32,

    scene_meta: SceneData,
    max_object_id: u32,
    state: RenderState,
    camera: OrbitCamera,
    targets: Option<RenderTargets>,
    png_rgba_scratch: Vec<u8>,
}

impl BuildingRenderer {
    /// Initialize a headless `wgpu` device preferring hardware D3D12/Vulkan/Metal with automatic
    /// WARP/software adapter fallback.
    pub fn new() -> Result<Self, RendererError> {
        let force_software = std::env::var("LBT_RENDERER_SOFTWARE")
            .map(|v| matches!(v.trim(), "1" | "true" | "TRUE" | "yes"))
            .unwrap_or(false);
        Self::new_internal(force_software)
    }

    /// Initialize a headless `wgpu` device forcing the WARP / software fallback adapter.
    pub fn new_software() -> Result<Self, RendererError> {
        Self::new_internal(true)
    }

    fn new_internal(force_software: bool) -> Result<Self, RendererError> {
        let (adapter, device, queue) = create_adapter_and_device(force_software)?;
        let adapter_info = adapter.get_info();
        let sample_count = choose_msaa_sample_count(&adapter);

        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("lbt_building_shader"),
            source: wgpu::ShaderSource::Wgsl(include_str!("shader.wgsl").into()),
        });

        let bind_group_layout =
            device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
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
                        ty: wgpu::BindingType::Buffer {
                            ty: wgpu::BufferBindingType::Storage { read_only: true },
                            has_dynamic_offset: false,
                            min_binding_size: None,
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

        let initial_styles = vec![GpuObjectStyle {
            color: [0.5, 0.5, 0.5, 1.0],
            flags: 0,
            _pad: [0; 3],
        }];
        let styles_capacity = 64usize;
        let styles_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("lbt_object_styles"),
            size: (styles_capacity * size_of::<GpuObjectStyle>()) as u64,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        queue.write_buffer(&styles_buffer, 0, bytemuck::cast_slice(&initial_styles));

        let bind_group = create_bind_group(&device, &bind_group_layout, &globals_buffer, &styles_buffer);

        let mesh_layout = [Some(wgpu::VertexBufferLayout {
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
        })];

        let edge_layout = [Some(wgpu::VertexBufferLayout {
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
        })];

        let color_multisample = wgpu::MultisampleState {
            count: sample_count,
            mask: !0,
            alpha_to_coverage_enabled: false,
        };

        let bg_pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("lbt_bg_pipeline"),
            layout: Some(&pipeline_layout),
            vertex: wgpu::VertexState {
                module: &shader,
                entry_point: Some("vs_bg"),
                compilation_options: Default::default(),
                buffers: &[],
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader,
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
                module: &shader,
                entry_point: Some("vs_opaque"),
                compilation_options: Default::default(),
                buffers: &mesh_layout,
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader,
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
                bias: Default::default(),
            }),
            multisample: color_multisample,
            multiview_mask: None,
            cache: None,
        });

        let edge_pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("lbt_edge_pipeline"),
            layout: Some(&pipeline_layout),
            vertex: wgpu::VertexState {
                module: &shader,
                entry_point: Some("vs_edge"),
                compilation_options: Default::default(),
                buffers: &edge_layout,
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader,
                entry_point: Some("fs_edge"),
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
            multisample: color_multisample,
            multiview_mask: None,
            cache: None,
        });

        let translucent_back_pipeline = create_translucent_pipeline(
            &device,
            &pipeline_layout,
            &shader,
            &mesh_layout,
            color_multisample,
            Some(wgpu::Face::Front),
            "lbt_translucent_back_pipeline",
        );
        let translucent_front_pipeline = create_translucent_pipeline(
            &device,
            &pipeline_layout,
            &shader,
            &mesh_layout,
            color_multisample,
            Some(wgpu::Face::Back),
            "lbt_translucent_front_pipeline",
        );

        let pick_pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("lbt_pick_pipeline"),
            layout: Some(&pipeline_layout),
            vertex: wgpu::VertexState {
                module: &shader,
                entry_point: Some("vs_pick"),
                compilation_options: Default::default(),
                buffers: &mesh_layout,
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader,
                entry_point: Some("fs_pick"),
                compilation_options: Default::default(),
                targets: &[
                    Some(wgpu::ColorTargetState {
                        format: PICK_FORMAT,
                        blend: None,
                        write_mask: wgpu::ColorWrites::ALL,
                    }),
                    Some(wgpu::ColorTargetState {
                        format: PICK_FORMAT,
                        blend: None,
                        write_mask: wgpu::ColorWrites::ALL,
                    }),
                ],
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
                bias: Default::default(),
            }),
            multisample: wgpu::MultisampleState::default(),
            multiview_mask: None,
            cache: None,
        });

        Ok(Self {
            device,
            queue,
            adapter_info,
            sample_count,
            globals_buffer,
            styles_buffer,
            styles_capacity,
            bind_group_layout,
            bind_group,
            bg_pipeline,
            opaque_pipeline,
            edge_pipeline,
            translucent_back_pipeline,
            translucent_front_pipeline,
            pick_pipeline,
            vertex_buffer: None,
            index_buffer: None,
            index_count: 0,
            edge_buffer: None,
            edge_vertex_count: 0,
            scene_meta: SceneData::default(),
            max_object_id: 0,
            state: RenderState::default(),
            camera: OrbitCamera::new(),
            targets: None,
            png_rgba_scratch: Vec::new(),
        })
    }

    /// Return metadata about the selected GPU or WARP/software adapter.
    pub fn adapter_info(&self) -> &wgpu::AdapterInfo {
        &self.adapter_info
    }

    /// Active MSAA sample count (`4` or `1`).
    pub const fn sample_count(&self) -> u32 {
        self.sample_count
    }

    /// Upload a tessellated [`SceneData`] to GPU buffers and refresh per-object styles.
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

        // Keep lightweight metadata for styling, room propagation, and story section cuts.
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
        self.max_object_id = scene
            .objects
            .iter()
            .map(|o| o.object_id)
            .max()
            .unwrap_or(0);

        self.upload_styles();
    }

    /// Update coloring, selection, highlight, isolation, validation, and section cut state.
    pub fn set_render_state(&mut self, state: &RenderState) {
        self.state = state.clone();
        self.upload_styles();
    }

    /// Read-only access to the active [`OrbitCamera`].
    pub const fn camera(&self) -> &OrbitCamera {
        &self.camera
    }

    /// Mutable access to the active [`OrbitCamera`].
    pub fn camera_mut(&mut self) -> &mut OrbitCamera {
        &mut self.camera
    }

    /// Render the scene into `out_rgba` (`width * height * 4` sRGB RGBA8 bytes), reusing `out_rgba`'s capacity.
    pub fn render_rgba(
        &mut self,
        width: u32,
        height: u32,
        out_rgba: &mut Vec<u8>,
    ) -> Result<(), RendererError> {
        self.ensure_targets(width, height)?;
        self.write_globals(width, height);

        let targets = self.targets.as_ref().expect("targets ensured");
        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("lbt_render_rgba_encoder"),
            });

        {
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
            // Pass 0: studio gradient background
            pass.set_pipeline(&self.bg_pipeline);
            pass.draw(0..3, 0..1);

            if let (Some(vb), Some(ib)) = (&self.vertex_buffer, &self.index_buffer)
                && self.index_count > 0
            {
                // Pass 1: Opaque solid architectural surfaces
                pass.set_pipeline(&self.opaque_pipeline);
                pass.set_vertex_buffer(0, vb.slice(..));
                pass.set_index_buffer(ib.slice(..), wgpu::IndexFormat::Uint32);
                pass.draw_indexed(0..self.index_count, 0, 0..1);
            }

            if self.state.show_edges
                && let Some(eb) = &self.edge_buffer
                && self.edge_vertex_count > 0
            {
                // Pass 2: Architectural crease & boundary edges
                pass.set_pipeline(&self.edge_pipeline);
                pass.set_vertex_buffer(0, eb.slice(..));
                pass.draw(0..self.edge_vertex_count, 0..1);
            }

            if let (Some(vb), Some(ib)) = (&self.vertex_buffer, &self.index_buffer)
                && self.index_count > 0
            {
                // Pass 3: Translucent glass apertures & ghost context (back-faces then front-faces)
                pass.set_vertex_buffer(0, vb.slice(..));
                pass.set_index_buffer(ib.slice(..), wgpu::IndexFormat::Uint32);
                pass.set_pipeline(&self.translucent_back_pipeline);
                pass.draw_indexed(0..self.index_count, 0, 0..1);
                pass.set_pipeline(&self.translucent_front_pipeline);
                pass.draw_indexed(0..self.index_count, 0, 0..1);
            }
        }

        encoder.copy_texture_to_buffer(
            wgpu::TexelCopyTextureInfo {
                texture: &targets.color_resolve_tex,
                mip_level: 0,
                origin: wgpu::Origin3d::ZERO,
                aspect: wgpu::TextureAspect::All,
            },
            wgpu::TexelCopyBufferInfo {
                buffer: &targets.rgba_readback_buf,
                layout: wgpu::TexelCopyBufferLayout {
                    offset: 0,
                    bytes_per_row: Some(targets.rgba_padded_row_bytes),
                    rows_per_image: Some(height),
                },
            },
            wgpu::Extent3d {
                width,
                height,
                depth_or_array_layers: 1,
            },
        );

        self.queue.submit([encoder.finish()]);
        map_and_read_rgba(
            &self.device,
            &targets.rgba_readback_buf,
            width,
            height,
            targets.rgba_padded_row_bytes,
            out_rgba,
        )
    }

    /// Render the scene and return an encoded PNG byte buffer.
    pub fn render_png(&mut self, width: u32, height: u32) -> Result<Vec<u8>, RendererError> {
        let mut scratch = std::mem::take(&mut self.png_rgba_scratch);
        let res = self.render_rgba(width, height, &mut scratch);
        if let Err(err) = res {
            self.png_rgba_scratch = scratch;
            return Err(err);
        }

        let mut png_bytes = Vec::with_capacity((width as usize * height as usize).max(1024));
        let encode_res = (|| {
            let mut encoder = png::Encoder::new(&mut png_bytes, width, height);
            encoder.set_color(png::ColorType::Rgba);
            encoder.set_depth(png::BitDepth::Eight);
            let mut writer = encoder
                .write_header()
                .map_err(|e| RendererError::PngEncode(e.to_string()))?;
            writer
                .write_image_data(&scratch)
                .map_err(|e| RendererError::PngEncode(e.to_string()))?;
            Ok(())
        })();
        self.png_rgba_scratch = scratch;
        encode_res?;
        Ok(png_bytes)
    }

    /// Execute the offscreen `R32Uint` pick pass and read back the object ID and world point at `(px, py)`.
    pub fn pick_at(
        &mut self,
        px: f32,
        py: f32,
        width: u32,
        height: u32,
    ) -> Result<Option<PickHit>, RendererError> {
        if width == 0 || height == 0 {
            return Err(RendererError::InvalidDimensions { width, height });
        }
        if !px.is_finite()
            || !py.is_finite()
            || px < 0.0
            || py < 0.0
            || px >= width as f32
            || py >= height as f32
        {
            return Ok(None);
        }
        if self.index_count == 0 || self.vertex_buffer.is_none() || self.index_buffer.is_none() {
            return Ok(None);
        }

        self.ensure_targets(width, height)?;
        self.write_globals(width, height);

        let ix = (px.floor() as u32).min(width - 1);
        let iy = (py.floor() as u32).min(height - 1);
        let row_align = wgpu::COPY_BYTES_PER_ROW_ALIGNMENT as u64;

        let targets = self.targets.as_ref().expect("targets ensured");
        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("lbt_pick_encoder"),
            });

        {
            let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("lbt_pick_pass"),
                color_attachments: &[
                    Some(wgpu::RenderPassColorAttachment {
                        view: &targets.pick_id_view,
                        depth_slice: None,
                        resolve_target: None,
                        ops: wgpu::Operations {
                            load: wgpu::LoadOp::Clear(wgpu::Color::TRANSPARENT),
                            store: wgpu::StoreOp::Store,
                        },
                    }),
                    Some(wgpu::RenderPassColorAttachment {
                        view: &targets.pick_depth_view,
                        depth_slice: None,
                        resolve_target: None,
                        ops: wgpu::Operations {
                            load: wgpu::LoadOp::Clear(wgpu::Color {
                                r: f64::from(1.0_f32.to_bits()),
                                g: 0.0,
                                b: 0.0,
                                a: 0.0,
                            }),
                            store: wgpu::StoreOp::Store,
                        },
                    }),
                ],
                depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment {
                    view: &targets.pick_z_view,
                    depth_ops: Some(wgpu::Operations {
                        load: wgpu::LoadOp::Clear(1.0),
                        store: wgpu::StoreOp::Discard,
                    }),
                    stencil_ops: None,
                }),
                ..Default::default()
            });

            if let (Some(vb), Some(ib)) = (&self.vertex_buffer, &self.index_buffer) {
                pass.set_bind_group(0, &self.bind_group, &[]);
                pass.set_pipeline(&self.pick_pipeline);
                pass.set_vertex_buffer(0, vb.slice(..));
                pass.set_index_buffer(ib.slice(..), wgpu::IndexFormat::Uint32);
                pass.draw_indexed(0..self.index_count, 0, 0..1);
            }
        }

        let origin = wgpu::Origin3d { x: ix, y: iy, z: 0 };
        let one_px = wgpu::Extent3d {
            width: 1,
            height: 1,
            depth_or_array_layers: 1,
        };
        encoder.copy_texture_to_buffer(
            wgpu::TexelCopyTextureInfo {
                texture: &targets.pick_id_tex,
                mip_level: 0,
                origin,
                aspect: wgpu::TextureAspect::All,
            },
            wgpu::TexelCopyBufferInfo {
                buffer: &targets.pick_readback_buf,
                layout: wgpu::TexelCopyBufferLayout {
                    offset: 0,
                    bytes_per_row: Some(wgpu::COPY_BYTES_PER_ROW_ALIGNMENT),
                    rows_per_image: Some(1),
                },
            },
            one_px,
        );
        encoder.copy_texture_to_buffer(
            wgpu::TexelCopyTextureInfo {
                texture: &targets.pick_depth_tex,
                mip_level: 0,
                origin,
                aspect: wgpu::TextureAspect::All,
            },
            wgpu::TexelCopyBufferInfo {
                buffer: &targets.pick_readback_buf,
                layout: wgpu::TexelCopyBufferLayout {
                    offset: row_align,
                    bytes_per_row: Some(wgpu::COPY_BYTES_PER_ROW_ALIGNMENT),
                    rows_per_image: Some(1),
                },
            },
            one_px,
        );

        self.queue.submit([encoder.finish()]);

        let (object_id, depth_bits) =
            map_and_read_pick(&self.device, &targets.pick_readback_buf, row_align)?;
        if object_id == 0 {
            return Ok(None);
        }

        let depth = f32::from_bits(depth_bits);
        let sample_x = ix as f32 + 0.5;
        let sample_y = iy as f32 + 0.5;
        let world_point = self
            .camera
            .unproject_depth(sample_x, sample_y, depth, width, height)
            .unwrap_or_else(|| {
                let (ray_o, ray_d) = self.camera.screen_ray(sample_x, sample_y, width, height);
                [
                    ray_o[0] + ray_d[0] * self.camera.distance,
                    ray_o[1] + ray_d[1] * self.camera.distance,
                    ray_o[2] + ray_d[2] * self.camera.distance,
                ]
            });

        Ok(Some(PickHit {
            object_id,
            world_point,
        }))
    }

    fn upload_styles(&mut self) {
        let len = (self.max_object_id as usize) + 1;
        let mut styles = vec![
            GpuObjectStyle {
                color: [0.5, 0.5, 0.5, 1.0],
                flags: 0,
                _pad: [0; 3],
            };
            len
        ];

        let base_srgb = resolve_scene_colors(&self.scene_meta, self.state.color_by);
        let selected_set = expand_room_descendants(&self.scene_meta.objects, &self.state.selected_ids);
        let highlighted_set =
            expand_room_descendants(&self.scene_meta.objects, &self.state.highlighted_ids);
        let error_set =
            expand_room_descendants(&self.scene_meta.objects, &self.state.validation_error_ids);
        let warning_set =
            expand_room_descendants(&self.scene_meta.objects, &self.state.validation_warning_ids);

        let isolation_active = !highlighted_set.is_empty()
            && matches!(
                self.state.isolation_mode,
                IsolationMode::GhostContext | IsolationMode::Isolate
            );

        for record in &self.scene_meta.objects {
            let id = record.object_id as usize;
            if id >= styles.len() {
                continue;
            }
            let srgb = base_srgb.get(id).copied().unwrap_or([0.6, 0.6, 0.6, 1.0]);
            let linear = srgb_to_linear(srgb);

            let mut flags = 0u32;
            let is_selected = selected_set.contains(&record.object_id);
            let is_highlighted = highlighted_set.contains(&record.object_id);
            let is_error = error_set.contains(&record.object_id);
            let is_warning = warning_set.contains(&record.object_id);

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

            if isolation_active && !is_highlighted {
                match self.state.isolation_mode {
                    IsolationMode::GhostContext => {
                        flags |= FLAG_GHOST | FLAG_TRANSLUCENT;
                    }
                    IsolationMode::Isolate => {
                        flags |= FLAG_HIDDEN;
                    }
                    IsolationMode::Highlight => {}
                }
            } else if record.kind == ObjectKind::Aperture || linear[3] < 0.99 {
                flags |= FLAG_TRANSLUCENT;
            }

            styles[id] = GpuObjectStyle {
                color: linear,
                flags,
                _pad: [0; 3],
            };
        }

        if len > self.styles_capacity {
            self.styles_capacity = len.next_power_of_two().max(64);
            self.styles_buffer = self.device.create_buffer(&wgpu::BufferDescriptor {
                label: Some("lbt_object_styles"),
                size: (self.styles_capacity * size_of::<GpuObjectStyle>()) as u64,
                usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST,
                mapped_at_creation: false,
            });
            self.bind_group = create_bind_group(
                &self.device,
                &self.bind_group_layout,
                &self.globals_buffer,
                &self.styles_buffer,
            );
        }

        self.queue
            .write_buffer(&self.styles_buffer, 0, bytemuck::cast_slice(&styles));
    }

    fn write_globals(&self, width: u32, height: u32) {
        let aspect = width.max(1) as f32 / height.max(1) as f32;
        let view_proj = self.camera.view_projection_matrix(aspect).to_cols_array_2d();
        let eye = self.camera.eye_position();
        let fwd = self.camera.forward();
        let is_ortho = self.camera.is_orthographic();
        let (section_enabled, section_plane) = self.resolve_section_plane();

        let (bg_bottom, bg_top) = if self.state.dark_mode {
            (
                srgb_to_linear([0.068, 0.086, 0.120, 1.0]),
                srgb_to_linear([0.115, 0.145, 0.200, 1.0]),
            )
        } else {
            (
                srgb_to_linear([0.890, 0.918, 0.952, 1.0]),
                srgb_to_linear([0.968, 0.978, 0.992, 1.0]),
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

    fn resolve_section_plane(&self) -> (bool, [f32; 4]) {
        let Some(sec) = &self.state.section else {
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
            story_section_value(&self.scene_meta, story, axis_idx).unwrap_or_else(|| {
                default_axis_midpoint(&self.scene_meta.bounds, axis_idx)
            })
        } else {
            default_axis_midpoint(&self.scene_meta.bounds, axis_idx)
        };

        let sign = if sec.invert { -1.0 } else { 1.0 };
        let mut normal = [0.0_f32; 3];
        normal[axis_idx] = sign;
        (true, [normal[0], normal[1], normal[2], sign * cut_val])
    }

    fn ensure_targets(&mut self, width: u32, height: u32) -> Result<(), RendererError> {
        let max_dim = self.device.limits().max_texture_dimension_2d;
        if width == 0 || height == 0 || width > max_dim || height > max_dim {
            return Err(RendererError::InvalidDimensions { width, height });
        }
        if let Some(existing) = &self.targets
            && existing.width == width
            && existing.height == height
        {
            return Ok(());
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
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::COPY_SRC,
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

        let pick_id_tex = self.device.create_texture(&wgpu::TextureDescriptor {
            label: Some("lbt_pick_id"),
            size,
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: PICK_FORMAT,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::COPY_SRC,
            view_formats: &[],
        });
        let pick_id_view = pick_id_tex.create_view(&Default::default());

        let pick_depth_tex = self.device.create_texture(&wgpu::TextureDescriptor {
            label: Some("lbt_pick_depth_bits"),
            size,
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: PICK_FORMAT,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::COPY_SRC,
            view_formats: &[],
        });
        let pick_depth_view = pick_depth_tex.create_view(&Default::default());

        let pick_z_tex = self.device.create_texture(&wgpu::TextureDescriptor {
            label: Some("lbt_pick_z"),
            size,
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: DEPTH_FORMAT,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
            view_formats: &[],
        });
        let pick_z_view = pick_z_tex.create_view(&Default::default());

        let rgba_padded_row_bytes = align_bytes_per_row(width * 4);
        let rgba_readback_buf = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("lbt_rgba_readback"),
            size: u64::from(rgba_padded_row_bytes) * u64::from(height),
            usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
            mapped_at_creation: false,
        });

        let pick_readback_buf = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("lbt_pick_readback"),
            size: u64::from(wgpu::COPY_BYTES_PER_ROW_ALIGNMENT) * 2,
            usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
            mapped_at_creation: false,
        });

        self.targets = Some(RenderTargets {
            width,
            height,
            color_msaa_view,
            color_resolve_tex,
            color_resolve_view,
            depth_view,
            pick_id_tex,
            pick_id_view,
            pick_depth_tex,
            pick_depth_view,
            pick_z_view,
            rgba_readback_buf,
            rgba_padded_row_bytes,
            pick_readback_buf,
        });
        Ok(())
    }
}

/// Align `unaligned` row byte count up to `wgpu::COPY_BYTES_PER_ROW_ALIGNMENT` (256 bytes).
const fn align_bytes_per_row(unaligned: u32) -> u32 {
    let align = wgpu::COPY_BYTES_PER_ROW_ALIGNMENT;
    unaligned.div_ceil(align) * align
}

fn create_bind_group(
    device: &wgpu::Device,
    layout: &wgpu::BindGroupLayout,
    globals_buffer: &wgpu::Buffer,
    styles_buffer: &wgpu::Buffer,
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
                resource: styles_buffer.as_entire_binding(),
            },
        ],
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
            bias: Default::default(),
        }),
        multisample,
        multiview_mask: None,
        cache: None,
    })
}

fn choose_msaa_sample_count(adapter: &wgpu::Adapter) -> u32 {
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

fn backend_rank(backend: wgpu::Backend) -> u8 {
    if cfg!(target_os = "windows") {
        match backend {
            wgpu::Backend::Dx12 => 0,
            wgpu::Backend::Vulkan => 1,
            _ => 2,
        }
    } else if cfg!(target_vendor = "apple") {
        match backend {
            wgpu::Backend::Metal => 0,
            _ => 1,
        }
    } else {
        match backend {
            wgpu::Backend::Vulkan => 0,
            _ => 1,
        }
    }
}

fn device_type_rank(ty: wgpu::DeviceType) -> u8 {
    match ty {
        wgpu::DeviceType::DiscreteGpu => 0,
        wgpu::DeviceType::IntegratedGpu => 1,
        wgpu::DeviceType::VirtualGpu => 2,
        wgpu::DeviceType::Other => 3,
        wgpu::DeviceType::Cpu => 4,
    }
}

fn preferred_backends() -> wgpu::Backends {
    if cfg!(target_os = "windows") {
        wgpu::Backends::DX12
    } else if cfg!(target_vendor = "apple") {
        wgpu::Backends::METAL
    } else {
        wgpu::Backends::VULKAN
    }
}

fn device_descriptor_for(
    adapter: &wgpu::Adapter,
    label: &'static str,
) -> wgpu::DeviceDescriptor<'static> {
    let adapter_limits = adapter.limits();
    let max_non_sampler = 65_536_u32.min(adapter_limits.max_non_sampler_bindings);
    let required_limits = wgpu::Limits {
        max_non_sampler_bindings: max_non_sampler,
        ..wgpu::Limits::downlevel_defaults()
            .using_resolution(adapter_limits.clone())
            .using_alignment(adapter_limits)
    };
    wgpu::DeviceDescriptor {
        label: Some(label),
        required_features: wgpu::Features::empty(),
        required_limits,
        experimental_features: Default::default(),
        memory_hints: wgpu::MemoryHints::MemoryUsage,
        trace: Default::default(),
    }
}

fn make_instance(backends: wgpu::Backends, allow_validation: bool) -> wgpu::Instance {
    let mut instance_desc = wgpu::InstanceDescriptor::new_without_display_handle();
    instance_desc.backends = backends;
    // Match Rune's stability configuration: use Windows inbox FXC to avoid dxcompiler.dll
    // conflicts and skip indirect-call validation shaders that can fault on WARP.
    instance_desc
        .flags
        .remove(wgpu::InstanceFlags::VALIDATION_INDIRECT_CALL);
    if !allow_validation {
        instance_desc
            .flags
            .remove(wgpu::InstanceFlags::VALIDATION);
    }
    instance_desc.backend_options.dx12.shader_compiler = wgpu::Dx12Compiler::Fxc;
    wgpu::Instance::new(instance_desc)
}

fn create_adapter_and_device(
    force_software: bool,
) -> Result<(wgpu::Adapter, wgpu::Device, wgpu::Queue), RendererError> {
    let backends = preferred_backends();
    let mut last_error = String::new();

    if !force_software {
        let instance = make_instance(backends, true);
        let mut candidates = pollster::block_on(instance.enumerate_adapters(backends));
        if candidates.is_empty() {
            candidates = pollster::block_on(instance.enumerate_adapters(wgpu::Backends::all()));
        }
        candidates.sort_by_key(|adapter| {
            let info = adapter.get_info();
            let is_cpu = info.device_type == wgpu::DeviceType::Cpu;
            (
                is_cpu,
                backend_rank(info.backend),
                device_type_rank(info.device_type),
            )
        });

        for adapter in candidates {
            let desc = device_descriptor_for(&adapter, "lbt_renderer_device");
            match pollster::block_on(adapter.request_device(&desc)) {
                Ok((device, queue)) => return Ok((adapter, device, queue)),
                Err(err) => {
                    last_error = format!("{} ({err})", adapter.get_info().name);
                }
            }
        }
    }

    // Automatic WARP / software fallback adapter (without D3D12 debug layers that fault in WARP).
    let fallback_instance = make_instance(backends, false);
    let fallback_adapter = pollster::block_on(fallback_instance.request_adapter(
        &wgpu::RequestAdapterOptions {
            power_preference: wgpu::PowerPreference::LowPower,
            force_fallback_adapter: true,
            compatible_surface: None,
            apply_limit_buckets: false,
        },
    ))
    .map_err(|err| {
        if last_error.is_empty() {
            RendererError::NoAdapter(err.to_string())
        } else {
            RendererError::NoAdapter(format!("{err}; previous attempt: {last_error}"))
        }
    })?;

    let desc = device_descriptor_for(&fallback_adapter, "lbt_renderer_software_device");
    let (device, queue) = pollster::block_on(fallback_adapter.request_device(&desc))
        .map_err(|err| RendererError::DeviceRequest(err.to_string()))?;

    Ok((fallback_adapter, device, queue))
}

fn map_and_read_rgba(
    device: &wgpu::Device,
    buffer: &wgpu::Buffer,
    width: u32,
    height: u32,
    padded_row_bytes: u32,
    out_rgba: &mut Vec<u8>,
) -> Result<(), RendererError> {
    let slice = buffer.slice(..);
    let (tx, rx) = mpsc::channel();
    slice.map_async(wgpu::MapMode::Read, move |res| {
        let _ = tx.send(res);
    });
    device
        .poll(wgpu::PollType::wait_indefinitely())
        .map_err(|e| RendererError::Poll(e.to_string()))?;
    rx.recv()
        .map_err(|e| RendererError::BufferMap(e.to_string()))?
        .map_err(|e| RendererError::BufferMap(e.to_string()))?;

    let unpadded_row_bytes = (width * 4) as usize;
    let total_bytes = unpadded_row_bytes * (height as usize);
    out_rgba.clear();
    if out_rgba.capacity() < total_bytes {
        out_rgba.reserve(total_bytes - out_rgba.capacity());
    }

    {
        let mapped = slice
            .get_mapped_range()
            .map_err(|e| RendererError::BufferMap(e.to_string()))?;
        let stride = padded_row_bytes as usize;
        if stride == unpadded_row_bytes {
            out_rgba.extend_from_slice(&mapped[..total_bytes]);
        } else {
            for row in 0..(height as usize) {
                let start = row * stride;
                out_rgba.extend_from_slice(&mapped[start..start + unpadded_row_bytes]);
            }
        }
    }
    buffer.unmap();
    Ok(())
}

fn map_and_read_pick(
    device: &wgpu::Device,
    buffer: &wgpu::Buffer,
    depth_offset: u64,
) -> Result<(u32, u32), RendererError> {
    let slice = buffer.slice(..);
    let (tx, rx) = mpsc::channel();
    slice.map_async(wgpu::MapMode::Read, move |res| {
        let _ = tx.send(res);
    });
    device
        .poll(wgpu::PollType::wait_indefinitely())
        .map_err(|e| RendererError::Poll(e.to_string()))?;
    rx.recv()
        .map_err(|e| RendererError::BufferMap(e.to_string()))?
        .map_err(|e| RendererError::BufferMap(e.to_string()))?;

    let (object_id, depth_bits) = {
        let mapped = slice
            .get_mapped_range()
            .map_err(|e| RendererError::BufferMap(e.to_string()))?;
        let id = u32::from_le_bytes([mapped[0], mapped[1], mapped[2], mapped[3]]);
        let d_off = depth_offset as usize;
        let depth = u32::from_le_bytes([
            mapped[d_off],
            mapped[d_off + 1],
            mapped[d_off + 2],
            mapped[d_off + 3],
        ]);
        (id, depth)
    };
    buffer.unmap();
    Ok((object_id, depth_bits))
}

fn expand_room_descendants(objects: &[ObjectRecord], ids: &[u32]) -> HashSet<u32> {
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

    let mut face_ids = HashSet::new();
    for record in objects {
        if record
            .parent_object_id
            .is_some_and(|pid| room_ids.contains(&pid))
        {
            expanded.insert(record.object_id);
            if record.kind == ObjectKind::Face {
                face_ids.insert(record.object_id);
            }
        }
    }
    if !face_ids.is_empty() {
        for record in objects {
            if record
                .parent_object_id
                .is_some_and(|pid| face_ids.contains(&pid))
            {
                expanded.insert(record.object_id);
            }
        }
    }
    expanded
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
        // Standard architectural floor-plan cut at ~1.2m above story floor.
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
