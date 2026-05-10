"""Editing operations on the Document model.

Tracks cursor position, manages insert/delete/format operations,
and maintains a dirty flag.
"""

from dataclasses import dataclass

from .model import Document, Paragraph, Run


@dataclass
class Cursor:
    """Cursor position within a document."""

    para: int = 0  # paragraph index
    offset: int = 0  # character offset within paragraph plain text


class Editor:
    """Manages document editing state and operations."""

    def __init__(self, doc: Document, filepath: str | None = None):
        self.doc = doc
        self.filepath = filepath
        self.cursor = Cursor(para=0, offset=0)
        self.dirty = False

    # ── helpers ────────────────────────────────────────────────────────

    def _current_para(self) -> Paragraph:
        if not self.doc.paragraphs:
            self.doc.paragraphs.append(Paragraph(runs=[Run()]))
        if self.cursor.para >= len(self.doc.paragraphs):
            self.cursor.para = len(self.doc.paragraphs) - 1
        if self.cursor.para < 0:
            self.cursor.para = 0
        return self.doc.paragraphs[self.cursor.para]

    def _ensure_run_at_cursor(self) -> tuple[Paragraph, int, int]:
        """Return (para, run_idx, char_idx) for the current cursor.

        If the paragraph is empty, add an empty run.
        """
        para = self._current_para()
        if not para.runs:
            para.runs.append(Run())
        run_idx, char_idx = para.run_at_offset(self.cursor.offset)
        return para, run_idx, char_idx

    # ── navigation ─────────────────────────────────────────────────────

    def move_up(self) -> None:
        if self.cursor.para > 0:
            self.cursor.para -= 1
            prev_len = len(self.doc.paragraphs[self.cursor.para].plain_text)
            if self.cursor.offset > prev_len:
                self.cursor.offset = prev_len

    def move_down(self) -> None:
        if self.cursor.para < len(self.doc.paragraphs) - 1:
            self.cursor.para += 1
            next_len = len(self.doc.paragraphs[self.cursor.para].plain_text)
            if self.cursor.offset > next_len:
                self.cursor.offset = next_len

    def move_left(self) -> None:
        if self.cursor.offset > 0:
            self.cursor.offset -= 1
        elif self.cursor.para > 0:
            self.cursor.para -= 1
            self.cursor.offset = len(self._current_para().plain_text)

    def move_right(self) -> None:
        para = self._current_para()
        if self.cursor.offset < len(para.plain_text):
            self.cursor.offset += 1
        elif self.cursor.para < len(self.doc.paragraphs) - 1:
            self.cursor.para += 1
            self.cursor.offset = 0

    def move_home(self) -> None:
        self.cursor.offset = 0

    def move_end(self) -> None:
        self.cursor.offset = len(self._current_para().plain_text)

    def move_top(self) -> None:
        self.cursor.para = 0
        self.cursor.offset = 0

    def move_bottom(self) -> None:
        last = len(self.doc.paragraphs) - 1
        if last >= 0:
            self.cursor.para = last
            self.cursor.offset = len(self.doc.paragraphs[last].plain_text)

    # ── editing ────────────────────────────────────────────────────────

    def insert_char(self, ch: str) -> None:
        """Insert a character at the cursor position."""
        if len(ch) != 1:
            return
        para, run_idx, char_idx = self._ensure_run_at_cursor()
        run = para.runs[run_idx]
        run.text = run.text[:char_idx] + ch + run.text[char_idx:]
        self.cursor.offset += 1
        self.dirty = True

    def insert_newline(self) -> None:
        """Split the current paragraph at the cursor."""
        para, run_idx, char_idx = self._ensure_run_at_cursor()
        run = para.runs[run_idx]

        # Split the run text
        left_text = run.text[:char_idx]
        right_text = run.text[char_idx:]
        run.text = left_text

        # Collect runs for the new paragraph: right part of split run + remaining runs
        new_runs: list[Run] = []
        if right_text:
            new_runs.append(Run(text=right_text, bold=run.bold, italic=run.italic, underline=run.underline))
        new_runs.extend(para.runs[run_idx + 1:])

        # Trim current paragraph's runs
        para.runs = para.runs[:run_idx + 1]

        # Insert new paragraph
        new_para = Paragraph(runs=new_runs if new_runs else [Run()])
        self.doc.paragraphs.insert(self.cursor.para + 1, new_para)

        self.cursor.para += 1
        self.cursor.offset = 0
        self.dirty = True

    def delete_backwards(self) -> None:
        """Delete the character before the cursor (Backspace)."""
        if self.cursor.offset > 0:
            para, run_idx, char_idx = self._ensure_run_at_cursor()
            # Find the run containing the character *before* the cursor
            prev_offset = self.cursor.offset - 1
            target_run_idx, target_char_idx = para.run_at_offset(prev_offset)
            run = para.runs[target_run_idx]
            run.text = run.text[:target_char_idx] + run.text[target_char_idx + 1:]
            self.cursor.offset -= 1
            self._cleanup_empty_runs(para)
            self.dirty = True
        elif self.cursor.para > 0:
            # Merge with previous paragraph
            prev_para = self.doc.paragraphs[self.cursor.para - 1]
            cur_para = self._current_para()
            self.cursor.offset = len(prev_para.plain_text)
            # Append all runs from current paragraph to previous
            prev_para.runs.extend(cur_para.runs)
            del self.doc.paragraphs[self.cursor.para]
            self.cursor.para -= 1
            self.dirty = True

    def delete_forwards(self) -> None:
        """Delete the character at the cursor (Delete key)."""
        para = self._current_para()
        if self.cursor.offset < len(para.plain_text):
            _para, run_idx, char_idx = self._ensure_run_at_cursor()
            run = para.runs[run_idx]
            run.text = run.text[:char_idx] + run.text[char_idx + 1:]
            self._cleanup_empty_runs(para)
            self.dirty = True
        elif self.cursor.para < len(self.doc.paragraphs) - 1:
            # Merge with next paragraph
            next_para = self.doc.paragraphs[self.cursor.para + 1]
            para.runs.extend(next_para.runs)
            del self.doc.paragraphs[self.cursor.para + 1]
            self.dirty = True

    # ── formatting ─────────────────────────────────────────────────────

    def toggle_bold(self) -> None:
        self._toggle_format("bold")

    def toggle_italic(self) -> None:
        self._toggle_format("italic")

    def toggle_underline(self) -> None:
        self._toggle_format("underline")

    def toggle_strikethrough(self) -> None:
        self._toggle_format("strikethrough")

    def _toggle_format(self, attr: str) -> None:
        """Toggle a formatting attribute at the cursor position.

        Strategy: if the cursor is inside a run, toggle that run's attribute.
        If there's a selection (future), toggle the selection.
        """
        para = self._current_para()
        if not para.runs or para.plain_text == "":
            # Create a run with the formatting toggled on
            para.runs = [Run(text="", **{attr: True})]  # type: ignore[arg-type]
            self.dirty = True
            return

        run_idx, _ = para.run_at_offset(self.cursor.offset)
        run = para.runs[run_idx]
        # Toggle the attribute on this run
        setattr(run, attr, not getattr(run, attr))
        self.dirty = True

    def apply_font_name(self, name: str) -> None:
        """Set font name on the run at cursor position."""
        para = self._current_para()
        if not para.runs or para.plain_text == "":
            para.runs = [Run(text="", font_name=name)]
            self.dirty = True
            return
        run_idx, _ = para.run_at_offset(self.cursor.offset)
        para.runs[run_idx].font_name = name
        self.dirty = True

    def apply_font_size(self, size: str) -> None:
        """Set font size (in points) on the run at cursor position."""
        para = self._current_para()
        if not para.runs or para.plain_text == "":
            para.runs = [Run(text="", font_size=size)]
            self.dirty = True
            return
        run_idx, _ = para.run_at_offset(self.cursor.offset)
        para.runs[run_idx].font_size = size
        self.dirty = True

    # ── internal ────────────────────────────────────────────────────────

    def _cleanup_empty_runs(self, para: Paragraph) -> None:
        """Remove runs that have become empty (unless it's the only run)."""
        para.runs = [r for r in para.runs if r.text != ""]
        if not para.runs:
            para.runs.append(Run())
