"""
Utility file for interacting with tmux on the command line
Allows injectable configurations for testing purposes
"""

from subprocess import Popen, PIPE, check_output
from shlex import split

from tmux_session_utils.utils import get_id

TMUX_DISPLAY_FORMAT_CMD = "tmux display-message -t {0} -p '#{{{1}}}'"
INITIAL_SESSION_DIR_CMD = "pwdx {0} | gawk -F ' ' '{{ print $2 }}'"
PANE_GET_COMMAND_CMD = (
    "ps -f --no-headers --ppid {0} | awk '{{ print substr($0, index($0,$8)) }}'"
)

WINDOW_ID_VARIABLE = "window_id"
PANE_PID_VARIABLE = "pane_pid"
PANE_PATH_VARIABLE = "pane_current_path"
PANE_ID_VARIABLE = "pane_id"
PANE_COMMAND_VARIABLE = "pane_command"

SESSION_INITIAL_DIR_KEY = "session_initial_dir"
WINDOW_LIST_KEY = "window_list"
WINDOW_LAYOUT_VARIABLE = "window_layout"

# Injected data about the session and panes, for testing
injectedSessionData = {}
# Keyed by session, window, and pane in the tmux pane syntax
injectedPaneData = {}


def inject_session_data(key: str, value: str) -> None:
    """
    Inject information about a session

    Parameters
    ----------
    key : str
        The key for the data
    value : str
        The value for the key
    """
    injectedSessionData[key] = value


def inject_pane_data(session: str, window: int, pane: int, data: dict) -> None:
    """
    Inject about a pane

    Parameters
    ----------
    session : str
        Name of the session
    window : int
        Window number of pane
    pane : int
        Pane index in the window
    data : dict
        A key - value mapping of pane data
    """
    key = get_pane_syntax(session, window, pane)
    if key not in injectedPaneData:
        injectedPaneData[key] = {}

    injectedPaneData[key].update(data)


def get_injected_pane_data(session: str, window: int, pane: int, variable: str):
    """
    Get a possibly-injected piece of information about a tmux pane

    Parameters
    ----------
    session : str
        Name of the session
    window : int
        Window number of pane
    pane : int
        Pane index in the window
    variable : str
        The variable to get about the tmux pane
    """
    data = None
    key = get_pane_syntax(session, window, pane)
    if key in injectedPaneData:
        data = injectedPaneData[key].get(variable, None)

    return data


def get_injected_session_data(key: str):
    """
    Get possibly-injected data about the session

    Parameters
    ----------
    key : str
        The key to check data for
    """
    return injectedSessionData.get(key, None)


def get_command_output(cmd):
    """
    Get the output of a command, handling pipes if needed

    Parameters
    ----------
    cmd
        The command to get output of
    """
    output = None
    if "|" in cmd:
        cmds = cmd.split("|")
        processes = []
        for subcmd in cmds:
            if len(processes) > 0:
                proc = Popen(split(subcmd), stdin=processes[-1].stdout, stdout=PIPE)
            else:
                proc = Popen(split(subcmd), stdout=PIPE)
            processes.append(proc)
        output = processes[-1].communicate()[0].strip().decode("utf-8")
    else:
        output = check_output(split(cmd)).strip().decode("utf-8")

    return output


def get_pane_syntax(session: str, window: int, pane: int = None):
    """
    Format a session, window, and optional pane into tmux formatting

    Parameters
    ----------
    session : str
        Name of the session
    window : int
        Window number of pane
    pane : int
        Pane index in the window
    """
    return "{0}:{1}".format(session, window) + (
        ".{0}".format(pane) if pane is not None else ""
    )


def get_tmux_details(session: str, window: int, pane: int, variable: str):
    """
    Get a piece of information about a tmux pane

    Parameters
    ----------
    session : str
        Name of the session
    window : int
        Window number of pane
    pane : int
        Pane index in the window
    variable : str
        The variable to get about the tmux pane
    """
    injected = get_injected_pane_data(session, window, pane, variable)
    if injected:
        return injected

    return get_command_output(
        TMUX_DISPLAY_FORMAT_CMD.format(get_pane_syntax(session, window, pane), variable)
    )


def select_pane(session: str, window: int, pane: int):
    """
    Mark a given tmux pane as selected

    Parameters
    ----------
    session : str
        Name of the session
    window : int
        Window number of pane
    pane : int
        Pane index in the window
    """
    result = None
    # Don't bother selecting panes if data is injected
    if not injectedPaneData:
        result = get_command_output(
            "tmux select-pane -t {0}".format(get_pane_syntax(session, window, pane))
        )

    return result


def get_pane_pid(session: str, window: int, pane: int):
    """
    Get the PID of a pane's process

    Parameters
    ----------
    session : str
        Name of the session
    window : int
        Window number of pane
    pane : int
        Pane index in the window
    """
    return get_tmux_details(session, window, pane, PANE_PID_VARIABLE)


def get_session_initial_dir(session: str):
    """
    Get the initial directory for a session

    Parameters
    ----------
    session : str
        Session name
    """
    injected = get_injected_session_data(SESSION_INITIAL_DIR_KEY)
    if injected:
        return injected

    pid = get_pane_pid(session, 0, 0)
    return get_command_output(INITIAL_SESSION_DIR_CMD.format(pid))


def get_window_list(session: str):
    """
    Get the window list for a given session

    Parameters
    ----------
    session : str
        Session name
    """
    injected = get_injected_session_data(WINDOW_LIST_KEY)
    if injected:
        return injected

    return get_command_output("tmux list-windows -t {0}".format(session))


def get_pane_working_directory(session: str, window: int, pane: int):
    """
    Get the working directory of a given pane

    Parameters
    ----------
    session : str
        Name of the session
    window : int
        Window number of pane
    pane : int
        Pane index in the window
    """
    return get_tmux_details(session, window, pane, PANE_PATH_VARIABLE)


def get_pane_command(session: str, window: int, pane: int):
    """
    Get the command inside a given pane

    Parameters
    ----------
    session : str
        Name of the session
    window : int
        Window number of pane
    pane : int
        Pane index in the window
    """
    injected = get_injected_pane_data(session, window, pane, PANE_COMMAND_VARIABLE)
    if injected is not None:
        return injected

    pid = get_pane_pid(session, window, pane)
    return get_command_output(PANE_GET_COMMAND_CMD.format(pid))


def get_pane_id(session: str, window: int, pane: int):
    """
    Get a given pane ID

    Parameters
    ----------
    session : str
        Name of the session
    window : int
        Window number of pane
    pane : int
        Pane index in the window
    """
    injected = get_injected_pane_data(session, window, pane, PANE_ID_VARIABLE)
    return injected if injected else get_id()


def get_window_id(session: str, window: int):
    """
    Get a given window ID

    Parameters
    ----------
    session : str
        Name of the session
    window : int
        Number of the window to get the ID of
    """
    injected = get_injected_pane_data(session, window, None, WINDOW_ID_VARIABLE)
    return injected if injected else get_id()


def escape_command(cmd: str, needs_enter: bool = True) -> str:
    """
    Escapes a given command for use in tmux shell commands
    If there is a "C-m" at the end of the command, assume this is already quoted

    Parameters
    ----------
    cmd : string
        The command to escape
    needs_enter : bool
        Whether the command needs an "enter" keystroke at the end of it

    Returns
    -------
    string
        The command, formatted for use in tmux
    """
    command = ""
    if not cmd or len(cmd.strip()) == 0:
        pass
    elif cmd.endswith('"C-m"'):
        command = cmd
    else:
        command = '"' + cmd.replace('"', '\\"') + '"'
        command += ' "C-m"' if needs_enter else ""

    return command


def format_working_directory(starting_directory: str) -> "TmuxBuilder":
    """
    Adds tmux command to starting directory, if one is provided

    Parameters
    ----------
    starting_directory : string
        The starting directory to use for this session

    Returns
    -------
    This instance
    """

    path_command = ""
    if starting_directory and len(starting_directory.strip()) != 0:
        path_command = '-c "' + starting_directory + '"'

    return path_command
