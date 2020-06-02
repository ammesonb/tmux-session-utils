<h2 align="center">Tmux Session Utilities</h2>

<p align="center">
  <a href="https://travis-ci.com/ammesonb/tmux-session-utils"><img alt="Build Status" src="https://travis-ci.com/ammesonb/tmux-session-utils.svg?branch=master"></a>
  <a href="https://codecov.io/gh/ammesonb/tmux-session-utils">
    <img src="https://codecov.io/gh/ammesonb/tmux-session-utils/branch/master/graph/badge.svg" />
  </a>
  <a href="https://pyup.io/repos/github/ammesonb/tmux-session-utils/"><img src="https://pyup.io/repos/github/ammesonb/tmux-session-utils/shield.svg" alt="Updates" /></a>
  <a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
  <a href="https://github.com/ammesonb/tmux-session-utils/blob/master/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-purple.svg"></a>
</p>

<hr>

<h3>Background &amp; Description</h3>
This is a utility I built for saving/automating tmux sessions.
I found the existing tmux plugins did not suit my needs or would not work in my environment, for whatever reason.
This includes the `select-layout` tmux command, which also did not handle file system paths or executing commands.

This system is capable of both:
- Analyzing an existing tmux session and outputting the `tmux` commands to recreate it
- Creating a new session using a python "builder" class

<h3>Usage</h3>
Most simply, to script an existing session, you can execute `python3 builder/tmux_scripter.py <your_session_name>`.
I have not yet figured out how to get pip to install that somewhere useful like `/usr/bin`, so for now you'd need to just run this from its file system path. (Would LOVE it if someone happened across this and could point me in the right direction)
The python-codified version of this is:

```python
from os import getcwd
from tmux_session_utils.builder.tmux_scripter import TmuxScripter
from tmux_session_utils.tmux_utils import get_window_list

session_name = "your_session_name"
scripter = TmuxScripter(session_name, getcwd())
scripter.analyze(get_window_list("your_session_name")) # Think this bad was just a not-great design idea - likely isn't hard to wrap it into the class itself but haven't gotten around to it yet
scripter.build_commands() # Will print the command to stdout
# AND/OR
scripter.get_builder().run() # Optionally, will execute the command instead
```

For the builder, see this example:

```python
# This will create a session as follows (not to scale):
#   Pane 0   |  Pane 1
#  (25%x75%) | (75%x75%)
#    shell   |   tail
#  ---------------------
#         Pane 2
#        (100%x25%)
#            vi

detach_immediately = True
TmuxBuilder("your_session_name", "session_start_directory", detach_immediately)
    .add_window("window_id", "zero_pane_id", "window_name", "optional_working_directory")
    # v for vertical split
    .add_pane("one_pane_id", "v", working_directory="optional_working_directory")
    # should be one quarter the height, but full width (by default)
    .set_pane_height(25)
    .run_command("vi README.md")
    # split from the original pane in the window
    .add_pane("two_pane_id", "h", "zero_pane_id")
    .set_pane_width(75)
    .run_command("tail -f /var/log/dmesg")
    .build() # To output the command
    # OR
    .run() # To immediately execute the session
```
