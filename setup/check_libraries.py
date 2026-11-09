"""Used by Install.bat: exit code 0 if the libraries are installed and work, 1 if not.

    python\\python.exe setup\\check_libraries.py requirements.txt

Checks that every "name==version" in the requirements file (and in the files it includes with
-r) is installed with exactly that version, and that Tcl/Tk, Pillow's ImageTk and python-chess
load. tkinter.Tcl() loads the Tcl library itself, not only the tkinter module.
Prints what is wrong; Install.bat hides that when it only wants to know whether to install.
"""

import importlib.metadata
import re
import sys
from pathlib import Path

PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s;\\]+)", re.MULTILINE)
INCLUDE = re.compile(r"^-r\s+(\S+)", re.MULTILINE)


def pins(path):
    text = Path(path).read_text(encoding="utf-8")
    yield from PIN.findall(text)
    for included in INCLUDE.findall(text):
        yield from pins(Path(path).parent / included)


def problems(requirements):
    for name, version in pins(requirements):
        try:
            installed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            yield f"{name} is not installed"
            continue
        if installed != version:
            yield f"{name} is {installed}, not {version}"
    try:
        import tkinter
        tkinter.Tcl()
        import PIL.ImageTk  # noqa: F401
        import chess.pgn  # noqa: F401
    except Exception as e:
        yield f"{type(e).__name__}: {e}"


def main():
    found = list(problems(sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"))
    for problem in found:
        print(f"      {problem}")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
