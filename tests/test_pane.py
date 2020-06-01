"""
Tests pane functionality
"""
from pytest import fixture

from utils import assert_objects_equal
from tmux_utils import get_pane_syntax
from builder.object_tracker import ObjectTracker
from builder.pane import Pane, SPLIT_HORIZONTAL, SPLIT_VERTICAL


@fixture(autouse=True)
def setup():
    """
    Reset object tracker
    """
    ObjectTracker().reset()


def test_pane_creation(capsys):
    """
    Test that a pane that is created has the proper attributes
    """
    pane = Pane("identity", "fake_window", SPLIT_HORIZONTAL)
    properties = {
        "identity": "identity",
        "window": "fake_window",
        "direction": SPLIT_HORIZONTAL,
        "split_from": None,
        "command": "",
        "width": 0,
        "height": 0,
        "is_first": False,
    }

    assert_objects_equal(properties, pane, properties.keys(), capsys)


def test_get_sets(capsys):
    """
    Test setting and getting of attributes
    """
    (Pane("target", "fake_window", None).set_session_name("session").set_number(0))
    pane = Pane("identity", "fake_window", SPLIT_VERTICAL, True)
    pane.set_number(5).set_session_name("session").set_target("target").set_start_dir(
        "dir"
    ).set_size(30, 40)

    properties = {
        "identity": "identity",
        "number": 5,
        "window": "fake_window",
        "direction": SPLIT_VERTICAL,
        "split_from": "target",
        "session_name": "session",
        "start_dir": "dir",
        "command": "",
        "width": 30,
        "height": 40,
        "is_first": True,
    }

    assert_objects_equal(properties, pane, properties.keys(), capsys)


def test_command_quoting(capsys):
    """
    Verify commands are escaped properly
    """
    pane = Pane("identity", "fake_window", SPLIT_VERTICAL)
    pane.set_command("foo")

    expected = {}
    actual = {}
    expected["command1"] = '"foo" "C-m"'
    actual["command1"] = pane.command

    pane.set_command("foo", False)
    expected["command2"] = '"foo"'
    actual["command2"] = pane.command

    pane.set_command('echo "foo"')
    expected["command3"] = '"echo \\"foo\\"" "C-m"'
    actual["command3"] = pane.command

    pane.set_command("echo 'foo'")
    expected["command4"] = '"echo \'foo\'" "C-m"'
    actual["command4"] = pane.command

    pane.set_command('"echo \\"things\\"" "C-m"')
    expected["already_quoted"] = '"echo \\"things\\"" "C-m"'
    actual["already_quoted"] = pane.command

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_get_target(capsys):
    """
    Verify getting of target works as expected
    """
    window = type("FakeWindow", (object,), {"number": 1})
    pane = (
        Pane("identity1", window, SPLIT_VERTICAL)
        .set_session_name("session")
        .set_number(1)
    )

    pane2 = (
        Pane("identity2", window, SPLIT_VERTICAL)
        .set_session_name("session")
        .set_number(2)
    )

    expected = {"none": None}
    actual = {"none": pane.get_target()}

    pane.set_target("identity2")
    expected["target"] = get_pane_syntax("session", 1, 2)
    actual["target"] = pane.get_target()

    pane2.set_number(3)

    expected[""] = get_pane_syntax("session", 1, 3)
    actual[""] = pane2.get_target(True)

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_get_split_command(capsys):
    """
    Tests the command to generate the split works correctly
    """
    pane = Pane("identity", type("Window", (object,), {"number": 1}), SPLIT_VERTICAL)

    expected = {}
    actual = {}

    window = type("FakeWindow", (object,), {"number": 1})
    (Pane("pane1", window, SPLIT_HORIZONTAL).set_session_name("session").set_number(1))

    expected["empty"] = "split-window -{0}".format(SPLIT_VERTICAL)
    actual["empty"] = pane.get_split_command()

    pane.set_start_dir('-c "home"')
    expected["with_dir"] = "split-window -{0} {1}".format(SPLIT_VERTICAL, '-c "home"')
    actual["with_dir"] = pane.get_split_command()

    pane.set_session_name("session").set_number(0).set_target("pane1")
    expected["all"] = "split-window -{0} -t {2} {1}".format(
        SPLIT_VERTICAL, '-c "home"', get_pane_syntax("session", 1, 1)
    )
    actual["all"] = pane.get_split_command()

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_get_command(capsys):
    """
    Verify getting the command works
    """
    pane = Pane("identity", "fake_window", SPLIT_VERTICAL)

    expected = {"none": ""}
    actual = {"none": pane.get_run_command()}

    pane.set_command("foo")
    expected["cmd"] = 'send-keys "foo" "C-m"'
    actual["cmd"] = pane.get_run_command()

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_size_command(capsys):
    """
    Check the size command works appropriately
    """
    window = type("FakeWindow", (object,), {"number": 1})
    target = get_pane_syntax("s", 1, 1)
    pane = Pane("identity1", window, SPLIT_VERTICAL).set_session_name("s").set_number(1)
    expected = {"none": ""}
    actual = {"none": pane.get_size_command()}

    pane.set_size(10)
    expected["width"] = "resize-pane -t {0} -x {1} ".format(target, 10)
    actual["width"] = pane.get_size_command()

    pane.set_size(10, 20)
    expected["both"] = "resize-pane -t {0} -x {1} -y {2}".format(target, 10, 20)
    actual["both"] = pane.get_size_command()

    pane = (
        Pane("identity2", window, SPLIT_VERTICAL)
        .set_session_name("s")
        .set_number(1)
        .set_size(0, 20)
    )
    expected["both"] = "resize-pane -t {0}  -y {1}".format(target, 20)
    actual["both"] = pane.get_size_command()

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_differences(capsys):
    """
    Test differences between panes
    """
    pane1 = Pane("identity1", "fake_window", SPLIT_VERTICAL)
    pane2 = Pane("identity2", "fake_window", SPLIT_VERTICAL)

    expected = {"none": {}}
    actual = {"none": pane1.get_difference(pane2)}

    pane2 = Pane("identity3", "fake_window", SPLIT_HORIZONTAL)
    expected["dir"] = {
        "direction": {"expected": SPLIT_VERTICAL, "actual": SPLIT_HORIZONTAL}
    }
    actual["dir"] = pane1.get_difference(pane2)

    pane2 = Pane("identity4", "fake_window", SPLIT_VERTICAL)
    pane1.set_size(10, 20)
    pane2.set_size(30, 40)
    expected["size"] = {
        "width": {"expected": 10, "actual": 30},
        "height": {"expected": 20, "actual": 40},
    }
    actual["size"] = pane1.get_difference(pane2)

    assert_objects_equal(expected, actual, expected.keys(), capsys)
