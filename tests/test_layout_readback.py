from copy import deepcopy
import json
from pathlib import Path

import pytest

from sciai_illustrator.layout import prepare_spec
from sciai_illustrator.schema import load_spec, validate_spec, SpecError
from sciai_illustrator.jsx_builder import build_jsx

EXAMPLE = Path(__file__).parents[1] / "examples" / "automatic-flow.json"


def source():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_horizontal_layout_and_boundary_endpoints():
    original = source()
    before = deepcopy(original)
    spec = prepare_spec(original)
    validate_spec(original)
    assert original == before
    assert prepare_spec(spec) == spec
    objects = {o["id"]: o for o in spec["objects"]}
    assert objects["process"]["x"] == 58
    assert objects["process-label"]["visual_center"] == [75, 25]
    assert objects["input-process"]["x1"] == 45.5
    assert objects["input-process"]["x2"] == 56.5
    assert objects["input-process"]["head_size"] == 2
    assert load_spec(EXAMPLE) == spec


def test_vertical_and_reverse_connections():
    spec = source()
    spec["canvas"]["height_mm"] = 130
    spec["layout"]["direction"] = "vertical"
    spec["connections"][0].update(source="process", target="input")
    objects = {o["id"]: o for o in prepare_spec(spec)["objects"]}
    assert objects["process"]["y"] == 49
    assert objects["input-process"]["y1"] == 47.5
    assert objects["input-process"]["y2"] == 36.5


@pytest.mark.parametrize("fault", ["duplicate", "reference", "overflow", "short", "crossing", "diagonal", "self", "missing", "nan"])
def test_unsafe_layouts_fail_explicitly(fault):
    spec = source()
    if fault == "duplicate": spec["objects"][1]["id"] = "input"
    if fault == "reference": spec["reference_image"] = {"path": "ref.png"}
    if fault == "overflow": spec["canvas"]["width_mm"] = 40
    if fault == "short": spec["layout"]["gap_mm"] = 2
    if fault == "crossing": spec["connections"][0]["target"] = "output"
    if fault == "diagonal":
        spec = prepare_spec(spec)
        spec["objects"] = [o for o in spec["objects"] if o["type"] != "arrow"]
        spec["objects"][1]["y"] += 2
        spec["connections"] = source()["connections"]
    if fault == "self": spec["connections"][0]["target"] = "input"
    if fault == "missing": spec["connections"][0]["source"] = "absent"
    if fault == "nan": spec["layout"]["gap_mm"] = float("nan")
    with pytest.raises(SpecError): validate_spec(spec)


def test_reference_coordinates_are_preserved_without_auto_layout():
    spec = prepare_spec(source())
    spec["reference_image"] = {"path": "ref.png", "layer": "01_Diagram"}
    assert prepare_spec(spec)["objects"] == spec["objects"]


def test_native_readback_precedes_final_save(tmp_path):
    jsx = build_jsx(source(), tmp_path / "flow.ai")
    assert 'doc.pageItems[i]' in jsx
    assert 'copy.createOutline()' in jsx
    assert 'glyphBounds(item' in jsx
    assert 'requested font unavailable or substituted' in jsx
    assert 'actual visible bounds exceed container/artboard' in jsx
    assert 'sciai:process-label' in jsx
    assert jsx.index('  readDocument([') < jsx.index('doc.saveAs(aiFile')
    assert 'flow.json' in jsx


def test_rotated_text_is_centered_after_its_transform(tmp_path):
    spec = source()
    spec["objects"][-1]["rotation_deg"] = 15
    jsx = build_jsx(spec, tmp_path / "flow.ai")
    assert jsx.index(".rotate(15)") < jsx.rindex(" = glyphBounds(")
