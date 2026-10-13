import json
from pathlib import Path

from sciai_illustrator.jsx_builder import build_jsx


ROOT = Path(__file__).parents[1]
EXAMPLE = ROOT / "examples" / "basic-layout.json"


def test_optional_document_metadata_is_guarded(tmp_path):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    jsx = build_jsx(spec, tmp_path / "demo.ai")
    assert "try { if (doc.info)" in jsx
    assert "catch (metadataError)" in jsx


def test_later_group_children_are_stacked_on_top(tmp_path):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    jsx = build_jsx(spec, tmp_path / "demo.ai")
    assert "ElementPlacement.PLACEATBEGINNING" in jsx


def test_preview_waits_for_illustrator_redraw(tmp_path):
    spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    jsx = build_jsx(spec, tmp_path / "demo.ai", tmp_path / "demo.png")
    assert "app.redraw();\n  $.sleep(1000);\n  app.redraw();\n  $.sleep(500);" in jsx
    assert "doc.exportFile(pngFile, ExportType.PNG24, pngOptions);\n  doc.save();" in jsx
