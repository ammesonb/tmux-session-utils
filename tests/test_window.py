"""
Tests window functionality
"""
from copy import deepcopy
from pytest import fixture

from tmux_session_utils.builder.object_tracker import ObjectTracker
from tmux_session_utils.builder.window import Window
from tmux_session_utils.builder.pane import Pane, SPLIT_HORIZONTAL, SPLIT_VERTICAL
from tmux_session_utils.utils import assert_objects_equal


@fixture(autouse=True)
def setup():
    """
    Reset the object tracker
    """
    ObjectTracker().reset()


def test_creation_get_set(capsys):
    """
    Test basic creation of a window
    """
    properties = {"identity": "window", "name": "thing", "first": True, "panes": []}
    window = Window(properties["identity"], properties["name"], properties["first"])

    expected = {"create": deepcopy(properties)}
    actual = {"create": window}

    properties.update({"number": 5})
    window.set_number(properties["number"])
    expected["number"] = deepcopy(properties)
    actual["number"] = window

    properties.update({"session_name": "session"})
    window.set_session_name(properties["session_name"])
    expected["session"] = deepcopy(properties)
    actual["session"] = window

    properties.update({"start_dir": '-c "/var/www"'})
    window.set_start_dir(properties["start_dir"])
    expected["dir"] = deepcopy(properties)
    actual["dir"] = window

    expected["pcount"] = 0
    actual["pcount"] = window.get_pane_count()

    expected["first"] = properties["first"]
    actual["first"] = window.is_first()

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_add_pane(capsys):
    """
    Test adding a pane
    """
    window = Window("id", "name").set_number(1)
    expected = {"init": []}
    actual = {"init": deepcopy(window.panes)}

    pane = (
        Pane("identity", window, SPLIT_HORIZONTAL)
        .set_session_name("session")
        .set_number(0)
    )
    window.add_pane(pane)

    expected["single"] = 1
    actual["single"] = window.get_pane_count()

    pane2 = (
        Pane("identity2", window, SPLIT_HORIZONTAL)
        .set_session_name("session")
        .set_number(2)
        .set_target("identity")
    )
    window.add_pane(pane2)
    expected["get"] = {"id": id(pane), "num": 1}
    actual["get"] = {"id": id(window.get_pane(0)), "num": pane2.number}

    pane3 = (
        Pane("identity3", window, SPLIT_HORIZONTAL)
        .set_session_name("session")
        .set_number(2)
        .set_target("identity")
    )
    window.add_pane(pane3)
    expected["inserted"] = 1
    actual["inserted"] = pane3.number
    expected["previous"] = 2
    actual["previous"] = pane2.number

    expected["middle"] = id(pane2)
    actual["middle"] = id(window.get_pane(1))

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_get_command(capsys):
    """
    Test the window creation command
    """
    window = Window("win1", "name", True)
    expected = {"first": "rename-window name"}
    actual = {"first": window.get_create_command()}

    window2 = Window("win2", "second").set_start_dir('-c "/home"')
    expected["second"] = 'new-window -n second -c "/home"'
    actual["second"] = window2.get_create_command()

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_get_differences(capsys):
    """
    Test getting window differences
    """
    window = Window("win", "name", True)
    window2 = Window("win2", "name2", False)
    expected = {
        "initial": {
            "name": {"expected": "name", "actual": "name2"},
            "first": {"expected": True, "actual": False},
        }
    }
    actual = {"initial": window.get_difference(window2)}

    window.set_session_name("s")
    window2.set_session_name("s2")
    window.set_start_dir('-c "/home"')
    window2.set_start_dir('-c "/"')

    expected["props"] = deepcopy(expected["initial"])
    expected["props"].update(
        {
            "session_name": {"expected": "s", "actual": "s2"},
            "start_dir": {"expected": '-c "/home"', "actual": '-c "/"'},
        }
    )

    actual["props"] = window.get_difference(window2)

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_pane_differences(capsys):
    """
    Test getting differences between panes
    """
    panes1 = [Pane("pane1", "p", SPLIT_HORIZONTAL).set_number(0)]
    panes2 = [Pane("pane2", "p2", SPLIT_VERTICAL).set_number(1)]

    window1 = Window("win1", "window")
    window1.panes = panes1
    window2 = Window("win2", "window2")
    window2.panes = panes2

    expected = {
        "single": [
            {
                "direction": {"expected": SPLIT_HORIZONTAL, "actual": SPLIT_VERTICAL,},
                "split_from": {},
                "start_dir": {},
            }
        ]
    }
    actual = {"single": window1.get_pane_differences(window2.panes)}

    panes1.append(Pane("pane3", "p", SPLIT_HORIZONTAL))
    panes2.append(Pane("pane4", "p", SPLIT_HORIZONTAL))
    panes1[-1].set_target("pane1")
    panes2[-1].set_target("pane2")

    expected["multi"] = deepcopy(expected["single"])
    expected["multi"].append(
        {"split_from": {"expected": "pane1", "actual": "pane2"}, "start_dir": {}}
    )
    actual["multi"] = window1.get_pane_differences(window2.panes)

    assert_objects_equal(expected, actual, expected.keys(), capsys)
