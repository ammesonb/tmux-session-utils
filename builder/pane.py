"""
Represents a pane in a tmux session
"""

from utils import get_object_differences
from tmux_utils import get_pane_syntax, escape_command
from builder.object_tracker import ObjectTracker

SPLIT_HORIZONTAL = "h"
SPLIT_VERTICAL = "v"

LAYOUT_INDICATORS = [",", "[", "{"]


# pylint: disable=too-many-instance-attributes
class Pane:
    """
    Represents a pane in a Tmux window

    Attributes
    ----------
    identity : string
        A unique ID representing this pane
    window : string
        The unique ID for the window this pane belongs to
    direction : string|None
        Which direction to split this pane - 'h' for horizontal, 'v' for vertical
        Can be None ONLY if this is the first pane
    is_first : bool
        Is this the first pane created in the window?
    number : int
        The number of this window
    session_name : string
        The name of the current session
    start_dir : string
        The starting directory for the pane
    split_from : string
        The ID of the pane to split this one from
    width : int
        The width of the pane, in lines
    height : int
        The height of the pane, in lines
    command : string
        The command to run in this pane
    """

    COMPARABLE_PROPERTIES = [
        "width",
        "height",
        "split_from",
        "direction",
        "start_dir",
        "command",
    ]

    # pylint: disable=bad-continuation
    # black auto-format disagrees
    def __init__(
        self, identity: str, window: "Window", direction: str, is_first: bool = False
    ) -> "Pane":
        """
        Sets up details about the pane

        Parameters
        ----------
        identity : string
            A unique ID representing this pane
        window : Window
            The Window object this pane belongs to
        direction : string|None
            Which direction to split this pane - 'h' for horizontal, 'v' for vertical
        is_first : bool
            Is this the first pane that was created?
        """
        self.identity = identity
        self.window = window
        self.direction = direction
        self.is_first = is_first
        self.session_name = None
        self.command = ""
        self.split_from = None
        self.width = 0
        self.height = 0
        self.number = None
        self.parent_number = None
        self.start_dir = None
        self.objects = ObjectTracker()
        self.objects.add_pane(self)

    def set_number(self, num: int) -> "Pane":
        """
        Set the pane number

        Parameters
        ----------
        num : int
            The pane number

        Returns
        -------
        This instance
        """
        self.number = num
        return self

    def set_session_name(self, name: str) -> "Pane":
        """
        Sets the session name for the pane

        Parameters
        ----------
        name : string
            The name of the current session

        Returns
        -------
        This instance
        """
        self.session_name = name
        return self

    def set_start_dir(self, directory: str) -> "Pane":
        """
        Sets the starting directory for the pane

        Parameters
        ----------
        directory : string
            The starting directory of the current session

        Returns
        -------
        This instance
        """
        self.start_dir = directory
        return self

    def set_target(self, target: str) -> "Pane":
        """
        Set the target to split this pane from

        Parameters
        ----------
        target : string
            The identity of the pane to split this pane from

        Returns
        -------
        This instance
        """
        self.split_from = target
        self.parent_number = self.objects.get_pane_by_id(target).number
        return self

    def set_size(self, width: int = 0, height: int = 0) -> "Pane":
        """
        Set the size of this pane

        Parameters
        ----------
        width : int|0
            The line width of the pane
        height : int|0
            The line height of the pane

        Returns
        -------
        This instance
        """
        if height:
            self.height = height
        if width:
            self.width = width

        return self

    def set_command(self, command: str, needs_enter: bool = True) -> "Pane":
        """
        Set the command to run in this pane

        Parameters
        ----------
        command : string
            The command to run in this pane
        needs_enter : bool
            Whether the command needs an "enter" keystroke at the end of it

        Returns
        -------
        This instance
        """
        self.command = escape_command(command, needs_enter)
        return self

    def set_parent_directly(self, parent_number: int) -> "Pane":
        """
        Set the number of the parent directly, rather than by ID
        Needed for scripting a Tmux session, since panes need to be created twice

        Parameters
        ----------
        parent_number : number
            The number of the parent of this pane

        Returns
        -------
        self
            This instance
        """
        self.parent_number = parent_number
        return self

    def get_target(self, target_self: bool = False) -> str:
        """
        Return the target for this pane, if any

        Parameters
        ----------
        target_self : bool
            Whether the target should be myself

        Returns
        -------
        string|None
            The tmux-formatted target for this pane
            None if no target set to split from
        """
        target = ""
        if target_self:
            target = get_pane_syntax(self.session_name, self.window.number, self.number)
        elif self.parent_number:
            target = get_pane_syntax(
                self.session_name, self.window.number, self.parent_number
            )
        elif self.split_from is not None:
            parent_pane = self.objects.get_pane_by_id(self.split_from)
            target = get_pane_syntax(
                self.session_name, self.window.number, parent_pane.number
            )
        else:
            target = None

        return target

    def get_split_command(self) -> str:
        """
        Creates the split command for this pane

        Returns
        -------
        string
            The command used to split this pane
        """
        split_command = ""
        # First pane does not need a command
        if self.is_first:
            pass
        else:
            split_command = "split-window "
            target = self.get_target()
            target = "-t " + target if target else ""
            if self.start_dir and target:
                split_command += "-{0} {2} {1}".format(
                    self.direction, self.start_dir, target
                )
            elif self.start_dir:
                split_command += "-{0} {1}".format(self.direction, self.start_dir)
            elif target:
                split_command += "-{0} {1}".format(self.direction, target)
            else:
                split_command += "-{0}".format(self.direction)

        return split_command

    def get_run_command(self) -> str:
        """
        Returns the tmux-formatted run command for this pane

        Returns
        -------
        string
            The tmux-formatted run command
        """
        if self.command and len(self.command) > 0:
            return "send-keys {0}".format(self.command)

        return ""

    def get_size_command(self) -> str:
        """
        Returns the command to set the pane size

        Returns
        -------
        string
            The command to set this pane's size
        """
        target = self.get_target(True)

        width = ""
        if self.width:
            width = "-x {0}".format(self.width)

        height = ""
        if self.height:
            height = "-y {0}".format(self.height)

        if width or height:
            return "resize-pane -t {0} {1} {2}".format(target, width, height)

        return ""

    def get_difference(self, pane: "Pane") -> dict:
        """
        Compare this instance to another pane
        Checks properties, not direct reference

        Parameters
        ----------
        pane : Pane
            The pane to compare against

        Returns
        -------
        dict
            A key-value comparison of the two panes, containing this versus the argument
        """
        return get_object_differences(self, pane, self.COMPARABLE_PROPERTIES)

    def to_string(self) -> str:
        """
        Makes a string representation of this class
        """
        return (
            "identity : {0}"
            "  number : {1}"
            "  parent : {2}"
            "    size : {3}"
            " command : {4}"
        ).format(
            self.identity,
            self.number,
            self.split_from,
            "{0}x{1}".format(self.width, self.height),
            self.command,
        )
