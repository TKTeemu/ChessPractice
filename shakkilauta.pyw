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
        raise
