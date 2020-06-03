"""
Builds a Tmux session, with configurable window names, panes, etc

Currently supports:
  Naming sessions
  Naming windows
  Splitting windows into panes
  Current file paths of window/panes
  Running commands in a given window/pane
  Setting the size of a pane, in percentage of available lines
"""

from subprocess import check_output
from math import floor
from os import system
from sys import stderr

from tmux_session_utils.builder.object_tracker import ObjectTracker
from tmux_session_utils.builder.window import Window
from tmux_session_utils.builder.pane import Pane
from tmux_session_utils.tmux_utils import format_working_directory

# pylint: disable=too-many-instance-attributes
class TmuxBuilder:
    """
    The class to build a Tmux session

    this was designed to chain methods, such as:
      TmuxBuilder('A session') \\ \n
          .add_window('main') \\ \n
          .add_pane('test') \\ \n
          .run_command('echo "foo"') \\ \\n
          ...

    Attributes
    ----------
    windows : list[Window]
        A list of the windows to create
    session_name : string
        The name of the session
    start_dir : string
        A directory to base all windows/panes from
    current_window : int
        The index of the currently-active window
    current_pane : int
        The index of the currently-active pane
    detach : bool
        Whether to detach the session after creation
    objects_by_id : dictionary
        A list of windows/panes indexed by ID, for target reference
    """

    size_warning_printed = False

    session_name = ""
    start_dir = ""
    current_window = -1
    current_pane = 0
    terminal_width = None
    terminal_height = None
    detach = True

    # pylint: disable=bad-continuation
    # black auto-format disagrees
    def __init__(
        self, session_name: str, starting_directory: str = "", detach: bool = True
    ) -> "TmuxBuilder":
        """
        Sets up details about the tmux builder

        Parameters
        ----------
        session_name : string
            The name of the session to create
        starting_directory : string
            The directory to base all windows/panes out of
        detach : bool
            Whether to detach this session after creatio
        """
        self.session_name = session_name
        self.objects = ObjectTracker()
        self.windows = []
        self.start_dir = format_working_directory(starting_directory)
        self.detach = bool(detach)

        self.__get_terminal_size()

    def __get_terminal_size(self) -> None:
        """
        Gets the terminal size using the tput command
        NOTE: ASSUMES CURRENT SIZE IS THE SAME SIZE AS THE INTENDED SESSION
        """
        if self.terminal_width and self.terminal_height:
            return

        self.terminal_height = int(
            check_output(["tput", "lines"]).decode("utf-8").strip()
        )
        self.terminal_width = int(
            check_output(["tput", "cols"]).decode("utf-8").strip()
        )

    # pylint: disable=bad-continuation
    # black auto-format disagrees
    def set_terminal_size(
        self, terminal_width: int, terminal_height: int
    ) -> "TmuxBuilder":
        """
        Sets the terminal height, rather than using tput
        This is used for testing

        Parameters
        ----------
        terminal_width : int
            The width of the terminal
        terminal_height : int
            The height of the terminal

        Returns
        -------
        This instance
        """
        self.terminal_width = terminal_width
        self.terminal_height = terminal_height

        return self

    def __coalesce_window(self, window: str = None) -> Window:
        """
        Determines which window to target
        If none provided, defaults to the current window

        Parameters
        ----------
        window : string|None
            The window ID to target

        Returns
        -------
        Window
            The window object
        """
        return (
            self.objects.get_window_by_id(window)
            if window
            else self.windows[self.current_window]
        )

    def __coalesce_pane(self, pane: str = None) -> Window:
        """
        Determines which pane to target
        If none provided, defaults to the current pane

        Parameters
        ----------
        pane : string|None
            The pane ID to target

        Returns
        -------
        Window
            The pane object to target
        """
        if pane == 0:
            return pane
        return (
            self.objects.get_pane_by_id(pane)
            if pane
            else self.windows[self.current_window].get_pane(self.current_pane)
        )

    def add_window(
        self,
        window_id: str,
        pane_id: str,
        window_name: str,
        working_directory: str = None,
    ) -> "TmuxBuilder":
        """
        Adds a new window

        Parameters
        ----------
        window_id : string
            A unique ID for the new window
        pane_id : string
            A unique ID for the new pane in the window
        window_name : string
            The name of the new window
        working_directory : string|None
            The working directory for the first pane

        Returns
        -------
        This instance
        """
        window_num = len(self.windows)
        window = (
            Window(window_id, window_name, window_num == 0)
            .set_number(window_num)
            .set_session_name(self.session_name)
            .set_start_dir(
                format_working_directory(working_directory) or self.start_dir
            )
        )
        self.windows.append(window)
        self.current_pane = 0
        self.current_window = len(self.windows) - 1
        return self.add_pane(pane_id, None, window_id)

    # pylint: disable=too-many-arguments
    def add_pane(
        self,
        identity: str,
        split_dir: str,
        window: str = None,
        split_from: str = None,
        working_directory: str = None,
    ) -> "TmuxBuilder":
        """
        Adds a new pane to target or current window

        Parameters
        ----------
        identity : string
            A unique ID for this pane
        split_dir : string
            The direction to split the window, either 'h' (horizontal) or 'v' (vertical)
        window : string|None
            The window ID to create the pane in, defaults to the current window
        split_from : string|None
            The pane ID to split this one from
        working_directory : string|None
            The working directory to set for this pane

        Returns
        -------
        This instance
        """
        if split_dir not in [None, "h", "v"]:
            raise ValueError('Invalid split direction specified: must be "v" or "h"!')

        if split_from:
            target = self.objects.get_pane_by_id(split_from)
            window = target.window
        else:
            window = self.__coalesce_window(window)
            target = None

        panes = window.get_pane_count()
        pane = (
            Pane(identity, window, split_dir, panes == 0)
            .set_number(panes)
            .set_session_name(self.session_name)
            .set_start_dir(
                format_working_directory(working_directory) or self.start_dir
            )
        )

        if split_from:
            pane.set_target(split_from)

        window.add_pane(pane)

        # The index of the current pane, not the number
        self.current_pane = window.get_pane_count() - 1
        return self

    def __print_size_warning(self) -> None:
        """
        Prints a warning about the size of the terminal
        """
        if not self.size_warning_printed:
            print(
                "NOTE: USING CURRENT TERMINAL SIZE AS TEMPLATE FOR SESSION", file=stderr
            )
            self.size_warning_printed = True

    def set_pane_height(self, height: int, pane: str = None) -> "TmuxBuilder":
        """
        Sets the height of the given pane, percent of available
        Can target a specific pane, or default to current

        Parameters
        ----------
        height : int
            The percentage of the screen this pane should be high
        pane : string|None
            The target pane ID

        Returns
        -------
        This instance
        """
        self.__print_size_warning()
        return self.__set_pane_size(0, height, pane)

    def set_pane_width(self, width: int, pane: str = None) -> "TmuxBuilder":
        """
        Sets the width of the given pane, percent of available
        Can target a specific pane, or default to current

        Parameters
        ----------
        width : int
            The percentage of the screen this pane should be wide
        pane : string|None
            The target pane ID

        Returns
        -------
        This instance
        """
        self.__print_size_warning()
        return self.__set_pane_size(width, 0, pane)

    def __set_pane_size(
        self, width: int = 0, height: int = 0, pane: str = None
    ) -> "TmuxBuilder":
        """
        Set the actual pane size, for a given target pane
        Defaults to current window/pane

        Parameters
        ----------
        width : int
            The width to set the pane to
        height : int
            The height to set the pane to
        pane : string|None
            The pane ID to target

        Returns
        -------
        This instance
        """
        pane = self.__coalesce_pane(pane)

        line_width = floor(self.terminal_width * (width / 100))
        line_height = floor(self.terminal_height * (height / 100))

        pane.set_size(line_width, line_height)
        return self

    def set_pane_parent(self, parent_number: int, pane_id: str = None):
        """
        Sets the parent number of the pane

        Parameters
        ----------
        parent_number : number
            The number of the pane's parent
        pane_id = None : string
            Optionally, the ID to set the parent for
            Defaults to the most recently-added pane
        """
        # If pane is passed in, use that, otherwise get the current pane
        pane = (
            self.objects.get_pane_by_id(pane_id) if pane_id else self.__coalesce_pane()
        )
        pane.set_parent_directly(parent_number)

    def run_command(self, command: str, window: str = None, pane: str = None):
        """
        Sets the command to run for a given window/pane
        Defaults to current window/pane

        Parameters
        ----------
        command : string
            The command to run in the pane
        window : string|None
            The window ID to run the command in
        pane : string|None
            The pane ID to run the command in

        Returns
        -------
        This instance
        """
        window = self.__coalesce_window(window)
        if not pane:
            pane = window.get_pane(self.current_pane)
        else:
            pane = self.__coalesce_pane(pane)

        pane.set_command(command)
        return self

    def debug(self) -> None:
        """
        Prints the built tmux command
        """
        print(self.build())

    def build(self) -> str:
        """
        Builds the actual bash command that will create the tmux session

        Parameters
        ----------

        Returns
        -------
        string
            The bash command to execute
        """
        if len(self.windows) == 0:
            raise RuntimeError("No windows provided!")

        commands = [
            "tmux new-session {2} -s {0} {1}".format(
                self.session_name, self.start_dir, "-d" if self.detach else ""
            )
        ]

        # Create windows, panes, and commands

        for window in self.windows:
            commands.append(window.get_create_command())

            for pane in window.panes:
                # Only split window for a new pane if not the first pane in the window
                split_command = pane.get_split_command()
                if split_command:
                    commands.append(split_command)

                run_cmd = pane.get_run_command()
                if run_cmd:
                    commands.append(run_cmd)

        # Set the panel dimensions later, since can't set dimensions if related panes aren't created
        # e.g., can't set a vertical height if the second pane doesn't exist yet
        for window in self.windows:
            for pane in window.panes:
                size_command = pane.get_size_command()
                if size_command:
                    commands.append(size_command)

        return " \\; \\\n".join(commands)

    def run(self) -> None:
        """
        Execute the commands to build a session
        """
        cmd = self.build()
        system(cmd)
