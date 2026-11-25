// Native-only Pass 5: Offscreen R32Uint Pick Pass (Object ID + IEEE Depth Bits)
// Concatenated onto shader.wgsl by BuildingRenderer so Globals, get_style, clipped_out,
// MeshIn, and MeshOut stay single-sourced.

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

@vertex
fn vs_pick_active(in: MeshIn) -> MeshOut {
    let style = get_style(in.object_id);
    var out: MeshOut;
    out.world_pos = in.position;
    out.normal = in.normal;
    out.object_id = in.object_id;
    out.kind_code = in.kind_code;
    if (style.flags & (FLAG_HIDDEN | FLAG_GHOST)) != 0u {
        out.clip_pos = vec4<f32>(0.0, 0.0, -2.0, 1.0);
    } else {
        out.clip_pos = globals.view_proj * vec4<f32>(in.position, 1.0);
    }
    return out;
}

@fragment
fn fs_pick_active(in: MeshOut) -> PickOut {
    if clipped_out(in.world_pos) {
        discard;
    }
    let style = get_style(in.object_id);
    if (style.flags & (FLAG_HIDDEN | FLAG_GHOST)) != 0u {
        discard;
    }
    var out: PickOut;
    out.object_id = in.object_id;
    out.depth_bits = bitcast<u32>(in.clip_pos.z);
    return out;
}
