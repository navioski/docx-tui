"""Menu bar widget — Word 2003-style dropdown menus.

The MenuBar is a fixed 1-row bar. When a menu is opened, a separate
DropdownWidget overlay is mounted on the app so that layout is not affected.
"""

from rich.style import Style
from rich.text import Text as RichText
from textual import events
from textual.widgets import Static

# ── Word 2003 Menu Definition ──────────────────────────────────────────

MENU_DEF = [
    ("File", [
        ("New", "new_doc"),
        ("Open...          Ctrl+O", "open"),
        ("Save             Ctrl+S", "save"),
        ("Save As...", "save_as"),
        ("──────────────", None),
        ("Exit", "quit"),
        ("Force Quit", "force_quit"),
    ]),
    ("Edit", [
        ("Undo             Ctrl+Z", "undo"),
        ("Redo             Ctrl+Y", "redo"),
        ("──────────────", None),
        ("Cut              Ctrl+X", "cut"),
        ("Copy             Ctrl+C", "copy"),
        ("Paste            Ctrl+V", "paste"),
        ("──────────────", None),
        ("Select All       Ctrl+A", "select_all"),
        ("Find...          Ctrl+F", "find"),
    ]),
    ("View", [
        ("Zoom In          Ctrl+=", "zoom_in"),
        ("Zoom Out         Ctrl+-", "zoom_out"),
        ("──────────────", None),
        ("Toggle Status Bar", "toggle_status"),
    ]),
    ("Insert", [
        ("Page Break       Ctrl+Enter", "page_break"),
        ("──────────────", None),
        ("Symbol...", "symbol"),
    ]),
    ("Format", [
        ("Bold             Ctrl+B", "toggle_bold"),
        ("Italic           Ctrl+I", "toggle_italic"),
        ("Underline        Ctrl+U", "toggle_underline"),
        ("──────────────", None),
        ("Strikethrough", "toggle_strikethrough"),
    ]),
    ("Tools", [
        ("Word Count", "word_count"),
        ("──────────────", None),
        ("Spell Check", "spell_check"),
    ]),
    ("Table", [
        ("Insert Table...", "insert_table"),
        ("──────────────", None),
        ("Delete Table", "delete_table"),
    ]),
    ("Window", [
        ("New Window", "new_window"),
    ]),
    ("Help", [
        ("Keyboard Shortcuts  F1", "help"),
        ("──────────────", None),
        ("About DocxEditor", "about"),
    ]),
]

# ── Styles ─────────────────────────────────────────────────────────────

BAR_BG      = Style(bgcolor="#1c3a5e", color="#ffffff")
BAR_ACTIVE  = Style(bgcolor="#2d5f9e", color="#ffffff", bold=True)
BAR_HOVER   = Style(bgcolor="#2d5f9e", color="#ffffff")
DROP_BG     = Style(bgcolor="#3c3c5c", color="#e8e8e8")
DROP_HOVER  = Style(bgcolor="#5c5c8c", color="#ffffff", bold=True)
DROP_SEP    = Style(bgcolor="#3c3c5c", color="#555577")
DROP_BORDER = Style(bgcolor="#3c3c5c", color="#5a5a7a")
SEP         = " │ "


# ── MenuBar ────────────────────────────────────────────────────────────

class MenuBar(Static):
    """Top menu bar — fixed 1-row height. Dropdown is an overlay widget."""

    DEFAULT_CSS = """
    MenuBar {
        height: 1;
    }
    """

    can_focus = True

    def __init__(self, app: object, title: str = "DocxEditor", *args, **kwargs):
        super().__init__("", *args, **kwargs)
        self._app = app
        self._title = title
        self._active: int | None = None
        self._hover_menu: int | None = None

        # Pre-compute label start column for each menu
        self._label_starts: list[int] = []
        col = 1
        for label, _ in MENU_DEF:
            self._label_starts.append(col)
            col += len(label) + 2 + len(SEP)

    @property
    def label_starts(self) -> list[int]:
        return self._label_starts

    # ── Geometry ───────────────────────────────────────────────────────

    def get_content_height(self, container, viewport, width):
        return 1

    # ── Rendering ──────────────────────────────────────────────────────

    def render(self) -> RichText:
        out = RichText()
        vw = self.size.width if self.size else 80

        for i, (label, _items) in enumerate(MENU_DEF):
            if i == self._active:
                s = BAR_ACTIVE
            elif i == self._hover_menu:
                s = BAR_HOVER
            else:
                s = BAR_BG
            out.append(f" {label} ", style=s)
            out.append(SEP, style=BAR_BG)

        out.append(self._title, style=Style(color="#88aacc", bgcolor="#1c3a5e"))
        cl = out.cell_len
        if cl < vw:
            out.append(" " * (vw - cl), style=BAR_BG)

        return out

    # ── Toggle active menu ─────────────────────────────────────────────

    def _set_active(self, idx: int | None) -> None:
        if self._active == idx:
            return
        self._active = idx
        self.refresh()

        # Tell the app to show/hide the dropdown overlay
        app = self._app
        if idx is not None:
            show = getattr(app, "_show_dropdown", None)
            if show:
                show(idx)
        else:
            hide = getattr(app, "_hide_dropdown", None)
            if hide:
                hide()

    # ── Click handling ─────────────────────────────────────────────────

    def on_click(self, event: events.Click) -> None:
        x, y = event.x, event.y

        if y == 0:
            for i, start in enumerate(self._label_starts):
                label, _items = MENU_DEF[i]
                end = start + len(label) + 1
                if start <= x <= end:
                    if self._active == i:
                        self._set_active(None)
                    else:
                        self._set_active(i)
                    return
            # Clicked elsewhere on bar — close
            if self._active is not None:
                self._set_active(None)

    # ── Mouse move ─────────────────────────────────────────────────────

    def on_mouse_move(self, event: events.MouseMove) -> None:
        x, y = event.x, event.y
        changed = False

        if y == 0:
            new_hover: int | None = None
            for i, start in enumerate(self._label_starts):
                label, _items = MENU_DEF[i]
                end = start + len(label) + 1
                if start <= x <= end:
                    new_hover = i
                    break
            if new_hover != self._hover_menu:
                self._hover_menu = new_hover
                changed = True
        elif self._hover_menu is not None:
            self._hover_menu = None
            changed = True

        if changed:
            self.refresh()

    # ── Keyboard ────────────────────────────────────────────────────────

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            if self._active is not None:
                self._set_active(None)


# ── DropdownWidget (overlay) ────────────────────────────────────────────

class DropdownWidget(Static):
    """Floating dropdown overlay — mounted on the app when a menu is open."""

    DEFAULT_CSS = """
    DropdownWidget {
        height: auto;
        width: auto;
    }
    """

    can_focus = True

    def __init__(
        self,
        app: object,
        menu_index: int,
        offset_x: int,
        *args,
        **kwargs,
    ):
        super().__init__("", *args, **kwargs)
        self._app = app
        self._menu_index = menu_index
        self._hover_item: int | None = None

        _, all_items = MENU_DEF[menu_index]
        self._items = [(d, a) for (d, a) in all_items if a is not None]

        # Compute dropdown width
        max_item_len = max((len(d) for d, _ in self._items), default=16)
        self._dd_width = min(max_item_len + 4, 42)

        # Position right below the menu bar, aligned with the active tab.
        # Mounted before doc_view in layout → natural y is right after menu bar.
        self.styles.overlay = "screen"
        self.styles.margin = (0, 0, 0, offset_x)  # left margin pushes it right
        self.styles.width = self._dd_width

    # ── Rendering ──────────────────────────────────────────────────────

    def render(self) -> RichText:
        out = RichText()
        w = self._dd_width

        # Top border
        out.append("┌" + "─" * (w - 2) + "┐", style=DROP_BORDER)

        for j, (display, _action) in enumerate(self._items):
            out.append("\n")
            if display.startswith("─"):
                s = DROP_SEP
                interior = "─" * (w - 2)
                out.append("│" + interior + "│", style=s)
            elif j == self._hover_item:
                s = DROP_HOVER
                content = f" {display}".ljust(w - 2)
                out.append("│" + content + "│", style=s)
            else:
                s = DROP_BG
                content = f" {display}".ljust(w - 2)
                out.append("│" + content + "│", style=s)

        # Bottom border
        out.append("\n")
        out.append("└" + "─" * (w - 2) + "┘", style=DROP_BORDER)

        return out

    # ── Click handling ─────────────────────────────────────────────────

    def on_click(self, event: events.Click) -> None:
        event.stop()  # prevent click from reaching widgets underneath
        x, y = event.x, event.y
        if 0 <= y - 1 < len(self._items):  # row 0 = top border
            idx = y - 1
            if 0 <= idx < len(self._items):
                if 1 <= x < self._dd_width - 1:  # inside the borders
                    self._trigger(self._items[idx][1])

    # ── Mouse move ─────────────────────────────────────────────────────

    def on_mouse_move(self, event: events.MouseMove) -> None:
        x, y = event.x, event.y
        idx = y - 1  # row 0 = top border
        if 0 <= idx < len(self._items) and 1 <= x < self._dd_width - 1:
            if idx != self._hover_item:
                self._hover_item = idx
                self.refresh()
        else:
            if self._hover_item is not None:
                self._hover_item = None
                self.refresh()

    # ── Trigger ─────────────────────────────────────────────────────────

    def _trigger(self, action_id: str) -> None:
        # Close menu BEFORE triggering action, so the dropdown is gone
        # before any new screen (e.g. ForceQuitScreen) is pushed.
        close = getattr(self._app, "_hide_dropdown", None)
        if close:
            close()
        bar = getattr(self._app, "menu_bar", None)
        if bar:
            bar._set_active(None)

        method = getattr(self._app, f"action_{action_id}", None)
        if method:
            method()
        else:
            notify = getattr(self._app, "notify", None)
            if notify:
                notify(f"'{action_id}' — coming soon", timeout=2)


# ── Picker dropdown (font / size / etc.) ────────────────────────────────

class PickerDropdown(Static):
    """Simple option-list overlay, like a dropdown for font/size selection."""

    DEFAULT_CSS = """
    PickerDropdown {
        height: auto;
        width: auto;
    }
    """

    def __init__(
        self,
        app: object,
        options: list[tuple[str, str]],
        offset_x: int,
        callback_name: str,
        *args,
        **kwargs,
    ):
        super().__init__("", *args, **kwargs)
        self._app = app
        self._options = options
        self._hover: int | None = None
        self._callback_name = callback_name

        max_len = max(len(label) for label, _ in options)
        self._dd_width = min(max_len + 4, 42)
        self.styles.overlay = "screen"
        self.styles.margin = (0, 0, 0, offset_x)
        self.styles.width = self._dd_width

    def render(self) -> RichText:
        out = RichText()
        w = self._dd_width
        out.append("┌" + "─" * (w - 2) + "┐", style=DROP_BORDER)
        for j, (label, _value) in enumerate(self._options):
            out.append("\n")
            s = DROP_HOVER if j == self._hover else DROP_BG
            content = f" {label}".ljust(w - 2)
            out.append("│" + content + "│", style=s)
        out.append("\n")
        out.append("└" + "─" * (w - 2) + "┘", style=DROP_BORDER)
        return out

    def on_click(self, event: events.Click) -> None:
        event.stop()
        x, y = event.x, event.y
        idx = y - 1
        if 0 <= idx < len(self._options) and 1 <= x < self._dd_width - 1:
            _label, value = self._options[idx]
            # Call callback first, then close picker
            cb = getattr(self._app, self._callback_name, None)
            if cb:
                cb(value)
            close = getattr(self._app, "_hide_picker", None)
            if close:
                close()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        x, y = event.x, event.y
        idx = y - 1
        if 0 <= idx < len(self._options) and 1 <= x < self._dd_width - 1:
            if idx != self._hover:
                self._hover = idx
                self.refresh()
        else:
            if self._hover is not None:
                self._hover = None
                self.refresh()


# ── Toolbar styles ─────────────────────────────────────────────────────

TB_BG      = Style(bgcolor="#c8c4bc", color="#111111")
TB_BTN     = Style(bgcolor="#dcd8d0", color="#111111")
TB_BTN_HOV = Style(bgcolor="#ece8e0", color="#111111", bold=True)
TB_SEP_BG  = Style(bgcolor="#c8c4bc", color="#999999")
TB_TOGGLE_ON = Style(bgcolor="#b8d0e8", color="#111111", bold=True)  # pressed-in look


# ── Standard toolbar ───────────────────────────────────────────────────

STD_BUTTONS = [
    (" New ", "new_doc"),
    (" Open ", "open"),
    (" Save ", "save"),
    (None, None),  # separator
    (" Undo ", "undo"),
    (" Redo ", "redo"),
]


class StandardToolbar(Static):
    """Word 2003-style Standard toolbar: New, Open, Save, Undo, Redo."""

    DEFAULT_CSS = """
    StandardToolbar {
        height: 1;
        background: #c8c4bc;
    }
    """

    def __init__(self, app: object, *args, **kwargs):
        super().__init__("", *args, **kwargs)
        self._app = app
        self._hover: int | None = None
        # Pre-compute button x-ranges
        self._btn_ranges: list[tuple[int, int] | None] = []
        col = 1
        for label, _action in STD_BUTTONS:
            if label is None:
                self._btn_ranges.append(None)
                col += 3  # " │ "
            else:
                self._btn_ranges.append((col, col + len(label)))
                col += len(label) + 1

    def render(self) -> RichText:
        out = RichText(style=TB_BG)
        vw = self.size.width if self.size else 80

        for i, (label, _action) in enumerate(STD_BUTTONS):
            if label is None:
                out.append(" │ ", style=TB_SEP_BG)
            elif i == self._hover:
                out.append(label, style=TB_BTN_HOV)
            else:
                out.append(label, style=TB_BTN)

        cl = out.cell_len
        if cl < vw:
            out.append(" " * (vw - cl), style=TB_BG)
        return out

    def on_click(self, event: events.Click) -> None:
        if event.y != 0:
            return
        for i, rng in enumerate(self._btn_ranges):
            if rng is None:
                continue
            start, end = rng
            if start <= event.x < end:
                _, action = STD_BUTTONS[i]
                if action:
                    method = getattr(self._app, f"action_{action}", None)
                    if method:
                        method()
                return

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if event.y != 0:
            if self._hover is not None:
                self._hover = None
                self.refresh()
            return
        new_hover: int | None = None
        for i, rng in enumerate(self._btn_ranges):
            if rng is None:
                continue
            start, end = rng
            if start <= event.x < end:
                new_hover = i
                break
        if new_hover != self._hover:
            self._hover = new_hover
            self.refresh()


# ── Formatting toolbar ─────────────────────────────────────────────────

FMT_FONT_SIZES = [
    "8", "9", "10", "11", "12", "14", "16", "18",
    "20", "24", "28", "36", "48", "72",
]

FMT_BUTTONS = [
    (" B ", "toggle_bold"),
    (" I ", "toggle_italic"),
    (" U ", "toggle_underline"),
    (" S ", "toggle_strikethrough"),
]


class FormattingToolbar(Static):
    """Word 2003-style Formatting toolbar: font, size, bold/italic/underline."""

    DEFAULT_CSS = """
    FormattingToolbar {
        height: 1;
        background: #c8c4bc;
    }
    """

    def __init__(self, app: object, *args, **kwargs):
        super().__init__("", *args, **kwargs)
        self._app = app
        self._hover: int | None = None
        self._font_btn_x = 0
        self._font_btn_w = 0
        self._size_btn_x = 0
        self._size_btn_w = 0
        self._segments: list[tuple[str, Style]] = []
        self._click_map: list[tuple[int, int, str | None]] = []

    def _build_layout(self) -> None:
        """Rebuild segments and click map with current font/size from editor."""
        editor = getattr(self._app, "editor", None)
        fs = Style(bgcolor="#c8c4bc", color="#111111")

        # Read current font name and size from the run under cursor
        font_name = "Times New Roman"
        font_size = "12"
        if editor:
            try:
                para = editor._current_para()
                if para.runs:
                    run_idx, _ = para.run_at_offset(editor.cursor.offset)
                    if 0 <= run_idx < len(para.runs):
                        run = para.runs[run_idx]
                        if run.font_name:
                            font_name = run.font_name
                        if run.font_size:
                            font_size = run.font_size
            except Exception:
                pass

        self._segments.clear()
        self._click_map.clear()
        col = 1

        # Font label
        self._segments.append((" Font: ", fs))
        col += 7

        # Font name button
        font_btn = f" {font_name} ▼ "
        self._font_btn_x = col
        self._font_btn_w = len(font_btn)
        self._click_map.append((col, col + len(font_btn), None))
        self._segments.append((font_btn, TB_BTN))
        col += len(font_btn)

        # Size label
        self._segments.append(("  Size: ", fs))
        col += 8

        # Size button
        size_btn = f" {font_size} ▼ "
        self._size_btn_x = col
        self._size_btn_w = len(size_btn)
        self._click_map.append((col, col + len(size_btn), None))
        self._segments.append((size_btn, TB_BTN))
        col += len(size_btn)

        # Separator
        self._segments.append((" │ ", TB_SEP_BG))
        col += 3

        # Toggle buttons
        for label, action in FMT_BUTTONS:
            start = col
            self._click_map.append((start, start + len(label), action))
            self._segments.append((label, TB_BTN))
            col += len(label)

    def render(self) -> RichText:
        self._build_layout()
        out = RichText(style=TB_BG)
        vw = self.size.width if self.size else 80

        for i, (text, base_style) in enumerate(self._segments):
            s = base_style
            if i == self._hover:
                s = Style.combine([base_style, TB_BTN_HOV]) if base_style == TB_BTN else TB_BTN_HOV
            out.append(text, style=s)

        cl = out.cell_len
        if cl < vw:
            out.append(" " * (vw - cl), style=TB_BG)
        return out

    def on_click(self, event: events.Click) -> None:
        if event.y != 0:
            return
        # Check font button
        if self._font_btn_x <= event.x < self._font_btn_x + self._font_btn_w:
            show = getattr(self._app, "_show_font_picker", None)
            if show:
                show(self._font_btn_x)
            return
        # Check size button
        if self._size_btn_x <= event.x < self._size_btn_x + self._size_btn_w:
            show = getattr(self._app, "_show_size_picker", None)
            if show:
                show(self._size_btn_x)
            return
        # Other buttons
        for start, end, action in self._click_map:
            if action and start <= event.x < end:
                method = getattr(self._app, f"action_{action}", None)
                if method:
                    method()
                else:
                    notify = getattr(self._app, "notify", None)
                    if notify:
                        notify(f"'{action}' — coming soon", timeout=2)
                return

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if event.y != 0:
            if self._hover is not None:
                self._hover = None
                self.refresh()
            return
        new_hover: int | None = None
        for i, (start, end, _action) in enumerate(self._click_map):
            if start <= event.x < end:
                new_hover = i
                break
        if new_hover != self._hover:
            self._hover = new_hover
            self.refresh()
