from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .schema import validate_spec
from .layout import prepare_spec


PT_PER_MM = 72.0 / 25.4


def build_jsx(
    spec: dict[str, Any],
    ai_path: str | Path,
    png_path: str | Path | None = None,
    spec_base_dir: str | Path | None = None,
    report_path: str | Path | None = None,
) -> str:
    spec = prepare_spec(spec)
    validate_spec(spec, base_dir=Path(spec_base_dir) if spec_base_dir else None)
    width_pt = _pt(spec["canvas"]["width_mm"])
    height_pt = _pt(spec["canvas"]["height_mm"])
    lines = [
        "#target illustrator",
        "(function () {",
        "  if (!/illustrator/i.test(app.name)) { throw new Error('Adobe Illustrator is required'); }",
        "  var MM = 72 / 25.4;",
        f"  var DOC_W = {_num(width_pt)};",
        f"  var DOC_H = {_num(height_pt)};",
        "  function rgb(hex) {",
        "    var c = new RGBColor();",
        "    c.red = parseInt(hex.substr(1, 2), 16);",
        "    c.green = parseInt(hex.substr(3, 2), 16);",
        "    c.blue = parseInt(hex.substr(5, 2), 16);",
        "    return c;",
        "  }",
        "  function py(y) { return DOC_H - y * MM; }",
        "  function styleItem(item, fillHex, strokeHex, strokeWidth, opacity) {",
        "    if (fillHex) { item.filled = true; item.fillColor = rgb(fillHex); } else { item.filled = false; }",
        "    if (strokeHex) { item.stroked = true; item.strokeColor = rgb(strokeHex); item.strokeWidth = strokeWidth * MM; } else { item.stroked = false; }",
        "    item.opacity = opacity;",
        "  }",
        "  function applyGradient(item, kind, angle, stops) {",
        "    var gradient = doc.gradients.add();",
        "    gradient.type = kind === 'radial' ? GradientType.RADIAL : GradientType.LINEAR;",
        "    while (gradient.gradientStops.length < stops.length) { gradient.gradientStops.add(); }",
        "    while (gradient.gradientStops.length > stops.length) { gradient.gradientStops[gradient.gradientStops.length - 1].remove(); }",
        "    for (var gradientIndex = 0; gradientIndex < stops.length; gradientIndex++) {",
        "      var gradientStop = gradient.gradientStops[gradientIndex];",
        "      gradientStop.rampPoint = stops[gradientIndex].offset;",
        "      gradientStop.color = rgb(stops[gradientIndex].color);",
        "      gradientStop.opacity = stops[gradientIndex].opacity;",
        "    }",
        "    var gradientColor = new GradientColor();",
        "    gradientColor.gradient = gradient;",
        "    gradientColor.angle = angle;",
        "    item.filled = true;",
        "    item.fillColor = gradientColor;",
        "  }",
        "  var doc = app.documents.add(DocumentColorSpace.RGB, DOC_W, DOC_H);",
        "  doc.artboards[0].artboardRect = [0, DOC_H, DOC_W, 0];",
        f"  try {{ if (doc.info) {{ doc.info.title = {_js(spec['title'])}; }} }} catch (metadataError) {{}}",
        "  var layers = {};",
    ]
    lines.extend(Path(__file__).with_name("readback.jsxinc").read_text(encoding="utf-8").splitlines())

    # The default layer is reused as the bottom declared layer.
    for index, layer in enumerate(spec["layers"]):
        name = layer["name"]
        if index == 0:
            lines.extend([
                "  var layer0 = doc.layers[0];",
                f"  layer0.name = {_js(name)};",
                f"  layers[{_js(name)}] = layer0;",
            ])
        else:
            lines.extend([
                "  var nextLayer = doc.layers.add();",
                f"  nextLayer.name = {_js(name)};",
                f"  layers[{_js(name)}] = nextLayer;",
            ])

    # Warm up Illustrator's point-text engine before placing images or locking
    # layers. Some Illustrator 2025 sessions otherwise reject the size of the
    # first real text frame with a PARM error even though later frames work.
    warmup_layer = spec["layers"][0]["name"]
    lines.extend([
        f"  var textWarmup = layers[{_js(warmup_layer)}].textFrames.pointText([0, DOC_H]);",
        "  textWarmup.contents = '.';",
        "  try { textWarmup.textRange.characterAttributes.textFont = app.textFonts.getByName('NotoSansSC-Regular'); } catch (warmupFontError) { try { textWarmup.textRange.characterAttributes.textFont = app.textFonts.getByName('AcuminConcept-Regular'); } catch (fallbackWarmupFontError) {} }",
        "  textWarmup.textRange.characterAttributes.size = 9;",
        "  textWarmup.remove();",
    ])

    background = spec["canvas"].get("background")
    if background:
        bottom_layer = spec["layers"][0]["name"]
        lines.extend([
            "  var canvasBg = layers[%s].pathItems.rectangle(DOC_H, 0, DOC_W, DOC_H);" % _js(bottom_layer),
            "  canvasBg.name = 'Canvas Background';",
            f"  styleItem(canvasBg, {_js(background)}, null, 0, 100);",
        ])

    reference = spec.get("reference_image")
    if reference:
        reference_path = Path(reference["path"])
        if not reference_path.is_absolute() and spec_base_dir:
            reference_path = (Path(spec_base_dir) / reference_path).resolve()
        layer = reference.get("layer", "00_Reference")
        x = reference.get("x", 0)
        y = reference.get("y", 0)
        lines.extend([
            f"  var referenceFile = new File({_js(_win_path(reference_path))});",
            "  if (!referenceFile.exists) { throw new Error('Reference image not found: ' + referenceFile.fsName); }",
            f"  var referenceItem = layers[{_js(layer)}].placedItems.add();",
            "  referenceItem.file = referenceFile;",
            "  referenceItem.name = 'Reference Image';",
            f"  referenceItem.position = [{_num(_pt(x))}, py({_num(y)})];",
            f"  referenceItem.opacity = {_num(reference.get('opacity', 35))};",
        ])
        if "width" in reference:
            lines.append(f"  referenceItem.width = {_num(_pt(reference['width']))};")
        if "height" in reference:
            lines.append(f"  referenceItem.height = {_num(_pt(reference['height']))};")
        lines.append(f"  layers[{_js(layer)}].locked = true;")

    counter = [0]
    for item in spec["objects"]:
        lines.extend(_object_lines(item, item.get("layer"), counter, indent="  "))

    calibration = spec.get("calibration_exports")
    if calibration and reference:
        calibration_path = Path(calibration["path"])
        if not calibration_path.is_absolute() and spec_base_dir:
            calibration_path = (Path(spec_base_dir) / calibration_path).resolve()
        region_layers = [region["layer"] for region in calibration.get("regions", [])]
        lines.extend([
            f"  var calibrationFolder = new Folder({_js(_win_path(calibration_path))});",
            "  if (!calibrationFolder.exists) { calibrationFolder.create(); }",
            f"  layers[{_js(reference.get('layer', '00_Reference'))}].visible = true;",
            "  var calibrationOptions = new ExportOptionsPNG24();",
            "  calibrationOptions.antiAliasing = true;",
            "  calibrationOptions.transparency = false;",
            "  calibrationOptions.artBoardClipping = true;",
            "  calibrationOptions.horizontalScale = 100;",
            "  calibrationOptions.verticalScale = 100;",
        ])
        for index, region in enumerate(calibration.get("regions", []), 1):
            for layer_name in region_layers:
                lines.append(
                    f"  layers[{_js(layer_name)}].visible = {'true' if layer_name == region['layer'] else 'false'};"
                )
            filename = f"{index:02d}_{region['id']}.png"
            relative_filename = "\\" + filename
            lines.extend([
                "  app.redraw();",
                f"  doc.exportFile(new File(calibrationFolder.fsName + {_js(relative_filename)}), ExportType.PNG24, calibrationOptions);",
            ])
        for layer_name in region_layers:
            lines.append(f"  layers[{_js(layer_name)}].visible = true;")

    if reference and not reference.get("visible_in_output", True):
        reference_layer = reference.get("layer", "00_Reference")
        lines.append(f"  layers[{_js(reference_layer)}].visible = false;")

    ai_path = Path(ai_path).resolve()
    report_path = Path(report_path).resolve() if report_path else ai_path.parent / "audits" / (ai_path.stem + ".json")
    expected = []
    def collect(items, inherited=None, transformed=False):
        for item in items:
            layer = item.get("layer", inherited)
            record = {"id": item["id"], "name": item["name"], "layer": layer,
                      "typename": "TextFrame" if item["type"] == "text" else "GroupItem" if item["type"] in {"group", "arrow"} else "PathItem",
                      "allow_outside": item.get("allow_outside_canvas", False)}
            if item["type"] in {"rectangle", "rounded_rectangle", "ellipse"} and not transformed and not item.get("rotation_deg", 0):
                record["geometry_mm"] = [item["x"], item["y"], item["x"] + item["width"], item["y"] + item["height"]]
            if item["type"] == "text":
                record.update(text=item["text"], font=item.get("font", "NotoSansSC-Regular"))
                if "visual_center" in item and not transformed:
                    record["center"] = item["visual_center"]
                if "container_id" in item:
                    record.update(container=item["container_id"], padding=item.get("padding_mm", 1))
            expected.append(record)
            if item["type"] == "group":
                collect(item["children"], layer, transformed or bool(item.get("rotation_deg", 0)))
    collect(spec["objects"])
    expected_counts = {}
    for entry in expected:
        kind = entry["typename"]
        expected_counts[kind] = expected_counts.get(kind, 0) + 1
    def arrow_count(items):
        return sum((1 if i["type"] == "arrow" else arrow_count(i["children"]) if i["type"] == "group" else 0) for i in items)
    extra_paths = 2 * arrow_count(spec["objects"]) + bool(background)
    if extra_paths:
        expected_counts["PathItem"] = expected_counts.get("PathItem", 0) + extra_paths
    if reference:
        expected_counts["PlacedItem"] = 1
    lines.extend([
        "  app.redraw();",
        f"  readDocument({json.dumps(expected, ensure_ascii=False)}, {_js(_win_path(report_path))}, {json.dumps(expected_counts)});",
        f"  var aiFile = new File({_js(_win_path(ai_path))});",
        "  var aiOptions = new IllustratorSaveOptions();",
        "  aiOptions.pdfCompatible = true;",
        "  doc.saveAs(aiFile, aiOptions);",
    ])
    if png_path is not None:
        png_path = Path(png_path).resolve()
        lines.extend([
            "  app.redraw();",
            "  $.sleep(1000);",
            "  app.redraw();",
            "  $.sleep(500);",
            f"  var pngFile = new File({_js(_win_path(png_path))});",
            "  var pngOptions = new ExportOptionsPNG24();",
            "  pngOptions.antiAliasing = true;",
            "  pngOptions.transparency = false;",
            "  pngOptions.artBoardClipping = true;",
            "  pngOptions.horizontalScale = 150;",
            "  pngOptions.verticalScale = 150;",
            "  doc.exportFile(pngFile, ExportType.PNG24, pngOptions);",
            "  doc.save();",
        ])
    lines.extend([
        "  return aiFile.fsName;",
        "}());",
        "",
    ])
    return "\n".join(lines)


def _object_lines(item: dict[str, Any], inherited_layer: str | None, counter: list[int], indent: str) -> list[str]:
    layer = item.get("layer", inherited_layer)
    object_type = item["type"]
    if object_type == "group":
        counter[0] += 1
        var = f"group{counter[0]}"
        result = [
            f"{indent}var {var} = layers[{_js(layer)}].groupItems.add();",
            f"{indent}{var}.name = {_js(item['name'])};",
        ]
        for child in item["children"]:
            child_lines = _object_lines(child, layer, counter, indent)
            child_var = child_lines[-1].split("//RETURN:", 1)[1] if child_lines[-1].startswith(f"{indent}//RETURN:") else None
            if child_var:
                child_lines = child_lines[:-1]
            result.extend(child_lines)
            if child_var:
                # Later children are visually above earlier children, matching the JSON order.
                result.append(f"{indent}{child_var}.move({var}, ElementPlacement.PLACEATBEGINNING);")
        result.extend(_post_transform_lines(var, item, indent))
        result.append(f"{indent}//RETURN:{var}")
        return result

    counter[0] += 1
    var = f"item{counter[0]}"
    result: list[str] = []
    if object_type in {"ellipse", "rectangle", "rounded_rectangle"}:
        x, y = item["x"], item["y"]
        width, height = item["width"], item["height"]
        collection = f"layers[{_js(layer)}].pathItems"
        if object_type == "ellipse":
            expression = f"{collection}.ellipse(py({_num(y)}), {_num(x)} * MM, {_num(width)} * MM, {_num(height)} * MM)"
        elif object_type == "rectangle":
            expression = f"{collection}.rectangle(py({_num(y)}), {_num(x)} * MM, {_num(width)} * MM, {_num(height)} * MM)"
        else:
            radius = item["radius"]
            expression = (
                f"{collection}.roundedRectangle(py({_num(y)}), {_num(x)} * MM, {_num(width)} * MM, "
                f"{_num(height)} * MM, {_num(radius)} * MM, {_num(radius)} * MM)"
            )
        result.append(f"{indent}var {var} = {expression};")
        result.append(f"{indent}{var}.name = {_js(item['name'])};")
        result.append(f"{indent}{_style_call(var, item.get('style', {}))}")
        result.extend(_gradient_lines(var, item.get("style", {}), indent))
    elif object_type == "open_circular_arch":
        result.extend(_open_circular_arch_lines(var, item, layer, indent))
    elif object_type == "line":
        result.extend(_line_lines(var, item, layer, indent))
    elif object_type == "arrow":
        result.extend(_arrow_lines(var, item, layer, counter, indent))
    elif object_type == "wave":
        result.extend(_wave_lines(var, item, layer, indent))
    elif object_type == "bezier_path":
        result.extend(_bezier_path_lines(var, item, layer, indent))
    elif object_type == "text":
        result.extend([
            f"{indent}var {var} = layers[{_js(layer)}].textFrames.pointText([{_num(item['x'])} * MM, py({_num(item['y'])})]);",
            f"{indent}{var}.name = {_js(item['name'])};",
            f"{indent}{var}.contents = {_js(item['text'])};",
        ])
        # Illustrator can return PARM when size is assigned before the requested
        # font on a newly-created point text frame. Resolve the font first, then
        # apply the remaining character attributes.
        requested_font = item.get("font", "NotoSansSC-Regular")
        result.append(
            f"{indent}try {{ {var}.textRange.characterAttributes.textFont = app.textFonts.getByName({_js(requested_font)}); }} catch (fontError) {{ try {{ {var}.textRange.characterAttributes.textFont = app.textFonts.getByName('NotoSansSC-Regular'); }} catch (fallbackFontError) {{}} }}"
        )
        result.extend([
            f"{indent}{var}.textRange.characterAttributes.size = {_num(item.get('font_size_pt', 9))};",
            f"{indent}{var}.textRange.characterAttributes.fillColor = rgb({_js(item.get('color', '#222222'))});",
            f"{indent}{var}.opacity = {_num(item.get('opacity', 100))};",
        ])
        justification = {
            "left": "LEFT",
            "center": "CENTER",
            "right": "RIGHT",
        }[item.get("align", "left")]
        result.append(
            f"{indent}try {{ {var}.textRange.paragraphAttributes.justification = Justification.{justification}; }} catch (justificationError) {{}}"
        )
    result.extend(_post_transform_lines(var, item, indent))
    if object_type == "text" and "visual_center" in item:
        visual_x, visual_y = item["visual_center"]
        bounds_var = f"{var}Bounds"
        result.extend([
            f"{indent}var {bounds_var} = glyphBounds({var});",
            f"{indent}{var}.translate({_num(_pt(visual_x))} - ({bounds_var}[0] + {bounds_var}[2]) / 2, py({_num(visual_y)}) - ({bounds_var}[1] + {bounds_var}[3]) / 2);",
        ])
    result.append(f"{indent}//RETURN:{var}")
    return result


def _gradient_lines(var: str, style: dict[str, Any], indent: str) -> list[str]:
    gradient = style.get("fill_gradient")
    if not gradient:
        return []
    stops = [
        {
            "offset": float(stop["offset"]),
            "color": stop["color"],
            "opacity": float(stop.get("opacity", 100)),
        }
        for stop in gradient["stops"]
    ]
    return [
        f"{indent}applyGradient({var}, {_js(gradient.get('type', 'linear'))}, {_num(gradient.get('angle_deg', 90))}, {json.dumps(stops, ensure_ascii=False)});"
    ]


def _post_transform_lines(var: str, item: dict[str, Any], indent: str) -> list[str]:
    result: list[str] = [f"{indent}{var}.note = {_js('sciai:' + item['id'])};"]
    if "rotation_deg" in item and float(item["rotation_deg"]) != 0:
        result.append(f"{indent}{var}.rotate({_num(item['rotation_deg'])});")
    return result


def _line_lines(var: str, item: dict[str, Any], layer: str, indent: str) -> list[str]:
    style = item.get("style", {})
    stroke = style.get("stroke", "#333333")
    width = style.get("stroke_width_mm", 0.5)
    opacity = style.get("opacity", 100)
    result = [
        f"{indent}var {var} = layers[{_js(layer)}].pathItems.add();",
        f"{indent}{var}.name = {_js(item['name'])};",
        f"{indent}{var}.setEntirePath([[{_num(item['x1'])} * MM, py({_num(item['y1'])})], [{_num(item['x2'])} * MM, py({_num(item['y2'])})]]);",
        f"{indent}styleItem({var}, null, {_js(stroke)}, {_num(width)}, {_num(opacity)});",
    ]
    result.extend(_stroke_finish_lines(var, style, indent))
    return result


def _wave_lines(var: str, item: dict[str, Any], layer: str, indent: str) -> list[str]:
    style = item.get("style", {})
    stroke = style.get("stroke", "#333333")
    width = style.get("stroke_width_mm", 0.5)
    opacity = style.get("opacity", 100)
    x = float(item["x"])
    y = float(item["y"])
    total_width = float(item["width"])
    amplitude = float(item["amplitude"])
    cycles = int(item["cycles"])
    orientation = item.get("orientation", "horizontal")
    half_count = cycles * 2
    segment_width = total_width / half_count
    handle_height = amplitude * 4.0 / 3.0
    points: list[tuple[float, float, float, float, float, float]] = []
    for index in range(half_count + 1):
        left_sign = -1 if (index - 1) % 2 == 0 else 1
        right_sign = -1 if index % 2 == 0 else 1
        if orientation == "horizontal":
            anchor_x = x + segment_width * index
            left_x = anchor_x - segment_width / 2.0 if index > 0 else anchor_x
            right_x = anchor_x + segment_width / 2.0 if index < half_count else anchor_x
            left_y = y + left_sign * handle_height if index > 0 else y
            right_y = y + right_sign * handle_height if index < half_count else y
            points.append((anchor_x, y, left_x, left_y, right_x, right_y))
        else:
            anchor_y = y + segment_width * index
            left_y = anchor_y - segment_width / 2.0 if index > 0 else anchor_y
            right_y = anchor_y + segment_width / 2.0 if index < half_count else anchor_y
            left_x = x + left_sign * handle_height if index > 0 else x
            right_x = x + right_sign * handle_height if index < half_count else x
            points.append((x, anchor_y, left_x, left_y, right_x, right_y))

    result = [
        f"{indent}var {var} = layers[{_js(layer)}].pathItems.add();",
        f"{indent}{var}.name = {_js(item['name'])};",
    ]
    for index, (ax, ay, lx, ly, rx, ry) in enumerate(points):
        result.extend([
            f"{indent}var {var}p{index} = {var}.pathPoints.add();",
            f"{indent}{var}p{index}.anchor = [{_num(ax)} * MM, py({_num(ay)})];",
            f"{indent}{var}p{index}.leftDirection = [{_num(lx)} * MM, py({_num(ly)})];",
            f"{indent}{var}p{index}.rightDirection = [{_num(rx)} * MM, py({_num(ry)})];",
            f"{indent}{var}p{index}.pointType = PointType.SMOOTH;",
        ])
    result.extend([
        f"{indent}{var}.closed = false;",
        f"{indent}styleItem({var}, null, {_js(stroke)}, {_num(width)}, {_num(opacity)});",
    ])
    result.extend(_stroke_finish_lines(var, style, indent))
    return result


def _bezier_path_lines(var: str, item: dict[str, Any], layer: str, indent: str) -> list[str]:
    style = item.get("style", {})
    fill = style.get("fill")
    stroke = style.get("stroke", "#333333")
    width = style.get("stroke_width_mm", 0.5)
    opacity = style.get("opacity", 100)
    result = [
        f"{indent}var {var} = layers[{_js(layer)}].pathItems.add();",
        f"{indent}{var}.name = {_js(item['name'])};",
    ]
    for index, point in enumerate(item["points"]):
        anchor = point["anchor"]
        left = point.get("left", anchor)
        right = point.get("right", anchor)
        point_type = "SMOOTH" if point.get("point_type") == "smooth" else "CORNER"
        result.extend([
            f"{indent}var {var}p{index} = {var}.pathPoints.add();",
            f"{indent}{var}p{index}.anchor = [{_num(anchor[0])} * MM, py({_num(anchor[1])})];",
            f"{indent}{var}p{index}.leftDirection = [{_num(left[0])} * MM, py({_num(left[1])})];",
            f"{indent}{var}p{index}.rightDirection = [{_num(right[0])} * MM, py({_num(right[1])})];",
            f"{indent}{var}p{index}.pointType = PointType.{point_type};",
        ])
    result.extend([
        f"{indent}{var}.closed = {'true' if item.get('closed', False) else 'false'};",
        f"{indent}styleItem({var}, {_js(fill)}, {_js(stroke)}, {_num(width)}, {_num(opacity)});",
    ])
    result.extend(_gradient_lines(var, style, indent))
    result.extend(_stroke_finish_lines(var, style, indent))
    return result


def _open_circular_arch_lines(var: str, item: dict[str, Any], layer: str, indent: str) -> list[str]:
    """Build one open path from two straight legs and an exact circular crown.

    The line/arc junctions are direct corner anchors. No transition anchors or
    freehand connector curves are inserted, so the contour cannot develop an
    accidental inward waist between the regular primitives.
    """
    style = item.get("style", {})
    stroke = style.get("stroke", "#333333")
    width = style.get("stroke_width_mm", 0.5)
    opacity = style.get("opacity", 100)
    cx = float(item["cx"])
    cy = float(item["cy"])
    radius = float(item["radius"])
    half_gap = float(item["half_gap"])
    alpha = math.acos(half_gap / radius)
    angles = [math.pi - alpha, math.pi, 1.5 * math.pi, 2.0 * math.pi, 2.0 * math.pi + alpha]

    arc_points: list[dict[str, Any]] = []
    for index, angle in enumerate(angles):
        ax = cx + radius * math.cos(angle)
        ay = cy + radius * math.sin(angle)
        tx = -math.sin(angle)
        ty = math.cos(angle)
        if index == 0:
            left = [ax, ay]
        else:
            delta = angle - angles[index - 1]
            handle = 4.0 / 3.0 * math.tan(delta / 4.0) * radius
            left = [ax - tx * handle, ay - ty * handle]
        if index == len(angles) - 1:
            right = [ax, ay]
        else:
            delta = angles[index + 1] - angle
            handle = 4.0 / 3.0 * math.tan(delta / 4.0) * radius
            right = [ax + tx * handle, ay + ty * handle]
        arc_points.append({"anchor": [ax, ay], "left": left, "right": right})

    points = [
        {"anchor": [cx - half_gap, float(item["left_leg_end_y"])]},
        *arc_points,
        {"anchor": [cx + half_gap, float(item["right_leg_end_y"])]},
    ]
    result = [
        f"{indent}var {var} = layers[{_js(layer)}].pathItems.add();",
        f"{indent}{var}.name = {_js(item['name'])};",
    ]
    for index, point in enumerate(points):
        anchor = point["anchor"]
        left = point.get("left", anchor)
        right = point.get("right", anchor)
        point_type = "SMOOTH" if 1 < index < len(points) - 2 else "CORNER"
        result.extend([
            f"{indent}var {var}p{index} = {var}.pathPoints.add();",
            f"{indent}{var}p{index}.anchor = [{_num(anchor[0])} * MM, py({_num(anchor[1])})];",
            f"{indent}{var}p{index}.leftDirection = [{_num(left[0])} * MM, py({_num(left[1])})];",
            f"{indent}{var}p{index}.rightDirection = [{_num(right[0])} * MM, py({_num(right[1])})];",
            f"{indent}{var}p{index}.pointType = PointType.{point_type};",
        ])
    result.extend([
        f"{indent}{var}.closed = false;",
        f"{indent}styleItem({var}, null, {_js(stroke)}, {_num(width)}, {_num(opacity)});",
    ])
    result.extend(_stroke_finish_lines(var, style, indent))
    return result


def _stroke_finish_lines(var: str, style: dict[str, Any], indent: str) -> list[str]:
    result: list[str] = []
    caps = {
        "butt": "BUTTENDCAP",
        "round": "ROUNDENDCAP",
        "projecting": "PROJECTINGENDCAP",
    }
    joins = {
        "miter": "MITERENDJOIN",
        "round": "ROUNDENDJOIN",
        "bevel": "BEVELENDJOIN",
    }
    if "stroke_cap" in style:
        result.append(f"{indent}{var}.strokeCap = StrokeCap.{caps[style['stroke_cap']]};")
    if "stroke_join" in style:
        result.append(f"{indent}{var}.strokeJoin = StrokeJoin.{joins[style['stroke_join']]};")
    return result


def _arrow_lines(
    var: str,
    item: dict[str, Any],
    layer: str,
    counter: list[int],
    indent: str,
) -> list[str]:
    style = item.get("style", {})
    stroke = style.get("stroke", "#333333")
    fill = style.get("fill", stroke) or stroke
    width = style.get("stroke_width_mm", 0.5)
    opacity = style.get("opacity", 100)
    head = item.get("head_size", 3.0)
    x1, y1, x2, y2 = (float(item[key]) for key in ("x1", "y1", "x2", "y2"))
    angle = math.atan2(y2 - y1, x2 - x1)
    wing = head * 0.58
    base_x = x2 - head * math.cos(angle)
    base_y = y2 - head * math.sin(angle)
    left_x = base_x + wing * math.cos(angle + math.pi / 2)
    left_y = base_y + wing * math.sin(angle + math.pi / 2)
    right_x = base_x + wing * math.cos(angle - math.pi / 2)
    right_y = base_y + wing * math.sin(angle - math.pi / 2)
    counter[0] += 1
    head_var = f"item{counter[0]}"
    group_var = var
    shaft_var = f"{var}Shaft"
    return [
        f"{indent}var {group_var} = layers[{_js(layer)}].groupItems.add();",
        f"{indent}{group_var}.name = {_js(item['name'])};",
        f"{indent}var {shaft_var} = layers[{_js(layer)}].pathItems.add();",
        f"{indent}{shaft_var}.setEntirePath([[{_num(x1)} * MM, py({_num(y1)})], [{_num(base_x)} * MM, py({_num(base_y)})]]);",
        f"{indent}styleItem({shaft_var}, null, {_js(stroke)}, {_num(width)}, {_num(opacity)});",
        f"{indent}var {head_var} = layers[{_js(layer)}].pathItems.add();",
        f"{indent}{head_var}.setEntirePath([[{_num(x2)} * MM, py({_num(y2)})], [{_num(left_x)} * MM, py({_num(left_y)})], [{_num(right_x)} * MM, py({_num(right_y)})]]);",
        f"{indent}{head_var}.closed = true;",
        f"{indent}styleItem({head_var}, {_js(fill)}, {_js(stroke)}, {_num(width)}, {_num(opacity)});",
        f"{indent}{shaft_var}.move({group_var}, ElementPlacement.PLACEATEND);",
        f"{indent}{head_var}.move({group_var}, ElementPlacement.PLACEATEND);",
    ]


def _style_call(var: str, style: dict[str, Any]) -> str:
    fill = style.get("fill", "#FFFFFF")
    stroke = style.get("stroke", "#333333")
    width = style.get("stroke_width_mm", 0.4)
    opacity = style.get("opacity", 100)
    return f"styleItem({var}, {_js(fill)}, {_js(stroke)}, {_num(width)}, {_num(opacity)});"


def _pt(mm: float) -> float:
    return float(mm) * PT_PER_MM


def _num(value: float | int) -> str:
    return f"{float(value):.6f}".rstrip("0").rstrip(".")


def _js(value: Any) -> str:
    if value is None:
        return "null"
    return json.dumps(str(value), ensure_ascii=False)


def _win_path(path: Path) -> str:
    return str(path).replace("/", "\\")
