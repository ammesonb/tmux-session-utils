"""
Test session scripter functions
"""
from pytest import fixture

from tmux_session_utils.builder.tmux_scripter import TmuxScripter
from tmux_session_utils.builder.object_tracker import ObjectTracker
from tmux_session_utils.builder.fake_window import FakeWindow
from tmux_session_utils.builder.fake_pane import FakePane
from tmux_session_utils.tmux_utils import (
    inject_session_data,
    SESSION_INITIAL_DIR_KEY,
    WINDOW_LIST_KEY,
)
from tmux_session_utils.utils import convert_lines_to_object, assert_objects_equal

GENERIC_START = [
    'pushd "/home/brett"',
    "tmux new-session -d -s session \\; \\",
    "rename-window window \\; \\",
]


# pylint: disable=bad-continuation
# black auto-format disagrees
def set_session_parameters(
    session: str, session_start_directory: str, windows: list
) -> str:
    """
    Sets session data based off of parameters

    Parameters
    ----------
    session: string
        The name of the session
    session_start_directory : string
        The path to the session's starting directory
    windows : list
        A list of window information
        Each needs:
          - identity
          - number
          - title
          - postfix (appended to title in window list)
          - dir
          - layout
          - panes (list of objects)
            - identity
            - number
            - dir
            - command [optional]
            - parent [optional]

    Returns
    -------
    string
        The window list to analyze
    """
    inject_session_data(SESSION_INITIAL_DIR_KEY, session_start_directory)
    layout = ""

    for window in windows:
        win_object = (
            FakeWindow(window["identity"])
            .set_session_name(session)
            .set_name(window["title"])
            .set_number(window["number"])
            .set_layout(window["layout"])
            .set_directory(window.get("dir", session_start_directory))
        )

        win_object.inject()
        ObjectTracker().add_window(win_object)

        for pane in window["panes"]:
            pane_object = (
                FakePane(pane["identity"])
                .set_session_name(session)
                .set_number(pane["number"])
                .set_window(win_object)
                .set_directory(
                    pane.get("dir", window.get("dir", session_start_directory))
                )
                .set_command(pane.get("command", ""))
            )

            if "parent" in pane:
                pane_object.set_split_from(pane["parent"])

            pane_object.inject()
            ObjectTracker().add_pane(pane_object)

        layout += "{0}: {1}{2} [200x60] ({3} panes) [{4}] @{0}\n".format(
            window["number"],
            window["title"],
            window["postfix"],
            len(window["panes"]),
            window["layout"],
        )

    inject_session_data(WINDOW_LIST_KEY, layout)
    return layout


TERMINAL_WIDTH = 200
TERMINAL_HEIGHT = 60
DEFAULT_SESSION = "session"
DEFAULT_DIRECTORY = "/home/brett"


@fixture(autouse=True)
def setup():
    """
    Reset the object tracker windows and panes
    """
    ObjectTracker().reset()


def test_single_pane_session(capsys):
    """
    Test creating a session with a single pane
    """

    window_data = [
        {
            "identity": "window",
            "number": 0,
            "title": "window",
            "postfix": "~-*",
            "layout": "c6e0,200x60,0,0,0",
            "panes": [{"identity": "pane", "number": 0, "command": "top"}],
        }
    ]

    window_list = set_session_parameters(
        DEFAULT_SESSION, DEFAULT_DIRECTORY, window_data,
    )

    scripter = TmuxScripter(DEFAULT_SESSION, DEFAULT_DIRECTORY)
    scripter.analyze(window_list)

    expected = convert_lines_to_object(
        GENERIC_START + ['send-keys "top" "C-m"', "popd",]
    )
    actual = convert_lines_to_object(scripter.commands.split("\n"))

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_split_pane_session(capsys):
    """
    Test a session with a single window, with a split pane
    """

    window_data = [
        {
            "identity": "window",
            "number": 0,
            "title": "window",
            "postfix": "~-",
            "dir": DEFAULT_DIRECTORY,
            "layout": "c6e0,200x60,0,0{100x60,0,0,0,100x60,101,0,1}",
            "panes": [
                {"identity": "pane", "number": 0, "command": "top"},
                {
                    "identity": "pane2",
                    "number": 1,
                    "dir": "/var/log",
                    "command": "tail -f syslog",
                    "parent": "pane",
                },
            ],
        }
    ]

    window_list = set_session_parameters(
        DEFAULT_SESSION, DEFAULT_DIRECTORY, window_data,
    )

    scripter = TmuxScripter(DEFAULT_SESSION, DEFAULT_DIRECTORY).set_terminal_size(
        TERMINAL_WIDTH, TERMINAL_HEIGHT
    )
    scripter.analyze(window_list)

    expected = convert_lines_to_object(
        GENERIC_START
        + [
            'send-keys "top" "C-m" \\; \\',
            'split-window -h -t session:0.0 -c "/var/log" \\; \\',
            'send-keys "tail -f syslog" "C-m" \\; \\',
            "resize-pane -t session:0.0 -x 100 -y 60 \\; \\",
            "resize-pane -t session:0.1 -x 100 -y 60",
            "popd",
        ]
    )
    actual = convert_lines_to_object(scripter.commands.split("\n"))

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_two_perpendicular_windows(capsys):
    """
    Check a session with two windows, one split vertically, the horizontally
    Should make this:

    Window 0:
       |  1
     0 | ---
       |  2

    Window 1:
      0
    -----
    1 | 2

    """

    window_layout_one = (
        "b652,200x60,0,0{100x60,0,0,255,100x60,101,0"
        "[100x40,101,0,256,100x20,101,41,257]}"
    )
    window_layout_two = (
        "6fc3,200x60,0,0[200x30,0,0,258,"
        "200x30,0,31{150x30,0,31,259,50x30,151,31,260}]"
    )
    window_data = [
        {
            "identity": "window",
            "number": 0,
            "title": "window",
            "postfix": "~-",
            "layout": window_layout_one,
            "panes": [
                {"identity": "pane", "number": 0, "command": "top"},
                {
                    "identity": "pane2",
                    "number": 1,
                    "dir": "/var/log",
                    "command": "tail -f syslog",
                    "parent": "pane",
                },
                {
                    "identity": "pane3",
                    "number": 2,
                    "command": "vi test.py",
                    "parent": "pane2",
                },
            ],
        },
        {
            "identity": "window2",
            "number": 1,
            "title": "zsh",
            "postfix": "*Z",
            "dir": "/root",
            "layout": window_layout_two,
            "panes": [
                {
                    "identity": "pane4",
                    "number": 0,
                    # This should override the window directory
                    "dir": "/home/brett",
                },
                {
                    "identity": "pane5",
                    "number": 1,
                    "command": "cat bar",
                    "parent": "pane4",
                },
                {
                    "identity": "pane6",
                    "number": 2,
                    "dir": DEFAULT_DIRECTORY,
                    "command": "netstat -noap | grep 443",
                    "parent": "pane5",
                },
            ],
        },
    ]

    window_list = set_session_parameters(
        DEFAULT_SESSION, DEFAULT_DIRECTORY, window_data,
    )

    scripter = TmuxScripter(DEFAULT_SESSION, DEFAULT_DIRECTORY).set_terminal_size(
        TERMINAL_WIDTH, TERMINAL_HEIGHT
    )
    scripter.analyze(window_list)

    expected = convert_lines_to_object(
        GENERIC_START
        + [
            'send-keys "top" "C-m" \\; \\',
            'split-window -h -t session:0.0 -c "/var/log" \\; \\',
            'send-keys "tail -f syslog" "C-m" \\; \\',
            'split-window -v -t session:0.1 -c "/home/brett" \\; \\',
            'send-keys "vi test.py" "C-m" \\; \\',
            'new-window -n zsh -c "/home/brett" \\; \\',
            'split-window -v -t session:1.0 -c "/root" \\; \\',
            'send-keys "cat bar" "C-m" \\; \\',
            'split-window -h -t session:1.1 -c "/home/brett" \\; \\',
            'send-keys "netstat -noap | grep 443" "C-m" \\; \\',
            "resize-pane -t session:0.0 -x 100 -y 60 \\; \\",
            "resize-pane -t session:0.1 -x 100 -y 40 \\; \\",
            "resize-pane -t session:0.2 -x 100 -y 20 \\; \\",
            "resize-pane -t session:1.0 -x 200 -y 30 \\; \\",
            "resize-pane -t session:1.1 -x 150 -y 30 \\; \\",
            "resize-pane -t session:1.2 -x 50 -y 30",
            "popd",
        ]
    )
    actual = convert_lines_to_object(scripter.commands.split("\n"))

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_nested_split(capsys):
    """
    Tests a layout which has nested splits

      0  |  2  |
     --- | --- | 4
      1  |  3  |
    """

    window_layout = (
        "32ff,200x60,0,0{100x60,0,0[100x30,0,0,49,100x30,0,31,53],50x60,119,0"
        "[50x30,101,0,51,50x30,101,31,52],50x60,151,0,51}"
    )
    window_data = [
        {
            "identity": "window",
            "number": 0,
            "title": "window",
            "postfix": "~-",
            "layout": window_layout,
            "panes": [
                {"identity": "pane0", "number": 0, "command": "top"},
                {"identity": "pane1", "number": 1, "parent": "pane0"},
                {"identity": "pane2", "number": 2, "parent": "pane0"},
                {
                    "identity": "pane3",
                    "number": 3,
                    "parent": "pane2",
                    "command": "tail -f foo.txt",
                },
                {
                    "identity": "pane4",
                    "number": 4,
                    "parent": "pane2",
                    "command": "tail -f test.txt",
                },
            ],
        }
    ]

    window_list = set_session_parameters(
        DEFAULT_SESSION, DEFAULT_DIRECTORY, window_data,
    )

    scripter = TmuxScripter(DEFAULT_SESSION, DEFAULT_DIRECTORY).set_terminal_size(
        TERMINAL_WIDTH, TERMINAL_HEIGHT
    )
    scripter.analyze(window_list)

    expected = convert_lines_to_object(
        GENERIC_START
        + [
            'send-keys "top" "C-m" \\; \\',
            'split-window -h -t session:0.0 -c "/home/brett" \\; \\',
            'split-window -h -t session:0.1 -c "/home/brett" \\; \\',
            'send-keys "tail -f test.txt" "C-m" \\; \\',
            'split-window -v -t session:0.0 -c "/home/brett" \\; \\',
            'split-window -v -t session:0.2 -c "/home/brett" \\; \\',
            'send-keys "tail -f foo.txt" "C-m" \\; \\',
            "resize-pane -t session:0.0 -x 100 -y 30 \\; \\",
            "resize-pane -t session:0.2 -x 50 -y 30 \\; \\",
            "resize-pane -t session:0.4 -x 50 -y 60 \\; \\",
            "resize-pane -t session:0.1 -x 100 -y 30 \\; \\",
            "resize-pane -t session:0.3 -x 50 -y 30",
            "popd",
        ]
    )
    actual = convert_lines_to_object(scripter.commands.split("\n"))

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_nested_middle_split(capsys):
    """
    Tests a layout which has nested splits, but around a middle section

      0  |   |  3
     --- | 2 | ---
      1  |   |  4
    """

    window_layout = (
        "32ff,200x60,0,0{"
        "30x60,0,0[30x20,0,0,49,30x40,0,31,53],"
        "100x60,31,0,50,"
        "70x60,131,0[70x45,131,0,51,70x15,131,46,52]}"
    )
    window_data = [
        {
            "identity": "window",
            "number": 0,
            "title": "window",
            "postfix": "~-",
            "layout": window_layout,
            "panes": [
                {"identity": "pane0", "number": 0},
                {"identity": "pane1", "number": 1, "parent": "pane0"},
                {"identity": "pane2", "number": 2, "parent": "pane0"},
                {"identity": "pane3", "number": 3, "parent": "pane2"},
                {"identity": "pane4", "number": 4, "parent": "pane3"},
            ],
        }
    ]

    window_list = set_session_parameters(
        DEFAULT_SESSION, DEFAULT_DIRECTORY, window_data,
    )

    scripter = TmuxScripter(DEFAULT_SESSION, DEFAULT_DIRECTORY).set_terminal_size(
        TERMINAL_WIDTH, TERMINAL_HEIGHT
    )
    scripter.analyze(window_list)

    expected = convert_lines_to_object(
        GENERIC_START
        + [
            'split-window -h -t session:0.0 -c "/home/brett" \\; \\',
            'split-window -h -t session:0.1 -c "/home/brett" \\; \\',
            'split-window -v -t session:0.0 -c "/home/brett" \\; \\',
            'split-window -v -t session:0.3 -c "/home/brett" \\; \\',
            "resize-pane -t session:0.0 -x 30 -y 20 \\; \\",
            "resize-pane -t session:0.2 -x 100 -y 60 \\; \\",
            "resize-pane -t session:0.3 -x 70 -y 45 \\; \\",
            "resize-pane -t session:0.1 -x 30 -y 40 \\; \\",
            "resize-pane -t session:0.4 -x 70 -y 15",
            "popd",
        ]
    )
    actual = convert_lines_to_object(scripter.commands.split("\n"))

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_horizontal_tri_split(capsys):
    """
    A complex horizontal layout with eight panes

     0 |     |  5
    ---|  3  | ---
     1 | --- |  6
    ---|  4  | ---
     2 |     |  7
    """

    window_layout = (
        "32ff,200x60,0,0"
        "{30x60,0,0[30x10,0,0,49,30x30,0,11,53,30x20,0,41,54],"
        "70x60,31,0[70x24,31,0,50,70x36,31,26,55],"
        "100x60,101,0[100x45,101,0,51,100x10,101,46,52,100x5,101,56,56]}"
    )
    window_data = [
        {
            "identity": "window",
            "number": 0,
            "title": "window",
            "postfix": "~-",
            "layout": window_layout,
            "panes": [
                {"identity": "pane0", "number": 0},
                {"identity": "pane1", "number": 1, "parent": "pane0"},
                {
                    "identity": "pane2",
                    "number": 2,
                    "parent": "pane1",
                    "command": "cat test.txt",
                },
                {"identity": "pane3", "number": 3, "parent": "pane0"},
                {
                    "identity": "pane4",
                    "number": 4,
                    "parent": "pane3",
                    "command": 'echo "hello world"',
                },
                {"identity": "pane5", "number": 5, "parent": "pane3"},
                {"identity": "pane6", "number": 6, "parent": "pane5"},
                {
                    "identity": "pane7",
                    "number": 7,
                    "parent": "pane6",
                    "command": "htop",
                },
            ],
        }
    ]

    window_list = set_session_parameters(
        DEFAULT_SESSION, DEFAULT_DIRECTORY, window_data,
    )

    scripter = TmuxScripter(DEFAULT_SESSION, DEFAULT_DIRECTORY).set_terminal_size(
        TERMINAL_WIDTH, TERMINAL_HEIGHT
    )
    scripter.analyze(window_list)

    expected = convert_lines_to_object(
        GENERIC_START
        + [
            'split-window -h -t session:0.0 -c "/home/brett" \\; \\',
            'split-window -h -t session:0.1 -c "/home/brett" \\; \\',
            'split-window -v -t session:0.0 -c "/home/brett" \\; \\',
            'split-window -v -t session:0.1 -c "/home/brett" \\; \\',
            'send-keys "cat test.txt" "C-m" \\; \\',
            'split-window -v -t session:0.3 -c "/home/brett" \\; \\',
            'send-keys "echo \\"hello world\\"" "C-m" \\; \\',
            'split-window -v -t session:0.5 -c "/home/brett" \\; \\',
            'split-window -v -t session:0.6 -c "/home/brett" \\; \\',
            'send-keys "htop" "C-m" \\; \\',
            "resize-pane -t session:0.0 -x 30 -y 10 \\; \\",
            "resize-pane -t session:0.3 -x 70 -y 24 \\; \\",
            "resize-pane -t session:0.5 -x 100 -y 45 \\; \\",
            "resize-pane -t session:0.1 -x 30 -y 30 \\; \\",
            "resize-pane -t session:0.2 -x 30 -y 20 \\; \\",
            "resize-pane -t session:0.4 -x 70 -y 36 \\; \\",
            "resize-pane -t session:0.6 -x 100 -y 10 \\; \\",
            "resize-pane -t session:0.7 -x 100 -y 5",
            "popd",
        ]
    )
    actual = convert_lines_to_object(scripter.commands.split("\n"))

    assert_objects_equal(expected, actual, expected.keys(), capsys)


def test_vertical_tri_split_with_hitch(capsys):
    """
    A complex vertical layout with nine panes

     0 | 1 | 2
    -----------
       3 | 4
    -----------
       | 6 |
     5 |---| 8
       | 7 |
    """

    window_layout = (
        # Top set
        "32ff,200x60,0,0[200x12,0,0{30x12,0,0,49,50x12,31,0,53,120x12,81,0,54},"
        # Second set
        "200x18,0,31{150x18,0,31,50,50x18,151,31,55},"
        # First pane of third set
        "200x30,0,31{100x30,0,31,51,60x30,101,46"
        # Second group and third pane of bottom set
        "[60x10,101,31,52,60x20,101,41,57],40x30,161,31,56}]"
    )
    window_data = [
        {
            "identity": "window",
            "number": 0,
            "title": "window",
            "postfix": "~-",
            "layout": window_layout,
            "panes": [
                {"identity": "pane0", "number": 0},
                {"identity": "pane1", "number": 1, "parent": "pane0"},
                {"identity": "pane2", "number": 2, "parent": "pane1"},
                {"identity": "pane3", "number": 3, "parent": "pane0"},
                {"identity": "pane4", "number": 4, "parent": "pane3"},
                {"identity": "pane5", "number": 5, "parent": "pane3"},
                {"identity": "pane6", "number": 6, "parent": "pane5"},
                {
                    "identity": "pane7",
                    "number": 7,
                    "parent": "pane6",
                    "command": "htop",
                },
                {"identity": "pane8", "number": 8, "parent": "pane6",},
            ],
        }
    ]

    window_list = set_session_parameters(
        DEFAULT_SESSION, DEFAULT_DIRECTORY, window_data,
    )

    scripter = TmuxScripter(DEFAULT_SESSION, DEFAULT_DIRECTORY).set_terminal_size(
        TERMINAL_WIDTH, TERMINAL_HEIGHT
    )
    scripter.analyze(window_list)

    expected = convert_lines_to_object(
        GENERIC_START
        + [
            'split-window -v -t session:0.0 -c "/home/brett" \\; \\',
            'split-window -v -t session:0.1 -c "/home/brett" \\; \\',
            'split-window -h -t session:0.0 -c "/home/brett" \\; \\',
            'split-window -h -t session:0.1 -c "/home/brett" \\; \\',
            'split-window -h -t session:0.3 -c "/home/brett" \\; \\',
            'split-window -h -t session:0.5 -c "/home/brett" \\; \\',
            'split-window -h -t session:0.6 -c "/home/brett" \\; \\',
            'split-window -v -t session:0.6 -c "/home/brett" \\; \\',
            'send-keys "htop" "C-m" \\; \\',
            "resize-pane -t session:0.0 -x 30 -y 12 \\; \\",
            "resize-pane -t session:0.3 -x 150 -y 18 \\; \\",
            "resize-pane -t session:0.5 -x 100 -y 30 \\; \\",
            "resize-pane -t session:0.1 -x 50 -y 12 \\; \\",
            "resize-pane -t session:0.2 -x 120 -y 12 \\; \\",
            "resize-pane -t session:0.4 -x 50 -y 18 \\; \\",
            "resize-pane -t session:0.6 -x 60 -y 10 \\; \\",
            "resize-pane -t session:0.8 -x 40 -y 30 \\; \\",
            "resize-pane -t session:0.7 -x 60 -y 20",
            "popd",
        ]
    )
    actual = convert_lines_to_object(scripter.commands.split("\n"))

    assert_objects_equal(expected, actual, expected.keys(), capsys)
