"""Python 3.16 removes asyncio.DefaultEventLoopPolicy. python-chess 1.11.2 uses it
in chess.engine, and chess.pgn imports chess.engine, so on 3.16 the program would fail at
"import chess.pgn". The program's own UCI client (app/engines/uci.py) does not need it.

This test is expected to fail (xfail) until python-chess is updated; pytest then reports
"1 xfailed". When it starts to pass (XPASS, which fails the run because strict=True), the
updated python-chess no longer warns: remove the xfail marker and the Python 3.15 note in
the README.
"""

import subprocess
import sys

import pytest


@pytest.mark.xfail(strict=True, reason="python-chess 1.11.2: chess.pgn -> chess.engine uses "
                                        "asyncio.DefaultEventLoopPolicy, removed in Python 3.16")
def test_chess_pgn_imports_without_deprecation_warning():
    result = subprocess.run([sys.executable, "-W", "error::DeprecationWarning", "-c", "import chess.pgn"],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr


def test_running_on_python_3_15():
    # The README asks for Python 3.15; see the module docstring for why 3.16 does not work yet
    assert sys.version_info[:2] == (3, 15)
