"""
Represents a window in a tmux session """

import re

from tmux_session_utils.builder.object_tracker import ObjectTracker
from tmux_session_utils.builder.pane import Pane, SPLIT_HORIZONTAL, SPLIT_VERTICAL
from tmux_session_utils.utils import parse_size, debug, get_object_differences
from tmux_session_utils.tmux_utils import (
    select_pane,
    get_tmux_details,
    WINDOW_LAYOUT_VARIABLE,
    get_pane_command,
    get_pane_working_directory,
)


# pylint: disable=too-many-instance-attributes
class Window:
    """
    Represents a window in Tmux

    Attributes
    ----------
    identity : string
        A unique ID representing this window
    name : string
        The name of the window
    number : number
        The number of this window
    is_first : boolean
        Is this the first window that was created?
    panes : list
        The panes to create in this window
    session_name : string
        The name of the current session
    start_dir : string
        The starting directory for the window
    """

    COMPARABLE_PROPERTIES = ["name", "start_dir", "session_name", "first"]
    # Contains <window_number>: <window_name><window_marker> (N panes)
    #          [<window_width>x<window_height>] [layout <layout_id,...
    WINDOW_TRAIL_REGEX = r"([\*~#\!MZ\-]+)"
    LAYOUT_DETAILS = r"([a-fA-F0-9]+),([0-9x]+),([0-9]+),([0-9]+)"
    DIRECTION_MAP = {"[": SPLIT_VERTICAL, "{": SPLIT_HORIZONTAL}
    LAYOUT_PAIRS = {"[": "]", "{": "}"}
    PANE_LAYOUT = r"([0-9]+x[0-9]+,[0-9]+,[0-9]+)"
    PANE_DETAILS = r"([0-9]+x[0-9]+),([0-9]+),([0-9]+)([,\[\{]?)([0-9]*)"

    number = None
    start_dir = None
    session_name = None
    layout_id = None
    layout_size = None
    offset_left = None
    offset_top = None

    def __init__(self, identity: str, name: str, is_first: bool = False) -> "Window":
        """
        Sets up details about the window

        Parameters
        ----------
        identity : string
            A unique ID representing this window
        name : string
            The name of the window
        is_first : boolean
            Is this the first window that was created?
        """
        self.identity = identity
        self.name = name
        self.first = is_first
        self.panes = []
        self.base_width = 0
        self.base_height = 0
        self.panes_added = 0
        self.last_pane = None
        self.objects = ObjectTracker()
        self.objects.add_window(self)

    def set_number(self, num: int) -> "Window":
        """
        Set the window number

        Parameters
        ----------
        num : number
            The window number

        Returns
        -------
        This instance
        """
        self.number = num
        return self

    def set_session_name(self, name: str) -> "Window":
        """
        Sets the session name for the window

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

    def set_start_dir(self, directory: str) -> "Window":
        """
        Sets the starting directory for the window

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

    def get_pane_count(self) -> int:
        """
        Returns the number of panes in this window

        Returns
        -------
        number
            The number of panes
        """
        return len(self.panes)

    def add_pane(self, pane: Pane) -> "Window":
        """
        Adds a pane to this window

        Parameters
        ----------
        pane : Pane
            The pane to add to the window

        Returns
        -------
        This instance
        """
        self.panes.append(pane)
        if pane.split_from is not None:
            parent_pane_number = self.objects.get_pane_by_id(pane.split_from).number
        # Tmux numbers panes left-to-right & top-down, order dependent on initial split
        # Each time a pane is split, the number increases by one from where it was split
        # Thus, anything equal to or larger than the initial pane will increase by one
        # This emulates that logic in the cached panes here
        if pane.split_from is not None:
            for window_pane in self.panes:
                if window_pane.number >= parent_pane_number + 1:
                    window_pane.number = window_pane.number + 1
            pane.number = parent_pane_number + 1

        return self

    def get_pane(self, idx: int) -> Pane:
        """
        Returns a pane at a given index

        Parameters
        ----------
        idx : number
            The index of the pane to get

        Returns
        -------
        Pane
            The pane at the given index
        """
        return self.panes[idx]

    def is_first(self) -> bool:
        """
        Returns true if this is the first window

        Returns
        -------
        boolean
            True if this is the first window
        """
        return self.first

    def get_create_command(self) -> str:
        """
        Gets the creation command for the window

        Returns
        -------
        string
            The creation command
        """
        # First window will be created automatically, so just need to rename it
        command = ""
        if not self.is_first():
            command = "new-window -n {0} {1}".format(self.name, self.start_dir)
        else:
            command = "rename-window " + self.name

        return command

    def get_difference(self, window: "Window") -> dict:
        """
        Compare this instance to another window
        Checks properties, not direct reference

        Parameters
        ----------
        window : Window
            The window to compare against

        Returns
        -------
        dict
            A key-value comparison of this and the other window
        """
        return get_object_differences(self, window, self.COMPARABLE_PROPERTIES)

    def get_pane_differences(self, panes: list) -> dict:
        """
        Compare this instance's panes to other panes
        Checks properties, not direct reference

        Parameters
        ----------
        panes : list[Pane]
            The panes to compare against

        Returns
        -------
        dict
            A key-value comparison of this window's panes and the provided list
        """
        differences = []
        for i in range(len(self.panes)):
            differences.append(
                get_object_differences(
                    self.panes[i], panes[i], panes[i].COMPARABLE_PROPERTIES
                )
            )

        return differences

    def load_from_layout(self, layout: str) -> None:
        """
        Load details about this window from a layout

        Parameters
        ----------
        layout : string
            The layout string to load details from
            Will be in a format of
                <num>: <name><status> (<N> panes) [<width>x<height>] [layout XXXX,...]
            May be zoomed, so this argument could be incomplete
        """
        match = re.match(r"^([0-9]+): ", layout)
        win_layout_num = match.groups()[0]
        debug("window", "loadLayout", "Parsing layout {0}".format(win_layout_num))
        layout = layout[len(win_layout_num) + 2 :]
        self.name = re.split(self.WINDOW_TRAIL_REGEX, layout)[0]
        layout = layout[len(self.name) :]
        chars = re.match(self.WINDOW_TRAIL_REGEX, layout)
        if chars:
            layout = layout[len(chars.groups()[0]) :]
        layout = layout.strip()

        match = re.match(r".*\[([0-9]+x[0-9]+)\]", layout)
        win_size = parse_size(match.groups()[0])
        self.base_width = int(win_size["width"])
        self.base_height = int(win_size["height"])

        # Make sure layout is not zoomed
        select_pane(self.session_name, win_layout_num, 0)
        # Pull only the layout details
        win_layout = get_tmux_details(
            self.session_name, win_layout_num, None, WINDOW_LAYOUT_VARIABLE
        )
        self.parse_layout(win_layout)

    def parse_layout(self, layout: str) -> None:
        """
        Parse a layout string into panes

        The layout string should be of the format:
          <pane_indicator>,<pane_number or further layout data>

        Parameters
        ----------
        layout : string
            The layout string to parse
            Will be in the form:
                <layout_id>,<win_size>,<offset_left>,<offset_top>,<pane_data>
        """
        match = re.match(self.LAYOUT_DETAILS, layout)
        (
            self.layout_id,
            self.layout_size,
            self.offset_left,
            self.offset_top,
        ) = match.groups()

        # Three commas separating fields
        pane_data = layout[
            len(self.layout_id)
            + len(self.layout_size)
            + len(self.offset_left)
            + len(self.offset_top)
            + 3 :
        ]
        # This will recursively populate all panes
        self.add_pane_row(pane_data)

        for pane in self.panes:
            pane.set_command(
                get_pane_command(self.session_name, self.number, pane.number)
            )
            pane.set_start_dir(
                get_pane_working_directory(self.session_name, self.number, pane.number)
            )

    def add_simple_pane(self, win_id: str, parent_id: str = None) -> None:
        """
        Adds a pane to this window

        Parameters
        ----------
        win_id : str
            The window ID to prefix this pane with
        parent_id = None : str
            Optionally, the ID of this pane's parent
        """
        if parent_id:
            number = self.objects.get_pane_by_id(parent_id).number + 1
        else:
            number = 0

        debug("Window", "add_simple_pane", "Adding pane: " + str(number))
        # The layout is a single pane
        pane = Pane(win_id + str(number), self, None, True)
        self.panes_added += 1
        # All that's left after the comma is the pane number
        pane.set_number(number)
        self.panes.append(pane)

    # pylint: disable=bad-continuation
    # black auto-format disagrees
    def add_pane_row(
        self, layout: str, parent_id: str = None, prevailing_split: str = None
    ) -> None:
        """
        Add a row of panes, either horizontally or vertically

        Parameters
        ----------
        layout : string
            The layout for the row, should start with either a [ or {,
            depending on whether the split is vertical or horizontal
        parent_id : string
            The identity of the pane to base these off of
        prevailing_split: string
            The current split direction, for the first pane to be based off of

            The following data will be a comma-separated array of pane data
            See add_pane_by_layout
        """
        win_id = "win{0}pane".format(self.number)
        debug("Window", "add_pane_row", "Adding pane row")
        debug("Window", "add_pane_row", layout)
        if layout[0] == ",":
            self.add_simple_pane(win_id, parent_id)
        else:
            direction = self.DIRECTION_MAP[layout[0]]
            debug("Window", "add_pane_row", "Layout split direction: " + direction)
            # Strip outermost direction indicators
            layout = layout[1:-1]
            debug("Window", "add_pane_row", "Resolved layout: " + layout)

            deferred_layouts = self.identify_deferred_layouts(
                layout, direction, parent_id, prevailing_split
            )

            for deferred_layout in deferred_layouts:
                debug("Window", "add_pane_row", "Processing deferred layout:")
                debug("Window", "add_pane_row", "Layout: " + deferred_layout["layout"])
                debug(
                    "Window",
                    "add_pane_row",
                    "Parent: "
                    + str(deferred_layout["parent"])
                    + ", number: "
                    + str(
                        self.objects.get_pane_by_id(deferred_layout["parent"]).number
                    ),
                )

                if deferred_layout["prevailingSplit"]:
                    debug(
                        "Window",
                        "add_pane_row",
                        "Prevailing split direction: "
                        + deferred_layout["prevailingSplit"],
                    )

                    self.add_pane_row(
                        deferred_layout["layout"],
                        deferred_layout["parent"],
                        deferred_layout["prevailingSplit"],
                    )
                else:
                    debug(
                        "Window",
                        "add_pane_row",
                        "Split direction: " + deferred_layout["split"],
                    )

                    self.add_pane_row(
                        deferred_layout["layout"],
                        deferred_layout["parent"],
                        deferred_layout["prevailingSplit"],
                    )

    # pylint: disable=bad-continuation
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    # Lots of debug calls, because of the complex logic that lives here
    # So should be okay to ignore for linting
    def identify_deferred_layouts(
        self,
        layout: str,
        direction: str,
        parent_id: str = None,
        prevailing_split: str = None,
    ) -> list:
        """
        Identifies any layouts needing to be resolved later
        This algorithm requires breadth-first parsing, to have
        correct numbering/re-creation behaviors

        Parameters
        ----------
        layout : str
            The layout to analyze
        direction : str
            The direction of this layout
        parent_id = None : str
            The original parent this layout should be created for
        prevailing_split = None : str
            The direction of the layout prior to this one

        Returns
        -------
        list
            A list of layouts which need to be processed later
        """
        first_found = True
        deferred_layouts = []

        while True:
            match = re.match(self.PANE_LAYOUT, layout)
            if not match:
                break

            pane_layout = match.groups()[0]
            debug("Window", "identify_deferred", "Pane details:")
            debug("Window", "identify_deferred", pane_layout)
            layout = layout[len(pane_layout) :]
            debug("Window", "identify_deferred", "Remaining layout:")
            debug("Window", "identify_deferred", layout)
            if layout[0] == ",":
                match = re.match(r",([0-9]+)", layout)
                pane_number = match.groups()[0]
                debug(
                    "Window", "identify_deferred", "Got pane number:" + str(pane_number)
                )
                match = re.match(r"(,[0-9]+,?)", layout)
                to_remove = match.groups()[0]
                layout = layout[len(to_remove) :]
                debug("Window", "identify_deferred", "Stripping number, leaves:")
                debug("Window", "identify_deferred", layout)
                debug(
                    "Window",
                    "identify_deferred",
                    "Adding pane with split direction: "
                    + (
                        direction
                        if not first_found or not prevailing_split
                        else prevailing_split
                    ),
                )
                self.add_pane_by_layout(
                    pane_layout,
                    pane_number,
                    direction
                    if not first_found or not prevailing_split
                    else prevailing_split,
                    parent_id if parent_id else self.last_pane,
                )
                first_found = False

            else:
                debug("Window", "identify_deferred", "Resolving layout recursively")
                # Find the end of the nested layout
                # Tracks the levels of layouts
                # e.g. for [ { [ ] } ] will have [, {, [
                nested_layouts = [layout[0]]
                length = 0
                for char in layout[1:]:
                    if char in self.LAYOUT_PAIRS.keys():
                        nested_layouts.append(char)
                    elif char == self.LAYOUT_PAIRS[nested_layouts[-1]]:
                        nested_layouts.pop()
                        # If this was the last one, then stop searching the string

                    length += 1
                    if len(nested_layouts) == 0:
                        break

                debug("Window", "identify_deferred", "Found deferred layout:")
                debug("Window", "identify_deferred", "Layout: " + layout[: length + 1])
                debug(
                    "Window",
                    "identify_deferred",
                    "Parent: " + str(self.panes_added - 1),
                )
                debug("Window", "identify_deferred", "Split direction: " + direction)
                debug(
                    "Window",
                    "identify_deferred",
                    "Prevailing split direction: "
                    + (prevailing_split if prevailing_split else "None"),
                )

                pane_details = self.get_pane_details_from_layout(layout[1:length])

                layout_string = ""
                # +1 because offset by initial direction indicator
                if (
                    layout[len(pane_details["selfLayout"]) + 1]
                    not in self.DIRECTION_MAP
                ):
                    debug(
                        "Window",
                        "identify_deferred",
                        "Placeholder layout: " + pane_details["selfLayout"],
                    )

                    self.add_pane_by_layout(
                        pane_details["selfLayout"],
                        pane_details["number"],
                        prevailing_split if prevailing_split else direction,
                        parent_id,
                    )
                    # Layout is direction indicator plus everything after the first pane
                    # until the end of the matched (nested) layout
                    # This will be added later, since
                    # we need to parse layouts breadth-first
                    layout_string = (
                        layout[0]
                        + layout[len(pane_details["selfLayout"]) + 1 : length + 1]
                    )

                    # After the prevailing split has been honored the first time
                    # then the nested direction should be sequential, in order
                    prevailing_split = None
                else:
                    debug(
                        "Window",
                        "identify_deferred",
                        "NOT adding placeholder for double-nested layout",
                    )

                    # Pass through as-is, since deferred
                    layout_string = layout
                    # However, overwrite the prevailing split direction to match the new
                    # nested split so the placeholder is created in the proper direction
                    prevailing_split = self.DIRECTION_MAP[
                        layout[len(pane_details["selfLayout"]) + 1]
                    ]

                deferred_layouts.append(
                    {
                        "layout": layout_string,
                        "parent": self.last_pane,
                        # Deferred layouts will contain the next direction,
                        # not the current direction
                        "split": self.DIRECTION_MAP[layout[0]],
                        "prevailingSplit": prevailing_split,
                    }
                )

                # Strip the part that was nested out of the layout
                # and remove a left-leading comma, if there is one
                layout = layout[length + 1 :].lstrip(",")
                debug("Window", "identify_deferred", "Removing deferred layout leaves:")
                debug("Window", "identify_deferred", layout)

            # For deferred layouts where multiple panes will be added,
            # chain parent to this pane
            # Otherwise, you end up with 0 - 2 - 1 for pane numbering,
            # when you really should have 0 - 1 - 2
            # This is because the "add_pane" bit will
            # shift numbers 1 and greater up one, but that doesn't match
            # the order of creation/insertion that is expected
            if parent_id:
                parent_id = self.last_pane

        return deferred_layouts

    # pylint: disable=bad-continuation
    def add_pane_by_layout(
        self,
        layout: str,
        pane_number: int,
        direction: str,
        parent_identity: str = None,
    ) -> None:
        """
        Adds a new pane, using the layout to fill in details

        Parameters
        ----------
        layout : string
            The layout string for the pane
            Will be in the following format:
              <size>,<offset_left>,<offset_top>
        pane_number : number
            The number of the pane, from the layout
        direction : string
            The direction this pane should be split from the previous one
        parent_identity : string
            The identity of the parent pane
            Used to re-order panes, if needed
        """
        size = parse_size(layout.split(",")[0])
        pane_id = "win{0}pane{1}".format(self.number, self.panes_added)
        pane = (
            Pane(pane_id, self, direction, self.panes_added == 0)
            .set_session_name(self.session_name)
            .set_size(
                100 * size["width"] / self.base_width,
                100 * size["height"] / self.base_height,
            )
        )

        parent = None
        try:
            parent = self.objects.get_pane_by_id(parent_identity)
            parent_number = parent.number
        except NameError:
            parent_number = None

        pane_number = (
            parent_number + 1 if parent_number is not None else self.panes_added
        )

        if parent_number is not None and self.panes_added > pane_number:
            debug(
                "Window",
                "add_pane",
                "Incrementing pane numbers above {0}".format(pane_number),
            )
            for pane_to_check in self.panes:
                if pane_to_check.number >= pane_number:
                    pane_to_check.set_number(pane_to_check.number + 1)

        pane.set_number(pane_number)

        if self.last_pane is not None and parent_number is None:
            pane.set_target(self.last_pane)
        elif parent:
            pane.set_target(parent.identity)

        self.last_pane = pane.identity
        self.panes_added += 1
        self.panes.append(pane)
        debug(
            "Window",
            "add_pane",
            "Adding pane number {0} for parent {1} with size {2}".format(
                pane_number, parent_number, size
            ),
        )

    def get_pane_details_from_layout(self, layout: str) -> dict:
        """
        Get details about a pane layout

        Parameters
        ----------
        layout : str
            The layout string

        Returns
        -------
        dict
            containing details about the pane
        """
        match = re.match(self.PANE_DETAILS, layout)
        if not match:
            debug(
                "Window",
                "pane_details",
                "Layout did not match pane format! ({0})".format(layout),
            )
            return {}

        size = match.group(1)
        offset_left = match.group(2)
        offset_top = match.group(3)
        indicator = match.group(4)
        pane_number = match.group(5)

        layout = "{0},{1},{2}".format(size, offset_left, offset_top)
        if indicator == ",":
            layout += ",{0},".format(pane_number)

        return {
            "size": size,
            "left": offset_left,
            "top": offset_top,
            "number": pane_number,
            "selfLayout": layout,
        }
