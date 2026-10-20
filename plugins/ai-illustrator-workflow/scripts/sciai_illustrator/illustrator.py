from __future__ import annotations

from pathlib import Path


class IllustratorConnectionError(RuntimeError):
    """Raised when Illustrator cannot be reached through Windows COM."""


def run_jsx(path: str | Path) -> str:
    jsx_path = Path(path).resolve()
    if not jsx_path.is_file():
        raise IllustratorConnectionError(f"JSX 文件不存在: {jsx_path}")
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise IllustratorConnectionError(
            "缺少 pywin32。请在当前 Python 环境中安装: pip install pywin32"
        ) from exc

    app = None
    initialized = False
    try:
        pythoncom.CoInitialize()
        initialized = True
        app = win32com.client.Dispatch("Illustrator.Application")
        result = app.DoJavaScriptFile(str(jsx_path))
        return str(result) if result is not None else "Illustrator 已执行脚本"
    except Exception as exc:
        raise IllustratorConnectionError(f"Illustrator 执行失败: {exc}") from exc
    finally:
        # Release the COM proxy before shutting down its apartment.
        app = None
        if initialized:
            pythoncom.CoUninitialize()
