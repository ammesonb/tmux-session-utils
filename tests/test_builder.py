"""
Test builder functions
"""
from pytest import fixture

from builder.tmux_builder import TmuxBuilder
from builder.object_tracker import ObjectTracker
from builder.pane import SPLIT_HORIZONTAL, SPLIT_VERTICAL
from utils import convert_lines_to_object, assert_objects_equal


@fixture(autouse=True)
def setup():
    """
    Reset the object tracker windows and panes
    """
    ObjectTracker().reset()


def test_create_get_set(capsys):
    """
    Test variable properties for creation, getters, and setters
    """

    builder = TmuxBuilder("session")

    expected = {"initial": {"session_name": "session", "start_dir": "", "detach": True}}
    actual = {"initial": builder}

    builder.set_terminal_size(20, 40)
    expected["size"] = {"terminal_width": 20, "terminal_height": 40}
    actual["size"] = builder

    builder = TmuxBuilder("session", "/home", False)
    expected["cwd"] = {
        "session_name": "session",
        "start_dir": '-c "/home"',
        "detach": False,
    }
    actual["cwd"] = builder

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_single_pane_window(capsys):
    """
    Test the creation of a basic single-pane window
    """
    builder = TmuxBuilder("session", "/etc")
    builder.add_window("win1", "pane1", "window", "/home")
    builder.run_command("top")
    actual = convert_lines_to_object(builder.build().split("\n"))

    expected = convert_lines_to_object(
        [
            'tmux new-session -d -s session -c "/etc" \\; \\',
            "rename-window window \\; \\",
            'send-keys "top" "C-m"',
        ]
    )

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_two_window_single_pane(capsys):
    """
    Test two windows with single panes
    """
    builder = TmuxBuilder("session", "/var")
    builder.add_window("win1", "pane1", "window")
    builder.run_command("top")
    builder.add_window("win2", "pane2", "window2", "/home")
    builder.run_command("tail")
    actual = convert_lines_to_object(builder.build().split("\n"))

    expected = convert_lines_to_object(
        [
            'tmux new-session -d -s session -c "/var" \\; \\',
            "rename-window window \\; \\",
            'send-keys "top" "C-m" \\; \\',
            'new-window -n window2 -c "/home" \\; \\',
            'send-keys "tail" "C-m"',
        ]
    )

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_two_split_panes(capsys):
    """
    Test two windows, both with split panes
    """
    builder = TmuxBuilder("session", "/var")
    builder.add_window("win1", "pane1", "window")
    builder.add_pane("pane2", SPLIT_HORIZONTAL)
    builder.run_command("top")
    builder.run_command("echo", "win1", "pane1")
    builder.add_window("win2", "pane3", "window2", "/home")
    builder.add_pane("pane4", SPLIT_VERTICAL, working_directory="/etc")
    builder.run_command("tail")
    actual = convert_lines_to_object(builder.build().split("\n"))

    expected = convert_lines_to_object(
        [
            'tmux new-session -d -s session -c "/var" \\; \\',
            "rename-window window \\; \\",
            'send-keys "echo" "C-m" \\; \\',
            'split-window -h -c "/var" \\; \\',
            'send-keys "top" "C-m" \\; \\',
            'new-window -n window2 -c "/home" \\; \\',
            'split-window -v -c "/etc" \\; \\',
            'send-keys "tail" "C-m"',
        ]
    )

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_double_three_split_with_target(capsys):
    """
    Test three-way split in two directions, with window targets
    """
    builder = TmuxBuilder("session", "/var")
    builder.add_window("w1", "w1p1", "w1")
    builder.add_pane("w1p2", SPLIT_HORIZONTAL)
    builder.add_window("w2", "w2p1", "w2", "/home")
    builder.add_pane("w2p2", SPLIT_VERTICAL, "w2", working_directory="/etc")
    builder.add_pane("w1p3", SPLIT_VERTICAL, split_from="w1p1")
    builder.add_pane("w2p3", SPLIT_HORIZONTAL, split_from="w2p1")
    actual = convert_lines_to_object(builder.build().split("\n"))

    expected = convert_lines_to_object(
        [
            'tmux new-session -d -s session -c "/var" \\; \\',
            "rename-window w1 \\; \\",
            'split-window -h -c "/var" \\; \\',
            'split-window -v -t session:0.0 -c "/var" \\; \\',
            'new-window -n w2 -c "/home" \\; \\',
            'split-window -v -c "/etc" \\; \\',
            'split-window -h -t session:1.0 -c "/var"',
        ]
    )

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_multiple_sequential_splits(capsys):
    """
    Test splitting a window in multiple directions, sequentially
    """
    builder = TmuxBuilder("session", "/var")
    builder.add_window("w1", "w1p1", "w1")
    builder.add_pane("w1p2", SPLIT_HORIZONTAL)
    builder.add_pane("w1p3", SPLIT_VERTICAL)
    builder.add_pane("w1p4", SPLIT_VERTICAL)
    builder.add_pane("w1p5", SPLIT_HORIZONTAL)
    actual = convert_lines_to_object(builder.build().split("\n"))

    expected = convert_lines_to_object(
        [
            'tmux new-session -d -s session -c "/var" \\; \\',
            "rename-window w1 \\; \\",
            'split-window -h -c "/var" \\; \\',
            'split-window -v -c "/var" \\; \\',
            'split-window -v -c "/var" \\; \\',
            'split-window -h -c "/var"',
        ]
    )

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_middle_split_pane_with_sizing(capsys):
    """
    Split a pane in between two others, setting its size
    """
    builder = TmuxBuilder("session", "/var").set_terminal_size(200, 200)
    builder.add_window("w0", "w0p0", "w0")
    builder.set_pane_width(40)
    builder.add_pane("w0p1", SPLIT_HORIZONTAL)
    builder.add_pane("w0p2", SPLIT_HORIZONTAL)
    # This becomes pane number 2, since horizontally before pane w0p3
    builder.add_pane("w0p3", SPLIT_VERTICAL, split_from="w0p1")
    builder.set_pane_width(30)
    builder.set_pane_height(20)
    actual = convert_lines_to_object(builder.build().split("\n"))

    expected = convert_lines_to_object(
        [
            'tmux new-session -d -s session -c "/var" \\; \\',
            "rename-window w0 \\; \\",
            'split-window -h -c "/var" \\; \\',
            'split-window -h -c "/var" \\; \\',
            'split-window -v -t session:0.1 -c "/var" \\; \\',
            "resize-pane -t session:0.0 -x 80  \\; \\",
            "resize-pane -t session:0.2 -x 60 -y 40",
        ]
    )

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_many_hard_panes(capsys):
    """
    Test creation of a bunch of complex windows
    """
    # Expected result:
    #  w0p0 (0) | w0p1 (2) |
    #  -------- | -------- | w0p2 (4)
    #  w0p3 (1) | w0p4 (3) |
    builder = TmuxBuilder("session", "/var")
    builder.add_window("w0", "w0p0", "w0")
    builder.add_pane("w0p1", SPLIT_HORIZONTAL)
    builder.add_pane("w0p2", SPLIT_HORIZONTAL)
    builder.add_pane("w0p3", SPLIT_VERTICAL, split_from="w0p0")
    # Will actually be split from pane #2, since the one before this was inserted after pane #0
    # Which causes pane #1 to become pane #2
    builder.add_pane("w0p4", SPLIT_VERTICAL, split_from="w0p1")

    # Expected result:
    #  w1p0 (0) |      w1p1 (2)       |
    #  -------- | ------------------- | w1p2 (5)
    #  w1p3 (1) | w1p4 (3) | w1p5 (4) |
    builder.add_window("w1", "w1p0", "w1")
    builder.add_pane("w1p1", SPLIT_HORIZONTAL)
    builder.add_pane("w1p2", SPLIT_HORIZONTAL)
    builder.add_pane("w1p3", SPLIT_VERTICAL, split_from="w1p0")
    # Will actually be split from pane #2,
    # since the one before this was inserted after pane #0
    # Which causes pane #1 to become pane #2
    builder.add_pane("w1p4", SPLIT_VERTICAL, split_from="w1p1")
    builder.add_pane("w1p5", SPLIT_HORIZONTAL)

    # Expected result:
    #          | w2p3 (1)
    # w2p0 (0) | --------
    #          | w2p4 (2)
    # -------------------
    #      w2p1 (3)
    # -------------------
    # w2p2 (4) | w2p5 (5)
    builder.add_window("w2", "w2p0", "w2")
    builder.add_pane("w2p1", SPLIT_VERTICAL)
    builder.add_pane("w2p2", SPLIT_VERTICAL)
    builder.add_pane("w2p3", SPLIT_HORIZONTAL, split_from="w2p0")
    builder.add_pane("w2p4", SPLIT_VERTICAL)
    # This is split from pane #3 since the top pane was split once
    builder.add_pane("w2p5", SPLIT_HORIZONTAL, split_from="w2p2")

    # Expected result:
    #          | w3p1 (1) | w3p3 (2)
    # w3p0 (0) | -------------------
    #          |      w3p2 (3)
    builder.add_window("w3", "w3p0", "w3")
    builder.add_pane("w3p1", SPLIT_HORIZONTAL)
    builder.add_pane("w3p2", SPLIT_VERTICAL, split_from="w3p1")
    builder.add_pane("w3p3", SPLIT_HORIZONTAL, split_from="w3p1")

    actual = convert_lines_to_object(builder.build().split("\n"))

    expected = convert_lines_to_object(
        [
            'tmux new-session -d -s session -c "/var" \\; \\',
            "rename-window w0 \\; \\",
            'split-window -h -c "/var" \\; \\',
            'split-window -h -c "/var" \\; \\',
            'split-window -v -t session:0.0 -c "/var" \\; \\',
            'split-window -v -t session:0.2 -c "/var" \\; \\',
            'new-window -n w1 -c "/var" \\; \\',
            'split-window -h -c "/var" \\; \\',
            'split-window -h -c "/var" \\; \\',
            'split-window -v -t session:1.0 -c "/var" \\; \\',
            'split-window -v -t session:1.2 -c "/var" \\; \\',
            'split-window -h -c "/var" \\; \\',
            'new-window -n w2 -c "/var" \\; \\',
            'split-window -v -c "/var" \\; \\',
            'split-window -v -c "/var" \\; \\',
            'split-window -h -t session:2.0 -c "/var" \\; \\',
            'split-window -v -c "/var" \\; \\',
            'split-window -h -t session:2.3 -c "/var" \\; \\',
            'new-window -n w3 -c "/var" \\; \\',
            'split-window -h -c "/var" \\; \\',
            'split-window -v -t session:3.1 -c "/var" \\; \\',
            'split-window -h -t session:3.1 -c "/var"',
        ]
    )
    assert_objects_equal(expected, actual, expected.keys(), capsys)
