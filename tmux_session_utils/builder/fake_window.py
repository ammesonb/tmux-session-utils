"""
An emulation of the Window class, for injecting pane data into tests
"""

from tmux_session_utils.tmux_utils import (
    inject_pane_data,
    WINDOW_ID_VARIABLE,
    WINDOW_LAYOUT_VARIABLE,
)


class FakeWindow:
    """
    Represents a window in a tmux session, for test injection
    """

    def __init__(self, identity: str = None):
        """
        Set invalid starting properties for the window
        """
        self.identity = identity
        self.name = ""
        self.session = ""
        self.number = None
        self.directory = ""
        self.layout = ""

    def set_session_name(self, session: str) -> "FakeWindow":
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

    def set_name(self, name: str) -> "FakeWindow":
        """
        Set the window name

        Parameters
        ----------
        name : string
            The window name to set

        Returns
        -------
        self
            This instance
        """
        self.name = name
        return self

    def set_number(self, number: int) -> "FakeWindow":
        """
        Set the window number

        Parameters
        ----------
        number : number
            The window number to set

        Returns
        -------
        self
            This instance
        """
        self.number = number
        return self

    def set_directory(self, directory: str) -> "FakeWindow":
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
        return self

    def set_layout(self, layout: str) -> "FakeWindow":
        """
        Set the layout

        Parameters
        ----------
        layout : string
            The layout to set

        Returns
        -------
        self
            This instance
        """
        self.layout = layout
        return self

    def inject(self):
        """
        Inject the attributes for this window into the session
        """
        inject_pane_data(
            self.session,
            self.number,
            None,
            {WINDOW_ID_VARIABLE: self.identity, WINDOW_LAYOUT_VARIABLE: self.layout},
        )
