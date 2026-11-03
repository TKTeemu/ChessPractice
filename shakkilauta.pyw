"""Chessboard – start the application (run with pythonw so no console window opens)."""

import logging
import sys
import traceback
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR / "vendor"))
sys.path.insert(0, str(APP_DIR))

logging.basicConfig(filename=APP_DIR / "error.log", level=logging.ERROR, encoding="utf-8",
                    format="%(asctime)s %(levelname)s %(message)s")

REQUIRED_PYTHON = (3, 15)
# (module, what to tell the user if it cannot be imported)
REQUIREMENTS = [
    ("tkinter", "Tcl/Tk is missing. Reinstall Python 3.15 from python.org with "
                "\"tcl/tk and IDLE\" selected."),
    ("PIL", "Pillow is missing. Run Asenna.bat, or: python -m pip install -r requirements-global.txt"),
    ("chess.pgn", "python-chess is missing from the vendor folder. Copy the whole program folder "
                  "again, or: python -m pip install --target vendor -r requirements-vendor.txt"),
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


def enable_dpi_awareness():
    """Draw sharply on scaled displays instead of letting Windows stretch a blurry bitmap."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (ImportError, AttributeError, OSError):
        pass


def main():
    problems = missing_requirements()
    if problems:
        version = ".".join(map(str, sys.version_info[:3]))
        wanted = ".".join(map(str, REQUIRED_PYTHON))
        show_error("Chessboard cannot start",
                   f"Chessboard needs Python {wanted}. This is Python {version} ({sys.executable}).\n\n"
                   + "\n\n".join(problems))
        sys.exit(1)

    import tkinter as tk

    from app.main_window import MainWindow

    sys.excepthook = log_exception
    enable_dpi_awareness()
    root = tk.Tk()
    root.report_callback_exception = log_exception
    MainWindow(root, APP_DIR)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_exception(*sys.exc_info())
        show_error("Chessboard", f"Chessboard stopped because of an error. The details are in\n"
                                 f"{APP_DIR / 'error.log'}")
        raise
