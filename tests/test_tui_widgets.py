import pytest
from textual.app import App
from tui.widgets.cpu_stats import CPUStatsGroup

class WidgetTestApp(App):
    def __init__(self, widget, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget = widget

    def compose(self):
        yield self.widget

@pytest.mark.asyncio

async def test_cpu_stats_group_update_data_with_empty_metrics():
    """
    Test that the CPUStatsGroup widget can handle an update with empty metrics
    without raising an exception.
    """
    widget = CPUStatsGroup(title="CPU Stats")
    app = WidgetTestApp(widget)

    async with app.run_test() as pilot:
        try:
            widget.update_data({})
            # If the above line doesn't raise an exception, the test passes.
        except Exception as e:
            pytest.fail(f"update_data with empty metrics raised an exception: {e}")
