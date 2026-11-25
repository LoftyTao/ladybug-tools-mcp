// Full-rect textured quad blit for embedding offscreen 3D renders inside Rune EffectSite passes.

struct BlitUniform {
    rect_norm: vec4<f32>, // [x / target_w, y / target_h, w / target_w, h / target_h]
    uv_rect: vec4<f32>,   // [u0, v0, u_scale, v_scale]
    flags: vec4<u32>,     // x = encode_srgb (0 or 1)
};

@group(0) @binding(0) var<uniform> blit: BlitUniform;
@group(0) @binding(1) var scene_tex: texture_2d<f32>;
@group(0) @binding(2) var scene_sampler: sampler;

struct BlitOut {
    @builtin(position) clip_pos: vec4<f32>,
    @location(0) uv: vec2<f32>,
};

@vertex
fn vs_blit(@builtin(vertex_index) vid: u32) -> BlitOut {
    var corners = array<vec2<f32>, 6>(
        vec2<f32>(0.0, 0.0),
        vec2<f32>(1.0, 0.0),
        vec2<f32>(0.0, 1.0),
        vec2<f32>(0.0, 1.0),
        vec2<f32>(1.0, 0.0),
        vec2<f32>(1.0, 1.0),
    );
    let c = corners[vid];
    let px = blit.rect_norm.xy + c * blit.rect_norm.zw;
    let ndc = vec2<f32>(px.x * 2.0 - 1.0, 1.0 - px.y * 2.0);
    var out: BlitOut;
    out.clip_pos = vec4<f32>(ndc, 0.0, 1.0);
    out.uv = blit.uv_rect.xy + c * blit.uv_rect.zw;
    return out;
}

fn linear_to_srgb_channel(c: f32) -> f32 {
    let v = clamp(c, 0.0, 1.0);
    if v <= 0.0031308 {
        return v * 12.92;
    }
    return 1.055 * pow(v, 1.0 / 2.4) - 0.055;
}

@fragment
fn fs_blit(in: BlitOut) -> @location(0) vec4<f32> {
    let sampled = textureSample(scene_tex, scene_sampler, in.uv);
    if blit.flags.x != 0u {
        return vec4<f32>(
            linear_to_srgb_channel(sampled.r),
            linear_to_srgb_channel(sampled.g),
            linear_to_srgb_channel(sampled.b),
            1.0,
        );
    }
    return vec4<f32>(sampled.rgb, 1.0);
}
