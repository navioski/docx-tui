"""Test font name/size round-trip."""
import sys
sys.path.insert(0, ".")

from src.docx_io import save_docx, load_docx
from src.model import Document, Paragraph, Run

doc = Document(paragraphs=[
    Paragraph(runs=[
        Run("Arial text", font_name="Arial", font_size="14"),
        Run("Times text", font_name="Times New Roman", font_size="12"),
    ]),
])
save_docx(doc, "/tmp/test_font.docx")
loaded = load_docx("/tmp/test_font.docx")

p0 = loaded.paragraphs[0]
assert p0.runs[0].font_name == "Arial", f"got {p0.runs[0].font_name!r}"
assert p0.runs[0].font_size == "14", f"got {p0.runs[0].font_size!r}"
assert p0.runs[1].font_name == "Times New Roman"
assert p0.runs[1].font_size == "12"

for r in p0.runs:
    print(f"  text={r.text!r} font={r.font_name!r} size={r.font_size!r}")
print("Font round-trip OK")
