from __future__ import annotations

if __package__:
    from .cli import main
else:  # Support direct execution: python okf_mcp/__main__.py
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    project_root_text = str(project_root)
    sys.path = [project_root_text, *[entry for entry in sys.path if entry != project_root_text]]
    from okf_mcp.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
