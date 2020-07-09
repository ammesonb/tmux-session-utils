#!/usr/bin/env python3
"""
Scripts an existing Tmux session

Outputs commands to recreate a Tmux session
This requires tput for terminal sizes, plus
the Python process integration to do parent/child command lookups
This will currently capture:
  The name of the session
  Names of windows
  Window/pane system paths
  Pane layout and sizes
  Commands executing in the panes
"""

from tmux_session_utils.builder.object_tracker import ObjectTracker
from tmux_session_utils.builder.tmux_builder import TmuxBuilder
from tmux_session_utils.builder.window import Window
from tmux_session_utils.utils import parse_args
from tmux_session_utils.tmux_utils import get_pane_working_directory, get_window_list


# pylint: disable=too-many-instance-attributes
class TmuxScripter:
    """
    Responsible for creating commands to recreate an existing tmux session
    """

    # pylint: disable=bad-continuation
    # black auto-format disagrees
    def __init__(
        self, session: str, defaultSessionPath: str, detach: bool = True
    ) -> "TmuxScripter":
        """
        Initialize the scripting engine

        Parameters
        ----------
        session : string
            The name of the session to script
        defaultSessionPath : string
            The path to use as the base for this session
        detach : boolean, optional
            Whether to detach the session after creation

        Returns
        -------
        TmuxScripter
            This instance
        """
        self.session_name = session
        self.start_dir = defaultSessionPath
        self.detach = detach

        self.windows = []
        self.layout_id = ""
        self.layout = ""
        self.window_width = 0
        self.window_height = 0

        self.builder = None
        self.commands = ""

        self.injected_width = None
        self.injected_height = None

    def set_terminal_size(self, width: int, height: int) -> "TmuxScripter":
        """
        Inject a terminal size to use

        Parameters
        ----------
        width : int
            The width of the terminal
        height : int
            The height of the terminal

        Returns
        -------
        self
            This instance
        """
        self.injected_width = width
        self.injected_height = height
        return self

    def analyze(self, window_list: str) -> None:
        """
        Analyze a session's window layouts, and create the commands needed to script it

        Parameters
        ----------
        window_list : string
            The list of window layouts to analyze
        """
        self.parse_windows(window_list)
        ObjectTracker().reset()
        self.create_builder()
        self.commands = self.build_commands()

    def parse_windows(self, layout_string: str) -> None:
        """
        Parse the remaining layout string into windows and panes

        Parameters
        ----------
        layout_string : string
            The layout string to parse
            Will be in a format of
              <num>: <name><status> (<N> panes) [layout XXXX,<further layout data>]
        """
        windows_data = layout_string.split("\n")
        if "" in windows_data:
            windows_data.remove("")

        num = 0
        for data in windows_data:
            window = Window("win" + str(num), "TBD", num == 0)
            window.set_session_name(self.session_name)
            # By default, always use the session start directory
            # Avoids chicken & egg due to needing to analyze pane
            # before window is fully spec'ed
            window.set_start_dir(self.start_dir)
            window.set_number(num)
            window.load_from_layout(data)
            self.windows.append(window)
            num += 1

    def create_builder(self):
        """
        Creates a builder with the data from the parsed windows/panes
            The builder that was created
        """
        self.builder = TmuxBuilder(self.session_name, self.start_dir, self.detach)
        if self.injected_width and self.injected_height:
            self.builder.set_terminal_size(self.injected_width, self.injected_height)

        for window in self.windows:
            first_pane = True
            for pane in window.panes:
                if first_pane:
                    self.builder.add_window(
                        window.identity,
                        pane.identity,
                        window.name,
                        window.panes[0].start_dir,
                    )
                    first_pane = False
                else:
                    self.builder.add_pane(
                        pane.identity,
                        pane.direction,
                        window.identity,
                        pane.split_from,
                        pane.start_dir,
                    )

                    if hasattr(pane, "parent_number"):
                        self.builder.set_pane_parent(pane.parent_number)

                self.builder.set_pane_height(pane.height).set_pane_width(
                    pane.width
                ).run_command(pane.command)

    def get_builder(self) -> TmuxBuilder:
        """
        Returns the Tmux session builder

        Returns
        -------
        TmuxBuilder
            The session builder for the scripter
        """
        return self.builder

    def build_commands(self) -> str:
        """
        Build the commands to script this session

        Returns
        -------
        string
            The commands needed to be run to make this session
        """
        if not self.builder:
            return ""
        return self.builder.build()


if __name__ == "__main__":
    args = parse_args()
    workingPath = (
        args["dir"]
        if "dir" in args and args["dir"]
        else get_pane_working_directory(args["session"], 0, 0)
    )

    scripter = TmuxScripter(args["session"], workingPath)
    layouts = get_window_list(args["session"])
    scripter.analyze(layouts)
    print(scripter.commands)
