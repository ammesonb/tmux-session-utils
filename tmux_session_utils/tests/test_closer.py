"""
Tests the session closer
"""
from os import path
import sys
import tempfile

from tmux_session_utils.builder import closer
from tmux_session_utils import tmux_utils


def test_get_session(monkeypatch):
    """
    .
    """
    monkeypatch.setattr(sys, "argv", ["script", "session"])

    assert closer.get_session() == "session", "Session returned for argv"

    assert closer.get_session("fake") == "fake", "Overridden session returned"


def test_closer_analysis(monkeypatch):
    """
    .
    """

    # pylint: disable=unused-argument
    # This has to match actual signature, so need the session argument
    def get_command(session: str, window: str, pane: int):
        command = ""
        if window == "0" and pane == 0:
            command = "zsh /var/www"
        elif window == "0" and pane == 1:
            command = "vi /test.txt"
        else:
            command = "bash"

        return command

    monkeypatch.setattr(
        tmux_utils,
        "get_window_list",
        lambda session: "0: fake~ (2 panes)\n1: zsh* (1 pane) ",
    )
    monkeypatch.setattr(tmux_utils, "get_pane_command", get_command)
    close = closer.Closer("test")

    assert close.pane_count_by_window == {"0": 2, "1": 1}, "Pane counts as expected"
    assert close.close_commands == [
        'tmux send-keys -t test:0.0 exit "C-m"',
        'tmux send-keys -t test:0.1 :q! "C-m"',
        'tmux send-keys -t test:0.1 exit "C-m"',
        'tmux send-keys -t test:1.0 exit "C-m"',
    ], "Closing commands properly identified"


def test_unrecognized_command(capsys):
    """
    .
    """

    closer.close_program("foobar")
    out = capsys.readouterr()
    assert (
        "Unknown command! 'foobar'" in out.out
    ), "Error message printed for unknown command"


def test_actual_close(monkeypatch):
    """
    .
    """
    name = tempfile.mkstemp()[1]
    monkeypatch.setattr(
        closer, "close_program", lambda program: '"rm {0}"'.format(name)
    )
    monkeypatch.setattr(
        tmux_utils, "get_window_list", lambda session: "0: fake~ (1 panes)"
    )
    monkeypatch.setattr(
        tmux_utils, "get_pane_command", lambda session, window, pane: "unimportant"
    )
    close = closer.Closer("test")
    monkeypatch.setattr(close, "close_commands", ["rm {0}".format(name)])
    close.close()

    assert not path.exists(name), "Temp file should be removed"
