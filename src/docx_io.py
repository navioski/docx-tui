"""Read and write .docx files via the python-docx library."""

from pathlib import Path

from docx import Document as DocxDocument
from docx.shared import Pt

from .model import Document, Paragraph, Run


def load_docx(path: str | Path) -> Document:
    """Parse a .docx file into our internal Document model."""
    docx = DocxDocument(str(path))
    paragraphs: list[Paragraph] = []

    for para in docx.paragraphs:
        runs: list[Run] = []
        for run in para.runs:
            font_name = run.font.name or ""
            if run.font.size:
                sz = run.font.size.pt
                font_size = str(int(sz)) if sz == int(sz) else str(sz)
            else:
                font_size = ""
            r = Run(
                text=run.text,
                bold=run.bold or False,
                italic=run.italic or False,
                underline=run.underline or False,
                strikethrough=run.font.strike or False,
                font_name=font_name,
                font_size=font_size,
            )
            runs.append(r)
        # If a paragraph has no runs (empty), add an empty run
        if not runs:
            runs.append(Run(text=""))
        paragraphs.append(Paragraph(runs=runs))

    # Ensure at least one paragraph
    if not paragraphs:
        paragraphs.append(Paragraph(runs=[Run(text="")]))

    return Document(paragraphs=paragraphs)


def save_docx(doc: Document, path: str | Path) -> None:
    """Write our Document model out as a .docx file."""
    docx = DocxDocument()

    # Clear default empty paragraph
    if docx.paragraphs:
        p = docx.paragraphs[0]._element
        p.getparent().remove(p)

    for para in doc.paragraphs:
        p = docx.add_paragraph()
        for run in para.runs:
            if not run.text:
                continue
            r = p.add_run(run.text)
            r.bold = run.bold
            r.italic = run.italic
            r.underline = run.underline
            r.font.strike = run.strikethrough
            if run.font_name:
                r.font.name = run.font_name
            if run.font_size:
                try:
                    r.font.size = Pt(float(run.font_size))
                except ValueError:
                    pass

    docx.save(str(path))
