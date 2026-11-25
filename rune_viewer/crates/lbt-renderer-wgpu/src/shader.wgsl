// Architectural 3D building shaders for lbt-renderer-wgpu.
// Passes:
//   0: Studio background gradient (vs_bg / fs_bg)
//   1: Opaque solid architectural surfaces (vs_opaque / fs_solid)
//   2: Crisp architectural wireframe/crease edges (vs_edge / fs_edge)
//   3: Translucent glass apertures & ghost_context geometry (vs_translucent / fs_translucent)
//   4: Offscreen R32Uint object ID + R32Uint depth-bits picking (vs_pick / fs_pick)

const FLAG_SELECTED: u32 = 1u << 0u;
const FLAG_HIGHLIGHTED: u32 = 1u << 1u;
const FLAG_ERROR: u32 = 1u << 2u;
const FLAG_WARNING: u32 = 1u << 3u;
const FLAG_GHOST: u32 = 1u << 4u;
const FLAG_HIDDEN: u32 = 1u << 5u;
const FLAG_TRANSLUCENT: u32 = 1u << 6u;

const KIND_APERTURE: u32 = 2u;

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
    color: vec4<f32>, // linear RGBA
    flags: u32,
    _pad0: u32,
    _pad1: u32,
    _pad2: u32,
};

@group(0) @binding(0) var<uniform> globals: Globals;
@group(0) @binding(1) var<storage, read> styles: array<ObjectStyle>;

fn get_style(object_id: u32) -> ObjectStyle {
    let idx = min(object_id, globals.flags.w);
    return styles[idx];
}

fn clipped_out(world_pos: vec3<f32>) -> bool {
    if globals.flags.x == 0u {
        return false;
    }
    return dot(world_pos, globals.section_plane.xyz) > globals.section_plane.w;
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
// Shared Mesh Vertex I/O
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
    let n_len = length(raw_normal);
    var n = vec3<f32>(0.0, 0.0, 1.0);
    if n_len > 1e-5 {
        n = raw_normal / n_len;
    }
    if !front_facing {
        n = -n;
    }

    // Architectural hemisphere + key sun + cool fill lighting (Z-up).
    let key_dir = normalize(vec3<f32>(0.48, -0.58, 0.66));
    let fill_dir = normalize(vec3<f32>(-0.58, 0.46, 0.45));
    let key_diff = max(dot(n, key_dir), 0.0);
    let fill_diff = max(dot(n, fill_dir), 0.0);
    let hemi_t = clamp(0.5 + 0.5 * n.z, 0.0, 1.0);

    let sky_tint = select(vec3<f32>(0.96, 0.98, 1.02), vec3<f32>(0.84, 0.90, 1.00), globals.flags.y != 0u);
    let ground_tint = select(vec3<f32>(0.68, 0.66, 0.64), vec3<f32>(0.42, 0.44, 0.48), globals.flags.y != 0u);
    let hemi = mix(ground_tint, sky_tint, hemi_t);

    let light = hemi * 0.46 + vec3<f32>(1.04, 0.99, 0.92) * (key_diff * 0.66) + vec3<f32>(0.78, 0.88, 1.02) * (fill_diff * 0.24);
    var base = style.color.rgb;

    if (style.flags & FLAG_ERROR) != 0u {
        base = mix(base, vec3<f32>(0.90, 0.06, 0.06), 0.55);
    } else if (style.flags & FLAG_WARNING) != 0u {
        base = mix(base, vec3<f32>(0.92, 0.45, 0.02), 0.46);
    }
    if (style.flags & FLAG_HIGHLIGHTED) != 0u {
        base = mix(base, globals.accent_highlight.rgb, 0.28);
    }
    if (style.flags & FLAG_SELECTED) != 0u {
        base = mix(base, globals.accent_selected.rgb, 0.34);
    }

    var shaded = base * light;
    if (style.flags & (FLAG_SELECTED | FLAG_HIGHLIGHTED)) != 0u {
        let view_dir = normalize(globals.camera_pos.xyz - world_pos);
        let rim = pow(1.0 - max(dot(n, view_dir), 0.0), 2.5);
        let rim_color = select(globals.accent_highlight.rgb, globals.accent_selected.rgb, (style.flags & FLAG_SELECTED) != 0u);
        shaded = shaded + rim_color * (rim * 0.35);
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
    if (style.flags & (FLAG_HIDDEN | FLAG_TRANSLUCENT)) != 0u {
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
    if (style.flags & (FLAG_HIDDEN | FLAG_TRANSLUCENT)) != 0u {
        discard;
    }
    let rgb = compute_lit_surface(in.world_pos, in.normal, front_facing, style);
    return vec4<f32>(rgb, 1.0);
}

// ---------------------------------------------------------------------------
// Pass 2: Architectural Edge Pass
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
    if (style.flags & FLAG_HIDDEN) != 0u {
        out.clip_pos = vec4<f32>(0.0, 0.0, -2.0, 1.0);
        return out;
    }

    var biased_pos = in.position;
    if globals.flags.z != 0u {
        let eps = clamp(globals.camera_forward.w * 0.0004, 0.001, 0.04);
        biased_pos = biased_pos - globals.camera_forward.xyz * eps;
    } else {
        let to_cam = globals.camera_pos.xyz - in.position;
        let dist = length(to_cam);
        if dist > 1e-4 {
            let eps = clamp(dist * 0.0005, 0.001, 0.04);
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
    if (style.flags & FLAG_HIDDEN) != 0u {
        discard;
    }

    if (style.flags & FLAG_ERROR) != 0u {
        return vec4<f32>(0.98, 0.14, 0.14, 1.0);
    }
    if (style.flags & FLAG_WARNING) != 0u {
        return vec4<f32>(0.98, 0.56, 0.05, 1.0);
    }
    if (style.flags & FLAG_SELECTED) != 0u {
        return vec4<f32>(globals.accent_selected.rgb * 1.25, 1.0);
    }
    if (style.flags & FLAG_HIGHLIGHTED) != 0u {
        return vec4<f32>(globals.accent_highlight.rgb * 1.25, 1.0);
    }
    if (style.flags & FLAG_GHOST) != 0u {
        let ghost_line = select(vec3<f32>(0.32, 0.36, 0.42), vec3<f32>(0.42, 0.48, 0.56), globals.flags.y != 0u);
        return vec4<f32>(ghost_line, 0.18);
    }

    let base_line = select(vec3<f32>(0.05, 0.07, 0.10), vec3<f32>(0.03, 0.04, 0.06), globals.flags.y != 0u);
    let tinted = mix(base_line, style.color.rgb * 0.25, 0.35);
    let alpha = select(0.88, 0.65, (style.flags & FLAG_TRANSLUCENT) != 0u);
    return vec4<f32>(tinted, alpha);
}

// ---------------------------------------------------------------------------
// Pass 3: Translucent Glass & Ghost Context Pass
// ---------------------------------------------------------------------------

@vertex
fn vs_translucent(in: MeshIn) -> MeshOut {
    let style = get_style(in.object_id);
    var out: MeshOut;
    out.world_pos = in.position;
    out.normal = in.normal;
    out.object_id = in.object_id;
    out.kind_code = in.kind_code;
    if (style.flags & FLAG_HIDDEN) != 0u || (style.flags & FLAG_TRANSLUCENT) == 0u {
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
    if (style.flags & FLAG_HIDDEN) != 0u || (style.flags & FLAG_TRANSLUCENT) == 0u {
        discard;
    }

    if (style.flags & FLAG_GHOST) != 0u {
        var ghost_rgb = select(vec3<f32>(0.42, 0.47, 0.54), vec3<f32>(0.30, 0.36, 0.44), globals.flags.y != 0u);
        var ghost_alpha = select(0.14, 0.07, in.kind_code == KIND_APERTURE);
        if (style.flags & FLAG_ERROR) != 0u {
            ghost_rgb = vec3<f32>(0.85, 0.12, 0.12);
            ghost_alpha = 0.34;
        } else if (style.flags & FLAG_WARNING) != 0u {
            ghost_rgb = vec3<f32>(0.90, 0.52, 0.06);
            ghost_alpha = 0.28;
        }
        return vec4<f32>(ghost_rgb, ghost_alpha);
    }

    let n_len = length(in.normal);
    var n = vec3<f32>(0.0, 0.0, 1.0);
    if n_len > 1e-5 {
        n = in.normal / n_len;
    }
    if !front_facing {
        n = -n;
    }

    let view_dir = select(
        normalize(globals.camera_pos.xyz - in.world_pos),
        -globals.camera_forward.xyz,
        globals.flags.z != 0u,
    );
    let fresnel = pow(1.0 - max(dot(n, view_dir), 0.0), 3.0);
    var rgb = compute_lit_surface(in.world_pos, in.normal, front_facing, style);
    rgb = rgb + vec3<f32>(0.36, 0.56, 0.78) * (fresnel * 0.55);

    var alpha = clamp(style.color.a + fresnel * 0.16, 0.25, 0.80);
    if (style.flags & (FLAG_SELECTED | FLAG_HIGHLIGHTED | FLAG_ERROR | FLAG_WARNING)) != 0u {
        alpha = max(alpha, 0.58);
    }
    return vec4<f32>(rgb, alpha);
}

// ---------------------------------------------------------------------------
// Pass 4: Offscreen R32Uint Pick Pass (Object ID + IEEE Depth Bits)
// ---------------------------------------------------------------------------

struct PickOut {
    @location(0) object_id: u32,
    @location(1) depth_bits: u32,
};

@vertex
fn vs_pick(in: MeshIn) -> MeshOut {
    let style = get_style(in.object_id);
    var out: MeshOut;
    out.world_pos = in.position;
    out.normal = in.normal;
    out.object_id = in.object_id;
    out.kind_code = in.kind_code;
    if (style.flags & FLAG_HIDDEN) != 0u {
        out.clip_pos = vec4<f32>(0.0, 0.0, -2.0, 1.0);
    } else {
        out.clip_pos = globals.view_proj * vec4<f32>(in.position, 1.0);
    }
    return out;
}

@fragment
fn fs_pick(in: MeshOut) -> PickOut {
    if clipped_out(in.world_pos) {
        discard;
    }
    let style = get_style(in.object_id);
    if (style.flags & FLAG_HIDDEN) != 0u {
        discard;
    }
    var out: PickOut;
    out.object_id = in.object_id;
    out.depth_bits = bitcast<u32>(in.clip_pos.z);
    return out;
}
