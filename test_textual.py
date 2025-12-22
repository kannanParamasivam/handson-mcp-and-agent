from textual.app import App
from textual.containers import Horizontal, HorizontalGroup
from textual.widgets import Header, Footer, Static, Input, RichLog, LoadingIndicator
from time import sleep

class TestApp(App):

    def __init__(self):
      print("init")
      super().__init__()

    def compose(self):
      print("compose")
      yield Header(show_clock=True)
      with Horizontal(id="body"):
        yield RichLog(id="chat", highlight=False, markup=True, wrap=True)
        yield Static(id="somethingelse")
      with Horizontal(id="input_row"):
        yield LoadingIndicator(id="spinner")
        yield Input(placeholder="Type a message and press Enter…", id="prompt")
      yield Footer()

    def _prompt(self) -> Input:
      return self.query_one("#prompt", Input)

    def on_mount(self):
      self.query_one("#spinner", LoadingIndicator).display = False
      self._prompt().focus()


if __name__ == "__main__":
    TestApp().run()