"""
Closes a session intelligently, for vim/zsh
"""
import os
import re
import sys

from tmux_session_utils import tmux_utils


class Closer:
    """
    Class with logic to close session
    """

    def __init__(self, session: str = None):
        """
        .
        """
        self.tmux_session = session if session else get_session(session)
        self.pane_count_by_window = {}
        self.__get_pane_counts()
        self.close_commands = []
        self.analyze()

    def __get_pane_counts(self):
        """
        Gets number of panes in each window
        """
        windows = tmux_utils.get_window_list(self.tmux_session)
        for window in windows.split("\n"):
            win_num_match = re.match(r"^([0-9]+):", window)
            pane_match = re.match(r".*([0-9]+) panes?", window)
            self.pane_count_by_window[win_num_match.group(1)] = int(pane_match.group(1))

    def analyze(self):
        """
        Identifies windows and panes, and figures out what commands to use to close them
        """
        for window, pane_count in self.pane_count_by_window.items():
            for pane in range(pane_count):
                pane_command = tmux_utils.get_pane_command(
                    self.tmux_session, window, pane
                )

                for run_command in close_program(pane_command):
                    self.close_commands.append(
                        'tmux send-keys -t {0}:{1}.{2} {3} "C-m"'.format(
                            self.tmux_session, window, pane, run_command
                        )
                    )

    def close(self):
        """
        Actually close the session
        """
        for command in self.close_commands:
            os.system(command)


def close_program(program: str) -> list:
    """
    Returns commands needed to close a pane with a given command
    """
    commands = []
    if program.startswith("vi"):
        commands.append(":q!")
        commands.append("exit")
    # pylint: disable=bad-continuation
    elif (
        any([program.startswith(shell) for shell in ["zsh", "sh", "bash"]])
        or not program
    ):
        commands.append("exit")
    else:
        print("Unknown command! '{0}'".format(program))

    return commands


def get_session(session: str = None) -> str:
    """
    Gets session name from command line, with injectable option
    """
    return session if session else sys.argv[1]


if __name__ == "__main__":
    Closer(get_session()).close()
