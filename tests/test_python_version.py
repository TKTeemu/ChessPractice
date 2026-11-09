"""Python 3.16 removes asyncio.DefaultEventLoopPolicy. python-chess 1.11.2 uses it
in chess.engine, and chess.pgn imports chess.engine, so on 3.16 the program would fail at
"import chess.pgn". The program's own UCI client (app/engines/uci.py) does not need it.

This test is expected to fail (xfail) until python-chess is updated; pytest then reports
"1 xfailed". When it starts to pass (XPASS, which fails the run because strict=True), the
updated python-chess no longer warns: remove the xfail marker and the Python 3.15 note in
the README.
"""

import site
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_PYTHON = ROOT / "python"
running_private_python = pytest.mark.skipif(
    not Path(sys.executable).resolve().is_relative_to(PRIVATE_PYTHON.resolve()),
    reason="runs only with the Python that Install.bat puts in python\\")


@pytest.mark.xfail(strict=True, reason="python-chess 1.11.2: chess.pgn -> chess.engine uses "
                                        "asyncio.DefaultEventLoopPolicy, removed in Python 3.16")
def test_chess_pgn_imports_without_deprecation_warning():
    result = subprocess.run([sys.executable, "-W", "error::DeprecationWarning", "-c", "import chess.pgn"],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr


def test_running_on_python_3_15():
    # The README asks for Python 3.15; see the module docstring for why 3.16 does not work yet
    assert sys.version_info[:2] == (3, 15)


def test_path_file_matches_the_required_python():
    # setup\python315._pth must be named after the Python version, or the embeddable Python
    # does not read it; its first line names the zip of the standard library
    major, minor = (3, 15)
    pth = ROOT / "setup" / f"python{major}{minor}._pth"
    assert pth.is_file()
    lines = pth.read_text(encoding="ascii").splitlines()
    assert lines[0] == f"python{major}{minor}.zip"
    assert ".." in lines   # the Chessboard folder, for "import app"


@running_private_python
def test_private_python_ignores_everything_outside_the_folder():
    # The ._pth file makes Python ignore PYTHONPATH, PYTHONHOME, the registry and the user's
    # own site-packages, so another Python on the computer cannot affect Chessboard
    root = ROOT.resolve()
    outside = [p for p in sys.path if p and not Path(p).resolve().is_relative_to(root)]
    assert outside == []
    assert not site.ENABLE_USER_SITE


@running_private_python
def test_private_python_has_tcl_tk():
    import tkinter
    tkinter.Tcl()
