"""Full save round-trip test."""
import asyncio
from pathlib import Path

from src.app import DocxEditorApp
from src.model import Document, Paragraph, Run
from src.docx_io import load_docx


async def main():
    doc = Document(paragraphs=[Paragraph(runs=[Run("Hello"), Run(" World", bold=True)])])
    app = DocxEditorApp(doc)
    app.editor.filepath = "/tmp/fake.docx"

    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()

        # Verify initial state
        assert len(app.editor.doc.paragraphs) == 1
        assert app.editor.doc.paragraphs[0].plain_text == "Hello World"

        # Save via dialog
        app.action_save()
        await pilot.pause()
        from textual.widgets import Input
        save_screen = app.screen
        inp = save_screen.query_one("#save-filename", Input)
        inp.value = "test_save_final.docx"
        await pilot.press("enter")
        await pilot.pause()

        # Verify screen dismissed
        assert "SaveScreen" not in type(app.screen).__name__

        out_path = Path("/private/tmp/test_save_final.docx")
        assert out_path.exists(), "File not created"
        loaded = load_docx(out_path)
        assert loaded.paragraphs[0].plain_text == "Hello World"
        assert loaded.paragraphs[0].runs[1].bold == True
        assert app.editor.dirty == False

        # Verify document not corrupted
        assert len(app.editor.doc.paragraphs) == 1
        assert app.editor.doc.paragraphs[0].plain_text == "Hello World"

        print("✓ Save round-trip OK")
        print(f"✓ Content: {loaded.paragraphs[0].plain_text!r}")
        print(f"✓ Bold preserved: {loaded.paragraphs[0].runs[1].bold}")
        print(f"✓ Document not corrupted")
        out_path.unlink()

    print("\nAll save tests passed.")


asyncio.run(main())
