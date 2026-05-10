"""Page rendering — Word 2003-style A4 page with ruler.

PageView: white page rectangle with border, shadow, and line numbers.
HorizontalRuler: column measurement bar above the page.
"""

from rich.style import Style
from rich.text import Text as RichText
from textual.widget import Widget

from .editor import Editor

# ── Page dimensions ────────────────────────────────────────────────────

PAGE_WIDTH = 70  # total columns (border included via CSS)
PADDING = 2  # CSS padding left+right (1 each side)
LINE_NUM_WIDTH = 4  # " 123│"
TEXT_WIDTH = PAGE_WIDTH - PADDING - LINE_NUM_WIDTH  # 64 chars for text

# ── Colors ─────────────────────────────────────────────────────────────

PAGE_BG = "#ffffff"
PAGE_BORDER = "#aaaaaa"
WORKSPACE_BG = "#808080"
RULER_BG = "#c0c0c0"
RULER_FG = "#444444"
LINE_NUM_FG = "#aaaaaa"
SHADOW = "#666666"


# ── Text wrapping helper ──────────────────────────────────────────────

def _wrap_paragraph(text: str, width: int) -> list[str]:
    """Soft-wrap text at word boundaries, with line width limit."""
    lines: list[str] = []
    while len(text) > width:
        split = text.rfind(" ", 0, width + 1)
        if split == -1:
            split = width  # hard break on long word
        lines.append(text[:split])
        text = text[split:].lstrip()
    if text or not lines:
        lines.append(text)
    return lines


# ── Horizontal ruler ───────────────────────────────────────────────────

class HorizontalRuler(Widget):
    """Horizontal ruler showing column marks, aligned with the page."""

    DEFAULT_CSS = f"""
    HorizontalRuler {{
        height: 1;
        width: {PAGE_WIDTH};
        background: {RULER_BG};
        color: {RULER_FG};
    }}
    """

    def render(self) -> RichText:
        out = RichText(style=Style(bgcolor=RULER_BG, color=RULER_FG))
        # Tick marks every 5 columns, with numbers at 10, 20, 30...
        ruler = ""
        for col in range(1, TEXT_WIDTH + 1):
            if col % 10 == 0:
                ruler += f"{col:<3}"[:2]
            elif col % 5 == 0:
                ruler += "▌"
            else:
                ruler += " "
        # Pad to page width (minus border area)
        padded = ruler.ljust(PAGE_WIDTH - 2)[: PAGE_WIDTH - 2]
        out.append(padded)
        return out


# ── Page view ──────────────────────────────────────────────────────────

class PageView(Widget):
    """A4-like page with white background, border, shadow, and line numbers."""

    DEFAULT_CSS = f"""
    PageView {{
        width: {PAGE_WIDTH};
        height: 1fr;
        background: {PAGE_BG};
        color: #111111;
        border: solid {PAGE_BORDER};
        padding: 0 1;
        overflow-y: auto;
    }}
    """

    can_focus = True

    def __init__(self, editor: Editor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor
        self._line_count = 1

    def on_click(self, event) -> None:
        """Close any open dropdown or picker when clicking the page area."""
        hide = getattr(self.app, "_hide_dropdown", None)
        if hide:
            hide()
        hide_picker = getattr(self.app, "_hide_picker", None)
        if hide_picker:
            hide_picker()
        bar = getattr(self.app, "menu_bar", None)
        if bar:
            bar._set_active(None)

    def on_mount(self) -> None:
        """Report cursor position so IME candidates appear at the right place."""
        self._cursor_timer = self.set_interval(0.1, self._sync_cursor)

    def stop_timers(self) -> None:
        """Stop background timers so the app can exit cleanly."""
        if hasattr(self, "_cursor_timer") and self._cursor_timer is not None:
            self._cursor_timer.stop()

    def _sync_cursor(self) -> None:
        cur = self.editor.cursor
        # Cursor column: LINE_NUM_WIDTH + offset within current visual line
        self.cursor_position = (cur.offset % 64 + LINE_NUM_WIDTH + 2, cur.para + 2)

    def render(self) -> RichText:
        doc = self.editor.doc
        cursor = self.editor.cursor
        out = RichText()

        line_no = 1
        cursor_line: int | None = None
        cursor_col: int | None = None

        for pi, para in enumerate(doc.paragraphs):
            text = para.plain_text
            wrapped = _wrap_paragraph(text, TEXT_WIDTH)

            for wi, line_text in enumerate(wrapped):
                # ── Line number ──
                ln = f" {line_no:2d} "
                out.append(ln, style=Style(color=LINE_NUM_FG))

                # ── Check if cursor is on this visual line ──
                if pi == cursor.para:
                    # Calculate the offset range this wrapped line covers
                    line_start = 0
                    for wj in range(wi):
                        line_start += len(wrapped[wj]) + 1  # +1 for space/break
                    line_end = line_start + len(line_text)

                    if cursor.offset >= line_start and (
                        cursor.offset < line_end
                        or (wi == len(wrapped) - 1 and cursor.offset >= line_start)
                    ):
                        cursor_line = line_no
                        cursor_col = LINE_NUM_WIDTH + (
                            cursor.offset - line_start
                        )

                # ── Render line text, with cursor highlight if needed ──
                if cursor_line == line_no and cursor_col is not None:
                    col = cursor_col - LINE_NUM_WIDTH
                    if col < 0:
                        col = 0
                    if col >= len(line_text):
                        out.append(line_text)
                        out.append(" ", style=Style(reverse=True))
                    else:
                        out.append(line_text[:col])
                        out.append(
                            line_text[col],
                            style=Style(reverse=True, bold=True),
                        )
                        out.append(line_text[col + 1 :])
                else:
                    out.append(line_text)

                out.append("\n")
                line_no += 1

        # Ensure at least one line
        if line_no == 1:
            out.append(f" {'1':>2} \n")
            line_no += 1

        self._line_count = line_no - 1
        return out

    @property
    def total_lines(self) -> int:
        return self._line_count
