"""
A singleton manager for tracking tmux panes/windows
"""

from tmux_session_utils.singleton import Singleton


@Singleton
class ObjectTracker:
    """
    Tracks objects by their identity


    Attributes
    ----------
    objects_by_id : dictionary
      A list of windows/panes indexed by ID, for target reference
    """

    def __init__(self) -> "ObjectTracker":
        """
        Creates the array of objects by IDs
        """
        self.objects_by_id = {}

    def __check_object_id(self, identity: str):
        """
        Checks that an object identity is not already used

        Parameters
        ----------
        identity : string
          The identity value to check
        """
        if identity in self.objects_by_id:
            raise ValueError('Object ID "{0}" is already in use!'.format(identity))

    def __get_object_by_id(self, identity: str) -> "Window|Pane":
        """
        Gets an object using the given ID

        Parameters
        ----------
        identity : string
            The identity to look up

        Returns
        -------
        Window|Pane
            The object for this identity
        """
        if identity not in self.objects_by_id:
            raise NameError("No such object: {0}!".format(identity))

        return self.objects_by_id.get(identity)

    def get_window_by_id(self, identity: str) -> "Window":
        """
        Gets an object using the given ID

        Parameters
        ----------
        identity : string
            The window identity to look up

        Returns
        -------
        Window
            The window for this identity
        """
        window = self.__get_object_by_id(identity)
        # Need to do string checking to avoid circular dependency
        if "Window" not in str(type(window)):
            raise TypeError("Identity provided is not a window!")
        return window

    def get_pane_by_id(self, identity: str) -> "Pane":
        """
        Gets an object using the given ID

        Parameters
        ----------
        identity : string
            The pane identity to look up

        Returns
        -------
        Pane
            The pane for this identity
        """
        pane = self.__get_object_by_id(identity)
        # Need to do string checking to avoid circular dependency
        if "Pane" not in str(type(pane)):
            raise TypeError("Identity provided is not a pane!")
        return pane

    def add_window(self, window: "Window") -> None:
        """
        Adds a new window

        Parameters
        ----------
        window : Window
          The window to add
        """
        self.__check_object_id(window.identity)
        if "Window" not in str(type(window)):
            raise TypeError("Object provided is not a window!")
        self.objects_by_id[window.identity] = window

    def add_pane(self, pane: "Pane") -> None:
        """
        Adds a new pane

        Parameters
        ----------
        pane : Pane
          The pane to add
        """
        self.__check_object_id(pane.identity)
        if "Pane" not in str(type(pane)):
            raise TypeError("Object provided is not a pane!")
        self.objects_by_id[pane.identity] = pane

    def reset(self) -> None:
        """
        Reset the data in the tracker
        """
        self.objects_by_id = {}

    def remove_pane(self, pane: "Pane") -> None:
        """
        Remove a pane from the mapping

        Parameters
        ----------
        pane : 'Pane'
            The pane to remove
        """
        self.__check_object_id(pane.identity)

        if "Pane" not in str(type(pane)):
            raise TypeError("Object provided is not a pane!")

        del self.objects_by_id[pane.identity]
