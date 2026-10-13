#!/usr/bin/env python3
"""Safely remove one Illustrator revision's temporary artifacts after promotion."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir")
    parser.add_argument("final_stem")
    parser.add_argument("--temp", action="append", default=[])
    parser.add_argument("--artifact", action="append", default=[])
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    outputs = (project / "outputs").resolve()
    final_ai = outputs / f"{args.final_stem}.ai"
    final_png = outputs / f"{args.final_stem}.png"
    for final in (final_ai, final_png):
        if not final.is_file() or final.stat().st_size == 0:
            raise SystemExit(f"Final deliverable missing or empty: {final}")

    removed: list[str] = []
    skipped: list[str] = []
    raw_targets = [(value, "temp") for value in args.temp]
    raw_targets += [(value, "artifact") for value in args.artifact]
    for raw, kind in raw_targets:
        target = Path(raw)
        if not target.is_absolute():
            target = project / target
        target = target.resolve()
        if target == project or not inside(target, project):
            raise SystemExit(f"Refusing target outside project: {target}")
        if target == outputs or inside(target, outputs):
            raise SystemExit(f"Refusing to remove permanent output: {target}")
        if not target.exists():
            skipped.append(str(target))
            continue
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        removed.append(f"{kind}:{target}")

    result = {
        "status": "passed",
        "finals": [str(final_ai), str(final_png)],
        "removed": removed,
        "already_absent": skipped,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
