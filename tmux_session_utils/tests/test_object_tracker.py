"""
Test object tracker functionality
"""
from pytest import fixture, raises

from tmux_session_utils.builder.object_tracker import ObjectTracker


# pylint: disable=too-few-public-methods
class Pane:
    """
    Trivial pane class stub
    """

    def __init__(self, identity):
        self.identity = identity


# pylint: disable=too-few-public-methods
class Window:
    """
    Trivial window class stub
    """

    def __init__(self, identity):
        self.identity = identity


# pylint: disable=too-few-public-methods
class Integer:
    """
    Trivial integer class stub, for error testing
    """

    def __init__(self, value):
        self.identity = value


def check_exception(exception, expected, expected_type):
    """
    Makes an exception-formatted object

    Parameters
    ----------
    exception
        The exception to expect
    expected
        Whether an exception should occur
    """
    actual = str(exception)
    assert actual == expected, "Expected exception {0} but got {1}".format(
        expected, actual
    )
    assert isinstance(
        exception, expected_type
    ), "Expected exception type {0} but got {1}".format(expected_type, type(exception))


@fixture(autouse=True)
def setup():
    """
    Reset the object tracker windows and panes
    """
    ObjectTracker().reset()


def test_adding_non_classes():
    """
    Try adding an integer as a window, etc.
    """
    tracker = ObjectTracker()

    try:
        tracker.add_pane(Integer(5))
        assert False, "Expected TypeError exception, but one was not thrown"
    # pylint: disable=broad-except
    except Exception as error:
        check_exception(error, "Object provided is not a pane!", TypeError)

    try:
        tracker.add_window(Integer(3))
        assert False, "Expected TypeError exception, but one was not thrown"
    # pylint: disable=broad-except
    except Exception as error:
        check_exception(error, "Object provided is not a window!", TypeError)


def test_adding_mismatched_types():
    """
    Try adding a pane as a window, or vice versa
    """
    tracker = ObjectTracker()

    try:
        tracker.add_window(Pane("foo"))
        assert False, "Expected TypeError exception, but one was not thrown"
    # pylint: disable=broad-except
    except Exception as error:
        check_exception(error, "Object provided is not a window!", TypeError)

    try:
        tracker.add_pane(Window("foo"))
        assert False, "Expected TypeError exception, but one was not thrown"
    # pylint: disable=broad-except
    except Exception as error:
        check_exception(error, "Object provided is not a pane!", TypeError)


def test_getting_nonexistent_items():
    """
    Try getting items which do not exist
    """
    tracker = ObjectTracker()

    try:
        tracker.get_window_by_id("foo")
        assert False, "Expected NameError exception, but one was not thrown"
    # pylint: disable=broad-except
    except Exception as error:
        check_exception(error, "No such object: foo!", NameError)

    try:
        tracker.get_pane_by_id("foo")
        assert False, "Expected NameError exception, but one was not thrown"
    # pylint: disable=broad-except
    except Exception as error:
        check_exception(error, "No such object: foo!", NameError)

    tracker.add_pane(Pane("foo"))
    try:
        tracker.get_window_by_id("foo")
        assert False, "Expected TypeError exception, but one was not thrown"
    # pylint: disable=broad-except
    except Exception as error:
        check_exception(error, "Identity provided is not a window!", TypeError)

    tracker.add_window(Window("foo2"))
    try:
        tracker.get_pane_by_id("foo2")
        assert False, "Expected TypeError exception, but one was not thrown"
    # pylint: disable=broad-except
    except Exception as error:
        check_exception(error, "Identity provided is not a pane!", TypeError)


def test_adding_duplicate_ids():
    """
    Try adding two items with the same ID
    """
    tracker = ObjectTracker()
    tracker.add_pane(Pane("foo"))

    try:
        tracker.add_pane(Pane("foo"))
        assert False, "Expected ValueError exception, but one was not thrown"
    # pylint: disable=broad-except
    except Exception as error:
        check_exception(error, 'Object ID "foo" is already in use!', ValueError)

    try:
        tracker.add_window(Window("foo"))
        assert False, "Expected ValueError exception, but one was not thrown"
    # pylint: disable=broad-except
    except Exception as error:
        check_exception(error, 'Object ID "foo" is already in use!', ValueError)


def test_adding_and_retrieving():
    """
    Try adding two items with the same ID
    """
    tracker = ObjectTracker()

    pane1 = Pane("pane1")
    tracker.add_pane(pane1)
    pane2 = Pane("pane2")
    tracker.add_pane(pane2)
    window1 = Window("window1")
    tracker.add_window(window1)
    window2 = Window("window2")
    tracker.add_window(window2)

    ids = ["pane1", "pane2", "window1", "window2"]
    for expected in ids:
        if "pane" in expected:
            actual = tracker.get_pane_by_id(expected).identity
        else:
            actual = tracker.get_window_by_id(expected).identity
        assert actual == expected, "Retrieved {0} does not match!".format(expected)


def test_removing_pane():
    """
    Test pane removal
    """
    tracker = ObjectTracker()

    pane = Pane("pane")
    pane2 = Pane("pane2")
    window = Window("window")

    tracker.add_window(window)
    tracker.add_pane(pane)

    with raises(TypeError):
        tracker.remove_pane(window)

    with raises(NameError):
        tracker.remove_pane(pane2)

    tracker.remove_pane(pane)
    with raises(NameError):
        tracker.get_pane_by_id("pane")
