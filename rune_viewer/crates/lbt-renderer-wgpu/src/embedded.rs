//! Zero-readback embedded `wgpu` scene renderer for Rune `Compositor` (desktop & browser).

use std::collections::HashMap;
use std::mem::size_of;

use bytemuck::{Pod, Zeroable};
use lbt_scene::SceneData;

use crate::camera::OrbitCamera;
use crate::core::{RenderState, SceneGpuCore, choose_msaa_sample_count};
use crate::error::RendererError;

#[repr(C)]
#[derive(Copy, Clone, Debug, Pod, Zeroable)]
struct BlitUniform {
    rect_norm: [f32; 4],
    uv_rect: [f32; 4],
    flags: [u32; 4],
}

const _: () = {
    assert!(size_of::<BlitUniform>() == 48);
};

/// Embedded `wgpu` 3D scene renderer sharing Rune's `Device`/`Queue` without CPU pixel readback.
pub struct EmbeddedSceneRenderer {
    core: SceneGpuCore,
    blit_shader: wgpu::ShaderModule,
    blit_bind_group_layout: wgpu::BindGroupLayout,
    blit_pipeline_layout: wgpu::PipelineLayout,
    blit_uniform_buf: wgpu::Buffer,
    sampler: wgpu::Sampler,
    blit_pipelines: HashMap<wgpu::TextureFormat, wgpu::RenderPipeline>,
    scene_blit_bind_group: Option<wgpu::BindGroup>,
    last_scene_version: u64,
}

impl EmbeddedSceneRenderer {
    /// Construct an embedded renderer sharing the host compositor's `Device` and `Queue`.
    pub fn new(
        adapter: Option<&wgpu::Adapter>,
        device: wgpu::Device,
        queue: wgpu::Queue,
    ) -> Self {
        let sample_count = adapter.map(choose_msaa_sample_count).unwrap_or(1);
        let core = SceneGpuCore::new(device.clone(), queue, sample_count);

        let blit_shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("lbt_blit_shader"),
            source: wgpu::ShaderSource::Wgsl(include_str!("blit_shader.wgsl").into()),
        });

        let blit_bind_group_layout =
            device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
                label: Some("lbt_blit_bind_group_layout"),
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
                        visibility: wgpu::ShaderStages::FRAGMENT,
                        ty: wgpu::BindingType::Texture {
                            sample_type: wgpu::TextureSampleType::Float { filterable: true },
                            view_dimension: wgpu::TextureViewDimension::D2,
                            multisampled: false,
                        },
                        count: None,
                    },
                    wgpu::BindGroupLayoutEntry {
                        binding: 2,
                        visibility: wgpu::ShaderStages::FRAGMENT,
                        ty: wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Filtering),
                        count: None,
                    },
                ],
            });

        let blit_pipeline_layout =
            device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                label: Some("lbt_blit_pipeline_layout"),
                bind_group_layouts: &[Some(&blit_bind_group_layout)],
                immediate_size: 0,
            });

        let blit_uniform_buf = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("lbt_blit_uniform"),
            size: size_of::<BlitUniform>() as u64,
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });

        let sampler = device.create_sampler(&wgpu::SamplerDescriptor {
            label: Some("lbt_blit_sampler"),
            mag_filter: wgpu::FilterMode::Linear,
            min_filter: wgpu::FilterMode::Linear,
            mipmap_filter: wgpu::MipmapFilterMode::Nearest,
            address_mode_u: wgpu::AddressMode::ClampToEdge,
            address_mode_v: wgpu::AddressMode::ClampToEdge,
            ..Default::default()
        });

        Self {
            core,
            blit_shader,
            blit_bind_group_layout,
            blit_pipeline_layout,
            blit_uniform_buf,
            sampler,
            blit_pipelines: HashMap::new(),
            scene_blit_bind_group: None,
            last_scene_version: 0,
        }
    }

    /// Synchronize scene geometry (only when `scene_version` changes), render state, and camera.
    pub fn sync(
        &mut self,
        scene: &SceneData,
        scene_version: u64,
        state: &RenderState,
        camera: &OrbitCamera,
    ) {
        if self.last_scene_version != scene_version {
            self.core.set_scene(scene);
            self.last_scene_version = scene_version;
        }
        self.core.set_render_state(state);
        self.core.camera = camera.clone();
    }

    /// Ensure offscreen targets and record passes 0..3 before opening the UI render pass.
    pub fn prepare_viewport(
        &mut self,
        encoder: &mut wgpu::CommandEncoder,
        width: u32,
        height: u32,
        target_format: wgpu::TextureFormat,
    ) -> Result<(), RendererError> {
        let max_dim = self.core.device.limits().max_texture_dimension_2d.max(1);
        let w = width.clamp(1, max_dim);
        let h = height.clamp(1, max_dim);

        let resized = self.core.ensure_color_targets(
            w,
            h,
            wgpu::TextureUsages::TEXTURE_BINDING,
        )?;
        if resized || self.scene_blit_bind_group.is_none() {
            let resolve_view = &self
                .core
                .targets
                .as_ref()
                .expect("targets ensured")
                .color_resolve_view;
            self.scene_blit_bind_group = Some(self.core.device.create_bind_group(
                &wgpu::BindGroupDescriptor {
                    label: Some("lbt_blit_bind_group"),
                    layout: &self.blit_bind_group_layout,
                    entries: &[
                        wgpu::BindGroupEntry {
                            binding: 0,
                            resource: self.blit_uniform_buf.as_entire_binding(),
                        },
                        wgpu::BindGroupEntry {
                            binding: 1,
                            resource: wgpu::BindingResource::TextureView(resolve_view),
                        },
                        wgpu::BindGroupEntry {
                            binding: 2,
                            resource: wgpu::BindingResource::Sampler(&self.sampler),
                        },
                    ],
                },
            ));
        }

        if !self.blit_pipelines.contains_key(&target_format) {
            self.blit_pipelines.insert(
                target_format,
                self.create_blit_pipeline(target_format),
            );
        }

        self.core.encode_scene_pass(encoder, w, h);
        Ok(())
    }

    /// Composite the resolved 3D scene texture into an active Rune `RenderPass` at `[x, y, w, h]`.
    pub fn draw_blit(
        &mut self,
        pass: &mut wgpu::RenderPass<'_>,
        target_format: wgpu::TextureFormat,
        target_size: [u32; 2],
        slot_origin: [f32; 2],
        slot_rect: [f32; 4],
        srgb_blend: bool,
    ) {
        let Some(bind_group) = &self.scene_blit_bind_group else {
            return;
        };

        if !self.blit_pipelines.contains_key(&target_format) {
            self.blit_pipelines.insert(
                target_format,
                self.create_blit_pipeline(target_format),
            );
        }
        let pipeline = self
            .blit_pipelines
            .get(&target_format)
            .expect("blit pipeline inserted");

        let tw = target_size[0].max(1) as f32;
        let th = target_size[1].max(1) as f32;
        let rx = (slot_rect[0] - slot_origin[0]) / tw;
        let ry = (slot_rect[1] - slot_origin[1]) / th;
        let rw = slot_rect[2].max(1.0) / tw;
        let rh = slot_rect[3].max(1.0) / th;

        let uniform = BlitUniform {
            rect_norm: [rx, ry, rw, rh],
            uv_rect: [0.0, 0.0, 1.0, 1.0],
            flags: [u32::from(srgb_blend), 0, 0, 0],
        };
        self.core
            .queue
            .write_buffer(&self.blit_uniform_buf, 0, bytemuck::bytes_of(&uniform));

        pass.set_pipeline(pipeline);
        pass.set_bind_group(0, bind_group, &[]);
        pass.draw(0..6, 0..1);
    }

    fn create_blit_pipeline(&self, target_format: wgpu::TextureFormat) -> wgpu::RenderPipeline {
        self.core
            .device
            .create_render_pipeline(&wgpu::RenderPipelineDescriptor {
                label: Some("lbt_blit_pipeline"),
                layout: Some(&self.blit_pipeline_layout),
                vertex: wgpu::VertexState {
                    module: &self.blit_shader,
                    entry_point: Some("vs_blit"),
                    compilation_options: Default::default(),
                    buffers: &[],
                },
                fragment: Some(wgpu::FragmentState {
                    module: &self.blit_shader,
                    entry_point: Some("fs_blit"),
                    compilation_options: Default::default(),
                    targets: &[Some(wgpu::ColorTargetState {
                        format: target_format,
                        blend: None,
                        write_mask: wgpu::ColorWrites::ALL,
                    })],
                }),
                primitive: wgpu::PrimitiveState {
                    topology: wgpu::PrimitiveTopology::TriangleList,
                    ..Default::default()
                },
                depth_stencil: None,
                multisample: wgpu::MultisampleState::default(),
                multiview_mask: None,
                cache: None,
            })
    }
}
