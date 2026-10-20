from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any


class SpecError(ValueError):
    """Raised when a figure specification is invalid."""


HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
OBJECT_TYPES = {
    "ellipse",
    "rectangle",
    "rounded_rectangle",
    "open_circular_arch",
    "line",
    "arrow",
    "wave",
    "bezier_path",
    "text",
    "group",
}


def load_spec(path: str | Path) -> dict[str, Any]:
    spec_path = Path(path)
    try:
        data = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecError(f"无法读取规范 {spec_path}: {exc}") from exc
    from .layout import prepare_spec
    data = prepare_spec(data)
    validate_spec(data, base_dir=spec_path.parent)
    return data


def validate_spec(spec: Any, base_dir: Path | None = None) -> None:
    from .layout import prepare_spec
    spec = prepare_spec(spec)
    if not isinstance(spec, dict):
        raise SpecError("顶层必须是 JSON 对象")

    title = spec.get("title")
    if not isinstance(title, str) or not title.strip():
        raise SpecError("title 必须是非空字符串")

    canvas = spec.get("canvas")
    if not isinstance(canvas, dict):
        raise SpecError("canvas 必须是对象")
    _positive(canvas.get("width_mm"), "canvas.width_mm")
    _positive(canvas.get("height_mm"), "canvas.height_mm")
    if "background" in canvas:
        _color(canvas["background"], "canvas.background", allow_none=False)

    layers = spec.get("layers")
    if not isinstance(layers, list) or not layers:
        raise SpecError("layers 必须是非空数组")
    layer_names: list[str] = []
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise SpecError(f"layers[{index}] 必须是对象")
        name = layer.get("name")
        if not isinstance(name, str) or not name.strip():
            raise SpecError(f"layers[{index}].name 必须是非空字符串")
        if name in layer_names:
            raise SpecError(f"图层名称重复: {name}")
        layer_names.append(name)

    objects = spec.get("objects")
    if not isinstance(objects, list):
        raise SpecError("objects 必须是数组")
    for index, item in enumerate(objects):
        _validate_object(item, f"objects[{index}]", layer_names, inherited_layer=None)

    reference = spec.get("reference_image")
    if reference is not None:
        if not isinstance(reference, dict):
            raise SpecError("reference_image 必须是对象")
        path = reference.get("path")
        if not isinstance(path, str) or not path.strip():
            raise SpecError("reference_image.path 必须是非空字符串")
        for field in ("x", "y"):
            if field in reference:
                _number(reference[field], f"reference_image.{field}")
        for field in ("width", "height"):
            if field in reference:
                _positive(reference[field], f"reference_image.{field}")
        if "opacity" in reference:
            _range(reference["opacity"], "reference_image.opacity", 0, 100)
        if "visible_in_output" in reference and not isinstance(reference["visible_in_output"], bool):
            raise SpecError("reference_image.visible_in_output must be a boolean")
        layer = reference.get("layer", "00_Reference")
        if layer not in layer_names:
            raise SpecError(f"reference_image 使用了未声明图层: {layer}")
        if base_dir is not None:
            candidate = (base_dir / path).resolve() if not Path(path).is_absolute() else Path(path)
            if not candidate.exists():
                raise SpecError(f"参考图不存在: {candidate}")


def _validate_object(
    item: Any,
    location: str,
    layer_names: list[str],
    inherited_layer: str | None,
) -> None:
    if not isinstance(item, dict):
        raise SpecError(f"{location} 必须是对象")
    if "allow_outside_canvas" in item and not isinstance(item["allow_outside_canvas"], bool):
        raise SpecError(f"{location}.allow_outside_canvas must be boolean")
    object_type = item.get("type")
    if object_type not in OBJECT_TYPES:
        raise SpecError(f"{location}.type 不支持: {object_type!r}")
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        raise SpecError(f"{location}.name 必须是非空字符串")
    layer = item.get("layer", inherited_layer)
    if layer not in layer_names:
        raise SpecError(f"{location} 使用了未声明图层: {layer}")

    if object_type in {"ellipse", "rectangle", "rounded_rectangle"}:
        for field in ("x", "y"):
            _number(item.get(field), f"{location}.{field}")
        for field in ("width", "height"):
            _positive(item.get(field), f"{location}.{field}")
        if object_type == "rounded_rectangle":
            _positive(item.get("radius"), f"{location}.radius")
        _style(item.get("style", {}), f"{location}.style")
    elif object_type == "open_circular_arch":
        for field in ("cx", "cy", "left_leg_end_y", "right_leg_end_y"):
            _number(item.get(field), f"{location}.{field}")
        radius = _positive(item.get("radius"), f"{location}.radius")
        half_gap = _positive(item.get("half_gap"), f"{location}.half_gap")
        if half_gap >= radius:
            raise SpecError(f"{location}.half_gap must be smaller than radius")
        join_y = float(item["cy"]) + math.sqrt(radius * radius - half_gap * half_gap)
        if float(item["left_leg_end_y"]) <= join_y or float(item["right_leg_end_y"]) <= join_y:
            raise SpecError(f"{location} leg endpoints must extend below the circular-arc junction")
        _style(item.get("style", {}), f"{location}.style")
    elif object_type in {"line", "arrow"}:
        for field in ("x1", "y1", "x2", "y2"):
            _number(item.get(field), f"{location}.{field}")
        if item["x1"] == item["x2"] and item["y1"] == item["y2"]:
            raise SpecError(f"{location} 的起点和终点不能相同")
        if object_type == "arrow" and "head_size" in item:
            _positive(item["head_size"], f"{location}.head_size")
        _style(item.get("style", {}), f"{location}.style")
    elif object_type == "wave":
        for field in ("x", "y"):
            _number(item.get(field), f"{location}.{field}")
        for field in ("width", "amplitude", "cycles"):
            _positive(item.get(field), f"{location}.{field}")
        if not float(item["cycles"]).is_integer():
            raise SpecError(f"{location}.cycles 必须是整数")
        if item.get("orientation", "horizontal") not in {"horizontal", "vertical"}:
            raise SpecError(f"{location}.orientation 必须是 horizontal 或 vertical")
        _style(item.get("style", {}), f"{location}.style")
    elif object_type == "bezier_path":
        points = item.get("points")
        if not isinstance(points, list) or len(points) < 2:
            raise SpecError(f"{location}.points must contain at least two path points")
        for index, point in enumerate(points):
            if not isinstance(point, dict):
                raise SpecError(f"{location}.points[{index}] must be an object")
            for field in ("anchor", "left", "right"):
                if field not in point:
                    continue
                value = point[field]
                if not isinstance(value, list) or len(value) != 2:
                    raise SpecError(f"{location}.points[{index}].{field} must be [x, y]")
                _number(value[0], f"{location}.points[{index}].{field}[0]")
                _number(value[1], f"{location}.points[{index}].{field}[1]")
            if "anchor" not in point:
                raise SpecError(f"{location}.points[{index}].anchor is required")
            if point.get("point_type", "corner") not in {"corner", "smooth"}:
                raise SpecError(f"{location}.points[{index}].point_type must be corner or smooth")
        if "closed" in item and not isinstance(item["closed"], bool):
            raise SpecError(f"{location}.closed must be a boolean")
        _style(item.get("style", {}), f"{location}.style")
    elif object_type == "text":
        for field in ("x", "y"):
            _number(item.get(field), f"{location}.{field}")
        if not isinstance(item.get("text"), str):
            raise SpecError(f"{location}.text 必须是字符串")
        _positive(item.get("font_size_pt", 9), f"{location}.font_size_pt")
        if "color" in item:
            _color(item["color"], f"{location}.color", allow_none=False)
        if "font" in item and not isinstance(item["font"], str):
            raise SpecError(f"{location}.font 必须是字符串")
        if item.get("align", "left") not in {"left", "center", "right"}:
            raise SpecError(f"{location}.align must be left, center, or right")
        if "visual_center" in item:
            visual_center = item["visual_center"]
            if not isinstance(visual_center, list) or len(visual_center) != 2:
                raise SpecError(f"{location}.visual_center must be [x, y]")
            _number(visual_center[0], f"{location}.visual_center[0]")
            _number(visual_center[1], f"{location}.visual_center[1]")
    else:
        children = item.get("children")
        if not isinstance(children, list) or not children:
            raise SpecError(f"{location}.children 必须是非空数组")
        for index, child in enumerate(children):
            _validate_object(child, f"{location}.children[{index}]", layer_names, layer)

    if "rotation_deg" in item:
        _number(item["rotation_deg"], f"{location}.rotation_deg")


def _style(style: Any, location: str) -> None:
    if not isinstance(style, dict):
        raise SpecError(f"{location} 必须是对象")
    if "fill" in style:
        _color(style["fill"], f"{location}.fill", allow_none=True)
    if "stroke" in style:
        _color(style["stroke"], f"{location}.stroke", allow_none=True)
    if "stroke_width_mm" in style:
        _positive(style["stroke_width_mm"], f"{location}.stroke_width_mm")
    if "opacity" in style:
        _range(style["opacity"], f"{location}.opacity", 0, 100)
    if "fill_gradient" in style:
        gradient = style["fill_gradient"]
        if not isinstance(gradient, dict):
            raise SpecError(f"{location}.fill_gradient must be an object")
        if gradient.get("type", "linear") not in {"linear", "radial"}:
            raise SpecError(f"{location}.fill_gradient.type must be linear or radial")
        if "angle_deg" in gradient:
            _number(gradient["angle_deg"], f"{location}.fill_gradient.angle_deg")
        stops = gradient.get("stops")
        if not isinstance(stops, list) or len(stops) < 2:
            raise SpecError(f"{location}.fill_gradient.stops must contain at least two stops")
        previous = -1.0
        for index, stop in enumerate(stops):
            if not isinstance(stop, dict):
                raise SpecError(f"{location}.fill_gradient.stops[{index}] must be an object")
            _color(stop.get("color"), f"{location}.fill_gradient.stops[{index}].color", allow_none=False)
            offset = _number(stop.get("offset"), f"{location}.fill_gradient.stops[{index}].offset")
            if offset < 0 or offset > 100 or offset < previous:
                raise SpecError(f"{location}.fill_gradient stop offsets must increase from 0 to 100")
            previous = offset
            if "opacity" in stop:
                _range(stop["opacity"], f"{location}.fill_gradient.stops[{index}].opacity", 0, 100)
    if style.get("stroke_cap", "butt") not in {"butt", "round", "projecting"}:
        raise SpecError(f"{location}.stroke_cap must be butt, round, or projecting")
    if style.get("stroke_join", "miter") not in {"miter", "round", "bevel"}:
        raise SpecError(f"{location}.stroke_join must be miter, round, or bevel")


def _color(value: Any, location: str, allow_none: bool) -> None:
    if allow_none and value is None:
        return
    if not isinstance(value, str) or not HEX_COLOR.fullmatch(value):
        raise SpecError(f"{location} 必须是 #RRGGBB 颜色")


def _number(value: Any, location: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise SpecError(f"{location} 必须是有限数值")
    return float(value)


def _positive(value: Any, location: str) -> float:
    result = _number(value, location)
    if result <= 0:
        raise SpecError(f"{location} 必须大于 0")
    return result


def _range(value: Any, location: str, minimum: float, maximum: float) -> None:
    result = _number(value, location)
    if result < minimum or result > maximum:
        raise SpecError(f"{location} 必须在 {minimum}–{maximum} 之间")
