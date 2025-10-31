from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label

class MetricGroup(Container):
    """Base class for all metric group widgets."""

    def __init__(self, title: str, *args, **kwargs) -> None:
        self.title = title
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """Renders the title of the metric group."""
        yield Label(self.title)
        content_id = f"content_{self.id}" if self.id else None
        yield Container(id=content_id)
