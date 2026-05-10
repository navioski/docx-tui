"""Entry point for the TUI .docx editor.

Usage:
    deepseek-tui [file.docx]    — open an existing .docx file
    deepseek-tui                — start with a blank document
"""

import sys
from pathlib import Path

from .app import DocxEditorApp
from .docx_io import load_docx
from .model import Document, Paragraph, Run


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
