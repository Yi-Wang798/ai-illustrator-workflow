"""Opt-in smoke tests against a real local Illustrator, not needed for normal CI."""
import json
import os
from pathlib import Path

import pytest

from sciai_illustrator.illustrator import run_jsx, IllustratorConnectionError
from sciai_illustrator.jsx_builder import build_jsx

pytestmark = pytest.mark.skipif(os.environ.get("SCIAI_LIVE_TEST") != "1", reason="requires local Illustrator")


@pytest.mark.parametrize("overflow", [False, True])
def test_actual_document_and_overflow_gate(tmp_path, overflow):
    source = Path(__file__).parents[1] / "examples" / "automatic-flow.json"
    spec = json.loads(source.read_text(encoding="utf-8"))
    marker = "sciai-smoke-" + tmp_path.name
    spec["layers"][0]["name"] = marker
    for item in spec["objects"]:
        item["layer"] = marker
    if overflow:
        spec["objects"][-1]["text"] = "A deliberately oversized label " * 10
    output = tmp_path / "flow.ai"
    script = tmp_path / "flow.jsx"
    script.write_text(build_jsx(spec, output), encoding="utf-8-sig")
    try:
        if overflow:
            with pytest.raises(IllustratorConnectionError, match="readback failed"):
                run_jsx(script)
        else:
            run_jsx(script)
        report = json.loads((tmp_path / "audits" / "flow.json").read_text(encoding="utf-8-sig"))
        assert report["passed"] is (not overflow)
        assert output.exists() is (not overflow)
        if overflow:
            assert any("exceed container" in error for error in report["errors"])
        else:
            assert len(report["objects"]) == 8
            assert report["native_type_counts"] == report["expected_type_counts"]
    finally:
        # Close only this test's newly created document; never unrelated user work.
        cleanup = tmp_path / "close-test.jsx"
        cleanup.write_text("(function(){for(var i=app.documents.length-1;i>=0;i--){var d=app.documents[i];for(var j=0;j<d.layers.length;j++){if(d.layers[j].name===" + json.dumps(marker) + "){d.close(SaveOptions.DONOTSAVECHANGES);break;}}}}());", encoding="utf-8-sig")
        run_jsx(cleanup)
