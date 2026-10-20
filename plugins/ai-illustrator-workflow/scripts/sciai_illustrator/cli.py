from __future__ import annotations

import argparse
import importlib.util
import platform
import sys
from pathlib import Path

from .illustrator import IllustratorConnectionError, run_jsx
from .jsx_builder import build_jsx
from .schema import SpecError, load_spec


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sciai", description="结构化图形规范 → Illustrator 原生对象")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="校验 Figure Spec")
    validate.add_argument("spec", type=Path)

    build = subparsers.add_parser("build", help="生成 JSX，并可选在 Illustrator 中执行")
    build.add_argument("spec", type=Path)
    build.add_argument("--output", type=Path, required=True, help="输出文件前缀，不含扩展名")
    build.add_argument("--run", action="store_true", help="通过 Windows COM 在 Illustrator 中执行")
    build.add_argument("--no-preview", action="store_true", help="不导出 PNG 预览")
    build.add_argument("--force", action="store_true", help="允许覆盖同名输出；默认自动创建新版本")

    subparsers.add_parser("doctor", help="检查本机运行条件")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        if args.command == "validate":
            load_spec(args.spec)
            print(f"规范有效: {args.spec.resolve()}")
            return 0
        if args.command == "doctor":
            return _doctor()
        return _build(args)
    except (SpecError, IllustratorConnectionError, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


def _build(args: argparse.Namespace) -> int:
    spec_path = args.spec.resolve()
    spec = load_spec(spec_path)
    output = resolve_output_stem(args.output.resolve(), force=args.force)
    output.parent.mkdir(parents=True, exist_ok=True)
    jsx_path = output.with_suffix(".jsx")
    ai_path = output.with_suffix(".ai")
    png_path = None if args.no_preview else output.with_suffix(".png")
    jsx = build_jsx(spec, ai_path=ai_path, png_path=png_path, spec_base_dir=spec_path.parent)
    jsx_path.write_text(jsx, encoding="utf-8-sig")
    print(f"已生成 JSX: {jsx_path}")
    if args.run:
        result = run_jsx(jsx_path)
        print(result)
        print(f"已生成 AI: {ai_path}")
        if png_path:
            print(f"已生成预览: {png_path}")
        print(f"实际文档读回报告: {ai_path.parent / 'audits' / (ai_path.stem + '.json')}")
    return 0


def resolve_output_stem(output: Path, force: bool = False) -> Path:
    """Return a non-conflicting output stem unless overwrite was explicitly requested."""
    if force or not _stem_exists(output):
        return output
    version = 2
    while True:
        candidate = output.with_name(f"{output.name}_v{version:02d}")
        if not _stem_exists(candidate):
            return candidate
        version += 1


def _stem_exists(output: Path) -> bool:
    return any(output.with_suffix(suffix).exists() for suffix in (".jsx", ".ai", ".png"))


def _doctor() -> int:
    is_windows = platform.system() == "Windows"
    has_pywin32 = importlib.util.find_spec("win32com") is not None
    print(f"Python: {sys.version.split()[0]}")
    print(f"Windows: {'是' if is_windows else '否（仍可生成 JSX，但不能通过 COM 运行 Illustrator）'}")
    print(f"pywin32: {'已安装' if has_pywin32 else '未安装（仅 --run 需要）'}")
    return 0 if is_windows else 1


if __name__ == "__main__":
    raise SystemExit(main())
