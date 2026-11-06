"""Quick test: does overlay:true affect layout?"""
from textual.app import App, ComposeResult
from textual.widgets import Static
from textual.containers import Vertical

class TestApp(App):
    CSS = """
    #overlay-box {
        overlay: true;
        offset-x: 20;
        offset-y: 2;
        width: 30;
        height: 5;
        background: red 20%;
        color: white;
    }
    """
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Row 0: Top bar area — this should NOT shift")
            yield Static("Row 1")
            yield Static("Row 2")
            yield Static("Row 3")
            yield Static("Row 4")
            yield Static("Row 5")
            yield Static("Row 6")
            yield Static("Row 7")
            yield Static("Row 8")
            yield Static("Row 9")
        yield Static("OVERLAY: this should float on top", id="overlay-box")

if __name__ == "__main__":
    app = TestApp()
    widget = app.query_one("#overlay-box")
    print(f"overlay={widget.styles.overlay}")
    print(f"offset_x={widget.styles.offset_x}")
    print(f"offset_y={widget.styles.offset_y}")
    print("CSS supported OK")
