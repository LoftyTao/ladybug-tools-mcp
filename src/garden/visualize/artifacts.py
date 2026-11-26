"""VisualizationSet artifact services."""

from __future__ import annotations

from contextlib import contextmanager
from ctypes.util import find_library
import json
import math
import os
from pathlib import Path
import sys
import threading
from typing import Any

import ladybug_vtk._extend_visualization_set  # noqa: F401
from ladybug.color import Colorset
from ladybug.legend import (
    Legend,
    LegendParameters,
    LegendParametersCategorized,
)
from ladybug_display.svg._types import ViewBoxSpec
from ladybug_display.visualization import AnalysisGeometry, ContextGeometry, VisualizationSet
from ladybug_geometry.geometry3d import Plane, Vector3D
from ladybug_vtk.display_polydata import DisplayMode, DisplayPolyData
from ladybug_vtk.joined_polydata import JoinedPolyData
from ladybug_vtk.writer import VTKWriters, write_to_file

from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from garden.visualize.legend import (
    create_2d_legend_parameter,
    edit_2d_legend_parameter,
    legend_3d_parameter_from_dict,
    legend_parameter_from_dict,
    resolve_colorset,
)

HTML_ARTIFACT_TYPE = "visualization_html"
SVG_ARTIFACT_TYPE = "visualization_svg"
VTKJS_ARTIFACT_TYPE = "visualization_vtkjs"
PNG_ARTIFACT_TYPE = "visualization_png"
VTK_ARTIFACT_TYPE = "visualization_vtk"
VTP_ARTIFACT_TYPE = "visualization_vtp"
VSF_ARTIFACT_TYPE = "visualization_vsf"
PKL_ARTIFACT_TYPE = "visualization_pkl"
VISUALIZATION_SET_TARGET_TYPE = "visualization_set"
VISUALIZATION_SET_ARTIFACT_TYPE = "visualization_set_json"
SVG_VIEWS = {"Top", "Left", "Right", "Front", "Back", "NE", "NW", "SE", "SW"}


def _resolve_output_dir(garden_root: Path, output_subdir: str) -> Path:
    output_dir = (garden_root / output_subdir).resolve()
    output_dir.relative_to(garden_root.resolve())
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _register_artifact(
    manifest: GardenManifest,
    *,
    artifact_type: str,
    name: str,
    path: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    record = {
        "artifact_type": artifact_type,
        "name": name,
        "path": path,
        "source": source,
        "created_at": utc_now_iso(),
    }
    return manifest.upsert_artifact(record)


def _visualization_set_target(
    *,
    manifest: GardenManifest,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    return {
        "target_type": VISUALIZATION_SET_TARGET_TYPE,
        "garden_id": manifest.garden_id,
        "domain": "visualize",
        "identifier": identifier,
        "path": path,
    }


_SVG_ORDER_LOCK = threading.RLock()
_SVG_SKIP_TAGS = {
    "Defs",
    "Style",
    "Title",
    "Desc",
    "LinearGradient",
    "RadialGradient",
    "Pattern",
    "ClipPath",
    "Mask",
    "Symbol",
    "Marker",
    "Script",
    "Metadata",
}


@contextmanager
def _fast_svg_group_child():
    """Avoid O(N^2) Title lookups in ladybug_display._svg_order._group_child on dense meshes."""
    import ladybug_display._svg_order as svg_order

    with _SVG_ORDER_LOCK:
        orig_group_child = svg_order._group_child
        title_cache: dict[int, tuple[Any, int, list[Any]]] = {}

        def _cached_group_child(parent: Any, child: Any) -> Any:
            from copy import copy

            elements = parent.elements
            n_elems = len(elements)
            key = id(parent)
            cached = title_cache.get(key)
            if cached is not None and cached[0] is parent and cached[1] == n_elems:
                titles = cached[2]
            else:
                titles = [e for e in elements if isinstance(e, svg_order.svg.Title)]
                title_cache[key] = (parent, n_elems, titles)
            group = copy(parent)
            group.elements = [child] + titles
            return group

        svg_order._group_child = _cached_group_child
        try:
            yield
        finally:
            svg_order._group_child = orig_group_child


def _extract_source_run_id(
    *,
    visualization_set: dict[str, Any] | None = None,
    visualization_set_target: dict[str, Any] | None = None,
    manifest: GardenManifest | None = None,
    explicit_source: dict[str, Any] | None = None,
) -> str | None:
    """Resolve source run_id from target, manifest artifact metadata, or VisualizationSet user_data."""
    candidates: list[Any] = []
    if isinstance(explicit_source, dict):
        candidates.extend((explicit_source.get("source_run_id"), explicit_source.get("run_id")))
    if isinstance(visualization_set_target, dict):
        candidates.extend(
            (visualization_set_target.get("source_run_id"), visualization_set_target.get("run_id"))
        )
        if manifest is not None:
            tgt_path = visualization_set_target.get("path")
            tgt_id = visualization_set_target.get("identifier")
            for art in reversed(manifest.artifacts):
                if tgt_path and art.get("path") == tgt_path:
                    src = art.get("source")
                    if isinstance(src, dict):
                        candidates.extend((src.get("source_run_id"), src.get("run_id")))
                    break
                if (
                    not tgt_path
                    and tgt_id
                    and art.get("name") == tgt_id
                    and art.get("artifact_type") == VISUALIZATION_SET_ARTIFACT_TYPE
                ):
                    src = art.get("source")
                    if isinstance(src, dict):
                        candidates.extend((src.get("source_run_id"), src.get("run_id")))
                    break
    if isinstance(visualization_set, dict):
        candidates.extend((visualization_set.get("source_run_id"), visualization_set.get("run_id")))
        user_data = visualization_set.get("user_data")
        if isinstance(user_data, dict):
            candidates.extend((user_data.get("source_run_id"), user_data.get("run_id")))
        vs_source = visualization_set.get("source")
        if isinstance(vs_source, dict):
            candidates.extend((vs_source.get("source_run_id"), vs_source.get("run_id")))
    for val in candidates:
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _normalize_visualization_set_dict(visualization_set: dict[str, Any]) -> dict[str, Any]:
    """Coerce inline legend_parameters lacking 'type' inside a VisualizationSet dict."""
    geos = visualization_set.get("geometry")
    if not isinstance(geos, list) or not geos:
        return visualization_set

    needs_norm = False
    for geo in geos:
        if not isinstance(geo, dict):
            continue
        data_sets = geo.get("data_sets")
        if not isinstance(data_sets, list):
            continue
        for ds in data_sets:
            if not isinstance(ds, dict):
                continue
            lp = ds.get("legend_parameters")
            if isinstance(lp, dict) and not lp.get("type"):
                needs_norm = True
                break
        if needs_norm:
            break
    if not needs_norm:
        return visualization_set

    copied = dict(visualization_set)
    new_geos = []
    for geo in geos:
        if isinstance(geo, dict) and isinstance(geo.get("data_sets"), list):
            new_ds_list = []
            for ds in geo["data_sets"]:
                if isinstance(ds, dict) and isinstance(ds.get("legend_parameters"), dict):
                    ds_copy = dict(ds)
                    ds_copy["legend_parameters"] = coerce_legend_parameter_dict(
                        ds["legend_parameters"]
                    )
                    new_ds_list.append(ds_copy)
                else:
                    new_ds_list.append(ds)
            geo_copy = dict(geo)
            geo_copy["data_sets"] = new_ds_list
            new_geos.append(geo_copy)
        else:
            new_geos.append(geo)
    copied["geometry"] = new_geos
    return copied


def _svg_num(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    inner = getattr(val, "value", None)
    if isinstance(inner, (int, float)) and not isinstance(inner, bool):
        return float(inner)
    if isinstance(val, str):
        stripped = val.strip().lower()
        for suffix in ("px", "pt", "em", "rem"):
            if stripped.endswith(suffix):
                stripped = stripped[: -len(suffix)].strip()
                break
        try:
            return float(stripped)
        except ValueError:
            return default
    return default


def _mat_mul(
    m1: tuple[float, float, float, float, float, float],
    m2: tuple[float, float, float, float, float, float],
) -> tuple[float, float, float, float, float, float]:
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _apply_transforms(
    base: tuple[float, float, float, float, float, float],
    transforms: Any,
) -> tuple[float, float, float, float, float, float]:
    if not transforms:
        return base
    cur = base
    for tr in transforms:
        name = type(tr).__name__
        if name == "Matrix":
            mat = (float(tr.a), float(tr.b), float(tr.c), float(tr.d), float(tr.e), float(tr.f))
        elif name == "Translate":
            mat = (1.0, 0.0, 0.0, 1.0, float(tr.x), float(tr.y or 0.0))
        elif name == "Scale":
            sx = float(tr.x)
            sy = sx if tr.y is None else float(tr.y)
            mat = (sx, 0.0, 0.0, sy, 0.0, 0.0)
        elif name == "Rotate":
            rad = math.radians(float(tr.a))
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            if tr.x is not None and tr.y is not None:
                cx = float(tr.x)
                cy = float(tr.y)
                mat = _mat_mul(
                    (1.0, 0.0, 0.0, 1.0, cx, cy),
                    _mat_mul((cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0), (1.0, 0.0, 0.0, 1.0, -cx, -cy)),
                )
            else:
                mat = (cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0)
        elif name == "SkewX":
            mat = (1.0, 0.0, math.tan(math.radians(float(tr.a))), 1.0, 0.0, 0.0)
        elif name == "SkewY":
            mat = (1.0, math.tan(math.radians(float(tr.a))), 0.0, 1.0, 0.0, 0.0)
        else:
            continue
        cur = _mat_mul(cur, mat)
    return cur


def _extract_path_points(commands: Any) -> list[tuple[float, float]]:
    if not commands:
        return []
    pts: list[tuple[float, float]] = []
    cur_x = 0.0
    cur_y = 0.0
    sub_x = 0.0
    sub_y = 0.0
    for cmd in commands:
        name = type(cmd).__name__
        if name == "MoveTo":
            cur_x, cur_y = float(cmd.x), float(cmd.y)
            sub_x, sub_y = cur_x, cur_y
            pts.append((cur_x, cur_y))
        elif name == "MoveToRel":
            cur_x += float(cmd.dx)
            cur_y += float(cmd.dy)
            sub_x, sub_y = cur_x, cur_y
            pts.append((cur_x, cur_y))
        elif name == "LineTo":
            cur_x, cur_y = float(cmd.x), float(cmd.y)
            pts.append((cur_x, cur_y))
        elif name == "LineToRel":
            cur_x += float(cmd.dx)
            cur_y += float(cmd.dy)
            pts.append((cur_x, cur_y))
        elif name == "HorizontalLineTo":
            cur_x = float(cmd.x)
            pts.append((cur_x, cur_y))
        elif name == "HorizontalLineToRel":
            cur_x += float(cmd.dx)
            pts.append((cur_x, cur_y))
        elif name == "VerticalLineTo":
            cur_y = float(cmd.y)
            pts.append((cur_x, cur_y))
        elif name == "VerticalLineToRel":
            cur_y += float(cmd.dy)
            pts.append((cur_x, cur_y))
        elif name == "CubicBezier":
            pts.extend(
                [
                    (float(cmd.x1), float(cmd.y1)),
                    (float(cmd.x2), float(cmd.y2)),
                    (float(cmd.x), float(cmd.y)),
                ]
            )
            cur_x, cur_y = float(cmd.x), float(cmd.y)
        elif name == "CubicBezierRel":
            pts.extend(
                [
                    (cur_x + float(cmd.dx1), cur_y + float(cmd.dy1)),
                    (cur_x + float(cmd.dx2), cur_y + float(cmd.dy2)),
                    (cur_x + float(cmd.dx), cur_y + float(cmd.dy)),
                ]
            )
            cur_x += float(cmd.dx)
            cur_y += float(cmd.dy)
        elif name == "SmoothCubicBezier":
            pts.extend([(float(cmd.x2), float(cmd.y2)), (float(cmd.x), float(cmd.y))])
            cur_x, cur_y = float(cmd.x), float(cmd.y)
        elif name == "SmoothCubicBezierRel":
            pts.extend(
                [
                    (cur_x + float(cmd.dx2), cur_y + float(cmd.dy2)),
                    (cur_x + float(cmd.dx), cur_y + float(cmd.dy)),
                ]
            )
            cur_x += float(cmd.dx)
            cur_y += float(cmd.dy)
        elif name == "QuadraticBezier":
            pts.extend([(float(cmd.x1), float(cmd.y1)), (float(cmd.x), float(cmd.y))])
            cur_x, cur_y = float(cmd.x), float(cmd.y)
        elif name == "QuadraticBezierRel":
            pts.extend(
                [
                    (cur_x + float(cmd.dx1), cur_y + float(cmd.dy1)),
                    (cur_x + float(cmd.dx), cur_y + float(cmd.dy)),
                ]
            )
            cur_x += float(cmd.dx)
            cur_y += float(cmd.dy)
        elif name == "SmoothQuadraticBezier":
            cur_x, cur_y = float(cmd.x), float(cmd.y)
            pts.append((cur_x, cur_y))
        elif name == "SmoothQuadraticBezierRel":
            cur_x += float(cmd.dx)
            cur_y += float(cmd.dy)
            pts.append((cur_x, cur_y))
        elif name == "Arc":
            rx = abs(float(cmd.rx))
            ry = abs(float(cmd.ry))
            nx, ny = float(cmd.x), float(cmd.y)
            mid_x = 0.5 * (cur_x + nx)
            mid_y = 0.5 * (cur_y + ny)
            pts.extend([(cur_x, cur_y), (nx, ny), (mid_x - rx, mid_y - ry), (mid_x + rx, mid_y + ry)])
            cur_x, cur_y = nx, ny
        elif name == "ArcRel":
            rx = abs(float(cmd.rx))
            ry = abs(float(cmd.ry))
            nx = cur_x + float(cmd.dx)
            ny = cur_y + float(cmd.dy)
            mid_x = 0.5 * (cur_x + nx)
            mid_y = 0.5 * (cur_y + ny)
            pts.extend([(cur_x, cur_y), (nx, ny), (mid_x - rx, mid_y - ry), (mid_x + rx, mid_y + ry)])
            cur_x, cur_y = nx, ny
        elif name == "ClosePath":
            cur_x, cur_y = sub_x, sub_y
    return pts


def _crop_svg_canvas(svg_obj: Any, *, margin: float | None = None) -> tuple[int, int, str | None]:
    """Compute a tight content bounding box for an SVG and update viewBox/width/height."""
    bounds = [math.inf, math.inf, -math.inf, -math.inf]

    def _expand_point(x: float, y: float, pad_r: float = 0.0) -> None:
        if x - pad_r < bounds[0]:
            bounds[0] = x - pad_r
        if y - pad_r < bounds[1]:
            bounds[1] = y - pad_r
        if x + pad_r > bounds[2]:
            bounds[2] = x + pad_r
        if y + pad_r > bounds[3]:
            bounds[3] = y + pad_r

    def _expand_transformed_points(
        ctm: tuple[float, float, float, float, float, float],
        points: list[tuple[float, float]],
        pad_r: float = 0.0,
    ) -> None:
        a, b, c, d, e, f = ctm
        for lx, ly in points:
            _expand_point(a * lx + c * ly + e, b * lx + d * ly + f, pad_r=pad_r)

    def _walk(node: Any, ctm: tuple[float, float, float, float, float, float]) -> None:
        cls_name = type(node).__name__
        if cls_name in _SVG_SKIP_TAGS:
            return
        local_ctm = _apply_transforms(ctm, getattr(node, "transform", None))
        scale_est = max(
            math.hypot(local_ctm[0], local_ctm[1]),
            math.hypot(local_ctm[2], local_ctm[3]),
            1.0,
        )
        stroke_w = _svg_num(getattr(node, "stroke_width", None), 0.0)
        half_stroke = 0.5 * stroke_w * scale_est

        if cls_name in ("Polygon", "Polyline"):
            pts = getattr(node, "points", None) or []
            pairs = [(float(pts[i]), float(pts[i + 1])) for i in range(0, len(pts) - 1, 2)]
            _expand_transformed_points(local_ctm, pairs, pad_r=half_stroke)
        elif cls_name == "Line":
            _expand_transformed_points(
                local_ctm,
                [
                    (_svg_num(getattr(node, "x1", 0.0)), _svg_num(getattr(node, "y1", 0.0))),
                    (_svg_num(getattr(node, "x2", 0.0)), _svg_num(getattr(node, "y2", 0.0))),
                ],
                pad_r=half_stroke,
            )
        elif cls_name == "Rect":
            w = _svg_num(getattr(node, "width", 0.0))
            h = _svg_num(getattr(node, "height", 0.0))
            if w > 0.0 or h > 0.0:
                rx = _svg_num(getattr(node, "x", 0.0))
                ry = _svg_num(getattr(node, "y", 0.0))
                _expand_transformed_points(
                    local_ctm,
                    [(rx, ry), (rx + w, ry), (rx + w, ry + h), (rx, ry + h)],
                    pad_r=half_stroke,
                )
        elif cls_name == "Circle":
            cx = _svg_num(getattr(node, "cx", 0.0))
            cy = _svg_num(getattr(node, "cy", 0.0))
            r = abs(_svg_num(getattr(node, "r", 0.0)))
            _expand_transformed_points(
                local_ctm,
                [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)],
                pad_r=half_stroke,
            )
        elif cls_name == "Ellipse":
            cx = _svg_num(getattr(node, "cx", 0.0))
            cy = _svg_num(getattr(node, "cy", 0.0))
            rx = abs(_svg_num(getattr(node, "rx", 0.0)))
            ry = abs(_svg_num(getattr(node, "ry", 0.0)))
            _expand_transformed_points(
                local_ctm,
                [(cx - rx, cy - ry), (cx + rx, cy - ry), (cx + rx, cy + ry), (cx - rx, cy + ry)],
                pad_r=half_stroke,
            )
        elif cls_name == "Path":
            pts = _extract_path_points(getattr(node, "d", None))
            _expand_transformed_points(local_ctm, pts, pad_r=half_stroke)
        elif cls_name == "Text":
            sub_spans = [
                sub for sub in (getattr(node, "elements", None) or []) if type(sub).__name__ == "TSpan"
            ]
            chunks: list[tuple[Any, str]] = []
            direct_txt = str(getattr(node, "text", None) or "")
            if direct_txt.strip():
                chunks.append((node, direct_txt))
            for span in sub_spans:
                span_txt = str(getattr(span, "text", None) or "")
                if span_txt.strip():
                    chunks.append((span, span_txt))
            for txt_node, content in chunks:
                tx = _svg_num(getattr(txt_node, "x", None), _svg_num(getattr(node, "x", 0.0)))
                ty = _svg_num(getattr(txt_node, "y", None), _svg_num(getattr(node, "y", 0.0)))
                tx += _svg_num(getattr(txt_node, "dx", None), 0.0)
                ty += _svg_num(getattr(txt_node, "dy", None), 0.0)
                fs = max(8.0, _svg_num(getattr(txt_node, "font_size", None), _svg_num(getattr(node, "font_size", None), 12.0)))
                text_w = max(fs * 0.72 * len(content.strip()), fs)
                anchor = str(getattr(txt_node, "text_anchor", None) or getattr(node, "text_anchor", None) or "start").lower()
                if anchor == "end":
                    lx0, lx1 = tx - text_w, tx
                elif anchor == "middle":
                    lx0, lx1 = tx - 0.5 * text_w, tx + 0.5 * text_w
                else:
                    lx0, lx1 = tx, tx + text_w
                baseline = str(
                    getattr(txt_node, "dominant_baseline", None)
                    or getattr(node, "dominant_baseline", None)
                    or "auto"
                ).lower()
                if baseline in ("hanging", "text-before-edge"):
                    ly0, ly1 = ty - 0.2 * fs, ty + 1.15 * fs
                elif baseline in ("middle", "central"):
                    ly0, ly1 = ty - 0.65 * fs, ty + 0.65 * fs
                else:
                    ly0, ly1 = ty - 1.15 * fs, ty + 0.35 * fs
                _expand_transformed_points(
                    local_ctm,
                    [(lx0, ly0), (lx1, ly0), (lx1, ly1), (lx0, ly1)],
                    pad_r=max(2.0, 0.15 * fs * scale_est),
                )

        if cls_name != "Text":
            for child in getattr(node, "elements", None) or []:
                _walk(child, local_ctm)

    _walk(svg_obj, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    if not all(math.isfinite(b) for b in bounds):
        orig_w = int(_svg_num(getattr(svg_obj, "width", 1600), 1600))
        orig_h = int(_svg_num(getattr(svg_obj, "height", 900), 900))
        vb = getattr(svg_obj, "viewBox", None)
        return orig_w, orig_h, str(vb) if vb is not None else None

    cw = max(1.0, bounds[2] - bounds[0])
    ch = max(1.0, bounds[3] - bounds[1])
    pad = max(0.0, float(margin)) if margin is not None else max(6.0, min(16.0, 0.015 * max(cw, ch)))
    vx = math.floor(bounds[0] - pad)
    vy = math.floor(bounds[1] - pad)
    vw = max(1, math.ceil(bounds[2] + pad) - vx)
    vh = max(1, math.ceil(bounds[3] + pad) - vy)
    svg_obj.viewBox = ViewBoxSpec(vx, vy, vw, vh)
    svg_obj.width = vw
    svg_obj.height = vh
    return vw, vh, str(svg_obj.viewBox)


def save_visualization_set(
    *,
    garden_root: str,
    visualization_set: dict[str, Any],
    name: str = "visualization_set",
    output_subdir: str = "artifacts/visualization_sets",
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a VisualizationSet dict and return a compact Garden target."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    safe_name = slugify_name(name)
    output_dir = _resolve_output_dir(garden_root_path, output_subdir)
    normalized_vis_set = _normalize_visualization_set_dict(visualization_set)
    VisualizationSet.from_dict(normalized_vis_set)
    vis_set_path = (output_dir / f"{safe_name}.json").resolve()
    vis_set_path.relative_to(garden_root_path)
    with vis_set_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(normalized_vis_set, handle)
        handle.write("\n")

    artifact_path = to_posix_relative(vis_set_path, garden_root_path)
    artifact_source = {
        "visualization_set_identifier": normalized_vis_set.get("identifier"),
        "visualization_set_display_name": normalized_vis_set.get("display_name"),
        **(source or {}),
    }
    source_run_id = _extract_source_run_id(
        visualization_set=normalized_vis_set,
        explicit_source=artifact_source,
    )
    if source_run_id is not None:
        artifact_source.setdefault("source_run_id", source_run_id)
    artifact = _register_artifact(
        manifest,
        artifact_type=VISUALIZATION_SET_ARTIFACT_TYPE,
        name=safe_name,
        path=artifact_path,
        source=artifact_source,
    )
    manifest.write(garden_root_path)
    target = _visualization_set_target(
        manifest=manifest,
        identifier=safe_name,
        path=artifact_path,
    )
    return {
        "target": target,
        "visualization_set_target": target,
        "artifact": artifact,
        "persistence_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=VISUALIZATION_SET_ARTIFACT_TYPE,
            artifact_path=artifact_path,
            absolute_path=str(vis_set_path),
            source=artifact_source,
        ),
    }


def _read_visualization_set_target_json(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    visualization_set_target: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(visualization_set_target, dict):
        raise ValueError("visualization_set_target must be a dictionary.")
    target_type = visualization_set_target.get("target_type")
    target_path = visualization_set_target.get("path")
    if target_type != VISUALIZATION_SET_TARGET_TYPE:
        raise ValueError(
            "visualization_set_target target_type must be "
            f"{VISUALIZATION_SET_TARGET_TYPE!r}; got {target_type!r}."
        )
    garden_id = visualization_set_target.get("garden_id")
    if garden_id != manifest.garden_id:
        raise ValueError("visualization_set_target garden_id does not match the Garden root.")
    if not isinstance(target_path, str) or not target_path:
        raise ValueError("visualization_set_target requires a Garden-relative path.")
    vis_set_path = (garden_root_path / target_path).resolve()
    vis_set_path.relative_to(garden_root_path)
    if not vis_set_path.is_file():
        raise ValueError(f"VisualizationSet target file was not found: {target_path}")
    with vis_set_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_visualization_set(
    *,
    garden_root: str,
    visualization_set_target: dict[str, Any],
) -> dict[str, Any]:
    """Load a Garden-backed VisualizationSet target."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    visualization_set = _normalize_visualization_set_dict(
        _read_visualization_set_target_json(
            garden_root_path=garden_root_path,
            manifest=manifest,
            visualization_set_target=visualization_set_target,
        )
    )
    VisualizationSet.from_dict(visualization_set)
    return visualization_set


def _resolve_visualization_set_input(
    *,
    garden_root: str,
    visualization_set: dict[str, Any] | None,
    visualization_set_target: dict[str, Any] | None,
) -> dict[str, Any]:
    has_dict = visualization_set is not None
    has_target = visualization_set_target is not None
    if has_dict == has_target:
        raise ValueError(
            "Provide exactly one of visualization_set or visualization_set_target."
        )
    if has_dict:
        if not isinstance(visualization_set, dict):
            raise ValueError("visualization_set must be a dictionary.")
        return _normalize_visualization_set_dict(visualization_set)
    return load_visualization_set(
        garden_root=garden_root,
        visualization_set_target=visualization_set_target or {},
    )


def _resolve_visualization_set_and_obj(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    visualization_set: dict[str, Any] | None,
    visualization_set_target: dict[str, Any] | None,
) -> tuple[dict[str, Any], VisualizationSet, str | None]:
    has_dict = visualization_set is not None
    has_target = visualization_set_target is not None
    if has_dict == has_target:
        raise ValueError(
            "Provide exactly one of visualization_set or visualization_set_target."
        )
    if has_dict:
        if not isinstance(visualization_set, dict):
            raise ValueError("visualization_set must be a dictionary.")
        raw_dict = _normalize_visualization_set_dict(visualization_set)
    else:
        raw_dict = _normalize_visualization_set_dict(
            _read_visualization_set_target_json(
                garden_root_path=garden_root_path,
                manifest=manifest,
                visualization_set_target=visualization_set_target or {},
            )
        )
    vis_set = VisualizationSet.from_dict(raw_dict)
    source_run_id = _extract_source_run_id(
        visualization_set=raw_dict,
        visualization_set_target=visualization_set_target,
        manifest=manifest,
    )
    return raw_dict, vis_set, source_run_id


def _resolve_view_arg(view: str | dict[str, Any] | Plane) -> tuple[str | Plane, Any]:
    if isinstance(view, Plane):
        return view, view.to_dict()
    if isinstance(view, dict):
        data = dict(view)
        data.setdefault("type", "Plane")
        try:
            plane = Plane.from_dict(data)
        except Exception as exc:
            raise ValueError(f"Invalid view Plane dict: {exc}") from exc
        return plane, plane.to_dict()
    view_text = str(view).strip()
    normalized_view = (
        view_text.upper()
        if view_text.lower() in {"ne", "nw", "se", "sw"}
        else view_text.title()
    )
    if normalized_view not in SVG_VIEWS:
        allowed = ", ".join(sorted(SVG_VIEWS))
        raise ValueError(f"Unsupported view: {view}. Allowed values: {allowed}, or a Plane dict.")
    return normalized_view, normalized_view


def _resolve_view_plane(view: str | dict[str, Any] | Plane) -> tuple[Plane, bool, Any]:
    resolved, view_meta = _resolve_view_arg(view)
    if isinstance(resolved, Plane):
        is_top = resolved == Plane()
        return resolved, is_top, view_meta
    plane = VisualizationSet.VIEW_MAP[resolved]
    return plane, resolved == "Top", view_meta


def _persist_exported_artifact(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    artifact_type: str,
    safe_name: str,
    output_path: Path,
    source: dict[str, Any],
    message: str,
    extra_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_path = output_path.resolve()
    resolved_path.relative_to(garden_root_path)
    artifact_path = to_posix_relative(resolved_path, garden_root_path)
    artifact = _register_artifact(
        manifest,
        artifact_type=artifact_type,
        name=safe_name,
        path=artifact_path,
        source=source,
    )
    manifest.write(garden_root_path)
    summary_view = {
        "garden_target": manifest.target(),
        "artifact": artifact,
        "artifact_name": safe_name,
        "artifact_path": artifact_path,
        "artifact_type": artifact_type,
        "exists": resolved_path.is_file(),
        **(extra_summary or {}),
    }
    if source.get("source_run_id"):
        summary_view.setdefault("source_run_id", source["source_run_id"])
    return {
        "artifact_name": safe_name,
        "artifact_path": artifact_path,
        "artifact_type": artifact_type,
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=artifact_type,
            artifact_path=artifact_path,
            absolute_path=str(resolved_path),
            source=source,
        ),
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message=message,
            details={"artifact_path": artifact_path},
        ),
    }


def visualization_set_to_html(
    *,
    garden_root: str,
    visualization_set: dict[str, Any] | None = None,
    visualization_set_target: dict[str, Any] | None = None,
    name: str = "visualization_set",
    output_subdir: str = "artifacts/visualization/html",
    open: bool = False,
) -> dict[str, Any]:
    """Export a VisualizationSet dict to a Garden HTML artifact."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    safe_name = slugify_name(name)
    output_dir = _resolve_output_dir(garden_root_path, output_subdir)

    visualization_set, vis_set, source_run_id = _resolve_visualization_set_and_obj(
        garden_root_path=garden_root_path,
        manifest=manifest,
        visualization_set=visualization_set,
        visualization_set_target=visualization_set_target,
    )
    html_path = Path(
        vis_set.to_html(
            output_folder=str(output_dir),
            file_name=safe_name,
            open=open,
        )
    )
    source: dict[str, Any] = {
        "visualization_set_identifier": visualization_set.get("identifier"),
        "visualization_set_display_name": visualization_set.get("display_name"),
    }
    if source_run_id is not None:
        source["source_run_id"] = source_run_id
    return _persist_exported_artifact(
        garden_root_path=garden_root_path,
        manifest=manifest,
        artifact_type=HTML_ARTIFACT_TYPE,
        safe_name=safe_name,
        output_path=html_path,
        source=source,
        message="VisualizationSet HTML artifact exported.",
    )


def visualization_set_to_vtkjs(
    *,
    garden_root: str,
    visualization_set: dict[str, Any] | None = None,
    visualization_set_target: dict[str, Any] | None = None,
    name: str = "visualization_set",
    output_subdir: str = "artifacts/visualization/vtkjs",
) -> dict[str, Any]:
    """Export a VisualizationSet dict to a Garden vtkjs artifact."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    safe_name = slugify_name(name)
    output_dir = _resolve_output_dir(garden_root_path, output_subdir)

    visualization_set, vis_set, source_run_id = _resolve_visualization_set_and_obj(
        garden_root_path=garden_root_path,
        manifest=manifest,
        visualization_set=visualization_set,
        visualization_set_target=visualization_set_target,
    )
    vtkjs_path = Path(
        vis_set.to_vtkjs(
            output_folder=str(output_dir),
            file_name=safe_name,
        )
    )
    source: dict[str, Any] = {
        "visualization_set_identifier": visualization_set.get("identifier"),
        "visualization_set_display_name": visualization_set.get("display_name"),
    }
    if source_run_id is not None:
        source["source_run_id"] = source_run_id
    return _persist_exported_artifact(
        garden_root_path=garden_root_path,
        manifest=manifest,
        artifact_type=VTKJS_ARTIFACT_TYPE,
        safe_name=safe_name,
        output_path=vtkjs_path,
        source=source,
        message="VisualizationSet vtkjs artifact exported.",
    )


def visualization_set_to_svg(
    *,
    garden_root: str,
    visualization_set: dict[str, Any] | None = None,
    visualization_set_target: dict[str, Any] | None = None,
    width: int = 1600,
    height: int = 900,
    margin: float | None = None,
    view: str | dict[str, Any] = "Top",
    interactive: bool = False,
    render_2d_legend: bool = True,
    render_3d_legend: bool = False,
    auto_crop: bool = True,
    name: str = "visualization_set",
    output_subdir: str = "artifacts/visualization/svg",
) -> dict[str, Any]:
    """Export a VisualizationSet dict to a Garden SVG artifact."""
    if width <= 0 or height <= 0:
        raise ValueError("SVG width and height must be positive integers.")
    if margin is not None and margin < 0:
        raise ValueError("SVG margin must be non-negative.")
    resolved_view, view_meta = _resolve_view_arg(view)

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    safe_name = slugify_name(name)
    output_dir = _resolve_output_dir(garden_root_path, output_subdir)

    visualization_set, vis_set, source_run_id = _resolve_visualization_set_and_obj(
        garden_root_path=garden_root_path,
        manifest=manifest,
        visualization_set=visualization_set,
        visualization_set_target=visualization_set_target,
    )
    with _fast_svg_group_child():
        svg = vis_set.to_svg(
            width=width,
            height=height,
            margin=margin,
            interactive=interactive,
            render_3d_legend=render_3d_legend,
            render_2d_legend=render_2d_legend,
            view=resolved_view,
        )
    if auto_crop:
        actual_w, actual_h, view_box_str = _crop_svg_canvas(svg, margin=margin)
    else:
        actual_w, actual_h = width, height
        vb = getattr(svg, "viewBox", None)
        view_box_str = str(vb) if vb is not None else None
    svg_path = (output_dir / f"{safe_name}.svg").resolve()
    svg_path.relative_to(garden_root_path)
    svg_path.write_text(svg.as_str(), encoding="utf-8")

    source: dict[str, Any] = {
        "visualization_set_identifier": visualization_set.get("identifier"),
        "visualization_set_display_name": visualization_set.get("display_name"),
        "view": view_meta,
        "width": actual_w,
        "height": actual_h,
        "canvas_width": width,
        "canvas_height": height,
        "margin": margin,
        "interactive": interactive,
        "render_2d_legend": render_2d_legend,
        "render_3d_legend": render_3d_legend,
        "auto_crop": auto_crop,
        "view_box": view_box_str,
    }
    if source_run_id is not None:
        source["source_run_id"] = source_run_id
    return _persist_exported_artifact(
        garden_root_path=garden_root_path,
        manifest=manifest,
        artifact_type=SVG_ARTIFACT_TYPE,
        safe_name=safe_name,
        output_path=svg_path,
        source=source,
        message="VisualizationSet SVG artifact exported.",
        extra_summary={
            "view": view_meta,
            "width": actual_w,
            "height": actual_h,
            "canvas_width": width,
            "canvas_height": height,
            "margin": margin,
            "auto_crop": auto_crop,
            "view_box": view_box_str,
        },
    )


def _apply_rgb_colors_to_polydata(
    poly_data: Any,
    colors: list[Any],
    *,
    per_face: bool,
) -> None:
    import vtk

    arr = vtk.vtkUnsignedCharArray()
    arr.SetNumberOfComponents(3)
    arr.SetName("RGB")
    for col in colors:
        arr.InsertNextTuple3(int(col.r), int(col.g), int(col.b))
    if per_face:
        poly_data.GetCellData().SetScalars(arr)
    else:
        poly_data.GetPointData().SetScalars(arr)


def _build_analysis_actors(
    geo: AnalysisGeometry,
) -> tuple[list[Any], Legend | None]:
    import vtk

    display_pd = DisplayPolyData.from_analysis_geometry(geo)
    if display_pd is None or not display_pd.polydata:
        return [], None

    legend_obj: Legend | None = None
    value_colors: list[Any] = []
    if geo.data_sets:
        active_idx = geo.active_data if geo.active_data is not None else 0
        if 0 <= active_idx < len(geo.data_sets):
            active_ds = geo.data_sets[active_idx]
            vals = list(active_ds.values)
            if vals:
                legend_obj = Legend(vals, active_ds.legend_parameters)
                value_colors = list(legend_obj.value_colors)

    poly_datas = display_pd.polydata
    geometries = geo.geometry
    matching_method = geo.matching_method
    all_points = len(poly_datas) == 1 and len(geometries) > 0 and all(
        hasattr(g, "x") and hasattr(g, "y") and hasattr(g, "z") and not hasattr(g, "faces")
        for g in geometries
    )
    if value_colors:
        if all_points and len(value_colors) == poly_datas[0].GetNumberOfPoints():
            _apply_rgb_colors_to_polydata(poly_datas[0], value_colors, per_face=False)
        elif matching_method == "geometries" and len(poly_datas) == len(value_colors):
            for pd_item, col in zip(poly_datas, value_colors):
                n_cells = pd_item.GetNumberOfCells()
                if n_cells > 0:
                    _apply_rgb_colors_to_polydata(pd_item, [col] * n_cells, per_face=True)
        elif len(poly_datas) == 1:
            pd_item = poly_datas[0]
            if matching_method == "vertices" and len(value_colors) == pd_item.GetNumberOfPoints():
                _apply_rgb_colors_to_polydata(pd_item, value_colors, per_face=False)
            elif len(value_colors) == pd_item.GetNumberOfCells():
                _apply_rgb_colors_to_polydata(pd_item, value_colors, per_face=True)
            elif len(value_colors) == pd_item.GetNumberOfPoints():
                _apply_rgb_colors_to_polydata(pd_item, value_colors, per_face=False)
        else:
            offset = 0
            for pd_item in poly_datas:
                use_verts = matching_method == "vertices"
                count = pd_item.GetNumberOfPoints() if use_verts else pd_item.GetNumberOfCells()
                chunk = value_colors[offset : offset + count]
                offset += count
                if len(chunk) == count and count > 0:
                    _apply_rgb_colors_to_polydata(pd_item, chunk, per_face=not use_verts)

    actors: list[Any] = []
    for pd_item in poly_datas:
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(pd_item)
        if value_colors:
            mapper.SetColorModeToDirectScalars()
            mapper.ScalarVisibilityOn()
        else:
            mapper.ScalarVisibilityOff()
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetColor(
            display_pd.color.r / 255.0,
            display_pd.color.g / 255.0,
            display_pd.color.b / 255.0,
        )
        prop.SetOpacity(display_pd.color.a / 255.0)
        if display_pd.display_mode == DisplayMode.SurfaceWithEdges:
            prop.EdgeVisibilityOn()
            prop.SetEdgeColor(0.2, 0.2, 0.2)
        elif display_pd.display_mode == DisplayMode.Wireframe:
            prop.SetRepresentationToWireframe()
        elif display_pd.display_mode == DisplayMode.Points:
            prop.SetRepresentationToPoints()
            prop.SetPointSize(6.0)
        actors.append(actor)
    return actors, legend_obj


def _build_context_actors(geo: ContextGeometry) -> list[Any]:
    import vtk

    display_pd = DisplayPolyData.from_context_geometry(geo)
    if display_pd is None or not display_pd.polydata:
        return []
    poly_datas = display_pd.polydata
    sub_geos = list(geo.geometry)
    actors: list[Any] = []
    for idx, pd_item in enumerate(poly_datas):
        sub_geo = sub_geos[idx] if len(poly_datas) == len(sub_geos) else None
        col = getattr(sub_geo, "color", None) or display_pd.color
        sub_mode = getattr(sub_geo, "display_mode", None)
        line_width = getattr(sub_geo, "line_width", None)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(pd_item)
        mapper.ScalarVisibilityOff()
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetColor(col.r / 255.0, col.g / 255.0, col.b / 255.0)
        prop.SetOpacity(col.a / 255.0)
        if isinstance(line_width, (int, float)) and line_width > 0:
            prop.SetLineWidth(float(line_width))
        if sub_mode == "Wireframe" or display_pd.display_mode == DisplayMode.Wireframe:
            prop.SetRepresentationToWireframe()
        elif sub_mode == "SurfaceWithEdges" or display_pd.display_mode == DisplayMode.SurfaceWithEdges:
            prop.EdgeVisibilityOn()
            prop.SetEdgeColor(0.15, 0.15, 0.15)
        elif sub_mode == "Points" or display_pd.display_mode == DisplayMode.Points:
            prop.SetRepresentationToPoints()
            prop.SetPointSize(6.0)
        actors.append(actor)
    return actors


def _draw_2d_legend_overlay(image: Any, legend_obj: Legend, *, width: int, height: int) -> Any:
    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    l_par = legend_obj.legend_parameters
    seg_colors = list(legend_obj.segment_colors)
    seg_texts = list(legend_obj.segment_text)
    if not seg_colors:
        return image

    margin_x = max(18, int(width * 0.02))
    margin_y = max(24, int(height * 0.05))
    box_w = max(20, min(36, int(width * 0.022)))
    max_total_h = max(120, int(height * 0.65))
    seg_h = max(14, min(36, max_total_h // max(len(seg_colors), 1)))
    title = str(l_par.title or "").strip()

    if title:
        draw.text((margin_x, max(6, margin_y - 18)), title, fill=(20, 20, 20), font=font)

    for idx, col in enumerate(reversed(seg_colors)):
        y0 = margin_y + idx * seg_h
        y1 = y0 + seg_h
        draw.rectangle(
            [margin_x, y0, margin_x + box_w, y1],
            fill=(int(col.r), int(col.g), int(col.b)),
            outline=(40, 40, 40),
            width=1,
        )
    for idx, label in enumerate(reversed(seg_texts)):
        y_pos = margin_y + int((idx + 0.5) * seg_h) - 5
        draw.text((margin_x + box_w + 8, y_pos), str(label), fill=(20, 20, 20), font=font)
    return image


def _render_png_vtk(
    vis_set: VisualizationSet,
    *,
    width: int,
    height: int,
    view: str | dict[str, Any],
    render_2d_legend: bool,
) -> Any:
    if sys.platform == "darwin" and threading.current_thread() is not threading.main_thread():
        raise RuntimeError("VTK's Cocoa render window requires the macOS main thread.")
    if sys.platform == "linux" and not (
        os.environ.get("DISPLAY") or find_library("EGL") or find_library("OSMesa")
    ):
        raise RuntimeError("VTK offscreen rendering requires a display, EGL, or OSMesa.")

    import numpy as np
    from PIL import Image
    import vtk

    view_plane, is_top, _ = _resolve_view_plane(view)
    ren = vtk.vtkRenderer()
    ren.SetBackground(1.0, 1.0, 1.0)
    ren_win = vtk.vtkRenderWindow()
    ren_win.SetOffScreenRendering(1)
    ren_win.SetSize(int(width), int(height))
    ren_win.AddRenderer(ren)

    legend_for_overlay: Legend | None = None
    actor_count = 0
    for geo in vis_set.geometry:
        if getattr(geo, "hidden", False):
            continue
        if isinstance(geo, AnalysisGeometry):
            actors, leg = _build_analysis_actors(geo)
            if leg is not None:
                legend_for_overlay = leg
        elif isinstance(geo, ContextGeometry):
            actors = _build_context_actors(geo)
        else:
            actors = []
        for actor in actors:
            ren.AddActor(actor)
            actor_count += 1

    if actor_count > 0:
        bounds = ren.ComputeVisiblePropBounds()
        cx = 0.5 * (bounds[0] + bounds[1])
        cy = 0.5 * (bounds[2] + bounds[3])
        cz = 0.5 * (bounds[4] + bounds[5])
        dx = bounds[1] - bounds[0]
        dy = bounds[3] - bounds[2]
        dz = bounds[5] - bounds[4]
        diag = max((dx * dx + dy * dy + dz * dz) ** 0.5, 1.0)
        cam = ren.GetActiveCamera()
        n = view_plane.n.normalize()
        up = view_plane.y.normalize()
        if abs(n.dot(up)) > 0.999:
            up = Vector3D(0, 1, 0) if abs(n.y) < 0.9 else Vector3D(0, 0, 1)
        cam.SetFocalPoint(cx, cy, cz)
        cam.SetPosition(cx + n.x * diag * 2.0, cy + n.y * diag * 2.0, cz + n.z * diag * 2.0)
        cam.SetViewUp(up.x, up.y, up.z)
        if is_top or dz < 1e-6 * diag:
            cam.ParallelProjectionOn()
        ren.ResetCamera()
        ren.ResetCameraClippingRange()

    ren_win.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(ren_win)
    w2i.SetInputBufferTypeToRGB()
    w2i.ReadFrontBufferOff()
    w2i.Update()
    vtk_img = w2i.GetOutput()
    dims = vtk_img.GetDimensions()
    scalars = vtk_img.GetPointData().GetScalars()
    if dims[0] <= 0 or dims[1] <= 0 or scalars is None:
        raise RuntimeError("VTK offscreen render produced an empty image.")
    from vtk.util.numpy_support import vtk_to_numpy

    arr = vtk_to_numpy(scalars).reshape(dims[1], dims[0], -1)
    arr = np.flipud(arr)
    image = Image.fromarray(arr[:, :, :3].astype("uint8"), mode="RGB")
    if render_2d_legend and legend_for_overlay is not None:
        image = _draw_2d_legend_overlay(image, legend_for_overlay, width=width, height=height)
    ren_win.Finalize()
    return image


def _render_png_matplotlib_fallback(
    vis_set: VisualizationSet,
    *,
    width: int,
    height: int,
    view: str | dict[str, Any],
) -> Any:
    import io
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from PIL import Image

    view_plane, is_top, _ = _resolve_view_plane(view)
    dpi = 100
    fig = Figure(figsize=(width / dpi, height / dpi), dpi=dpi)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.set_facecolor("white")
    ax.set_aspect("equal", adjustable="datalim")
    for geo in vis_set.geometry:
        if getattr(geo, "hidden", False):
            continue
        for sub in geo.geometry:
            verts = getattr(sub, "vertices", None)
            if verts:
                pts = [
                    (pt.x, pt.y) if is_top else (view_plane.xyz_to_xy(pt).x, view_plane.xyz_to_xy(pt).y)
                    for pt in verts
                ]
                xs = [p[0] for p in pts] + [pts[0][0]]
                ys = [p[1] for p in pts] + [pts[0][1]]
                ax.plot(xs, ys, color="#333333", linewidth=0.8)
    ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def visualization_set_to_png(
    *,
    garden_root: str,
    visualization_set: dict[str, Any] | None = None,
    visualization_set_target: dict[str, Any] | None = None,
    width: int = 1600,
    height: int = 900,
    view: str | dict[str, Any] = "Top",
    render_2d_legend: bool = True,
    name: str = "visualization_set",
    output_subdir: str = "artifacts/visualization/png",
) -> dict[str, Any]:
    """Render a VisualizationSet offscreen to a PNG raster artifact."""
    if width <= 0 or height <= 0:
        raise ValueError("PNG width and height must be positive integers.")
    _, _, view_meta = _resolve_view_plane(view)

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    safe_name = slugify_name(name)
    output_dir = _resolve_output_dir(garden_root_path, output_subdir)

    visualization_set, vis_set, source_run_id = _resolve_visualization_set_and_obj(
        garden_root_path=garden_root_path,
        manifest=manifest,
        visualization_set=visualization_set,
        visualization_set_target=visualization_set_target,
    )
    png_path = (output_dir / f"{safe_name}.png").resolve()
    png_path.relative_to(garden_root_path)

    renderer_used = "vtk_offscreen"
    try:
        image = _render_png_vtk(
            vis_set,
            width=width,
            height=height,
            view=view,
            render_2d_legend=render_2d_legend,
        )
    except Exception:
        renderer_used = "matplotlib_fallback"
        image = _render_png_matplotlib_fallback(
            vis_set,
            width=width,
            height=height,
            view=view,
        )
    image.save(png_path, format="PNG")

    source: dict[str, Any] = {
        "visualization_set_identifier": visualization_set.get("identifier"),
        "visualization_set_display_name": visualization_set.get("display_name"),
        "view": view_meta,
        "width": width,
        "height": height,
        "render_2d_legend": render_2d_legend,
        "renderer": renderer_used,
    }
    if source_run_id is not None:
        source["source_run_id"] = source_run_id
    return _persist_exported_artifact(
        garden_root_path=garden_root_path,
        manifest=manifest,
        artifact_type=PNG_ARTIFACT_TYPE,
        safe_name=safe_name,
        output_path=png_path,
        source=source,
        message="VisualizationSet PNG artifact exported.",
        extra_summary={
            "view": view_meta,
            "width": width,
            "height": height,
            "renderer": renderer_used,
        },
    )


def visualization_set_to_vtk_file(
    *,
    garden_root: str,
    export_format: str,
    visualization_set: dict[str, Any] | None = None,
    visualization_set_target: dict[str, Any] | None = None,
    name: str = "visualization_set",
    output_subdir: str | None = None,
) -> dict[str, Any]:
    """Export a VisualizationSet to legacy .vtk or binary .vtp polydata."""
    fmt = export_format.strip().lower()
    if fmt not in {"vtk", "vtp"}:
        raise ValueError("export_format must be 'vtk' or 'vtp'.")
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    safe_name = slugify_name(name)
    output_dir = _resolve_output_dir(
        garden_root_path, output_subdir or f"artifacts/visualization/{fmt}"
    )

    visualization_set, vis_set, source_run_id = _resolve_visualization_set_and_obj(
        garden_root_path=garden_root_path,
        manifest=manifest,
        visualization_set=visualization_set,
        visualization_set_target=visualization_set_target,
    )
    polydatas = []
    for geo in vis_set.geometry:
        dp = DisplayPolyData.from_visualization_geometry(geo)
        if dp is not None and dp.polydata:
            polydatas.extend(dp.polydata)
    if not polydatas:
        raise ValueError("VisualizationSet contains no geometry convertible to VTK polydata.")
    polydata_or_append = polydatas[0] if len(polydatas) == 1 else JoinedPolyData.from_polydata(polydatas)
    writer = VTKWriters.legacy if fmt == "vtk" else VTKWriters.binary
    written_path = Path(write_to_file(polydata_or_append, str(output_dir), safe_name, writer=writer))
    artifact_type = VTK_ARTIFACT_TYPE if fmt == "vtk" else VTP_ARTIFACT_TYPE
    source: dict[str, Any] = {
        "visualization_set_identifier": visualization_set.get("identifier"),
        "visualization_set_display_name": visualization_set.get("display_name"),
        "vtk_format": fmt,
    }
    if source_run_id is not None:
        source["source_run_id"] = source_run_id
    return _persist_exported_artifact(
        garden_root_path=garden_root_path,
        manifest=manifest,
        artifact_type=artifact_type,
        safe_name=safe_name,
        output_path=written_path,
        source=source,
        message=f"VisualizationSet {fmt.upper()} artifact exported.",
    )


def visualization_set_to_native_file(
    *,
    garden_root: str,
    export_format: str,
    visualization_set: dict[str, Any] | None = None,
    visualization_set_target: dict[str, Any] | None = None,
    name: str = "visualization_set",
    output_subdir: str | None = None,
) -> dict[str, Any]:
    """Export a VisualizationSet to .vsf (JSON) or .pkl (binary pickle)."""
    fmt = export_format.strip().lower()
    if fmt not in {"vsf", "pkl"}:
        raise ValueError("export_format must be 'vsf' or 'pkl'.")
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    safe_name = slugify_name(name)
    output_dir = _resolve_output_dir(
        garden_root_path, output_subdir or f"artifacts/visualization/{fmt}"
    )

    visualization_set, vis_set, source_run_id = _resolve_visualization_set_and_obj(
        garden_root_path=garden_root_path,
        manifest=manifest,
        visualization_set=visualization_set,
        visualization_set_target=visualization_set_target,
    )
    if fmt == "vsf":
        written_path = Path(vis_set.to_json(f"{safe_name}.vsf", str(output_dir)))
        artifact_type = VSF_ARTIFACT_TYPE
    else:
        written_path = Path(vis_set.to_pkl(f"{safe_name}.pkl", str(output_dir)))
        artifact_type = PKL_ARTIFACT_TYPE
    source: dict[str, Any] = {
        "visualization_set_identifier": visualization_set.get("identifier"),
        "visualization_set_display_name": visualization_set.get("display_name"),
        "file_format": fmt,
    }
    if source_run_id is not None:
        source["source_run_id"] = source_run_id
    return _persist_exported_artifact(
        garden_root_path=garden_root_path,
        manifest=manifest,
        artifact_type=artifact_type,
        safe_name=safe_name,
        output_path=written_path,
        source=source,
        message=f"VisualizationSet {fmt.upper()} artifact exported.",
    )


_HELPER_LEGEND_KEYS = {
    "title",
    "segment_count",
    "decimal_count",
    "minimum",
    "maximum",
    "position_2d",
    "dimensions_2d",
    "orientation",
    "color_set",
    "properties_3d",
}
_SDK_LEGEND_KEYS = {
    "min",
    "max",
    "segment_count",
    "colors",
    "title",
    "continuous_legend",
    "font",
    "font_size",
    "decimal_count",
    "include_larger_smaller",
    "vertical",
    "base_plane",
    "segment_height",
    "segment_width",
    "text_gap",
    "properties_2d",
    "properties_3d",
    "user_data",
}
_CATEGORIZED_KEYS = {"domain", "category_names", "continuous_colors"}


def _normalize_position_2d(
    value: Any,
    raw: dict[str, Any] | None = None,
) -> Any:
    if value is None and isinstance(raw, dict):
        extracted: dict[str, Any] = {}
        if "origin_x" in raw and raw["origin_x"] is not None:
            extracted["origin_x"] = raw["origin_x"]
        elif "originx" in raw and raw["originx"] is not None:
            extracted["origin_x"] = raw["originx"]
        if "origin_y" in raw and raw["origin_y"] is not None:
            extracted["origin_y"] = raw["origin_y"]
        elif "originy" in raw and raw["originy"] is not None:
            extracted["origin_y"] = raw["originy"]
        return extracted or None
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    if "originx" in normalized and "origin_x" not in normalized:
        normalized["origin_x"] = normalized.pop("originx")
    if "originy" in normalized and "origin_y" not in normalized:
        normalized["origin_y"] = normalized.pop("originy")
    return normalized


def _extract_properties_3d(raw: dict[str, Any]) -> dict[str, Any] | None:
    prop3d = raw.get("properties_3d")
    if isinstance(prop3d, dict):
        return legend_3d_parameter_from_dict(prop3d).to_dict()
    inline_3d: dict[str, Any] = {}
    for k in ("base_plane", "segment_height", "segment_width", "text_height"):
        val = raw.get(k)
        if val is None or isinstance(val, str):
            continue
        inline_3d[k] = val
    if inline_3d:
        return legend_3d_parameter_from_dict(inline_3d).to_dict()
    return None


def _normalize_dimensions_2d(raw: dict[str, Any]) -> Any:
    dims = raw.get("dimensions_2d")
    if isinstance(dims, dict):
        return dict(dims)
    extracted: dict[str, Any] = {}
    for k in ("segment_height", "segment_width", "text_height"):
        val = raw.get(k)
        if isinstance(val, str) and val.strip():
            extracted[k] = val.strip()
    return extracted or dims


def _normalize_properties_2d_dict(prop2d: Any) -> Any:
    if not isinstance(prop2d, dict):
        return prop2d
    normalized = dict(prop2d)
    if not normalized.get("type"):
        normalized["type"] = "Legend2DParameters"
    return normalized


def coerce_legend_parameter_dict(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Normalize LegendParameters, LegendParametersCategorized, or Legend3DParameters dicts."""
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("legend_parameter must be a dictionary.")
    raw = data.get("object_dict") if isinstance(data.get("object_dict"), dict) else data
    raw = dict(raw)
    explicit_type = raw.get("type")
    if isinstance(explicit_type, str) and not explicit_type.strip():
        explicit_type = None
        raw.pop("type", None)
    elif explicit_type is None and "type" in raw:
        raw.pop("type", None)

    if isinstance(raw.get("properties_2d"), dict):
        raw["properties_2d"] = _normalize_properties_2d_dict(raw["properties_2d"])

    if explicit_type == "Legend3DParameters":
        return legend_parameter_from_dict(raw).to_dict()

    if explicit_type == "LegendParametersCategorized" or (
        explicit_type is None and "domain" in raw and raw["domain"] is not None
    ):
        cat_dict = dict(raw)
        cat_dict["type"] = "LegendParametersCategorized"
        if not cat_dict.get("colors"):
            domain = cat_dict.get("domain") or []
            n_colors = (len(domain) + 1) if isinstance(domain, list) else 2
            if cat_dict.get("color_set"):
                palette = resolve_colorset(str(cat_dict["color_set"]))
            else:
                palette = list(Colorset.original())
            sampled = (
                palette[:n_colors]
                if len(palette) >= n_colors
                else [palette[i % len(palette)] for i in range(n_colors)]
            )
            cat_dict["colors"] = [c.to_dict() for c in sampled]
        if "properties_3d" in cat_dict and isinstance(cat_dict["properties_3d"], dict):
            cat_dict["properties_3d"] = legend_3d_parameter_from_dict(
                cat_dict["properties_3d"]
            ).to_dict()
        else:
            extracted_cat_3d = _extract_properties_3d(cat_dict)
            if extracted_cat_3d is not None:
                cat_dict["properties_3d"] = extracted_cat_3d
        dims_2d = _normalize_dimensions_2d(raw)
        legend_obj = legend_parameter_from_dict(cat_dict)
        if dims_2d is not None or any(
            k in raw and raw[k] is not None
            for k in ("position_2d", "dimensions_2d", "orientation", "origin_x", "origin_y", "color_set")
        ):
            edited = edit_2d_legend_parameter(
                legend_parameter=legend_obj.to_dict(),
                title=raw.get("title"),
                decimal_count=raw.get("decimal_count"),
                position_2d=_normalize_position_2d(raw.get("position_2d"), raw),
                dimensions_2d=dims_2d,
                orientation=raw.get("orientation"),
                color_set=raw.get("color_set") if not raw.get("colors") else None,
                properties_3d=_extract_properties_3d(raw),
            )
            return dict(edited["object_dict"])
        return legend_obj.to_dict()

    if explicit_type is not None and explicit_type != "LegendParameters":
        raise ValueError(
            "legend_parameter.type must be 'LegendParameters', 'LegendParametersCategorized', "
            "or 'Legend3DParameters'."
        )

    normalized_pos_2d = _normalize_position_2d(raw.get("position_2d"), raw)
    normalized_dims_2d = _normalize_dimensions_2d(raw)
    extracted_3d = _extract_properties_3d(raw)

    if explicit_type == "LegendParameters":
        override_keys = {
            k: v
            for k, v in raw.items()
            if (
                (k in _HELPER_LEGEND_KEYS and k not in {"title", "segment_count", "decimal_count"})
                or k in {"origin_x", "origin_y", "originx", "originy"}
                or (k in {"segment_height", "segment_width", "text_height"} and isinstance(v, str))
            )
        }
        base_dict = {k: v for k, v in raw.items() if k == "type" or k in _SDK_LEGEND_KEYS}
        if isinstance(base_dict.get("properties_3d"), dict):
            base_dict["properties_3d"] = legend_3d_parameter_from_dict(
                base_dict["properties_3d"]
            ).to_dict()
        if not override_keys:
            return legend_parameter_from_dict(base_dict).to_dict()
        edited = edit_2d_legend_parameter(
            legend_parameter=base_dict,
            title=raw.get("title"),
            segment_count=raw.get("segment_count"),
            decimal_count=raw.get("decimal_count"),
            minimum=raw.get("minimum"),
            maximum=raw.get("maximum"),
            position_2d=normalized_pos_2d,
            dimensions_2d=normalized_dims_2d,
            orientation=raw.get("orientation"),
            color_set=raw.get("color_set"),
            properties_3d=extracted_3d,
        )
        return dict(edited["object_dict"])

    created = create_2d_legend_parameter(
        title=raw.get("title"),
        segment_count=raw.get("segment_count"),
        decimal_count=raw.get("decimal_count"),
        minimum=raw.get("minimum", raw.get("min")),
        maximum=raw.get("maximum", raw.get("max")),
        position_2d=normalized_pos_2d,
        dimensions_2d=normalized_dims_2d,
        orientation=raw.get("orientation") or ("horizontal" if raw.get("vertical") is False else "vertical"),
        color_set=raw.get("color_set"),
        properties_3d=extracted_3d,
    )
    merged = dict(created["object_dict"])
    merged["type"] = "LegendParameters"
    for key in _SDK_LEGEND_KEYS:
        if key in raw and raw[key] is not None and key not in {"min", "max", "vertical", "properties_3d"}:
            if key in {"segment_height", "segment_width", "text_height"} and isinstance(raw[key], str):
                continue
            if key == "properties_2d" and isinstance(raw[key], dict):
                merged["properties_2d"] = _normalize_properties_2d_dict(
                    {**(merged.get("properties_2d") or {}), **raw[key]}
                )
            else:
                merged[key] = raw[key]
    return LegendParameters.from_dict(merged).to_dict()


def coerce_legend_parameter(
    data: dict[str, Any] | None,
) -> LegendParameters | LegendParametersCategorized | None:
    """Coerce a full or inline legend parameter dict into a Ladybug legend object."""
    coerced = coerce_legend_parameter_dict(data)
    if coerced is None:
        return None
    return legend_parameter_from_dict(coerced)


def export_visualization_set(
    *,
    garden_root: str,
    export_format: str,
    visualization_set: dict[str, Any] | None = None,
    visualization_set_target: dict[str, Any] | None = None,
    name: str = "visualization_set",
    output_subdir: str | None = None,
    open: bool = False,
    width: int = 1600,
    height: int = 900,
    margin: float | None = None,
    view: str | dict[str, Any] = "Top",
    interactive: bool = False,
    render_2d_legend: bool = True,
    render_3d_legend: bool = False,
    auto_crop: bool = True,
) -> dict[str, Any]:
    """Export a VisualizationSet to HTML, SVG, VTKJS, PNG, VTK, VTP, VSF, or PKL."""
    fmt = export_format.strip().lower()
    if fmt == "html":
        return visualization_set_to_html(
            garden_root=garden_root,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
            name=name,
            output_subdir=output_subdir or "artifacts/visualization/html",
            open=open,
        )
    if fmt == "svg":
        return visualization_set_to_svg(
            garden_root=garden_root,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
            width=width,
            height=height,
            margin=margin,
            view=view,
            interactive=interactive,
            render_2d_legend=render_2d_legend,
            render_3d_legend=render_3d_legend,
            auto_crop=auto_crop,
            name=name,
            output_subdir=output_subdir or "artifacts/visualization/svg",
        )
    if fmt == "vtkjs":
        return visualization_set_to_vtkjs(
            garden_root=garden_root,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
            name=name,
            output_subdir=output_subdir or "artifacts/visualization/vtkjs",
        )
    if fmt == "png":
        return visualization_set_to_png(
            garden_root=garden_root,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
            width=width,
            height=height,
            view=view,
            render_2d_legend=render_2d_legend,
            name=name,
            output_subdir=output_subdir or "artifacts/visualization/png",
        )
    if fmt in {"vtk", "vtp"}:
        return visualization_set_to_vtk_file(
            garden_root=garden_root,
            export_format=fmt,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
            name=name,
            output_subdir=output_subdir,
        )
    if fmt in {"vsf", "pkl"}:
        return visualization_set_to_native_file(
            garden_root=garden_root,
            export_format=fmt,
            visualization_set=visualization_set,
            visualization_set_target=visualization_set_target,
            name=name,
            output_subdir=output_subdir,
        )
    raise ValueError(
        "export_format must be one of: html, svg, vtkjs, png, vtk, vtp, vsf, pkl."
    )
