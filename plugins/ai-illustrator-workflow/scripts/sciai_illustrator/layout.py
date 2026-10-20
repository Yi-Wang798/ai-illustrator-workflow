"""Small, deterministic layout compiler; measured reference geometry is never reflowed."""
from __future__ import annotations

from copy import deepcopy
import math


def prepare_spec(source):
    from .schema import SpecError

    spec = deepcopy(source)
    if not isinstance(spec, dict):
        return spec
    objects = spec.get("objects", [])
    if not isinstance(objects, list):
        return spec
    seen = {}

    def visit(items, prefix="object"):
        if not isinstance(items, list):
            return
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            key = item.setdefault("id", f"{prefix}.{i}")
            if not isinstance(key, str) or not key.strip() or key in seen:
                raise SpecError(f"Object id must be nonempty and unique: {key!r}")
            seen[key] = item
            if item.get("type") == "group":
                visit(item.get("children", []), key)
    visit(objects)

    def number(value, label, minimum=None):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise SpecError(f"{label} must be finite")
        if minimum is not None and value < minimum:
            raise SpecError(f"{label} must be >= {minimum}")
        return value

    layout = spec.pop("layout", None)
    if layout is not None:
        if spec.get("reference_image"):
            raise SpecError("Automatic layout cannot reflow a measured reference; omit layout")
        if not isinstance(layout, dict) or layout.get("direction") not in {"horizontal", "vertical"}:
            raise SpecError("layout.direction must be horizontal or vertical")
        ids = layout.get("node_ids")
        if not isinstance(ids, list) or not ids or any(not isinstance(k, str) for k in ids) or len(set(ids)) != len(ids):
            raise SpecError("layout.node_ids must be a nonempty unique string list")
        origin = layout.get("origin", [10, 10])
        if not isinstance(origin, list) or len(origin) != 2:
            raise SpecError("layout.origin must be [x, y]")
        x, y = [number(v, "layout.origin") for v in origin]
        gap = number(layout.get("gap_mm", 12), "layout.gap_mm", 0.1)
        nodes = []
        for key in ids:
            node = seen.get(key)
            if node not in objects or node.get("type") not in {"rectangle", "rounded_rectangle", "ellipse"} or node.get("rotation_deg", 0):
                raise SpecError(f"Layout node {key} must be a top-level, unrotated primitive")
            number(node.get("width"), "node.width", 0.001)
            number(node.get("height"), "node.height", 0.001)
            nodes.append(node)
        horizontal = layout["direction"] == "horizontal"
        cross = max(n["height" if horizontal else "width"] for n in nodes)
        cursor = x if horizontal else y
        for node in nodes:
            node["x"] = cursor if horizontal else x + (cross - node["width"]) / 2
            node["y"] = y + (cross - node["height"]) / 2 if horizontal else cursor
            cursor += node["width" if horizontal else "height"] + gap
            canvas = spec.get("canvas", {})
            if node["x"] < 0 or node["y"] < 0 or node["x"] + node["width"] > canvas.get("width_mm", 0) or node["y"] + node["height"] > canvas.get("height_mm", 0):
                raise SpecError(f"Layout node {node['id']} exceeds canvas; enlarge canvas or reduce spacing")

    for item in list(seen.values()):
        if "container_id" not in item:
            continue
        if not isinstance(item["container_id"], str):
            raise SpecError("container_id must be a string")
        host = seen.get(item["container_id"])
        if item.get("type") != "text" or host not in objects or host.get("type") not in {"rectangle", "rounded_rectangle"} or host.get("rotation_deg", 0):
            raise SpecError("container_id requires text and a top-level unrotated rectangular container")
        number(item.get("padding_mm", 1), "padding_mm", 0)
        for field in ("x", "y", "width", "height"):
            number(host.get(field), "container." + field)
        item["x"], item["y"] = host["x"] + host["width"] / 2, host["y"] + host["height"] / 2
        item["visual_center"] = [item["x"], item["y"]]
        item["align"] = "center"

    connections = spec.pop("connections", [])
    if not isinstance(connections, list):
        raise SpecError("connections must be an array")
    arrows = []
    for edge_index, edge in enumerate(connections):
        if not isinstance(edge, dict):
            raise SpecError("Each connection must be an object")
        if not isinstance(edge.get("source"), str) or not isinstance(edge.get("target"), str):
            raise SpecError("Connection source and target must be string ids")
        a, b = seen.get(edge.get("source")), seen.get(edge.get("target"))
        if a is None or b is None or a is b:
            raise SpecError("Connection requires distinct existing source and target ids")
        for n in (a, b):
            if n not in objects or n.get("type") not in {"rectangle", "rounded_rectangle", "ellipse"} or n.get("rotation_deg", 0):
                raise SpecError("Connections support top-level unrotated primitives only")
            for field in ("x", "y", "width", "height"):
                number(n.get(field), "connection node." + field, 0.001 if field in {"width", "height"} else None)
        ax, ay = a["x"] + a["width"] / 2, a["y"] + a["height"] / 2
        bx, by = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
        dx, dy = bx - ax, by - ay
        if abs(dx) > 1e-8 and abs(dy) > 1e-8:
            raise SpecError("Only axis-aligned connections are automatic; use explicit paths for other routes")
        distance = math.hypot(dx, dy)
        if distance == 0:
            raise SpecError("Connection centers overlap")
        ux, uy = dx / distance, dy / distance
        da = a["width"] / 2 if dx else a["height"] / 2
        db = b["width"] / 2 if dx else b["height"] / 2
        clearance = number(edge.get("clearance_mm", 1), "clearance_mm", 0)
        head = number(edge.get("head_size", 2), "head_size", 0.001)
        if distance - da - db - 2 * clearance <= head:
            raise SpecError("Connection gap is too short for its arrowhead")
        arrow = {k: deepcopy(v) for k, v in edge.items() if k not in {"source", "target", "clearance_mm"}}
        arrow.setdefault("id", f"connection.{edge_index}")
        arrow.setdefault("name", arrow["id"])
        arrow["head_size"] = head
        arrow.update(type="arrow", x1=ax + ux * (da + clearance), y1=ay + uy * (da + clearance),
                     x2=bx - ux * (db + clearance), y2=by - uy * (db + clearance))
        # Do not route through unrelated nodes or silently invent a bent route.
        for n in objects:
            if n is a or n is b or n.get("type") not in {"rectangle", "rounded_rectangle", "ellipse"}:
                continue
            if dx and n["y"] <= ay <= n["y"] + n["height"] and max(min(arrow["x1"], arrow["x2"]), n["x"]) < min(max(arrow["x1"], arrow["x2"]), n["x"] + n["width"]):
                raise SpecError("Connection crosses an unrelated node; provide an explicit route")
            if dy and n["x"] <= ax <= n["x"] + n["width"] and max(min(arrow["y1"], arrow["y2"]), n["y"]) < min(max(arrow["y1"], arrow["y2"]), n["y"] + n["height"]):
                raise SpecError("Connection crosses an unrelated node; provide an explicit route")
        arrows.append(arrow)
    spec["objects"] = arrows + objects
    # Assign and validate identities for newly compiled connectors too.
    seen.clear()
    visit(spec["objects"])
    return spec
