import json
from pathlib import Path

from sciai_illustrator.cli import resolve_output_stem
from sciai_illustrator.jsx_builder import build_jsx


ROOT = Path(__file__).parents[1]
EXAMPLE = ROOT / "examples" / "basic-layout.json"


def test_builds_native_illustrator_objects(tmp_path):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    jsx = build_jsx(spec, tmp_path / "demo.ai", tmp_path / "demo.png")
    assert "app.documents.add" in jsx
    assert ".pathItems.ellipse" in jsx
    assert ".textFrames.pointText" in jsx
    assert ".groupItems.add" in jsx
    assert "IllustratorSaveOptions" in jsx
    assert "<svg" not in jsx.lower()


def test_escapes_text_as_js_string(tmp_path):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    spec["objects"][-1]["text"] = 'A "quoted" label\nline 2'
    jsx = build_jsx(spec, tmp_path / "demo.ai")
    assert 'A \\"quoted\\" label\\nline 2' in jsx


def test_output_is_automatically_versioned(tmp_path):
    output = tmp_path / "figure"
    output.with_suffix(".ai").write_bytes(b"existing")
    assert resolve_output_stem(output).name == "figure_v02"
    (tmp_path / "figure_v02.jsx").write_text("existing", encoding="utf-8")
    assert resolve_output_stem(output).name == "figure_v03"
    assert resolve_output_stem(output, force=True) == output


def test_builds_editable_smooth_wave(tmp_path):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    spec["objects"].append({
        "type": "wave",
        "name": "Smooth Wave",
        "layer": "03_Connections",
        "x": 10,
        "y": 10,
        "width": 20,
        "amplitude": 2,
        "cycles": 3,
        "style": {"stroke": "#1769AA", "stroke_width_mm": 0.7},
    })
    jsx = build_jsx(spec, tmp_path / "wave.ai")
    assert ".pathPoints.add()" in jsx
    assert "PointType.SMOOTH" in jsx
    assert "Smooth Wave" in jsx


def test_builds_vertical_smooth_wave(tmp_path):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    spec["objects"].append({
        "type": "wave", "name": "Vertical Tail", "layer": "03_Connections",
        "x": 10, "y": 10, "width": 20, "amplitude": 1, "cycles": 2,
        "orientation": "vertical", "style": {"stroke": "#F28B20"},
    })
    jsx = build_jsx(spec, tmp_path / "vertical-wave.ai")
    assert "Vertical Tail" in jsx
    assert "py(30)" in jsx


def test_builds_editable_bezier_path_with_round_stroke(tmp_path):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    spec["objects"].append({
        "type": "bezier_path", "name": "Smooth Contour", "layer": "03_Connections",
        "points": [
            {"anchor": [10, 30]},
            {"anchor": [10, 15], "right": [7, 10], "point_type": "smooth"},
            {"anchor": [20, 15], "left": [23, 10], "point_type": "smooth"},
            {"anchor": [20, 25]},
        ],
        "style": {"stroke": "#148C88", "stroke_width_mm": 0.8,
                  "stroke_cap": "round", "stroke_join": "round"},
    })
    jsx = build_jsx(spec, tmp_path / "contour.ai")
    assert "Smooth Contour" in jsx
    assert "PointType.SMOOTH" in jsx
    assert "StrokeCap.ROUNDENDCAP" in jsx
    assert "StrokeJoin.ROUNDENDJOIN" in jsx


def test_builds_open_circular_arch_without_transition_anchors(tmp_path):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    spec["objects"].append({
        "type": "open_circular_arch", "name": "Regular Arch", "layer": "03_Connections",
        "cx": 30, "cy": 20, "radius": 8, "half_gap": 3,
        "left_leg_end_y": 42, "right_leg_end_y": 48,
        "style": {"stroke": "#148C88", "stroke_width_mm": 0.8,
                  "stroke_cap": "round", "stroke_join": "round"},
    })
    jsx = build_jsx(spec, tmp_path / "arch.ai")
    arch_block = jsx[jsx.index('name = "Regular Arch"'):]
    assert "p6 =" in arch_block
    assert "p7 =" not in arch_block
    assert ".closed = false" in arch_block
    assert "PointType.CORNER" in arch_block
    assert "PointType.SMOOTH" in arch_block


def test_builds_center_aligned_text(tmp_path):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    spec["objects"].append({
        "type": "text", "name": "Centered", "layer": "04_Labels",
        "x": 90, "y": 20, "text": "Centered", "align": "center",
    })
    jsx = build_jsx(spec, tmp_path / "centered.ai")
    assert "Justification.CENTER" in jsx


def test_defaults_text_to_noto_sans_sc(tmp_path):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    spec["objects"].append({
        "type": "text", "name": "Default font", "layer": "04_Labels",
        "x": 20, "y": 20, "text": "默认字体",
    })
    jsx = build_jsx(spec, tmp_path / "noto.ai")
    assert "NotoSansSC-Regular" in jsx


def test_hides_locked_reference_in_clean_output(tmp_path):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    spec["layers"].insert(0, {"name": "00_Reference"})
    spec["reference_image"] = {
        "path": "reference.png", "layer": "00_Reference", "opacity": 30,
        "visible_in_output": False,
    }
    jsx = build_jsx(spec, tmp_path / "clean.ai")
    assert 'layers["00_Reference"].locked = true' in jsx
    assert 'layers["00_Reference"].visible = false' in jsx


def test_builds_gradient_group_rotation_and_visual_center(tmp_path):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    spec["objects"].append({
        "type": "group", "name": "Angled motif", "layer": "03_Connections",
        "rotation_deg": 12,
        "children": [{
            "type": "rectangle", "name": "Gradient body",
            "x": 10, "y": 10, "width": 20, "height": 8,
            "style": {"fill_gradient": {"type": "linear", "angle_deg": 90,
                "stops": [{"offset": 0, "color": "#FFFFFF"},
                          {"offset": 100, "color": "#778899"}]}}
        }],
    })
    spec["objects"].append({
        "type": "text", "name": "Visually centered", "layer": "04_Labels",
        "x": 50, "y": 50, "text": "Centered", "align": "center",
        "visual_center": [50, 50],
    })
    jsx = build_jsx(spec, tmp_path / "calibrated.ai")
    assert "applyGradient" in jsx
    assert ".rotate(12)" in jsx
    assert ".visibleBounds" in jsx
