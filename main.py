"""TUI .docx editor — terminal-based Microsoft Word document editor.

Usage:
    python3 main.py                  start with blank document
    python3 main.py file.docx        open existing .docx file

If python-docx is not installed, automatically re-runs with the project's .venv.
"""

import os
import sys

# ── Auto-bootstrap: if docx is missing, re-exec with .venv python ──
try:
    import docx  # noqa: F401  — just checking availability
except ImportError:
    venv_python = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".venv", "bin", "python"
    )
    if os.path.exists(venv_python):
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print(
            "Error: python-docx is not installed and .venv is missing.\n"
            "Run:  python3 -m venv .venv && .venv/bin/pip install textual python-docx"
        )
        sys.exit(1)

from pathlib import Path

from src.app import DocxEditorApp
from src.docx_io import load_docx
from src.model import Document, Paragraph, Run


def main() -> None:
    filepath: str | None = None
    doc: Document

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        path = Path(filepath)
        if not path.exists():
            print(f"File not found: {filepath}")
            sys.exit(1)
        if path.suffix.lower() not in (".docx",):
            print(f"Warning: {filepath} does not have a .docx extension")
        doc = load_docx(path)
    else:
        doc = Document(paragraphs=[Paragraph(runs=[Run()])])

    app = DocxEditorApp(doc, filepath)
    app.run()


if __name__ == "__main__":
    main()
