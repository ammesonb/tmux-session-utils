"""
An emulation of the Pane class, for injecting pane data into tests
"""

from tmux_utils import (
    inject_pane_data,
    PANE_ID_VARIABLE,
    PANE_PATH_VARIABLE,
    PANE_COMMAND_VARIABLE,
)

ATTRIBUTE_MAPPING = {
    "identity": PANE_ID_VARIABLE,
    "directory": PANE_PATH_VARIABLE,
    "command": PANE_COMMAND_VARIABLE,
}


# pylint: disable=too-many-instance-attributes
class FakePane:
    """
    Represents a pane in a tmux session, for test injection
    """

    def __init__(self, identity: str = None):
        """
        Set invalid starting properties for the pane
        """
        self.identity = identity
        self.session = ""
        self.split_from = None
        self.window = None
        self.number = None
        self.command = ""
        self.width = 0
        self.height = 0
        self.directory = ""

        self.attributes_set = []

    def set_session_name(self, session: str) -> "FakePane":
        """
        Set the session name

        Parameters
        ----------
        session : string
            The session name to set

        Returns
        -------
        self
            This instance
        """
        self.session = session
        return self

    def set_identity(self, identity: str) -> "FakePane":
        """
        Set the identity

        Parameters
        ----------
        identity : string
            The identity to set

        Returns
        -------
        self
            This instance
        """
        self.identity = identity
        self.attributes_set.append("identity")
        return self

    def set_number(self, number: int) -> "FakePane":
        """
        Set the pane number

        Parameters
        ----------
        number : number
            The pane number to set

        Returns
        -------
        self
            This instance
        """
        self.number = number
        return self

    def set_window(self, window: "FakeWindow") -> "FakePane":
        """
        Set the window

        Parameters
        ----------
        window : FakeWindow
            The window this pane is in

        Returns
        -------
        self
            This instance
        """
        self.window = window
        return self

    def set_split_from(self, parent: int) -> "FakePane":
        """
        Set the pane number this is split from

        Parameters
        ----------
        parent : number
            The number of the pane this is split from

        Returns
        -------
        self
            This instance
        """
        self.split_from = parent
        return self

    def set_directory(self, directory: str) -> "FakePane":
        """
        Set the directory

        Parameters
        ----------
        directory : string
            The directory to set

        Returns
        -------
        self
            This instance
        """
        self.directory = directory
        self.attributes_set.append("directory")
        return self

    def set_command(self, command: str) -> "FakePane":
        """
        Set the command to execute in the pane

        Parameters
        ----------
        command
            The command to execute

        Returns
        -------
        self
            This instance
        """
        self.command = command
        self.attributes_set.append("command")
        return self

    def set_size(self, width: int, height: int) -> "FakePane":
        """
        Set the size of this pane

        Parameters
        ----------
        width : int
            The width of the pane
        height : int
            The height of the pane

        Returns
        -------
        self
            This instance
        """
        self.width = width
        self.height = height
        return self

    def inject(self):
        """
        Inject the various attributes into the pane data for the session
        """
        for attr in self.attributes_set:
            inject_pane_data(
                self.session,
                self.window.number,
                self.number,
                {ATTRIBUTE_MAPPING[attr]: getattr(self, attr)},
            )
