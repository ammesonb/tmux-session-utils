"""
Generic utility functions
"""

import pprint
from uuid import uuid4
import argparse
from os import getenv

arguments = {}


def set_args(args: dict) -> None:
    """
    Updates the global arguments with the given ones

    Parameters
    ----------
    args : dict
        Arguments to add
    """
    arguments.update(args)


def get_id():
    """
    Returns a unique ID
    """
    return uuid4()


def do_debug(is_command_line: bool = False) -> bool:
    """
    Whether to show debug messages

    Parameters
    ----------
    is_command_line = False : bool
        If this is executing on the command line

    Returns
    -------
    bool
        True if debug messages should be shown
    """
    return (
        parse_args()["debug"]
        if is_command_line
        else getenv("SHOW_DEBUG") in ("1", 1, True,)
    )


# pylint: disable=bad-continuation
# black auto-format disagrees
def debug(
    cls: str, method: str, msg: str, max_width: int = 20, is_command_line: bool = False
) -> None:
    """
    Print a debug message

    Parameters
    ----------
    cls : string
        The class this is called from
    method : string
        The method this is called from
    msg : string
        The message to print
    max_width = 20 : int
        The maximum message length, for padding
    is_command_line = False : bool
        If this is executing on the command line

    Returns
    -------
    None
        -
    """
    if do_debug(is_command_line):
        msg = str(msg)
        msg = msg.replace("\n", "\n" + (" " * (max_width + 3)))  # 3 is " | "
        descriptor = "{0}[{1}]".format(cls, method).rjust(max_width)
        print("{0} | {1}".format(descriptor, msg))


# pylint: disable=bad-continuation
# black auto-format disagrees
def debug_object(
    cls: str, method: str, obj: dict, is_command_line: bool = False
) -> None:
    """
    Debugs a given object, with some metadata

    Parameters
    ----------
    cls : string
        The class this is called from
    method : string
        The method this is called from
    obj : dict
        An object to debug
    is_command_line = False : bool
        Whether this is executing on the command line
    """
    if not do_debug(is_command_line):
        return

    fields = obj.keys()
    max_key_len = max([len(k) for k in fields])
    fields = [f.rjust(max_key_len) for f in fields]

    message = "\n".join(["{0} = {1}".format(f, obj[f.lstrip(" ")]) for f in fields])
    debug(cls, method, message)


def parse_args():
    """
    Parse command-line arguments
    """
    if not arguments.keys():
        parser = argparse.ArgumentParser(
            description="Script the building of a given tmux session"
        )
        parser.add_argument("session", type=str, help="The session to script")
        parser.add_argument(
            "-d", "--debug", action="store_true", help="Whether to print debug messages"
        )
        parser.add_argument(
            "-s", "--directory", type=str, help="The initial session directory"
        )
        parser.add_argument(
            "-n",
            "--nodetach",
            action="store_false",
            default=True,
            help="Do not detach this session after creation",
        )
        parsed = parser.parse_args()
        arguments.update(
            {
                "session": parsed.session,
                "debug": parsed.debug,
                "dir": parsed.directory,
                "detach": parsed.nodetach,
            }
        )

    return arguments


def parse_size(size: str) -> dict:
    """
    Parses a tmux size in the {width}x{height} format to a dict

    Parameters
    ----------
    size : string
        A size string from tmux

    Returns
    -------
    dict
        A dict with the width/height attributes set
    """
    size = size.split("x")
    return {"width": int(size[0]), "height": int(size[1])}


def shorten_id(identity: str) -> str:
    """
    Shortens a unique ID to a printable format; i.e. the last octet

    Parameters
    ----------
    identity : string
        The unique ID to shorten

    Returns
    -------
    string
        The shortened unique ID
    """
    return str(identity).split("-")[-1]


def resolve_parent(previous, parent):
    """
    Figure out the parent to use based on the previous pane or given parent

    Breadth-based recursion means the previous pane should take precedence
    over the original parent if one is provided

    Parameters
    ----------
    previous
        The previous pane
    parent
        The current parent
    """
    resolved = None

    if previous:
        resolved = previous
    elif parent:
        resolved = parent

    return resolved


def get_split_direction(indicator: str):
    """
    Gets split direction from an indicator

    Parameters
    ----------
    indicator : string
        The indicator, should be [ or {

    Returns
    -------
        v if vertical "[" otherwise "h"
    """
    return "v" if indicator == "[" else "h"


def is_null(value, replace: str = ""):
    """
    Checks if something is empty and will replace it with the given value

    Parameters
    ----------
    value
        A thing to check if empty
    replace : string
        The thing to replace it with
    """
    return value if value else replace


def convert_lines_to_object(lines: list) -> dict:
    """
    Convert an array of lines into an object indexed by the line number
    Indexing from 0

    Parameters
    ----------
    lines : list
        The list of lines to convert

    Returns
    -------
    dictionary
        A dictionary of the lines, indexed by the line number (starting from 0)
    """
    i = 0
    pad_to = len(str(len(lines)))
    obj = {"count": len(lines)}
    for line in lines:
        obj.update({"line" + str(i).rjust(pad_to, "0"): line})
        i += 1

    return obj


def convert_dict_to_class(data: dict) -> object:
    """
    Converts a dictionary to a class

    Parameters
    ----------
    data : dict
        Data to put into a class

    Returns
    -------
    object
        An anonymous class with attributes from dictionary
    """
    if isinstance(data, dict):
        return type("Class", (object,), data)

    raise TypeError("Data is not a dictionary")


def is_primitive(thing) -> bool:
    """
    Check if a given thing is a primitive type

    Parameters
    ----------
    thing
        The thing to check

    Returns
    -------
    bool
        True if thing is a primitive
    """
    primitives = [int, str, bool, dict, list, float]

    return type(thing) in primitives


def get_object_differences(obj1, obj2, properties: list) -> dict:
    """
    Checks for differences between two objects, and outputs a dict of them

    Parameters
    ----------
    obj1 : class
        The first class object
    obj2 : class
        The second class object
    properties : list
        The properties to compare between the objects

    Returns
    -------
    dict
        Any properties differing between the two classes

    Throws
    ------
    TypeError
        The two objects are not of the same type
    """
    # Change dictionaries to classes, for comparison
    # since classes can't be turned to dicts as easily
    if isinstance(obj1, dict):
        obj1 = convert_dict_to_class(obj1)
    if isinstance(obj2, dict):
        obj2 = convert_dict_to_class(obj2)

    differences = {}
    # For each property passed in
    for prop in properties:
        attr1 = getattr(obj1, prop, "[No such property]")
        keys = {}

        # Check if properties are dictionaries, for recursive comparison
        if isinstance(attr1, dict):
            keys = attr1.keys()
            attr1 = convert_dict_to_class(attr1)
        attr2 = getattr(obj2, prop, "[No such property]")
        if isinstance(attr2, dict):
            if not keys:
                keys = attr2.keys()
            attr2 = convert_dict_to_class(attr2)

        if not is_primitive(attr1) or not is_primitive(attr2):
            differences[prop] = get_object_differences(attr1, attr2, keys)
        elif attr1 != attr2:
            differences[prop] = {"expected": attr1, "actual": attr2}

    return differences


def assert_objects_equal(obj1, obj2, properties: list, capsys) -> None:
    """
    Compare two objects and assert their properties match

    Parameters
    ----------
    obj1
        First object
    obj2
        Second object
    properties : list
        Properties to check
    """
    differences = get_object_differences(obj1, obj2, properties)
    assert_object_values(differences, capsys)


def assert_object_values(differences: dict, capsys, parent_path: str = "") -> None:
    """
    Assert object values match, recursively
    Looks for "expected" and "actual" properties in a dictionary for comparison

    Parameters
    ----------
    differences : dict
        Differences to analyze
    capsys
        A capsys object to allow for printing the mismatch values to stdout
    parent_path = "" : str
        Recursed path thus far, for identifying location of mismatch
    """
    for key, value in differences.items():
        key_path = parent_path + ("/" if parent_path else "") + key
        if "expected" in value and "actual" in value:
            if value["expected"] != value["actual"]:
                with capsys.disabled():
                    pprint.pprint(value)
            assert (
                value["expected"] == value["actual"]
            ), "Value mismatch in '{0}'".format(key_path)
        elif value:
            assert_object_values(value, capsys, key_path)
