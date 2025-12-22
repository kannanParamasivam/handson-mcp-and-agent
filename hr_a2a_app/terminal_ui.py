#!/usr/bin/env python3

import io
import re
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime

import httpx
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Input, RichLog, Static, LoadingIndicator

from langchain_core.messages import HumanMessage

import hr_router_agent as router_mod


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class _CaptureStream(io.StringIO):
    def __init__(self, on_line):
        super().__init__()
        self._on_line = on_line
        self._buf = ""

    def write(self, s: str) -> int:
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.rstrip()
            if line:
                self._on_line(line)
        return len(s)

    def flush(self) -> None:
        if self._buf.strip():
            self._on_line(self._buf.strip())
        self._buf = ""


class RouterChatApp(App):
    TITLE = "HR Agent"

    BINDINGS = [
        Binding("f2", "focus_logs", "Logs"),
        Binding("escape", "focus_prompt", "Input", show=False),
        Binding("pageup", "scroll_logs_up", show=False),
        Binding("pagedown", "scroll_logs_down", show=False),
    ]

    CSS = """
    Screen {
        layout: vertical;
    }

    /* Main area: chat + result side by side
       Logs below, input at the bottom.
       Sizes are responsive and will fit terminal window.
       NOTE: Textual automatically supports scrolling. */
     
    #body {
        height: 1fr;
    }

    #chat {
        border: solid $primary;
        width: 2fr;
    }

    #result {
        border: solid green;
        height: 14;
    }

    #right {
        width: 1fr;
    }

    #shortcuts {
        border: solid $accent;
        height: 1fr;
    }

    #logs {
        height: 12;
        border: solid magenta;
        overflow-y: auto;
    }

    #input_row {
        height: 5;
        border: solid $primary;
    }

    #spinner {
        width: 4;
    }

    #prompt {
        width: 1fr;
    }
    """

    def __init__(self):
        super().__init__()
        self.last_route: str | None = None
        self.last_answer: str | None = None

        self._busy: bool = False
        self._activity_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._activity_index = 0
 
        self._mcp_connected: bool = False
        self._policy_connected: bool = False
        self._timeoff_connected: bool = False
        self._mcp_proc: subprocess.Popen[str] | None = None
        self._policy_proc: subprocess.Popen[str] | None = None
        self._timeoff_proc: subprocess.Popen[str] | None = None
        self._health_stop = threading.Event()
        self._logged_in: bool = False
        self.router_agent: router_mod.RouterHRAgent | None = None

        # Patch router module logger function so we can display logs inside the UI
        self._orig_log_message = router_mod.log_message

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            yield RichLog(id="chat", highlight=False, markup=True, wrap=True)
            with Vertical(id="right"):
                yield Static("", id="result")
                yield Static("", id="shortcuts")
        yield RichLog(id="logs", highlight=False, markup=True, wrap=True, auto_scroll=False)
        with Horizontal(id="input_row"):
            yield LoadingIndicator(id="spinner")
            yield Input(placeholder="Type a message and press Enter…", id="prompt")
        yield Footer()

    def on_mount(self) -> None:
        self._spinner().display = False
        self._install_log_hook()
        self._start_wrapper_servers_if_needed()
        self._start_health_thread()
        self._refresh_result()
        self._refresh_shortcuts()
        self._show_login_prompt()
        self._logs().can_focus = True

        self._chat().border_title = "Chat"
        self._logs().border_title = "Logs"
        self._result().border_title = "Status"
        self._shortcuts().border_title = "Shortcuts"

        # Drives the animated indicator in the side panel.
        self.set_interval(0.12, self._tick_activity)


    def _tick_activity(self) -> None:
        if not self._busy:
            return
        self._activity_index = (self._activity_index + 1) % len(self._activity_frames)
        self._refresh_result()

    def _current_activity_agent(self) -> str:
        # While busy, we treat the Router as active until the decision is known.
        if not self._busy:
            return "Idle"
        if self.last_route is None:
            return "Router"
        if self.last_route == "POLICY":
            return "Policy agent"
        if self.last_route == "TIMEOFF":
            return "Timeoff agent"
        if self.last_route == "UNSUPPORTED":
            return "Unsupported"
        return "Router"

    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def action_focus_logs(self) -> None:
        self._logs().focus()

    def action_focus_prompt(self) -> None:
        self._prompt().focus()

    def action_scroll_logs_up(self) -> None:
        self._logs().scroll_page_up(animate=False)

    def action_scroll_logs_down(self) -> None:
        self._logs().scroll_page_down(animate=False)

    def _start_wrapper_servers_if_needed(self) -> None:
        mcp_up = self._check_http_up("http://localhost:8000/")
        policy_up = self._check_agent_card("http://localhost:9001")
        timeoff_up = self._check_agent_card("http://localhost:9002")

        # Start Timeoff MCP server (8000)
        if not mcp_up:
            self._mcp_proc = self._spawn_server(
                [sys.executable, "-m", "time_off_app.time_off_mcp_server"],
                "MCP-SERVER",
            )
        else:
            self._mcp_connected = True

        # Start HR Policy A2A wrapper server (9001)
        if not policy_up:
            self._policy_proc = self._spawn_server(
                [sys.executable, "-m", "hr_a2a_app.hr_policy_a2a_wrapper_server"],
                "POLICY-SERVER",
            )
        else:
            self._policy_connected = True

        # Start Timeoff A2A wrapper server (9002)
        if not timeoff_up:
            self._timeoff_proc = self._spawn_server(
                [sys.executable, "-m", "hr_a2a_app.time_off_policy_a2a_wrapper_server"],
                "TIMEOFF-SERVER",
            )
        else:
            self._timeoff_connected = True

    def _spawn_server(self, argv: list[str], prefix: str) -> subprocess.Popen[str]:
        proc = subprocess.Popen(
            argv,
            cwd=str(self._repo_root()),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        def _is_ping_line(s: str) -> bool:
            # Uvicorn access log examples:
            #   INFO: 127.0.0.1:... - "GET /.well-known/agent-card.json HTTP/1.1" 200 OK
            # FastMCP may log similar GET / probes.
            if "GET /.well-known/agent-card.json" in s:
                return True
            if "MCP" in prefix and "GET /" in s:
                return True
            return False

        def _pump() -> None:
            if proc.stdout is None:
                return
            for line in proc.stdout:
                line = line.rstrip("\n")
                if line:
                    if _is_ping_line(line):
                        continue
                    self.call_from_thread(self._append_log, f"{prefix}: {line}")

        threading.Thread(target=_pump, daemon=True).start()
        return proc

    def _check_agent_card(self, base_url: str) -> bool:
        try:
            r = httpx.get(f"{base_url}/.well-known/agent-card.json", timeout=0.5)
            return r.status_code == 200
        except Exception:
            return False

    def _check_http_up(self, url: str) -> bool:
        try:
            r = httpx.get(url, timeout=0.5)
            return 200 <= r.status_code < 500
        except Exception:
            return False

    def _start_health_thread(self) -> None:
        def _loop() -> None:
            while not self._health_stop.is_set():
                mcp_up = self._check_http_up("http://localhost:8000/")
                policy_up = self._check_agent_card("http://localhost:9001")
                timeoff_up = self._check_agent_card("http://localhost:9002")

                changed = (
                    (mcp_up != self._mcp_connected)
                    or (policy_up != self._policy_connected)
                    or (timeoff_up != self._timeoff_connected)
                )
                self._mcp_connected = mcp_up
                self._policy_connected = policy_up
                self._timeoff_connected = timeoff_up
                if changed:
                    self.call_from_thread(self._refresh_result)
                self._health_stop.wait(1.0)

        threading.Thread(target=_loop, daemon=True).start()

    def _chat(self) -> RichLog:
        return self.query_one("#chat", RichLog)

    def _logs(self) -> RichLog:
        return self.query_one("#logs", RichLog)

    def _result(self) -> Static:
        return self.query_one("#result", Static)

    def _shortcuts(self) -> Static:
        return self.query_one("#shortcuts", Static)

    def _refresh_shortcuts(self) -> None:
        self._shortcuts().update(
            "help  / ?     Show examples\n"
            "clear         Clear chat + logs\n"
            "exit / q      Quit\n"
            "F2            Focus logs\n"
            "Esc           Focus input\n"
            "PgUp/PgDn     Scroll logs"
        )

    def _prompt(self) -> Input:
        return self.query_one("#prompt", Input)

    def _spinner(self) -> LoadingIndicator:
        return self.query_one("#spinner", LoadingIndicator)

    def _append_log(self, line: str) -> None:
        clean = _ANSI_RE.sub("", line)
        m = re.search(r"Destination chosen\s*:\s*(\w+)", clean)
        if m:
            self.last_route = m.group(1)
            self._refresh_result()

        ts = datetime.now().strftime("%H:%M:%S")
        self._logs().write(f"[dim]{ts}[/dim] {clean}")

    def _install_log_hook(self) -> None:
        def _ui_log_message(actor: str, log_msg: str):
            self.call_from_thread(self._append_log, f"{actor}: {log_msg}")

        router_mod.log_message = _ui_log_message

    def _refresh_result(self) -> None:
        route = self.last_route or "-"

        if self._busy:
            frame = self._activity_frames[self._activity_index]
            active = self._current_activity_agent()
            activity_line = f"[b]Active[/b]\n{frame} {active}\n\n"
        else:
            activity_line = "[b]Active[/b]\n-\n\n"

        if self._mcp_connected:
            mcp_badge = "[black on green] CONNECTED [/black on green]"
        elif self._mcp_proc is not None and self._mcp_proc.poll() is None:
            mcp_badge = "[black on yellow] STARTING [/black on yellow]"
        else:
            mcp_badge = "[white on red] DOWN [/white on red]"

        if self._policy_connected:
            policy_badge = "[black on green] CONNECTED [/black on green]"
        elif self._policy_proc is not None and self._policy_proc.poll() is None:
            policy_badge = "[black on yellow] STARTING [/black on yellow]"
        else:
            policy_badge = "[white on red] DOWN [/white on red]"

        if self._timeoff_connected:
            timeoff_badge = "[black on green] CONNECTED [/black on green]"
        elif self._timeoff_proc is not None and self._timeoff_proc.poll() is None:
            timeoff_badge = "[black on yellow] STARTING [/black on yellow]"
        else:
            timeoff_badge = "[white on red] DOWN [/white on red]"

        self._result().update(
            "[b]Servers[/b]\n"
            f"Timeoff MCP server  {mcp_badge}\n"
            f"Policy agent        {policy_badge}\n"
            f"Timeoff agent       {timeoff_badge}\n\n"
            f"{activity_line}"
            f"[b]Decision[/b]\n{route}"
        )

    def _set_busy(self, busy: bool) -> None:
        self._spinner().display = busy
        self._prompt().disabled = busy
        self._busy = busy
        if busy:
            self._activity_index = 0
        self._refresh_result()

    def _show_login_prompt(self) -> None:
        self._chat().write(
            "[b]Login[/b]: enter your user name (default: [b]Alice[/b]) and press Enter."
        )
        self._prompt().placeholder = "User name (default Alice)…"
        self._prompt().focus()

    def _clear_input_and_refocus(self) -> None:
        self._prompt().value = ""
        self._prompt().focus()

    def _write_user_chat(self, text: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._chat().write(f"[dim]{ts}[/dim] [cyan][b]You[/b][/cyan]: {text}")

    def _write_agent_chat(self, text: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._chat().write(f"[dim]{ts}[/dim] [green][b]Agent[/b][/green]: {text}")

    def _write_error_chat(self, text: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._chat().write(f"[dim]{ts}[/dim] [red][b]Error[/b][/red]: {text}")

    def _reset_result(self) -> None:
        # reset result
        self.last_route = None
        self.last_answer = None
        self._refresh_result()

    def _handle_exit(self, cmd: str) -> bool:
        if cmd in {"exit", "quit", "q"}:
            self.exit()
            return True
        return False

    def _handle_login_and_create_router_agent(self, user_name: str) -> None:
        router_mod.user = user_name
        self.router_agent = router_mod.RouterHRAgent(
            router_mod.model, router_mod.system_prompt, router_mod.user, debug=True
        )
        self._logged_in = True
        self._chat().write(f"[b]Logged in as[/b] {router_mod.user}.")
        self._chat().write("[b]Welcome[/b]. Commands: help | clear | exit")
        self._prompt().placeholder = "Type a message and press Enter…"
        self._prompt().focus()

    def _handle_command(self, cmd: str) -> bool:
        if cmd == "clear":
            self._chat().clear()
            self._logs().clear()
            self.last_route = None
            self.last_answer = None
            self._refresh_result()
            if not self._logged_in:
                self._show_login_prompt()
            self._prompt().focus()
            return True

        if cmd in {"help", "?"}:
            self._chat().write(
                "[b]Examples[/b]\n"
                "- What is the policy for remote work?\n"
                "- What is my vacation balance?\n"
                "- File a time off request for 5 days starting from 2025-05-05\n"
                "- Tell me about payroll processing"
            )
            self._prompt().focus()
            return True

        return False

    async def _process_user_prompt(self, prompt: str) -> None:
        self._write_user_chat(prompt)
        self._reset_result()
        self._set_busy(True)

        capture = _CaptureStream(lambda line: self.call_from_thread(self._append_log, line))

        def _run_invoke() -> str:
            with redirect_stdout(capture), redirect_stderr(capture):
                if self.router_agent is None:
                    raise RuntimeError("Not logged in")
                user_message = {"messages": [HumanMessage(prompt)]}
                result = self.router_agent.router_graph.invoke(
                    user_message,
                    config=router_mod.router_graph_config,
                )
                return result["messages"][-1].content

        try:
            worker = self.run_worker(_run_invoke, thread=True, exclusive=True)
            response = await worker.wait()
            self.last_answer = response
            self._refresh_result()
            self._write_agent_chat(response)
        except Exception as e:
            self._write_error_chat(str(e))
        finally:
            self._set_busy(False)
            self._prompt().focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        self._clear_input_and_refocus()

        if not text:
            if not self._logged_in:
                text = "Alice"
            else:
                return

        cmd = text.lower()
        if self._handle_exit(cmd):
            return

        # Allow commands like clear/help even before login.
        if self._handle_command(cmd):
            return

        if not self._logged_in:
            self._handle_login_and_create_router_agent(text)
            return

        await self._process_user_prompt(text)

    def on_unmount(self) -> None:
        router_mod.log_message = self._orig_log_message
        self._health_stop.set()

        for proc in (self._mcp_proc, self._policy_proc, self._timeoff_proc):
            if proc is None:
                continue
            if proc.poll() is not None:
                continue
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


if __name__ == "__main__":
    RouterChatApp().run()
