import copy
import json
from pathlib import Path

import pytest

from sciai_illustrator.schema import SpecError, load_spec, validate_spec


EXAMPLE = Path(__file__).parents[1] / "examples" / "basic-layout.json"


def example_spec():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_example_is_valid():
    load_spec(EXAMPLE)


def test_rejects_unknown_object_type():
    spec = example_spec()
    spec["objects"][0]["type"] = "raw_js"
    with pytest.raises(SpecError, match="不支持"):
        validate_spec(spec)


def test_rejects_unknown_layer():
    spec = example_spec()
    spec["objects"][0]["layer"] = "Missing"
    with pytest.raises(SpecError, match="未声明图层"):
        validate_spec(spec)


def test_group_children_inherit_layer():
    spec = example_spec()
    grouped = copy.deepcopy(spec["objects"][2])
    assert all("layer" not in child for child in grouped["children"])
    validate_spec(spec)


def test_wave_requires_integer_cycles():
    spec = example_spec()
    spec["objects"].append({
        "type": "wave", "name": "bad wave", "layer": "03_Connections",
        "x": 10, "y": 10, "width": 10, "amplitude": 2, "cycles": 2.5,
    })
    with pytest.raises(SpecError, match="cycles 必须是整数"):
        validate_spec(spec)


def test_wave_rejects_unknown_orientation():
    spec = example_spec()
    spec["objects"].append({
        "type": "wave", "name": "bad direction", "layer": "03_Connections",
        "x": 10, "y": 10, "width": 10, "amplitude": 2, "cycles": 2,
        "orientation": "diagonal",
    })
    with pytest.raises(SpecError, match="orientation"):
        validate_spec(spec)


def test_bezier_path_requires_two_points():
    spec = example_spec()
    spec["objects"].append({
        "type": "bezier_path", "name": "bad path", "layer": "03_Connections",
        "points": [{"anchor": [10, 10]}],
    })
    with pytest.raises(SpecError, match="at least two"):
        validate_spec(spec)


def test_bezier_path_rejects_invalid_handle():
    spec = example_spec()
    spec["objects"].append({
        "type": "bezier_path", "name": "bad handle", "layer": "03_Connections",
        "points": [{"anchor": [10, 10]}, {"anchor": [20, 20], "left": [12]}],
    })
    with pytest.raises(SpecError, match="must be \\[x, y\\]"):
        validate_spec(spec)


def test_open_circular_arch_requires_gap_smaller_than_radius():
    spec = example_spec()
    spec["objects"].append({
        "type": "open_circular_arch", "name": "bad arch", "layer": "03_Connections",
        "cx": 20, "cy": 20, "radius": 8, "half_gap": 8,
        "left_leg_end_y": 40, "right_leg_end_y": 45,
    })
    with pytest.raises(SpecError, match="half_gap"):
        validate_spec(spec)


def test_open_circular_arch_requires_legs_below_arc_junction():
    spec = example_spec()
    spec["objects"].append({
        "type": "open_circular_arch", "name": "bad legs", "layer": "03_Connections",
        "cx": 20, "cy": 20, "radius": 8, "half_gap": 3,
        "left_leg_end_y": 25, "right_leg_end_y": 26,
    })
    with pytest.raises(SpecError, match="leg endpoints"):
        validate_spec(spec)


def test_text_rejects_invalid_alignment():
    spec = example_spec()
    spec["objects"].append({
        "type": "text", "name": "bad alignment", "layer": "04_Labels",
        "x": 10, "y": 10, "text": "label", "align": "middle",
    })
    with pytest.raises(SpecError, match="align"):
        validate_spec(spec)


def test_reference_visibility_flag_must_be_boolean():
    spec = example_spec()
    spec["reference_image"] = {
        "path": "reference.png", "layer": "01_Background", "visible_in_output": "no",
    }
    with pytest.raises(SpecError, match="visible_in_output"):
        validate_spec(spec)


def test_rejects_invalid_gradient_stop_order():
    spec = example_spec()
    spec["objects"][0]["style"]["fill_gradient"] = {
        "type": "linear",
        "stops": [
            {"offset": 80, "color": "#FFFFFF"},
            {"offset": 20, "color": "#000000"},
        ],
    }
    with pytest.raises(SpecError, match="offsets"):
        validate_spec(spec)


def test_text_visual_center_must_be_coordinate_pair():
    spec = example_spec()
    spec["objects"].append({
        "type": "text", "name": "bad center", "layer": "04_Labels",
        "x": 10, "y": 10, "text": "label", "visual_center": [10],
    })
    with pytest.raises(SpecError, match="visual_center"):
        validate_spec(spec)
