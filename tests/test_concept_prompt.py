"""Contract safety and shared-content preservation, without paid image calls."""
import copy
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/ai-illustrator-workflow/skills/scientific-ai-illustrator/scripts/concept_prompt.py"
module_spec = importlib.util.spec_from_file_location("concept_prompt", SCRIPT)
module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(module)


def contract():
    return {
        "message": "A switches B from bound to released.",
        "audience": "researchers", "figure_type": "state comparison",
        "aspect_ratio": "3:2", "reading_order": "before then after",
        "evidence_boundary": "Symbolic; no quantitative claim.",
        "entities": [{"id": "b", "label": "B", "color": "#0072B2",
                      "representation": "two parallel lines", "construction": "line tool plus duplicated rungs"}],
        "panels": [{"id": "p1", "role": "before", "states": [{"entity": "b", "state": "bound"}]},
                   {"id": "p2", "role": "after", "states": [{"entity": "b", "state": "released"}]}],
        "invariants": ["B keeps its shape and color."],
        "variants": [{"id": str(i), "layout": f"layout {i}", "focal_element": "release",
                      "label_placement": "outside contours with clear arrow gap"} for i in range(1, 6)],
        "labels": ["B"],
    }


def test_five_prompts_share_semantics_but_have_distinct_layouts():
    spec = contract()
    before = copy.deepcopy(spec)
    output = module.compile_prompts(spec)
    assert len(output["candidates"]) == 5
    prompts = [x["prompt"] for x in output["candidates"]]
    assert len(set(prompts)) == 5
    shared = [x.split("This candidate's composition:")[0] for x in prompts]
    assert len(set(shared)) == 1
    assert all("bound" in p and "released" in p and "#0072B2" in p for p in prompts)
    assert all(x["review"]["status"] == "unreviewed" for x in output["candidates"])
    assert spec == before


def test_missing_recipe_blocks_generation_plan():
    spec = contract()
    del spec["entities"][0]["construction"]
    with pytest.raises(module.ContractError, match="construction"):
        module.compile_prompts(spec)


def test_unknown_state_entity_is_rejected():
    spec = contract()
    spec["panels"][0]["states"][0]["entity"] = "invented"
    with pytest.raises(module.ContractError, match="unknown entity"):
        module.compile_prompts(spec)


def test_relationship_cannot_point_to_an_absent_entity():
    spec = contract()
    spec["panels"][0]["relationships"] = [{"from": "b", "to": "missing", "meaning": "binds"}]
    with pytest.raises(module.ContractError, match="no visible entity state"):
        module.compile_prompts(spec)


@pytest.mark.parametrize("mutation", ["four", "duplicate_id", "duplicate_layout"])
def test_missing_or_duplicate_choices_are_rejected(mutation):
    spec = contract()
    if mutation == "four":
        spec["variants"].pop()
    elif mutation == "duplicate_id":
        spec["variants"][1]["id"] = spec["variants"][0]["id"]
    else:
        spec["variants"][1]["layout"] = spec["variants"][0]["layout"]
    with pytest.raises(module.ContractError):
        module.compile_prompts(spec)


def test_labels_cannot_be_accidentally_treated_as_characters():
    spec = contract()
    spec["labels"] = "B"
    with pytest.raises(module.ContractError, match="labels"):
        module.compile_prompts(spec)
