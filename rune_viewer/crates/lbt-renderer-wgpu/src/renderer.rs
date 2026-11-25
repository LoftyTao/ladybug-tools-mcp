//! Native offscreen `wgpu` 3D architectural building renderer, PNG export, and R32Uint picking.

use std::sync::mpsc;

use lbt_scene::SceneData;

use crate::camera::OrbitCamera;
use crate::core::{
    DEPTH_FORMAT, PickHit, RenderState, SceneGpuCore, choose_msaa_sample_count, mesh_vertex_layout,
};
use crate::error::RendererError;

const PICK_FORMAT: wgpu::TextureFormat = wgpu::TextureFormat::R32Uint;

struct ReadbackTargets {
    width: u32,
    height: u32,
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
    adapter_info: wgpu::AdapterInfo,
    core: SceneGpuCore,
    pick_pipeline: wgpu::RenderPipeline,
    pick_active_pipeline: wgpu::RenderPipeline,
    readback: Option<ReadbackTargets>,
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
        let core = SceneGpuCore::new(device, queue, sample_count);

        let pick_source = concat!(include_str!("shader.wgsl"), "\n", include_str!("pick_shader.wgsl"));
        let pick_shader = core
            .device
            .create_shader_module(wgpu::ShaderModuleDescriptor {
                label: Some("lbt_pick_shader"),
                source: wgpu::ShaderSource::Wgsl(pick_source.into()),
            });

        let mesh_layout = mesh_vertex_layout();
        let pick_pipeline = create_pick_pipeline(
            &core.device,
            &core.pipeline_layout,
            &pick_shader,
            &mesh_layout,
            "vs_pick",
            "fs_pick",
            "lbt_pick_pipeline",
        );
        let pick_active_pipeline = create_pick_pipeline(
            &core.device,
            &core.pipeline_layout,
            &pick_shader,
            &mesh_layout,
            "vs_pick_active",
            "fs_pick_active",
            "lbt_pick_active_pipeline",
        );

        Ok(Self {
            adapter_info,
            core,
            pick_pipeline,
            pick_active_pipeline,
            readback: None,
            png_rgba_scratch: Vec::new(),
        })
    }

    /// Return metadata about the selected GPU or WARP/software adapter.
    pub fn adapter_info(&self) -> &wgpu::AdapterInfo {
        &self.adapter_info
    }

    /// Active MSAA sample count (`4` or `1`).
    pub const fn sample_count(&self) -> u32 {
        self.core.sample_count
    }

    /// Upload a tessellated [`SceneData`] to GPU buffers and refresh per-object styles.
    pub fn set_scene(&mut self, scene: &SceneData) {
        self.core.set_scene(scene);
    }

    /// Update coloring, selection, highlight, isolation, Room Edit Mode, validation, and section cut state.
    pub fn set_render_state(&mut self, state: &RenderState) {
        self.core.set_render_state(state);
    }

    /// Read-only access to the active [`OrbitCamera`].
    pub const fn camera(&self) -> &OrbitCamera {
        &self.core.camera
    }

    /// Mutable access to the active [`OrbitCamera`].
    pub fn camera_mut(&mut self) -> &mut OrbitCamera {
        &mut self.core.camera
    }

    /// Render the scene into `out_rgba` (`width * height * 4` sRGB RGBA8 bytes), reusing `out_rgba`'s capacity.
    pub fn render_rgba(
        &mut self,
        width: u32,
        height: u32,
        out_rgba: &mut Vec<u8>,
    ) -> Result<(), RendererError> {
        self.ensure_targets(width, height)?;

        let mut encoder = self
            .core
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("lbt_render_rgba_encoder"),
            });

        self.core.encode_scene_pass(&mut encoder, width, height);

        let targets = self.core.targets.as_ref().expect("color targets ensured");
        let readback = self.readback.as_ref().expect("readback targets ensured");
        encoder.copy_texture_to_buffer(
            wgpu::TexelCopyTextureInfo {
                texture: &targets.color_resolve_tex,
                mip_level: 0,
                origin: wgpu::Origin3d::ZERO,
                aspect: wgpu::TextureAspect::All,
            },
            wgpu::TexelCopyBufferInfo {
                buffer: &readback.rgba_readback_buf,
                layout: wgpu::TexelCopyBufferLayout {
                    offset: 0,
                    bytes_per_row: Some(readback.rgba_padded_row_bytes),
                    rows_per_image: Some(height),
                },
            },
            wgpu::Extent3d {
                width,
                height,
                depth_or_array_layers: 1,
            },
        );

        self.core.queue.submit([encoder.finish()]);
        map_and_read_rgba(
            &self.core.device,
            &readback.rgba_readback_buf,
            width,
            height,
            readback.rgba_padded_row_bytes,
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
    ///
    /// Mirrors [`crate::pick_scene_ray`]: when [`RenderState::editing_room_id`] is active, picks
    /// active edited-room descendants ahead of ghosted outer context shells, falling back to
    /// ghosted context when clicking outside the edited room.
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
        if self.core.index_count == 0
            || self.core.vertex_buffer.is_none()
            || self.core.index_buffer.is_none()
        {
            return Ok(None);
        }

        self.ensure_targets(width, height)?;
        self.core.write_globals(width, height);

        let ix = (px.floor() as u32).min(width - 1);
        let iy = (py.floor() as u32).min(height - 1);

        let (object_id, depth_bits) = if self.core.active_editing_room_id().is_some() {
            let active_hit = self.run_pick_pass(&self.pick_active_pipeline, ix, iy)?;
            if active_hit.0 != 0 {
                active_hit
            } else {
                self.run_pick_pass(&self.pick_pipeline, ix, iy)?
            }
        } else {
            self.run_pick_pass(&self.pick_pipeline, ix, iy)?
        };

        if object_id == 0 {
            return Ok(None);
        }

        let depth = f32::from_bits(depth_bits);
        let sample_x = ix as f32 + 0.5;
        let sample_y = iy as f32 + 0.5;
        let world_point = self
            .core
            .camera
            .unproject_depth(sample_x, sample_y, depth, width, height)
            .unwrap_or_else(|| {
                let (ray_o, ray_d) = self.core.camera.screen_ray(sample_x, sample_y, width, height);
                [
                    ray_o[0] + ray_d[0] * self.core.camera.distance,
                    ray_o[1] + ray_d[1] * self.core.camera.distance,
                    ray_o[2] + ray_d[2] * self.core.camera.distance,
                ]
            });

        let (owner_room_id, is_ghosted) = self.core.object_pick_meta(object_id);
        Ok(Some(PickHit {
            object_id,
            owner_room_id,
            is_ghosted,
            world_point,
        }))
    }

    fn run_pick_pass(
        &self,
        pipeline: &wgpu::RenderPipeline,
        ix: u32,
        iy: u32,
    ) -> Result<(u32, u32), RendererError> {
        let row_align = wgpu::COPY_BYTES_PER_ROW_ALIGNMENT as u64;
        let readback = self.readback.as_ref().expect("readback targets ensured");
        let mut encoder = self
            .core
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("lbt_pick_encoder"),
            });

        {
            let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("lbt_pick_pass"),
                color_attachments: &[
                    Some(wgpu::RenderPassColorAttachment {
                        view: &readback.pick_id_view,
                        depth_slice: None,
                        resolve_target: None,
                        ops: wgpu::Operations {
                            load: wgpu::LoadOp::Clear(wgpu::Color::TRANSPARENT),
                            store: wgpu::StoreOp::Store,
                        },
                    }),
                    Some(wgpu::RenderPassColorAttachment {
                        view: &readback.pick_depth_view,
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
                    view: &readback.pick_z_view,
                    depth_ops: Some(wgpu::Operations {
                        load: wgpu::LoadOp::Clear(1.0),
                        store: wgpu::StoreOp::Discard,
                    }),
                    stencil_ops: None,
                }),
                ..Default::default()
            });

            if let (Some(vb), Some(ib)) = (&self.core.vertex_buffer, &self.core.index_buffer) {
                pass.set_bind_group(0, &self.core.bind_group, &[]);
                pass.set_pipeline(pipeline);
                pass.set_vertex_buffer(0, vb.slice(..));
                pass.set_index_buffer(ib.slice(..), wgpu::IndexFormat::Uint32);
                pass.draw_indexed(0..self.core.index_count, 0, 0..1);
            }
        }

        let origin = wgpu::Origin3d {
            x: ix,
            y: iy,
            z: 0,
        };
        let one_px = wgpu::Extent3d {
            width: 1,
            height: 1,
            depth_or_array_layers: 1,
        };
        encoder.copy_texture_to_buffer(
            wgpu::TexelCopyTextureInfo {
                texture: &readback.pick_id_tex,
                mip_level: 0,
                origin,
                aspect: wgpu::TextureAspect::All,
            },
            wgpu::TexelCopyBufferInfo {
                buffer: &readback.pick_readback_buf,
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
                texture: &readback.pick_depth_tex,
                mip_level: 0,
                origin,
                aspect: wgpu::TextureAspect::All,
            },
            wgpu::TexelCopyBufferInfo {
                buffer: &readback.pick_readback_buf,
                layout: wgpu::TexelCopyBufferLayout {
                    offset: row_align,
                    bytes_per_row: Some(wgpu::COPY_BYTES_PER_ROW_ALIGNMENT),
                    rows_per_image: Some(1),
                },
            },
            one_px,
        );

        self.core.queue.submit([encoder.finish()]);
        map_and_read_pick(&self.core.device, &readback.pick_readback_buf, row_align)
    }

    fn ensure_targets(&mut self, width: u32, height: u32) -> Result<(), RendererError> {
        self.core
            .ensure_color_targets(width, height, wgpu::TextureUsages::COPY_SRC)?;

        if let Some(existing) = &self.readback
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

        let pick_id_tex = self.core.device.create_texture(&wgpu::TextureDescriptor {
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

        let pick_depth_tex = self.core.device.create_texture(&wgpu::TextureDescriptor {
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

        let pick_z_tex = self.core.device.create_texture(&wgpu::TextureDescriptor {
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
        let rgba_readback_buf = self.core.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("lbt_rgba_readback"),
            size: u64::from(rgba_padded_row_bytes) * u64::from(height),
            usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
            mapped_at_creation: false,
        });

        let pick_readback_buf = self.core.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("lbt_pick_readback"),
            size: u64::from(wgpu::COPY_BYTES_PER_ROW_ALIGNMENT) * 2,
            usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
            mapped_at_creation: false,
        });

        self.readback = Some(ReadbackTargets {
            width,
            height,
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

fn create_pick_pipeline(
    device: &wgpu::Device,
    layout: &wgpu::PipelineLayout,
    shader: &wgpu::ShaderModule,
    mesh_layout: &[Option<wgpu::VertexBufferLayout<'_>>],
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
            buffers: mesh_layout,
        },
        fragment: Some(wgpu::FragmentState {
            module: shader,
            entry_point: Some(fs_entry),
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
    })
}

/// Align `unaligned` row byte count up to `wgpu::COPY_BYTES_PER_ROW_ALIGNMENT` (256 bytes).
const fn align_bytes_per_row(unaligned: u32) -> u32 {
    let align = wgpu::COPY_BYTES_PER_ROW_ALIGNMENT;
    unaligned.div_ceil(align) * align
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
