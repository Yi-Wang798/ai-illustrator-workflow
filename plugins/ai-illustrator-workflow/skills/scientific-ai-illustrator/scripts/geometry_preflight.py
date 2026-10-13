#!/usr/bin/env python3
"""Fail-fast geometry checks for Illustrator reconstruction contracts."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


def _distance(a: list[float], b: list[float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _bbox_intersects(a: list[float], b: list[float], clearance: float) -> bool:
    return not (
        a[2] + clearance <= b[0]
        or b[2] + clearance <= a[0]
        or a[3] + clearance <= b[1]
        or b[3] + clearance <= a[1]
    )


def _point_line_distance(point: list[float], line: list[list[float]]) -> float:
    a, b = line
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return float("inf")
    return abs(dy * point[0] - dx * point[1] + b[0] * a[1] - b[1] * a[0]) / length


def _luminance(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    if len(value) != 6:
        return float("nan")
    r, g, b = (int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def validate(contract: dict) -> list[str]:
    tol = {
        "circle": 0.5,
        "straight": 0.5,
        "parallel": 0.5,
        "center": 1.5,
        "endpoint": 0.5,
        "clearance": 3.0,
        "uniform_scale": 0.001,
        "band_depth": 0.5,
        "offset": 0.5,
        "tangent": 0.01,
    }
    tol.update(contract.get("tolerances", {}))
    errors: list[str] = []

    for check in contract.get("checks", []):
        cid = check.get("id", "unnamed")
        kind = check.get("type")

        if kind == "circle":
            bounds = check["bounds"]
            if abs(bounds[2] - bounds[3]) > tol["circle"]:
                errors.append(f"{cid}: circle width/height mismatch")

        elif kind == "open_circular_arch":
            center = check["center"]
            radius = float(check["radius"])
            half_gap = float(check["half_gap"])
            if radius <= 0 or half_gap <= 0 or half_gap >= radius:
                errors.append(f"{cid}: open circular arch requires 0 < half_gap < radius")
                continue
            join_y = float(center[1]) + math.sqrt(radius * radius - half_gap * half_gap)
            expected_left = [float(center[0]) - half_gap, join_y]
            expected_right = [float(center[0]) + half_gap, join_y]
            if _distance(check["left_join"], expected_left) > tol["endpoint"]:
                errors.append(f"{cid}: left leg does not join the circular arc directly")
            if _distance(check["right_join"], expected_right) > tol["endpoint"]:
                errors.append(f"{cid}: right leg does not join the circular arc directly")
            if float(check["left_leg_end"][1]) <= join_y or float(check["right_leg_end"][1]) <= join_y:
                errors.append(f"{cid}: legs do not extend beyond the circular-arc junction")
            if int(check.get("actual_anchor_count", -1)) != 7:
                errors.append(f"{cid}: expected exactly 7 anchors for two legs plus the circular crown")
            if int(check.get("transition_anchor_count", -1)) != 0:
                errors.append(f"{cid}: transition anchors are forbidden between regular primitives")

        elif kind == "ellipse_band":
            center = [float(v) for v in check["center"]]
            radii = [float(v) for v in check["radii"]]
            depth = float(check["depth"])
            if radii[0] <= 0 or radii[1] <= 0 or depth <= 0:
                errors.append(f"{cid}: ellipse radii and band depth must be positive")
                continue
            left_join = [center[0] - radii[0], center[1]]
            right_join = [center[0] + radii[0], center[1]]
            expected_left_drop = [left_join[0], left_join[1] + depth]
            expected_right_drop = [right_join[0], right_join[1] + depth]
            expected_front_bottom = [center[0], center[1] + depth + radii[1]]
            if _distance(check["left_join"], left_join) > tol["endpoint"]:
                errors.append(f"{cid}: left side is not joined to the shared ellipse extremum")
            if _distance(check["right_join"], right_join) > tol["endpoint"]:
                errors.append(f"{cid}: right side is not joined to the shared ellipse extremum")
            if _distance(check["left_drop"], expected_left_drop) > tol["band_depth"]:
                errors.append(f"{cid}: left side depth does not match the declared band depth")
            if _distance(check["right_drop"], expected_right_drop) > tol["band_depth"]:
                errors.append(f"{cid}: right side depth does not match the declared band depth")
            if _distance(check["front_arc_left"], expected_left_drop) > tol["endpoint"]:
                errors.append(f"{cid}: front arc does not start at the left side endpoint")
            if _distance(check["front_arc_right"], expected_right_drop) > tol["endpoint"]:
                errors.append(f"{cid}: front arc does not end at the right side endpoint")
            if _distance(check["front_arc_bottom"], expected_front_bottom) > tol["band_depth"]:
                errors.append(f"{cid}: front arc is not derived from the shared ellipse family")
            if not check.get("derived_from_shared_ellipse", False):
                errors.append(f"{cid}: independently drawn band curves are forbidden")

        elif kind == "parallel_ellipse_strip":
            center = [float(v) for v in check["source_center"]]
            radii = [float(v) for v in check["source_radii"]]
            x_range = [float(v) for v in check["x_range"]]
            depth = float(check["depth"])
            if radii[0] <= 0 or radii[1] <= 0 or depth <= 0 or x_range[0] >= x_range[1]:
                errors.append(f"{cid}: source ellipse, crop range, and strip depth must be positive")
                continue

            def ellipse_lower_y(x: float) -> float:
                ratio = (x - center[0]) / radii[0]
                if abs(ratio) > 1:
                    return float("nan")
                return center[1] + radii[1] * math.sqrt(max(0.0, 1 - ratio * ratio))

            top_left = [x_range[0], ellipse_lower_y(x_range[0])]
            top_right = [x_range[1], ellipse_lower_y(x_range[1])]
            if not math.isfinite(top_left[1]) or not math.isfinite(top_right[1]):
                errors.append(f"{cid}: crop range extends outside the source ellipse")
                continue
            bottom_left = [top_left[0], top_left[1] + depth]
            bottom_right = [top_right[0], top_right[1] + depth]
            for label, actual, expected in (
                ("top-left", check["top_left"], top_left),
                ("top-right", check["top_right"], top_right),
                ("bottom-left", check["bottom_left"], bottom_left),
                ("bottom-right", check["bottom_right"], bottom_right),
            ):
                if _distance(actual, expected) > tol["endpoint"]:
                    errors.append(f"{cid}: {label} corner is not derived from the duplicated ellipse")
            left_drop = float(check["bottom_left"][1]) - float(check["top_left"][1])
            right_drop = float(check["bottom_right"][1]) - float(check["top_right"][1])
            if abs(left_drop - depth) > tol["band_depth"] or abs(right_drop - depth) > tol["band_depth"]:
                errors.append(f"{cid}: strip side drops do not match the shared translation depth")
            if not check.get("derived_from_duplicated_ellipse", False):
                errors.append(f"{cid}: strip curves must come from one ellipse and its translated duplicate")

        elif kind == "boundary_attachment":
            if _distance(check["endpoint"], check["boundary_point"]) > tol["endpoint"]:
                errors.append(f"{cid}: endpoint does not meet the final enclosure boundary")
            if not check.get("final_outline_above", False):
                errors.append(f"{cid}: final enclosure outline must be above the attached stroke")
            if check.get("attachment_mode") not in {"exact", "underlap"}:
                errors.append(f"{cid}: attachment_mode must be 'exact' or 'underlap'")

        elif kind == "offset_ring":
            outer = [float(v) for v in check["outer_bounds"]]
            inner = [float(v) for v in check["inner_bounds"]]
            expected = float(check["expected_inset"])
            if outer[0] >= outer[2] or outer[1] >= outer[3] or inner[0] >= inner[2] or inner[1] >= inner[3]:
                errors.append(f"{cid}: ring bounds must have positive size")
                continue
            if inner[0] < outer[0] or inner[1] < outer[1] or inner[2] > outer[2] or inner[3] > outer[3]:
                errors.append(f"{cid}: inner contour is not contained by the outer contour")
            insets = {
                "left": inner[0] - outer[0],
                "top": inner[1] - outer[1],
                "right": outer[2] - inner[2],
                "bottom": outer[3] - inner[3],
            }
            for side in check.get("visible_sides", ["left", "top", "right", "bottom"]):
                if side not in insets:
                    errors.append(f"{cid}: unsupported visible side {side!r}")
                elif abs(insets[side] - expected) > tol["offset"]:
                    errors.append(f"{cid}: {side} inset is not the declared offset")
            if not check.get("constructed_as_compound", False):
                errors.append(f"{cid}: ring must be a compound/offset construction")

        elif kind == "tangent_circle_base":
            center = [float(v) for v in check["center"]]
            radius = float(check["radius"])
            if radius <= 0:
                errors.append(f"{cid}: circle radius must be positive")
                continue
            for side in ("left", "right"):
                line = check[f"{side}_line"]
                join = check[f"{side}_join"]
                if abs(_distance(join, center) - radius) > tol["circle"]:
                    errors.append(f"{cid}: {side} join is not on the declared circle")
                if _point_line_distance(join, line) > tol["endpoint"]:
                    errors.append(f"{cid}: {side} join is not on the straight taper line")
                if abs(_point_line_distance(center, line) - radius) > tol["circle"]:
                    errors.append(f"{cid}: {side} taper line is not tangent to the circle")
                lv = [line[1][0] - line[0][0], line[1][1] - line[0][1]]
                rv = [join[0] - center[0], join[1] - center[1]]
                denom = math.hypot(*lv) * math.hypot(*rv)
                if denom == 0 or abs((lv[0] * rv[0] + lv[1] * rv[1]) / denom) > tol["tangent"]:
                    errors.append(f"{cid}: {side} line and circular arc do not share a tangent")
            if _distance(check["bottom"], [center[0], center[1] + radius]) > tol["endpoint"]:
                errors.append(f"{cid}: bottom point is not the exact circle nadir")
            if not check.get("built_from_standard_circle", False):
                errors.append(f"{cid}: rounded base must retain standard-circle provenance")

        elif kind == "fill_boundary_underlap":
            underlap = float(check.get("underlap", 0))
            minimum = float(check.get("minimum_underlap", 0))
            if underlap < minimum:
                errors.append(f"{cid}: fill does not bleed far enough beneath the boundary stroke")
            if not check.get("clipped_to_enclosure", False):
                errors.append(f"{cid}: boundary fill must use the enclosure as a clipping/intersection source")
            if not check.get("final_outline_above", False):
                errors.append(f"{cid}: final outline must sit above the boundary fill")

        elif kind == "occlusion_trim":
            axis = check.get("axis")
            if axis not in {"x", "y"}:
                errors.append(f"{cid}: occlusion axis must be 'x' or 'y'")
                continue
            index = 0 if axis == "x" else 1
            endpoint = float(check["hidden_endpoint"][index])
            boundary = float(check["cover_boundary"])
            maximum = float(check.get("max_underlap", 1.0))
            direction = check.get("hidden_direction")
            underlap = endpoint - boundary if direction == "positive" else boundary - endpoint
            if direction not in {"positive", "negative"}:
                errors.append(f"{cid}: hidden_direction must be 'positive' or 'negative'")
            elif underlap < 0 or underlap > maximum:
                errors.append(f"{cid}: hidden endpoint is not narrowly trimmed beneath the occluder")
            if check.get("crosses_visible_seam", True):
                errors.append(f"{cid}: hidden connector crosses a visible seam")

        elif kind == "mirror_symmetry":
            mode = check.get("mode")
            center = [float(v) for v in check["center"]]
            if mode not in {"vertical", "horizontal", "central"}:
                errors.append(f"{cid}: symmetry mode must be vertical, horizontal, or central")
                continue
            pairs = check.get("pairs", [])
            if not pairs:
                errors.append(f"{cid}: no mirrored point pairs declared")
            for index, pair in enumerate(pairs):
                a = [float(v) for v in pair["a"]]
                b = [float(v) for v in pair["b"]]
                if mode == "vertical":
                    expected = [2 * center[0] - a[0], a[1]]
                elif mode == "horizontal":
                    expected = [a[0], 2 * center[1] - a[1]]
                else:
                    expected = [2 * center[0] - a[0], 2 * center[1] - a[1]]
                if _distance(b, expected) > tol["endpoint"]:
                    errors.append(f"{cid}: point pair {index + 1} is not symmetric")
            if not check.get("constructed_by_reflection", False):
                errors.append(f"{cid}: symmetric geometry must be constructed by reflection/duplication")

        elif kind == "translated_depth_copy":
            vector = [float(v) for v in check["translation"]]
            source = check.get("source_points", [])
            translated = check.get("translated_points", [])
            if len(source) != len(translated) or not source:
                errors.append(f"{cid}: depth copy point lists must be non-empty and equal in length")
                continue
            for index, (a, b) in enumerate(zip(source, translated)):
                expected = [float(a[0]) + vector[0], float(a[1]) + vector[1]]
                if _distance(b, expected) > tol["endpoint"]:
                    errors.append(f"{cid}: translated point {index + 1} does not match the extrusion vector")
            if not check.get("shared_geometry_source", False):
                errors.append(f"{cid}: depth face must be a translated duplicate of the source geometry")

        elif kind == "layered_3d_lighting":
            light = [float(v) for v in check["light_vector"]]
            center = [float(v) for v in check["object_center"]]
            highlight = [float(v) for v in check["highlight_center"]]
            shadow = [float(v) for v in check["shadow_center"]]
            hdot = (highlight[0] - center[0]) * light[0] + (highlight[1] - center[1]) * light[1]
            sdot = (shadow[0] - center[0]) * light[0] + (shadow[1] - center[1]) * light[1]
            if math.hypot(*light) == 0:
                errors.append(f"{cid}: light vector must be non-zero")
            if hdot <= 0 or sdot >= 0:
                errors.append(f"{cid}: highlight and shadow zones contradict the declared light direction")
            lum_h = _luminance(check["highlight_color"])
            lum_b = _luminance(check["base_color"])
            lum_s = _luminance(check["shadow_color"])
            if not all(math.isfinite(v) for v in (lum_h, lum_b, lum_s)) or not (lum_h > lum_b > lum_s):
                errors.append(f"{cid}: expected highlight luminance > base luminance > shadow luminance")
            faces = check.get("face_ids", [])
            if len(set(faces)) < int(check.get("minimum_distinct_faces", 3)):
                errors.append(f"{cid}: insufficient distinct light/shadow/depth faces")
            if not check.get("shared_geometry_source", False):
                errors.append(f"{cid}: light faces must be derived from the same object geometry")
            if not check.get("occlusion_clipped", False):
                errors.append(f"{cid}: 3D faces must respect the object's occlusion boundary")

        elif kind == "specular_highlight":
            if int(check.get("layer_count", 0)) < 2:
                errors.append(f"{cid}: a curved specular highlight needs at least a soft and a core layer")
            if float(check.get("width_ratio", 1)) > float(check.get("maximum_width_ratio", 0.25)):
                errors.append(f"{cid}: specular strip is too wide for the host surface")
            for flag, message in (
                ("clipped_to_surface", "highlight must be clipped to the host surface"),
                ("follows_surface_contour", "highlight must follow surface curvature"),
                ("edge_falloff", "highlight requires transparent/gradient edge falloff"),
                ("rounded_or_tapered_ends", "highlight ends must taper or round naturally"),
            ):
                if not check.get(flag, False):
                    errors.append(f"{cid}: {message}")

        elif kind == "shaded_2d_illusion":
            if int(check.get("silhouette_count", 0)) != 1:
                errors.append(f"{cid}: shaded-2D mode must retain exactly one visible silhouette")
            if not check.get("no_extruded_duplicate", False):
                errors.append(f"{cid}: shaded-2D mode forbids an offset/extruded duplicate silhouette")
            if not check.get("shading_clipped_inside", False):
                errors.append(f"{cid}: all depth shading must remain inside the original 2D silhouette")
            before = [float(v) for v in check["outer_bounds_before"]]
            after = [float(v) for v in check["outer_bounds_after"]]
            if len(before) != 4 or len(after) != 4 or max(abs(a - b) for a, b in zip(before, after)) > tol["endpoint"]:
                errors.append(f"{cid}: depth styling changed the outer silhouette bounds")
            if int(check.get("shading_layer_count", 0)) < 3:
                errors.append(f"{cid}: shaded-2D mode requires highlight, base/midtone, and shadow layers")
            lum_h = _luminance(check["highlight_color"])
            lum_b = _luminance(check["base_color"])
            lum_s = _luminance(check["shadow_color"])
            if not all(math.isfinite(v) for v in (lum_h, lum_b, lum_s)) or not (lum_h > lum_b > lum_s):
                errors.append(f"{cid}: shaded-2D luminance must descend from highlight to base to shadow")
            if not check.get("light_direction_consistent", False):
                errors.append(f"{cid}: internal highlight and shadow do not share one light direction")

        elif kind == "occlusion_stack":
            if not check.get("back_drawn_before_front", False):
                errors.append(f"{cid}: rear component must be drawn below the covering component")
            if not check.get("hidden_segments_clipped_or_covered", False):
                errors.append(f"{cid}: hidden rear segments are not clipped or covered")
            if not check.get("front_outline_above", False):
                errors.append(f"{cid}: covering component's final outline must be above the rear component")
            if int(check.get("visible_protrusion_count", 1)) != 0:
                errors.append(f"{cid}: rear geometry protrudes through the covering component")
            if not check.get("source_geometry_retained", False):
                errors.append(f"{cid}: occlusion must not deform the rear source geometry to fake the overlap")

        elif kind == "straight_line":
            points = check["points"]
            axis = check["axis"]
            values = [p[1] if axis == "horizontal" else p[0] for p in points]
            if max(values) - min(values) > tol["straight"]:
                errors.append(f"{cid}: line is not {axis}")

        elif kind == "parallel_pair":
            a = check["line_a"]
            b = check["line_b"]
            axis = check["axis"]
            fixed_a = [p[1] if axis == "horizontal" else p[0] for p in a]
            fixed_b = [p[1] if axis == "horizontal" else p[0] for p in b]
            if max(fixed_a) - min(fixed_a) > tol["straight"]:
                errors.append(f"{cid}: first backbone is not straight")
            if max(fixed_b) - min(fixed_b) > tol["straight"]:
                errors.append(f"{cid}: second backbone is not straight")
            gap_start = abs(fixed_a[0] - fixed_b[0])
            gap_end = abs(fixed_a[-1] - fixed_b[-1])
            if abs(gap_start - gap_end) > tol["parallel"]:
                errors.append(f"{cid}: backbone gap is not constant")

        elif kind == "centered":
            if _distance(check["actual_center"], check["target_center"]) > tol["center"]:
                errors.append(f"{cid}: optical center is outside tolerance")

        elif kind == "inside":
            b = check["bounds"]
            c = check["container"]
            gap = check.get("clearance", tol["clearance"])
            if b[0] < c[0] + gap or b[1] < c[1] + gap or b[2] > c[2] - gap or b[3] > c[3] - gap:
                errors.append(f"{cid}: object is not safely contained")

        elif kind == "arrow":
            if _distance(check["shaft_end"], check["head_base"]) > tol["endpoint"]:
                errors.append(f"{cid}: arrow shaft does not end at the head base")
            for index, obstacle in enumerate(check.get("forbidden_bounds", [])):
                if _bbox_intersects(check["bounds"], obstacle, check.get("clearance", tol["clearance"])):
                    errors.append(f"{cid}: arrow collides with obstacle {index + 1}")

        elif kind == "master_instances":
            master_id = check["master_id"]
            instances = check.get("instances", [])
            expected_count = check.get("expected_count")
            if expected_count is not None and len(instances) != expected_count:
                errors.append(f"{cid}: expected {expected_count} instances, found {len(instances)}")
            if not instances:
                errors.append(f"{cid}: no master instances declared")
            allowed = {"id", "master_id", "position", "scale", "rotation"}
            for index, instance in enumerate(instances):
                label = instance.get("id", str(index + 1))
                if instance.get("master_id") != master_id:
                    errors.append(f"{cid}/{label}: instance does not use master {master_id!r}")
                scale = instance.get("scale", [1.0, 1.0])
                if not isinstance(scale, list) or len(scale) != 2:
                    errors.append(f"{cid}/{label}: scale must be [x, y]")
                elif abs(float(scale[0]) - float(scale[1])) > tol["uniform_scale"]:
                    errors.append(f"{cid}/{label}: non-uniform scaling changes the master geometry")
                unexpected = set(instance) - allowed
                if unexpected:
                    errors.append(f"{cid}/{label}: forbidden instance overrides {sorted(unexpected)}")

        else:
            errors.append(f"{cid}: unsupported check type {kind!r}")

    if not contract.get("checks"):
        errors.append("contract: no checks declared")
    return errors


def self_test() -> None:
    good = {
        "checks": [
            {"id": "c", "type": "circle", "bounds": [0, 0, 40, 40]},
            {"id": "arch", "type": "open_circular_arch", "center": [20, 20], "radius": 10,
             "half_gap": 6, "left_join": [14, 28], "right_join": [26, 28],
             "left_leg_end": [14, 42], "right_leg_end": [26, 48],
             "actual_anchor_count": 7, "transition_anchor_count": 0},
            {"id": "l", "type": "straight_line", "axis": "horizontal", "points": [[0, 5], [20, 5]]},
            {"id": "band", "type": "ellipse_band", "center": [50, 20], "radii": [30, 8], "depth": 12,
             "left_join": [20, 20], "right_join": [80, 20], "left_drop": [20, 32], "right_drop": [80, 32],
             "front_arc_left": [20, 32], "front_arc_right": [80, 32], "front_arc_bottom": [50, 40],
             "derived_from_shared_ellipse": True},
            {"id": "ellipse-strip", "type": "parallel_ellipse_strip", "source_center": [50, 20],
             "source_radii": [30, 10], "x_range": [20, 80], "depth": 12,
             "top_left": [20, 20], "top_right": [80, 20],
             "bottom_left": [20, 32], "bottom_right": [80, 32],
             "derived_from_duplicated_ellipse": True},
            {"id": "attach", "type": "boundary_attachment", "endpoint": [20, 5], "boundary_point": [20, 5],
             "attachment_mode": "underlap", "final_outline_above": True},
            {"id": "ring", "type": "offset_ring", "outer_bounds": [0, 0, 60, 40], "inner_bounds": [8, 8, 52, 32],
             "expected_inset": 8, "visible_sides": ["left", "top", "right", "bottom"], "constructed_as_compound": True},
            {"id": "round-base", "type": "tangent_circle_base", "center": [20, 20], "radius": 10,
             "left_line": [[0, 14.142136], [12.928932, 27.071068]], "right_line": [[40, 14.142136], [27.071068, 27.071068]],
             "left_join": [12.928932, 27.071068], "right_join": [27.071068, 27.071068], "bottom": [20, 30],
             "built_from_standard_circle": True},
            {"id": "fill-edge", "type": "fill_boundary_underlap", "underlap": 1.2, "minimum_underlap": 1,
             "clipped_to_enclosure": True, "final_outline_above": True},
            {"id": "trim", "type": "occlusion_trim", "axis": "x", "hidden_endpoint": [10.5, 5],
             "cover_boundary": 10, "hidden_direction": "positive", "max_underlap": 1, "crosses_visible_seam": False},
            {"id": "symmetry", "type": "mirror_symmetry", "mode": "vertical", "center": [10, 5],
             "pairs": [{"a": [4, 2], "b": [16, 2]}, {"a": [6, 9], "b": [14, 9]}],
             "constructed_by_reflection": True},
            {"id": "depth-copy", "type": "translated_depth_copy", "translation": [0, 4],
             "source_points": [[0, 0], [10, 0]], "translated_points": [[0, 4], [10, 4]],
             "shared_geometry_source": True},
            {"id": "light-model", "type": "layered_3d_lighting", "light_vector": [-1, -1],
             "object_center": [10, 10], "highlight_center": [6, 6], "shadow_center": [14, 14],
             "highlight_color": "#F8F8F8", "base_color": "#D0D0D0", "shadow_color": "#888888",
             "face_ids": ["base", "highlight", "shadow"], "minimum_distinct_faces": 3,
             "shared_geometry_source": True, "occlusion_clipped": True},
            {"id": "specular", "type": "specular_highlight", "layer_count": 2,
             "width_ratio": 0.14, "maximum_width_ratio": 0.2, "clipped_to_surface": True,
             "follows_surface_contour": True, "edge_falloff": True, "rounded_or_tapered_ends": True},
            {"id": "shaded-2d", "type": "shaded_2d_illusion", "silhouette_count": 1,
             "no_extruded_duplicate": True, "shading_clipped_inside": True,
             "outer_bounds_before": [0, 0, 40, 20], "outer_bounds_after": [0, 0, 40, 20],
             "shading_layer_count": 4, "highlight_color": "#F8F8F8", "base_color": "#CCCCCC",
             "shadow_color": "#777777", "light_direction_consistent": True},
            {"id": "occlusion", "type": "occlusion_stack", "back_drawn_before_front": True,
             "hidden_segments_clipped_or_covered": True, "front_outline_above": True,
             "visible_protrusion_count": 0, "source_geometry_retained": True},
            {"id": "p", "type": "parallel_pair", "axis": "vertical", "line_a": [[4, 0], [4, 30]], "line_b": [[12, 0], [12, 30]]},
            {"id": "t", "type": "centered", "actual_center": [10, 10], "target_center": [10, 10]},
            {"id": "a", "type": "arrow", "shaft_end": [8, 5], "head_base": [8, 5], "bounds": [0, 4, 10, 6], "forbidden_bounds": []},
            {"id": "m", "type": "master_instances", "master_id": "motif-a", "expected_count": 2, "instances": [
                {"id": "i1", "master_id": "motif-a", "position": [0, 0], "scale": [1, 1], "rotation": 0},
                {"id": "i2", "master_id": "motif-a", "position": [10, 0], "scale": [0.5, 0.5], "rotation": 90},
            ]},
        ]
    }
    bad = {"checks": [
        {"id": "bad-circle", "type": "circle", "bounds": [0, 0, 40, 31]},
        {"id": "bad-arch", "type": "open_circular_arch", "center": [20, 20], "radius": 10,
         "half_gap": 6, "left_join": [14, 32], "right_join": [26, 32],
         "left_leg_end": [14, 42], "right_leg_end": [26, 48],
         "actual_anchor_count": 9, "transition_anchor_count": 2},
        {"id": "bad-attach", "type": "boundary_attachment", "endpoint": [19, 5], "boundary_point": [20, 5],
         "attachment_mode": "exact", "final_outline_above": False},
        {"id": "bad-ring", "type": "offset_ring", "outer_bounds": [0, 0, 60, 40], "inner_bounds": [8, 4, 52, 32],
         "expected_inset": 8, "visible_sides": ["left", "top", "bottom"], "constructed_as_compound": False},
        {"id": "bad-fill-edge", "type": "fill_boundary_underlap", "underlap": 0.2, "minimum_underlap": 1,
         "clipped_to_enclosure": False, "final_outline_above": False},
        {"id": "bad-trim", "type": "occlusion_trim", "axis": "x", "hidden_endpoint": [18, 5],
         "cover_boundary": 10, "hidden_direction": "positive", "max_underlap": 1, "crosses_visible_seam": True},
        {"id": "bad-symmetry", "type": "mirror_symmetry", "mode": "vertical", "center": [10, 5],
         "pairs": [{"a": [4, 2], "b": [15, 3]}], "constructed_by_reflection": False},
        {"id": "bad-light", "type": "layered_3d_lighting", "light_vector": [-1, -1],
         "object_center": [10, 10], "highlight_center": [14, 14], "shadow_center": [6, 6],
         "highlight_color": "#777777", "base_color": "#AAAAAA", "shadow_color": "#EEEEEE",
         "face_ids": ["flat"], "minimum_distinct_faces": 3, "shared_geometry_source": False, "occlusion_clipped": False},
        {"id": "bad-specular", "type": "specular_highlight", "layer_count": 1,
         "width_ratio": 0.5, "maximum_width_ratio": 0.2, "clipped_to_surface": False,
         "follows_surface_contour": False, "edge_falloff": False, "rounded_or_tapered_ends": False},
        {"id": "bad-shaded-2d", "type": "shaded_2d_illusion", "silhouette_count": 2,
         "no_extruded_duplicate": False, "shading_clipped_inside": False,
         "outer_bounds_before": [0, 0, 40, 20], "outer_bounds_after": [-2, 2, 40, 24],
         "shading_layer_count": 1, "highlight_color": "#777777", "base_color": "#AAAAAA",
         "shadow_color": "#EEEEEE", "light_direction_consistent": False},
        {"id": "bad-occlusion", "type": "occlusion_stack", "back_drawn_before_front": False,
         "hidden_segments_clipped_or_covered": False, "front_outline_above": False,
         "visible_protrusion_count": 2, "source_geometry_retained": False},
    ]}
    assert not validate(good)
    assert validate(bad)
    print("geometry_preflight self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.contract is None:
        parser.error("contract JSON is required")
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    errors = validate(contract)
    result = {"status": "failed" if errors else "passed", "checks": len(contract.get("checks", [])), "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
