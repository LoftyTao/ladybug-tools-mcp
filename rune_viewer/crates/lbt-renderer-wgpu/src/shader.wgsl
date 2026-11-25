// Architectural 3D building shaders for lbt-renderer-wgpu (WebGPU, WebGL2, DX12, Metal, Vulkan).
// Passes:
//   0: Studio background gradient (vs_bg / fs_bg)
//   1: Opaque solid architectural surfaces (vs_opaque / fs_solid)
//   2: Crisp active architectural wireframe/crease edges (vs_edge / fs_edge)
//   3: Active translucent glazing & air boundaries (vs_translucent / fs_translucent)
//   4a: Ghost context depth-only shell pre-pass (vs_ghost / fs_ghost_depth)
//   4b: Ghost context single-layer color pass (vs_ghost / fs_ghost_color)
//   4c: Ghost context visible silhouette/crease edges (vs_ghost_edge / fs_ghost_edge)
// Styles are packed into 2D Rgba8Unorm lookup textures (width = 256) so both WebGPU and
// WebGL2 execute the exact same shader without storage buffers, bitcasts, or integer textures.

const FLAG_SELECTED: u32 = 1u << 0u;
const FLAG_HIGHLIGHTED: u32 = 1u << 1u;
const FLAG_ERROR: u32 = 1u << 2u;
const FLAG_WARNING: u32 = 1u << 3u;
const FLAG_GHOST: u32 = 1u << 4u;
const FLAG_HIDDEN: u32 = 1u << 5u;
const FLAG_TRANSLUCENT: u32 = 1u << 6u;
const FLAG_CULL_BACK: u32 = 1u << 7u;

const KIND_APERTURE: u32 = 2u;
const KIND_DOOR: u32 = 3u;

struct Globals {
    view_proj: mat4x4<f32>,
    camera_pos: vec4<f32>,     // xyz = eye position, w = is_ortho (1.0 / 0.0)
    camera_forward: vec4<f32>, // xyz = unit forward, w = ortho_scale
    section_plane: vec4<f32>,  // xyz = outward cut normal, w = signed threshold
    bg_bottom: vec4<f32>,
    bg_top: vec4<f32>,
    accent_selected: vec4<f32>,
    accent_highlight: vec4<f32>,
    flags: vec4<u32>,          // x = section_enabled, y = dark_mode, z = is_ortho, w = max_object_id
};

struct ObjectStyle {
    color: vec4<f32>, // linear RGB + sRGB/linear alpha
    flags: u32,
};

@group(0) @binding(0) var<uniform> globals: Globals;
@group(0) @binding(1) var style_color_tex: texture_2d<f32>;
@group(0) @binding(2) var style_flags_tex: texture_2d<f32>;

fn srgb_to_linear_channel(c: f32) -> f32 {
    if c <= 0.04045 {
        return c / 12.92;
    }
    return pow((c + 0.055) / 1.055, 2.4);
}

fn get_style(object_id: u32) -> ObjectStyle {
    let idx = min(object_id, globals.flags.w);
    let coord = vec2<i32>(i32(idx & 255u), i32(idx >> 8u));
    let c = textureLoad(style_color_tex, coord, 0);
    let f = textureLoad(style_flags_tex, coord, 0);
    var style: ObjectStyle;
    style.color = vec4<f32>(
        srgb_to_linear_channel(c.r),
        srgb_to_linear_channel(c.g),
        srgb_to_linear_channel(c.b),
        c.a,
    );
    style.flags = u32(round(f.r * 255.0));
    return style;
}

fn clipped_out(world_pos: vec3<f32>) -> bool {
    if globals.flags.x == 0u {
        return false;
    }
    return dot(world_pos, globals.section_plane.xyz) > globals.section_plane.w;
}

fn compute_view_dir(world_pos: vec3<f32>) -> vec3<f32> {
    if globals.flags.z != 0u {
        let f_len = length(globals.camera_forward.xyz);
        if f_len > 1e-5 {
            return -globals.camera_forward.xyz / f_len;
        }
        return vec3<f32>(0.0, 0.0, 1.0);
    }
    let to_cam = globals.camera_pos.xyz - world_pos;
    let d_len = length(to_cam);
    if d_len > 1e-5 {
        return to_cam / d_len;
    }
    return vec3<f32>(0.0, 0.0, 1.0);
}

fn orient_normal(raw_normal: vec3<f32>, front_facing: bool) -> vec3<f32> {
    let n_len = length(raw_normal);
    var n = vec3<f32>(0.0, 0.0, 1.0);
    if n_len > 1e-5 {
        n = raw_normal / n_len;
    }
    if !front_facing {
        n = -n;
    }
    return n;
}

// ---------------------------------------------------------------------------
// Pass 0: Studio background gradient
// ---------------------------------------------------------------------------

struct BgOut {
    @builtin(position) clip_pos: vec4<f32>,
    @location(0) v_t: f32,
};

@vertex
fn vs_bg(@builtin(vertex_index) vid: u32) -> BgOut {
    var pos = array<vec2<f32>, 3>(
        vec2<f32>(-1.0, -1.0),
        vec2<f32>(3.0, -1.0),
        vec2<f32>(-1.0, 3.0),
    );
    let p = pos[vid];
    var out: BgOut;
    out.clip_pos = vec4<f32>(p, 1.0, 1.0);
    out.v_t = p.y * 0.5 + 0.5;
    return out;
}

@fragment
fn fs_bg(in: BgOut) -> @location(0) vec4<f32> {
    let t = clamp(in.v_t, 0.0, 1.0);
    return mix(globals.bg_bottom, globals.bg_top, t);
}

// ---------------------------------------------------------------------------
// Shared Mesh Vertex I/O & Faithful honeybee-display Studio Lighting
// ---------------------------------------------------------------------------

struct MeshIn {
    @location(0) position: vec3<f32>,
    @location(1) normal: vec3<f32>,
    @location(2) object_id: u32,
    @location(3) kind_code: u32,
};

struct MeshOut {
    @builtin(position) clip_pos: vec4<f32>,
    @location(0) world_pos: vec3<f32>,
    @location(1) normal: vec3<f32>,
    @location(2) @interpolate(flat) object_id: u32,
    @location(3) @interpolate(flat) kind_code: u32,
};

fn compute_lit_surface(
    world_pos: vec3<f32>,
    raw_normal: vec3<f32>,
    front_facing: bool,
    style: ObjectStyle,
) -> vec3<f32> {
    let n = orient_normal(raw_normal, front_facing);
    let view_dir = compute_view_dir(world_pos);

    // Neutral architectural studio lighting (Z-up) tuned so official honeybee-display
    // colors (Wall gold, Roof crimson, Aperture blue, Shade purple, Surface green)
    // remain crisp, vibrant, and true across all orientations in Dark and Light themes.
    let key_dir = normalize(vec3<f32>(0.50, -0.62, 0.60));
    let fill_dir = normalize(vec3<f32>(-0.62, 0.48, 0.42));
    let bounce_dir = normalize(vec3<f32>(-0.20, 0.30, -0.93));

    let key_diff = max(dot(n, key_dir), 0.0);
    let fill_diff = max(dot(n, fill_dir), 0.0);
    let bounce_diff = max(dot(n, bounce_dir), 0.0);
    let cam_diff = max(dot(n, view_dir), 0.0);
    let hemi_t = clamp(0.5 + 0.5 * n.z, 0.0, 1.0);

    let is_dark = globals.flags.y != 0u;
    let sky_tint = select(vec3<f32>(1.00, 1.00, 1.02), vec3<f32>(0.96, 0.98, 1.02), is_dark);
    let ground_tint = select(vec3<f32>(0.74, 0.73, 0.72), vec3<f32>(0.62, 0.63, 0.66), is_dark);
    let hemi = mix(ground_tint, sky_tint, hemi_t);

    let light = hemi * 0.58
        + vec3<f32>(1.03, 1.00, 0.96) * (key_diff * 0.50)
        + vec3<f32>(0.93, 0.97, 1.03) * (fill_diff * 0.18)
        + vec3<f32>(0.96, 0.95, 0.94) * (bounce_diff * 0.08)
        + vec3<f32>(1.00, 1.00, 1.00) * (cam_diff * 0.11);

    var base = style.color.rgb;

    if (style.flags & FLAG_ERROR) != 0u {
        base = mix(base, vec3<f32>(0.92, 0.06, 0.06), 0.55);
    } else if (style.flags & FLAG_WARNING) != 0u {
        base = mix(base, vec3<f32>(0.94, 0.46, 0.02), 0.46);
    }
    if (style.flags & FLAG_HIGHLIGHTED) != 0u {
        base = mix(base, globals.accent_highlight.rgb, 0.24);
    }
    if (style.flags & FLAG_SELECTED) != 0u {
        base = mix(base, globals.accent_selected.rgb, 0.28);
    }

    var shaded = base * light;
    if (style.flags & (FLAG_SELECTED | FLAG_HIGHLIGHTED)) != 0u {
        let rim = pow(1.0 - max(dot(n, view_dir), 0.0), 2.5);
        let rim_color = select(
            globals.accent_highlight.rgb,
            globals.accent_selected.rgb,
            (style.flags & FLAG_SELECTED) != 0u,
        );
        shaded = shaded + rim_color * (rim * 0.34);
    }
    return shaded;
}

// ---------------------------------------------------------------------------
// Pass 1: Opaque Solid Pass
// ---------------------------------------------------------------------------

@vertex
fn vs_opaque(in: MeshIn) -> MeshOut {
    let style = get_style(in.object_id);
    var out: MeshOut;
    out.world_pos = in.position;
    out.normal = in.normal;
    out.object_id = in.object_id;
    out.kind_code = in.kind_code;
    if (style.flags & (FLAG_HIDDEN | FLAG_GHOST | FLAG_TRANSLUCENT)) != 0u {
        out.clip_pos = vec4<f32>(0.0, 0.0, -2.0, 1.0);
    } else {
        out.clip_pos = globals.view_proj * vec4<f32>(in.position, 1.0);
    }
    return out;
}

@fragment
fn fs_solid(in: MeshOut, @builtin(front_facing) front_facing: bool) -> @location(0) vec4<f32> {
    if clipped_out(in.world_pos) {
        discard;
    }
    let style = get_style(in.object_id);
    if (style.flags & (FLAG_HIDDEN | FLAG_GHOST | FLAG_TRANSLUCENT)) != 0u {
        discard;
    }
    let rgb = compute_lit_surface(in.world_pos, in.normal, front_facing, style);
    return vec4<f32>(rgb, 1.0);
}

// ---------------------------------------------------------------------------
// Pass 2: Active Architectural Edge Pass
// ---------------------------------------------------------------------------

struct EdgeIn {
    @location(0) position: vec3<f32>,
    @location(1) object_id: u32,
};

struct EdgeOut {
    @builtin(position) clip_pos: vec4<f32>,
    @location(0) world_pos: vec3<f32>,
    @location(1) @interpolate(flat) object_id: u32,
};

@vertex
fn vs_edge(in: EdgeIn) -> EdgeOut {
    let style = get_style(in.object_id);
    var out: EdgeOut;
    out.world_pos = in.position;
    out.object_id = in.object_id;
    if (style.flags & (FLAG_HIDDEN | FLAG_GHOST)) != 0u {
        out.clip_pos = vec4<f32>(0.0, 0.0, -2.0, 1.0);
        return out;
    }

    var biased_pos = in.position;
    if globals.flags.z != 0u {
        let eps = clamp(globals.camera_forward.w * 0.00035, 0.0008, 0.035);
        biased_pos = biased_pos - globals.camera_forward.xyz * eps;
    } else {
        let to_cam = globals.camera_pos.xyz - in.position;
        let dist = length(to_cam);
        if dist > 1e-4 {
            let eps = clamp(dist * 0.00045, 0.0008, 0.035);
            biased_pos = biased_pos + (to_cam / dist) * eps;
        }
    }
    out.clip_pos = globals.view_proj * vec4<f32>(biased_pos, 1.0);
    return out;
}

@fragment
fn fs_edge(in: EdgeOut) -> @location(0) vec4<f32> {
    if clipped_out(in.world_pos) {
        discard;
    }
    let style = get_style(in.object_id);
    if (style.flags & (FLAG_HIDDEN | FLAG_GHOST)) != 0u {
        discard;
    }

    if (style.flags & FLAG_ERROR) != 0u {
        return vec4<f32>(0.98, 0.14, 0.14, 1.0);
    }
    if (style.flags & FLAG_WARNING) != 0u {
        return vec4<f32>(0.98, 0.56, 0.05, 1.0);
    }
    if (style.flags & FLAG_SELECTED) != 0u {
        return vec4<f32>(globals.accent_selected.rgb * 1.22, 1.0);
    }
    if (style.flags & FLAG_HIGHLIGHTED) != 0u {
        return vec4<f32>(globals.accent_highlight.rgb * 1.22, 1.0);
    }

    let is_dark = globals.flags.y != 0u;
    let base_line = select(vec3<f32>(0.04, 0.05, 0.07), vec3<f32>(0.025, 0.032, 0.045), is_dark);
    let tinted = mix(base_line, style.color.rgb * 0.22, 0.28);
    let alpha = select(0.90, 0.72, (style.flags & FLAG_TRANSLUCENT) != 0u);
    return vec4<f32>(tinted, alpha);
}

// ---------------------------------------------------------------------------
// Pass 3: Active Translucent Glazing & Air Boundary Pass
// ---------------------------------------------------------------------------

@vertex
fn vs_translucent(in: MeshIn) -> MeshOut {
    let style = get_style(in.object_id);
    var out: MeshOut;
    out.world_pos = in.position;
    out.normal = in.normal;
    out.object_id = in.object_id;
    out.kind_code = in.kind_code;
    if (style.flags & (FLAG_HIDDEN | FLAG_GHOST)) != 0u || (style.flags & FLAG_TRANSLUCENT) == 0u {
        out.clip_pos = vec4<f32>(0.0, 0.0, -2.0, 1.0);
    } else {
        out.clip_pos = globals.view_proj * vec4<f32>(in.position, 1.0);
    }
    return out;
}

@fragment
fn fs_translucent(in: MeshOut, @builtin(front_facing) front_facing: bool) -> @location(0) vec4<f32> {
    if clipped_out(in.world_pos) {
        discard;
    }
    let style = get_style(in.object_id);
    if (style.flags & (FLAG_HIDDEN | FLAG_GHOST)) != 0u || (style.flags & FLAG_TRANSLUCENT) == 0u {
        discard;
    }
    // Paired interior Surface-BC glazing / Air Boundaries only render their front-facing sheet
    // so adjacent rooms never double-blend coplanar translucent panes.
    if !front_facing && (style.flags & FLAG_CULL_BACK) != 0u {
        discard;
    }

    let n = orient_normal(in.normal, front_facing);
    let view_dir = compute_view_dir(in.world_pos);
    let fresnel = pow(1.0 - max(dot(n, view_dir), 0.0), 3.0);

    var rgb = compute_lit_surface(in.world_pos, in.normal, front_facing, style);
    let is_glazing = in.kind_code == KIND_APERTURE || in.kind_code == KIND_DOOR;
    if is_glazing {
        rgb = rgb + vec3<f32>(0.48, 0.72, 0.94) * (fresnel * 0.42);
    } else {
        let sheen = mix(vec3<f32>(0.95, 0.95, 0.86), style.color.rgb, 0.50);
        rgb = rgb + sheen * (fresnel * 0.22);
    }

    var base_alpha = style.color.a;
    if base_alpha > 0.98 {
        base_alpha = 0.40;
    }
    var alpha = clamp(base_alpha + fresnel * 0.14, 0.28, 0.76);
    if (style.flags & (FLAG_SELECTED | FLAG_HIGHLIGHTED | FLAG_ERROR | FLAG_WARNING)) != 0u {
        alpha = max(alpha, 0.56);
    }
    return vec4<f32>(rgb, alpha);
}

// ---------------------------------------------------------------------------
// Pass 4a & 4b: Ghost Context Single-Layer Shell (Depth Pre-Pass + Color Pass)
// ---------------------------------------------------------------------------

@vertex
fn vs_ghost(in: MeshIn) -> MeshOut {
    let style = get_style(in.object_id);
    var out: MeshOut;
    out.world_pos = in.position;
    out.normal = in.normal;
    out.object_id = in.object_id;
    out.kind_code = in.kind_code;
    if (style.flags & FLAG_HIDDEN) != 0u || (style.flags & FLAG_GHOST) == 0u {
        out.clip_pos = vec4<f32>(0.0, 0.0, -2.0, 1.0);
    } else {
        out.clip_pos = globals.view_proj * vec4<f32>(in.position, 1.0);
    }
    return out;
}

@fragment
fn fs_ghost_depth(in: MeshOut, @builtin(front_facing) front_facing: bool) -> @location(0) vec4<f32> {
    if clipped_out(in.world_pos) {
        discard;
    }
    let style = get_style(in.object_id);
    if (style.flags & FLAG_HIDDEN) != 0u || (style.flags & FLAG_GHOST) == 0u {
        discard;
    }
    if !front_facing && (style.flags & FLAG_CULL_BACK) != 0u {
        discard;
    }
    return vec4<f32>(0.0, 0.0, 0.0, 0.0);
}

@fragment
fn fs_ghost_color(in: MeshOut, @builtin(front_facing) front_facing: bool) -> @location(0) vec4<f32> {
    if clipped_out(in.world_pos) {
        discard;
    }
    let style = get_style(in.object_id);
    if (style.flags & FLAG_HIDDEN) != 0u || (style.flags & FLAG_GHOST) == 0u {
        discard;
    }
    if !front_facing && (style.flags & FLAG_CULL_BACK) != 0u {
        discard;
    }

    let n = orient_normal(in.normal, front_facing);
    let key_dir = normalize(vec3<f32>(0.50, -0.62, 0.60));
    let hemi_t = clamp(0.5 + 0.5 * n.z, 0.0, 1.0);
    let shade = 0.68 + 0.22 * hemi_t + 0.16 * max(dot(n, key_dir), 0.0);

    let is_dark = globals.flags.y != 0u;
    let is_glass = (style.flags & FLAG_TRANSLUCENT) != 0u || in.kind_code == KIND_APERTURE;
    let neutral_tint = select(vec3<f32>(0.54, 0.58, 0.65), vec3<f32>(0.34, 0.40, 0.48), is_dark);
    var ghost_rgb = mix(neutral_tint, style.color.rgb, 0.20) * shade;
    var ghost_alpha = select(
        select(0.16, 0.18, is_dark),
        select(0.08, 0.09, is_dark),
        is_glass,
    );

    if (style.flags & FLAG_ERROR) != 0u {
        ghost_rgb = vec3<f32>(0.88, 0.12, 0.12) * shade;
        ghost_alpha = 0.36;
    } else if (style.flags & FLAG_WARNING) != 0u {
        ghost_rgb = vec3<f32>(0.92, 0.52, 0.06) * shade;
        ghost_alpha = 0.30;
    }
    return vec4<f32>(ghost_rgb, ghost_alpha);
}

// ---------------------------------------------------------------------------
// Pass 4c: Ghost Context Visible Edges Pass
// ---------------------------------------------------------------------------

@vertex
fn vs_ghost_edge(in: EdgeIn) -> EdgeOut {
    let style = get_style(in.object_id);
    var out: EdgeOut;
    out.world_pos = in.position;
    out.object_id = in.object_id;
    if (style.flags & FLAG_HIDDEN) != 0u || (style.flags & FLAG_GHOST) == 0u {
        out.clip_pos = vec4<f32>(0.0, 0.0, -2.0, 1.0);
        return out;
    }
    // No camera pull: ghost triangles are depth-biased away in Pass 4a so visible ghost
    // silhouette edges pass cleanly while shared-wall edges stay hidden behind active rooms.
    out.clip_pos = globals.view_proj * vec4<f32>(in.position, 1.0);
    return out;
}

@fragment
fn fs_ghost_edge(in: EdgeOut) -> @location(0) vec4<f32> {
    if clipped_out(in.world_pos) {
        discard;
    }
    let style = get_style(in.object_id);
    if (style.flags & FLAG_HIDDEN) != 0u || (style.flags & FLAG_GHOST) == 0u {
        discard;
    }

    if (style.flags & FLAG_ERROR) != 0u {
        return vec4<f32>(0.92, 0.16, 0.16, 0.55);
    }
    if (style.flags & FLAG_WARNING) != 0u {
        return vec4<f32>(0.94, 0.54, 0.08, 0.48);
    }
    let is_dark = globals.flags.y != 0u;
    let ghost_line = select(vec3<f32>(0.30, 0.35, 0.42), vec3<f32>(0.48, 0.56, 0.66), is_dark);
    let alpha = select(0.22, 0.24, is_dark);
    return vec4<f32>(ghost_line, alpha);
}
