"""Compile a shared editable-figure contract into five built-in image prompts.

No network, image generation, model selection, or visual validation is performed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


class ContractError(ValueError):
    pass


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{where}: expected non-empty text")
    return value.strip()


def _records(value: Any, where: str) -> list[dict]:
    if not isinstance(value, list) or not value or not all(isinstance(x, dict) for x in value):
        raise ContractError(f"{where}: expected non-empty list of objects")
    return value


def _ids(records: list[dict], where: str) -> set[str]:
    ids = [_text(x.get("id"), f"{where}.id") for x in records]
    if len(set(ids)) != len(ids):
        raise ContractError(f"{where}: duplicate IDs")
    return set(ids)


def validate_contract(spec: Any) -> None:
    if not isinstance(spec, dict):
        raise ContractError("contract: expected object")
    if "scientific" in spec and not isinstance(spec["scientific"], bool):
        raise ContractError("scientific: expected boolean")
    for key in ("message", "audience", "figure_type", "aspect_ratio", "reading_order", "evidence_boundary"):
        _text(spec.get(key), key)
    entities = _records(spec.get("entities"), "entities")
    entity_ids = _ids(entities, "entities")
    for entity in entities:
        for key in ("label", "representation", "construction"):
            _text(entity.get(key), f"entity {entity['id']}.{key}")
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(entity.get("color", ""))):
            raise ContractError(f"entity {entity['id']}.color: expected #RRGGBB")
    panels = _records(spec.get("panels"), "panels")
    _ids(panels, "panels")
    for panel in panels:
        _text(panel.get("role"), f"panel {panel['id']}.role")
        states = _records(panel.get("states"), f"panel {panel['id']}.states")
        seen = set()
        for state in states:
            entity = _text(state.get("entity"), "state.entity")
            if entity not in entity_ids:
                raise ContractError(f"panel {panel['id']}: unknown entity {entity}")
            if entity in seen:
                raise ContractError(f"panel {panel['id']}: duplicate entity state {entity}; describe repeated copies in one state")
            seen.add(entity)
            _text(state.get("state"), f"panel {panel['id']}.{entity}.state")
        relations = panel.get("relationships", [])
        if not isinstance(relations, list):
            raise ContractError("relationships: expected list")
        for relation in relations:
            if not isinstance(relation, dict):
                raise ContractError("relationship: expected object")
            for end in ("from", "to"):
                if relation.get(end) not in seen:
                    raise ContractError(f"panel {panel['id']}: relationship {end} has no visible entity state")
            _text(relation.get("meaning"), "relationship.meaning")
    invariants = spec.get("invariants")
    if not isinstance(invariants, list) or not invariants:
        raise ContractError("invariants: expected non-empty list")
    for invariant in invariants:
        _text(invariant, "invariant")
    variants = _records(spec.get("variants"), "variants")
    if len(variants) != 5:
        raise ContractError("variants: exactly five required")
    _ids(variants, "variants")
    layouts = set()
    for variant in variants:
        for key in ("layout", "focal_element", "label_placement"):
            _text(variant.get(key), f"variant {variant['id']}.{key}")
        layouts.add(variant["layout"].strip())
    if len(layouts) != 5:
        raise ContractError("variants: five distinct composition plans required")
    labels = spec.get("labels", [])
    if not isinstance(labels, list):
        raise ContractError("labels: expected list")
    for label in labels:
        _text(label, "label")
    for key in ("font", "visual_treatment", "reference_role"):
        if key in spec:
            _text(spec[key], key)


def compile_prompts(spec: dict) -> dict:
    validate_contract(spec)
    scientific = spec.get("scientific", True)
    shared = [
        f"Use case: {'scientific-educational' if scientific else 'infographic-diagram'}",
        "Asset type: two-dimensional concept draft for native Adobe Illustrator reconstruction.",
        f"Primary message: {spec['message']}",
        f"Audience: {spec['audience']}",
        f"Figure type: {spec['figure_type']}; aspect ratio: {spec['aspect_ratio']}; reading order: {spec['reading_order']}",
        f"Evidence and abstraction limits: {spec['evidence_boundary']}",
        "Fixed component dictionary (preserve identity, internal proportions, domain colors, and construction logic):",
    ]
    for entity in spec["entities"]:
        shared.append(f"- {entity['id']} | {entity['label']} | {entity['color']} | representation: {entity['representation']} | Illustrator recipe: {entity['construction']}")
    shared.append("Required panel content and states:")
    for panel in spec["panels"]:
        shared.append(f"- {panel['id']}: {panel['role']}")
        for state in panel["states"]:
            shared.append(f"  {state['entity']}: {state['state']}")
        for relation in panel.get("relationships", []):
            shared.append(f"  Relationship {relation['from']} -> {relation['to']}: {relation['meaning']}")
    shared.extend(["Preserve these invariants:", *[f"- {x}" for x in spec["invariants"]]])
    labels = spec.get("labels", [])
    shared.append("Text (verbatim only): " + (json.dumps(labels, ensure_ascii=False) if labels else "none; leave text out"))
    shared.append(f"Typography: {spec.get('font', 'Noto Sans SC')}; short labels, clear negative space. Generated text is provisional.")
    shared.append("Visual treatment: " + spec.get("visual_treatment", "White background, crisp standard geometry, restrained flat fills, coherent stroke hierarchy, semantic colors, one focal step, clean whitespace. Use a small number of simple gradients only when needed to explain a surface."))
    shared.append("Avoid: invented entities, structures, measurements or causal links; changed molecular states; unrequested glow, glossy blobs, floating decorative particles, decorative helices, perspective distortion, fuzzy fused contours, texture-dependent detail, oversized title banners, and arrows hidden by other objects.")
    if spec.get("reference_role"):
        shared.append("Input reference role: " + _text(spec["reference_role"], "reference_role"))
    review = [
        "Check all states, connections, color mappings and evidence boundaries against the contract.",
        "Inspect physical silhouettes and critical junctions at component scale.",
        "Explain a workable native Illustrator recipe for each critical generated component.",
        "Check labels, arrow clearance, reading order and hierarchy at intended viewing size.",
        "Check recurring components for drift; record visible evidence, not an overall beauty score.",
    ]
    return {
        "status": "contract-valid; generated images not yet reviewed",
        "candidates": [{
            "id": v["id"],
            "prompt": "\n".join(shared + [
                "This candidate's composition: " + v["layout"],
                "Focal element: " + v["focal_element"],
                "Label placement and connector clearance: " + v["label_placement"],
                "Output: exactly one complete composition, no contact sheet. Preserve fixed scientific content while following this composition. Make all important contours individually reconstructable with the recipes above.",
            ]),
            "review": {"status": "unreviewed", "criteria": review},
        } for v in spec["variants"]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--output", type=Path, help="Save compiled JSON; defaults to stdout")
    args = parser.parse_args(argv)
    try:
        spec = json.loads(args.contract.read_text(encoding="utf-8-sig"))
        result = compile_prompts(spec)
        output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
            print(f"Compiled five prompts: {args.output}")
        else:
            print(output, end="")
        return 0
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        print(f"Concept contract rejected: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
