"""
Handles setup for the module
"""
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tmux-session-utilities",
    version="1.0.0",
    author="Brett Ammeson",
    author_email="ammesonb@gmail.com",
    description="A utility for scripting Tmux sessions",
    long_description=long_description,
    url="https://github.com/ammesonb/tmux-session-utils",
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
)
