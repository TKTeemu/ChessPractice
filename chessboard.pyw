"""Chessboard – start the application (run with pythonw so no console window opens)."""

import logging
import sys
import tempfile
import time
import traceback
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent


def setup_logging():
    """Log to error.log in the program folder or, if that is read-only, in the temp folder.
    Returns the path of the log."""
    for path in (APP_DIR / "error.log", Path(tempfile.gettempdir()) / "chessboard-error.log"):
        try:
            logging.basicConfig(filename=path, level=logging.ERROR, encoding="utf-8",
                                format="%(asctime)s %(levelname)s %(message)s", force=True)
            return path
        except OSError:
            continue
    return None   # nowhere to write: logging falls back to stderr, and the program still runs


LOG_PATH = setup_logging()
ERROR_QUIET_SECONDS = 30   # a repeating error (a timer) shows its message box only this often

REQUIRED_PYTHON = (3, 15)
# (module, what to tell the user if it cannot be imported)
REQUIREMENTS = [
    ("tkinter", "Tcl/Tk is missing. Reinstall Python 3.15 from python.org with "
                "\"tcl/tk and IDLE\" selected."),
    ("PIL", "Pillow is missing. Run Install.bat, then start the program with Chessboard.bat."),
    ("chess.pgn", "python-chess is missing. Run Install.bat, then start the program with Chessboard.bat."),
]


def show_error(title, text):
    """A message box that works even without tkinter (pythonw has no console to print to)."""
    if sys.stderr:
        sys.stderr.write(f"{title}\n{text}\n")
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)   # MB_ICONERROR
    except (ImportError, AttributeError, OSError):
        pass


def missing_requirements():
    """Texts for the requirements that cannot be imported; empty if all is well."""
    problems = []
    for module, advice in REQUIREMENTS:
        try:
            __import__(module)
        except Exception as e:   # ImportError, or e.g. AttributeError from a newer Python
            logging.error("Cannot import %s: %r", module, e)
            problems.append(f"• {advice}\n  ({type(e).__name__}: {e})")
    return problems


def log_exception(exc_type, exc, tb):
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    logging.error("Unhandled exception:\n%s", text)
    if sys.stderr:
        sys.stderr.write(text)


def callback_error_reporter(root):
    """For root.report_callback_exception: an error in a button or timer callback does not stop
    the program, so without a message the user would just see nothing happen."""
    import tkinter as tk
    from tkinter import messagebox

    state = {"open": False, "last": -ERROR_QUIET_SECONDS}

    def report(exc_type, exc, tb):
        log_exception(exc_type, exc, tb)
        if state["open"] or time.monotonic() - state["last"] < ERROR_QUIET_SECONDS:
            return
        state["open"] = True
        try:
            messagebox.showerror("Chessboard", f"Something went wrong: {exc}\n\n"
                                               f"The program keeps running, but save your game "
                                               f"soon. The details are in\n{LOG_PATH}", parent=root)
        except tk.TclError:   # the window is already closing
            pass
        state["open"] = False
        state["last"] = time.monotonic()

    return report


def enable_dpi_awareness():
    """Draw sharply on scaled displays instead of letting Windows stretch a blurry bitmap."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (ImportError, AttributeError, OSError):
        pass


def main():
    problems = missing_requirements()
    if problems or sys.version_info[:2] != REQUIRED_PYTHON:
        version = ".".join(map(str, sys.version_info[:3]))
        wanted = ".".join(map(str, REQUIRED_PYTHON))
        show_error("Chessboard cannot start",
                   f"Chessboard needs Python {wanted}. This is Python {version} ({sys.executable}).\n\n"
                   + "\n\n".join(problems or ["Run Install.bat, which installs the right version."]))
        sys.exit(1)

    import tkinter as tk

    from app.main_window import MainWindow

    sys.excepthook = log_exception
    enable_dpi_awareness()
    root = tk.Tk()
    root.report_callback_exception = callback_error_reporter(root)
    MainWindow(root, APP_DIR)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_exception(*sys.exc_info())
        show_error("Chessboard", f"Chessboard stopped because of an error. The details are in\n{LOG_PATH}")
        raise
