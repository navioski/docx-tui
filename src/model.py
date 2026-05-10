"""Document model for the TUI docx editor.

Represents a .docx document as paragraphs composed of styled runs.
"""

from dataclasses import dataclass, field


@dataclass
class Run:
    """A contiguous run of text with uniform formatting."""

    text: str = ""
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    font_name: str = ""
    font_size: str = ""

    def __bool__(self) -> bool:
        return len(self.text) > 0


@dataclass
class Paragraph:
    """A paragraph composed of zero or more runs."""

    runs: list[Run] = field(default_factory=list)

    @property
    def plain_text(self) -> str:
        return "".join(r.text for r in self.runs)

    def run_at_offset(self, offset: int) -> tuple[int, int]:
        """Return (run_index, char_index_within_run) for the given character offset.

        If offset equals the total length, returns the position just past the last run.
        If there are no runs, returns (0, 0).
        """
        if offset < 0:
            return (0, 0)
        current = 0
        for i, run in enumerate(self.runs):
            run_len = len(run.text)
            if current + run_len > offset:
                return (i, offset - current)
            current += run_len
        # offset is at or past the end
        if self.runs:
            return (len(self.runs) - 1, len(self.runs[-1].text))
        return (0, 0)


@dataclass
class Document:
    """A complete document: a sequence of paragraphs."""

    paragraphs: list[Paragraph] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.paragraphs) == 0 or all(
            p.plain_text == "" for p in self.paragraphs
        )

    @property
    def total_chars(self) -> int:
        return sum(len(p.plain_text) for p in self.paragraphs)
