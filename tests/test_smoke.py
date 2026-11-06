"""Smoke test: verify imports + basic editing + .docx round-trip."""
import sys
sys.path.insert(0, ".")

from src.model import Document, Paragraph, Run
from src.editor import Editor
from src.docx_io import load_docx, save_docx

# 1. Model + Editor smoke test
doc = Document(paragraphs=[Paragraph(runs=[Run(text="Hello World")])])
ed = Editor(doc)
ed.insert_char("!")
txt = ed.doc.paragraphs[0].plain_text
assert txt == "!Hello World", f"Expected '!Hello World', got {txt!r}"
print(f"✓ Editor insert: {txt}")

# 2. .docx round-trip
path = "/tmp/test_tui.docx"
save_docx(doc, path)
loaded = load_docx(path)
loaded_txt = loaded.paragraphs[0].plain_text
assert loaded_txt == "!Hello World", f"Round-trip failed: {loaded_txt!r}"
print(f"✓ .docx round-trip: {loaded_txt}")
print("All tests passed.")
