"""Textual TUI application for the .docx editor.

Word 2003-style menu bar, formatted document rendering, file-browser
save dialog, and full keyboard shortcut support.
"""

from pathlib import Path

from rich.style import Style
from rich.text import Text as RichText
from textual import events
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static, Label, DirectoryTree
from textual.widget import Widget

from .editor import Editor
from .model import Document, Paragraph, Run
from .docx_io import load_docx, save_docx
from .toolbar import MenuBar, DropdownWidget, PickerDropdown, StandardToolbar, FormattingToolbar
from .page import PageView, HorizontalRuler, PAGE_WIDTH


# ── Help modal ─────────────────────────────────────────────────────────

HELP_TEXT = """
  Esc            Quit (when no menu is open)
  Ctrl+S         Save
  Ctrl+O         Open file
  Ctrl+B         Toggle bold
  Ctrl+I         Toggle italic
  Ctrl+U         Toggle underline
  Ctrl+Z         Undo
  Ctrl+Y         Redo
  Ctrl+A         Select all
  Ctrl+F         Find...

  Arrows         Navigate
  Home / End     Line start / end
  Ctrl+Home/End  Document start / end
  Backspace      Delete backwards
  Delete         Delete forwards
  Enter          New line
  F1             Help
"""


class HelpScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        yield Static(HELP_TEXT, id="help-text")

    def on_key(self, event) -> None:
        event.stop()
        self.dismiss()


# ── About modal ────────────────────────────────────────────────────────

class AboutScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("DocxEditor v0.1.0", id="about-title"),
            Static("Terminal-based .docx document editor", id="about-desc"),
            Static("Built with Textual + python-docx", id="about-tech"),
            id="about-dialog",
        )

    def on_key(self, event) -> None:
        event.stop()
        self.dismiss()


# ── Open-file modal ────────────────────────────────────────────────────

class OpenScreen(ModalScreen[str | None]):
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Open .docx file:", id="open-label"),
            Input(placeholder="path/to/file.docx", id="open-input"),
            Label("Enter = Open   Esc = Cancel", id="open-hint"),
            id="open-dialog",
        )

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)
        elif event.key == "enter":
            event.stop()
            # Read path from input and dismiss
            inp = self.query_one("#open-input", Input)
            self.dismiss(inp.value.strip())


# ── Force-quit confirmation ────────────────────────────────────────────

class ForceQuitScreen(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("⚠  Unsaved changes!", id="fq-warning"),
            Label("Discard changes and quit?", id="fq-question"),
            Label("Y = Quit without saving   N / Esc = Cancel", id="fq-hint"),
            id="fq-dialog",
        )

    def on_key(self, event) -> None:
        char = (event.character or event.key).lower()
        if char == "y":
            event.stop()
            self.dismiss(True)
        elif char in ("n", "escape"):
            event.stop()
            self.dismiss(False)


# ── Save-file modal ────────────────────────────────────────────────────

class SaveScreen(ModalScreen[Path | None]):
    def __init__(self, start_dir: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_dir = Path(start_dir).expanduser().resolve()

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(f"Save to: {self._current_dir}", id="save-dir-label"),
            DirectoryTree(str(self._current_dir), id="save-dir-tree"),
            Input(placeholder="filename.docx", id="save-filename"),
            Label("", id="save-preview"),
            Label("Enter = Save   Esc = Cancel   Tab = switch focus", id="save-hint"),
            id="save-dialog",
        )

    def on_mount(self) -> None:
        self.query_one("#save-filename", Input).focus()

    @on(DirectoryTree.DirectorySelected)
    def on_dir_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        self._current_dir = Path(event.path)
        self.query_one("#save-dir-label", Label).update(f"Save to: {self._current_dir}")
        self._update_preview()

    @on(Input.Changed, "#save-filename")
    def on_filename_changed(self) -> None:
        self._update_preview()

    def on_key(self, event) -> None:
        if event.key == "escape":
            event.stop()
            self.dismiss(None)
        elif event.key == "enter":
            event.stop()
            # Read filename from input and dismiss with full path
            inp = self.query_one("#save-filename", Input)
            fname = inp.value.strip()
            if not fname:
                return
            if not fname.endswith(".docx"):
                fname += ".docx"
            self.dismiss(self._current_dir / fname)

    def _update_preview(self) -> None:
        inp = self.query_one("#save-filename", Input)
        fname = inp.value.strip() or "filename.docx"
        if not fname.endswith(".docx"):
            fname += ".docx"
        self.query_one("#save-preview", Label).update(
            f"Will save as: {self._current_dir / fname}"
        )


# ── Status bar ─────────────────────────────────────────────────────────

class StatusBar(Widget):
    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 2;
    }
    """

    def __init__(self, editor: Editor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor

    def render(self) -> RichText:
        editor = self.editor
        fname = Path(editor.filepath).name if editor.filepath else "[new document]"
        dirty = " ●" if editor.dirty else ""
        pos = f"Ln {editor.cursor.para + 1}, Col {editor.cursor.offset + 1}"
        mode = "INSERT"

        status = RichText()
        status.append(f" {fname}{dirty} ", style=Style(bold=True))
        status.append(f"  {pos}  ")
        status.append(f"  {mode}  ")
        return status


# ── Main App ───────────────────────────────────────────────────────────

class DocxEditorApp(App):
    """Terminal UI for editing .docx files — Word 2003 style."""

    CSS = """
    Screen {
        background: #808080;
    }

    #workspace {
        height: 1fr;
        align-horizontal: center;
        background: #808080;
    }

    #save-dialog {
        width: 60;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    #save-dir-tree {
        height: 12;
        border: solid $primary;
        margin: 1 0;
    }

    #save-filename { margin: 1 0; }
    #save-preview { color: $text-muted; margin: 1 0; }
    #save-hint { color: $text-disabled; }
    #save-dir-label { color: $accent; text-style: bold; }

    #fq-dialog {
        width: 50;
        height: auto;
        background: $panel;
        border: thick $error;
        padding: 2 3;
    }

    #fq-warning { color: $error; text-style: bold; }
    #fq-hint { color: $text-muted; margin-top: 1; }

    #about-dialog {
        width: 50;
        height: auto;
        background: $panel;
        border: thick $accent;
        padding: 2 3;
    }

    #about-title { text-style: bold; color: $accent; }
    #about-desc { margin-top: 1; }
    #about-tech { color: $text-muted; margin-top: 1; }
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+o", "open", "Open"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+b", "toggle_bold", "Bold"),
        Binding("ctrl+i", "toggle_italic", "Italic"),
        Binding("ctrl+u", "toggle_underline", "Underline"),
        Binding("ctrl+z", "undo", "Undo"),
        Binding("ctrl+y", "redo", "Redo"),
        Binding("ctrl+a", "select_all", "Select All"),
        Binding("ctrl+f", "find", "Find"),
        Binding("ctrl+home", "doc_top", "Doc Top"),
        Binding("ctrl+end", "doc_bottom", "Doc Bottom"),
        Binding("ctrl+equal", "zoom_in", "Zoom In"),
        Binding("ctrl+minus", "zoom_out", "Zoom Out"),
        Binding("f1", "help", "Help"),
    ]

    # ── Font / size lists for picker ──────────────────────────────────

    FONT_LIST = [
        ("Times New Roman", "Times New Roman"),
        ("Arial", "Arial"),
        ("Calibri", "Calibri"),
        ("Cambria", "Cambria"),
        ("Courier New", "Courier New"),
        ("Georgia", "Georgia"),
        ("Verdana", "Verdana"),
        ("Tahoma", "Tahoma"),
        ("Trebuchet MS", "Trebuchet MS"),
        ("Comic Sans MS", "Comic Sans MS"),
        ("Impact", "Impact"),
        ("Lucida Console", "Lucida Console"),
    ]

    SIZE_LIST = [
        ("8 pt", "8"), ("9 pt", "9"), ("10 pt", "10"),
        ("11 pt", "11"), ("12 pt", "12"), ("14 pt", "14"),
        ("16 pt", "16"), ("18 pt", "18"), ("20 pt", "20"),
        ("24 pt", "24"), ("28 pt", "28"), ("36 pt", "36"),
        ("48 pt", "48"), ("72 pt", "72"),
    ]

    def __init__(self, doc: Document, filepath: str | None = None):
        super().__init__()
        self.editor = Editor(doc, filepath)
        self.page_view: PageView | None = None
        self.status_bar: StatusBar | None = None
        self.menu_bar: MenuBar | None = None
        self._dropdown: DropdownWidget | None = None
        self._picker: PickerDropdown | None = None
        self.fmt_toolbar: FormattingToolbar | None = None
        self._show_status = True

    def compose(self) -> ComposeResult:
        self.menu_bar = MenuBar(self, title="DocxEditor")
        yield self.menu_bar
        yield StandardToolbar(self)
        self.fmt_toolbar = FormattingToolbar(self)
        yield self.fmt_toolbar
        with Vertical(id="workspace"):
            yield HorizontalRuler()
            self.page_view = PageView(self.editor)
            yield self.page_view
        self.status_bar = StatusBar(self.editor)
        yield self.status_bar

    def on_mount(self) -> None:
        if self.page_view:
            self.page_view.focus()

    # ── Dropdown overlay management ────────────────────────────────────

    def _show_dropdown(self, menu_index: int) -> None:
        """Mount the dropdown overlay for the given menu index."""
        self._hide_dropdown()  # close any existing first
        if self.menu_bar is None:
            return
        offset_x = self.menu_bar.label_starts[menu_index]
        self._dropdown = DropdownWidget(self, menu_index, offset_x)
        self.mount(self._dropdown, after=self.menu_bar)

    def _hide_dropdown(self) -> None:
        """Remove the dropdown overlay if present."""
        if self._dropdown is not None:
            self._dropdown.remove()
            self._dropdown = None

    # ── Picker (font/size dropdown) management ─────────────────────────

    def _show_font_picker(self, offset_x: int) -> None:
        self._hide_picker()
        self._picker = PickerDropdown(
            self, self.FONT_LIST, offset_x, "_on_font_selected"
        )
        self.mount(self._picker, after=self.menu_bar)

    def _show_size_picker(self, offset_x: int) -> None:
        self._hide_picker()
        self._picker = PickerDropdown(
            self, self.SIZE_LIST, offset_x, "_on_size_selected"
        )
        self.mount(self._picker, after=self.menu_bar)

    def _hide_picker(self) -> None:
        if self._picker is not None:
            self._picker.remove()
            self._picker = None

    def _on_font_selected(self, font: str) -> None:
        self.editor.apply_font_name(font)
        self._flash(f"Font: {font}")
        self.refresh_widgets()

    def _on_size_selected(self, size: str) -> None:
        self.editor.apply_font_size(size)
        self._flash(f"Size: {size} pt")
        self.refresh_widgets()

    def refresh_widgets(self) -> None:
        if self.page_view:
            self.page_view.refresh()
        if self.fmt_toolbar:
            self.fmt_toolbar.refresh(layout=True)
        if self.status_bar:
            if self._show_status:
                self.status_bar.styles.display = "block"
            else:
                self.status_bar.styles.display = "none"
            self.status_bar.refresh()

    # ── File menu actions ──────────────────────────────────────────────

    def action_new_doc(self) -> None:
        self.editor = Editor(
            Document(paragraphs=[Paragraph(runs=[Run()])]), None
        )
        self.page_view.editor = self.editor  # type: ignore[union-attr]
        self.status_bar.editor = self.editor  # type: ignore[union-attr]
        self.refresh_widgets()
        self._flash("New document")

    def action_save(self) -> None:
        start_dir = str(Path.home())
        if self.editor.filepath:
            start_dir = str(Path(self.editor.filepath).parent)
        self.push_screen(SaveScreen(start_dir), self._on_save_callback)

    def action_save_as(self) -> None:
        self.action_save()

    def _on_save_callback(self, save_path: Path | None) -> None:
        if save_path is None:
            return
        try:
            save_docx(self.editor.doc, save_path)
            self.editor.filepath = str(save_path)
            self.editor.dirty = False
            self._flash(f"Saved: {save_path.name}")
        except Exception as e:
            self._flash(f"Save failed: {e}")
        self.refresh_widgets()

    def action_open(self) -> None:
        self.push_screen(OpenScreen(), self._on_open_callback)

    def _on_open_callback(self, result: str | None) -> None:
        if not result:
            return
        path = Path(result)
        if not path.exists():
            self._flash(f"File not found: {result}")
            return
        try:
            doc = load_docx(path)
            self.editor = Editor(doc, str(path))
            self.page_view.editor = self.editor  # type: ignore[union-attr]
            self.status_bar.editor = self.editor  # type: ignore[union-attr]
            self._flash(f"Opened: {path.name}")
        except Exception as e:
            self._flash(f"Open failed: {e}")
        self.refresh_widgets()

    def action_quit(self) -> None:
        if self.editor.dirty:
            self.push_screen(ForceQuitScreen(), self._on_force_quit_callback)
        else:
            self._force_exit()

    def action_force_quit(self) -> None:
        if self.editor.dirty:
            self.push_screen(ForceQuitScreen(), self._on_force_quit_callback)
        else:
            self._force_exit()

    def _force_exit(self) -> None:
        """Stop timers and exit the app cleanly."""
        if self.page_view:
            self.page_view.stop_timers()
        self.exit()

    def _on_force_quit_callback(self, confirmed: bool) -> None:
        if confirmed:
            self._force_exit()

    # ── Edit menu actions ──────────────────────────────────────────────

    def action_undo(self) -> None:
        self._flash("Undo — coming soon")

    def action_redo(self) -> None:
        self._flash("Redo — coming soon")

    def action_cut(self) -> None:
        self._flash("Cut — coming soon (use terminal clipboard)")

    def action_copy(self) -> None:
        self._flash("Copy — coming soon (use terminal clipboard)")

    def action_paste(self) -> None:
        self._flash("Paste — coming soon (use terminal clipboard)")

    def action_select_all(self) -> None:
        self._flash("Select All — coming soon")

    def action_find(self) -> None:
        self._flash("Find — coming soon")

    # ── View menu actions ──────────────────────────────────────────────

    def action_zoom_in(self) -> None:
        self._flash("Zoom In — adjust terminal font size (Ctrl++)")

    def action_zoom_out(self) -> None:
        self._flash("Zoom Out — adjust terminal font size (Ctrl+-)")

    def action_toggle_status(self) -> None:
        self._show_status = not self._show_status
        self.refresh_widgets()
        state = "shown" if self._show_status else "hidden"
        self._flash(f"Status bar {state}")

    # ── Insert menu actions ────────────────────────────────────────────

    def action_page_break(self) -> None:
        self.editor.insert_newline()
        self.editor.insert_newline()
        self.editor.insert_char("─")
        self.editor.insert_char("─")
        self.editor.insert_char("─")
        self.editor.insert_newline()
        self.editor.insert_newline()
        self.refresh_widgets()

    def action_symbol(self) -> None:
        self._flash("Symbol — coming soon")

    # ── Format menu actions ────────────────────────────────────────────

    def action_toggle_bold(self) -> None:
        self.editor.toggle_bold()
        self.refresh_widgets()

    def action_toggle_italic(self) -> None:
        self.editor.toggle_italic()
        self.refresh_widgets()

    def action_toggle_underline(self) -> None:
        self.editor.toggle_underline()
        self.refresh_widgets()

    def action_toggle_strikethrough(self) -> None:
        self.editor.toggle_strikethrough()
        self.refresh_widgets()

    # ── Tools menu actions ─────────────────────────────────────────────

    def action_word_count(self) -> None:
        doc = self.editor.doc
        chars = sum(len(p.plain_text) for p in doc.paragraphs)
        words = sum(len(p.plain_text.split()) for p in doc.paragraphs if p.plain_text.strip())
        paras = len([p for p in doc.paragraphs if p.plain_text.strip()])
        self._flash(f"Words: {words}  |  Chars: {chars}  |  Paragraphs: {paras}")

    def action_spell_check(self) -> None:
        self._flash("Spell Check — coming soon")

    # ── Table menu actions ─────────────────────────────────────────────

    def action_insert_table(self) -> None:
        self._flash("Insert Table — coming soon")

    def action_delete_table(self) -> None:
        self._flash("Delete Table — coming soon")

    # ── Window menu actions ────────────────────────────────────────────

    def action_new_window(self) -> None:
        self._flash("New Window — open another terminal tab")

    # ── Help menu actions ──────────────────────────────────────────────

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_about(self) -> None:
        self.push_screen(AboutScreen())

    # ── Navigation ─────────────────────────────────────────────────────

    def action_doc_top(self) -> None:
        self.editor.move_top()
        self.refresh_widgets()

    def action_doc_bottom(self) -> None:
        self.editor.move_bottom()
        self.refresh_widgets()

    # ── Keyboard (editing) ─────────────────────────────────────────────

    def on_key(self, event) -> None:
        key = event.key

        # Esc: close menu first, else try quit
        if key == "escape":
            if self.menu_bar and self.menu_bar._active is not None:  # type: ignore[attr-defined]
                self._hide_dropdown()
                self.menu_bar._set_active(None)  # type: ignore[attr-defined]
                return
            self.action_quit()
            return

        if key == "up":
            self.editor.move_up()
        elif key == "down":
            self.editor.move_down()
        elif key == "left":
            self.editor.move_left()
        elif key == "right":
            self.editor.move_right()
        elif key == "home":
            self.editor.move_home()
        elif key == "end":
            self.editor.move_end()
        elif key == "pageup":
            for _ in range(10):
                self.editor.move_up()
        elif key == "pagedown":
            for _ in range(10):
                self.editor.move_down()
        elif key == "enter":
            self.editor.insert_newline()
        elif key == "backspace":
            self.editor.delete_backwards()
        elif key == "delete":
            self.editor.delete_forwards()
        else:
            # Use event.character (what the terminal actually sent), fall back to event.key
            char = event.character or event.key
            if len(char) == 1 and char.isprintable():
                self.editor.insert_char(char)
            else:
                return

        self.refresh_widgets()

    # ── Utility ────────────────────────────────────────────────────────

    def _flash(self, message: str) -> None:
        self.notify(message, timeout=3)
