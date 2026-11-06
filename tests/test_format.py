"""Test formatting round-trip: bold, italic, underline."""
import sys
sys.path.insert(0, ".")

from src.docx_io import save_docx, load_docx
from src.model import Document, Paragraph, Run

doc = Document(paragraphs=[
    Paragraph(runs=[Run("Bold ", bold=True), Run("Italic ", italic=True), Run("Normal")]),
    Paragraph(runs=[Run("Underlined", underline=True)]),
])
save_docx(doc, "/tmp/test_format.docx")
loaded = load_docx("/tmp/test_format.docx")
for p in loaded.paragraphs:
    for r in p.runs:
        print(f"  text={r.text!r} bold={r.bold} italic={r.italic} underline={r.underline}")

# Verify
p0 = loaded.paragraphs[0]
assert p0.runs[0].bold == True and p0.runs[0].text == "Bold "
assert p0.runs[1].italic == True and p0.runs[1].text == "Italic "
assert p0.runs[2].bold == False and p0.runs[2].italic == False

p1 = loaded.paragraphs[1]
assert p1.runs[0].underline == True and p1.runs[0].text == "Underlined"

print("Format round-trip OK")
