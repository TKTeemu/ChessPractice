# Maintenance

Setting up, testing, updating dependencies, releasing and diagnosing problems.

## Setting up

Requires Python 3.15 (64-bit) with Tcl/Tk 9. `py -3.15 -m tkinter` opens a test window if Tk is there.

```
.\Install.bat dev
```

This creates `.venv` next to `chessboard.pyw`, installs the libraries into it and downloads Stockfish. It is safe to run again, and it builds `.venv` again if the libraries in it cannot be imported.

| File | Contents |
| --- | --- |
| `requirements.txt` | Pillow and python-chess, needed to run |
| `requirements-dev.txt` | `requirements.txt` plus pytest |

`.venv`, engine exes and `engines/syzygy/` are not in git. pip also writes `pip.exe` and `pytest.exe` launchers to `.venv\Scripts`, which the project does not use. They are also the only part of `.venv` that breaks if the program folder is moved.

Run from a console to see errors directly:

```
.venv\Scripts\python.exe chessboard.pyw
```

## Tests

```
.venv\Scripts\python.exe -m pytest
```

**A healthy run is all passed plus exactly 1 xfailed.** That xfail is the [Python 3.16 watch](#moving-to-a-new-python-minor-version). Without `stockfish.exe`, the real-engine tests are also skipped; on a machine where Tk cannot open a window, so is `test_main_window.py`.

| Kind | Where | How |
| --- | --- | --- |
| Rules and services | `test_model`, `test_fileio`, `test_settings`, `test_clock`, `test_computer_game`, `test_learning_game`, `test_endgame_game`, `test_middlegame_game`, `test_openings`, `test_endgames`, `test_middlegames` | No Tk. Clocks take a fake `now`, and randomness takes a seeded `rng`. |
| Modes without windows | `test_modes` | `fake_context()` records calls; `FakeRoot.run_timers()` runs timers on demand. |
| The real window | `test_main_window` | A real, hidden `MainWindow` with dialogs replaced by the `answers` fixture. `pump()` runs the event loop until a condition holds. One focus test shows the window briefly. |
| UCI protocol | `test_engines` with `fake_uci.py` | A small UCI engine in Python. |
| Real Stockfish | `test_engines` | Skipped when the exe is missing. |
| Data files | `test_openings`, `test_endgames`, `test_middlegames` | Every file in `assets/` loads and meets the rules. |
| Python version | `test_python_version` | See below. |

### Manual checks

The tests do not cover these. Run the ones your change touches:

- Drag and click moves, promotion picker, arrows, animation, sounds.
- Layout at a small window size and at 125 % display scaling.
- A game as White and as Black against Stockfish.
- Resign, change mode and close the program **while the engine is thinking**. Afterwards no `stockfish.exe` remains in Task Manager.
- The clocks stay right while the window is moved or minimised.
- The program without `stockfish.exe`: dialogs offer only *Random moves*, and Middlegame and Endgame Practice say moves off the solution are not judged.
- With the network disconnected.

## Tools

Run from the program folder.

| Command | Purpose |
| --- | --- |
| `.venv\Scripts\python.exe -m tools.check_endgames [--key K] [--level N] [--time S] [--folder DIR] [--first-moves]` | Check endgame positions, or with `--folder assets/middlegames` the middlegame puzzles, with Stockfish. `--first-moves` also notes where the engine prefers another first move. Slow, so not part of the tests. Exit status 1 if there are problems. Run it after changing positions or the Stockfish version. |
| `.venv\Scripts\python.exe -m tools.make_dist [--no-wheels] [--out DIR]` | Build the zip. |
| `.venv\Scripts\python.exe -m tools.make_sounds` | Regenerate `assets/sounds/`. |
| `.venv\Scripts\python.exe -m tools.extract_pieces` | Write the SVG pieces from the data bundled with python-chess. |

## Updating dependencies

Versions are pinned, and the same version appears in several places. Change them all together.

### A new Python 3.15.x

1. Update `PY_URL`, `PY_SHA256` and `PY_SETUP` at the top of `Install.bat`, and the file name in its "no Python" message.
2. Update the link and file names in `INSTALL.txt`.
3. Run the tests and `Install.bat` on a clean folder.

### Moving to a new Python minor version

**Python 3.16 is blocked today.** It removes `asyncio.DefaultEventLoopPolicy`. The program's own UCI client does not use it, but python-chess 1.11.2 does in `chess.engine`, and `chess.pgn` imports `chess.engine`, so the program would stop at `import chess.pgn`.

`test_chess_pgn_imports_without_deprecation_warning` watches for the fix. It stays xfailed until python-chess no longer warns, and then fails the run as an unexpected pass. When that happens:

1. Update python-chess in `requirements.txt`, run `Install.bat dev`, then remove the xfail marker.
2. Check that a Pillow wheel exists for the new version, and update `requirements.txt` if needed.
3. Change the version everywhere it is written:
   - `REQUIRED_PYTHON` and the messages in `chessboard.pyw`
   - `Install.bat`: `:find_python`, the URLs and messages
   - `INSTALL.txt`, the requirements table in `README.md`
   - `test_running_on_python_3_15`
   - Delete `.venv` and run `Install.bat dev`, because a venv keeps the Python it was made with.
4. Check that Tk still reads SVG pieces, because `pieces.py` relies on Tk 9.

### A new Stockfish

1. Update `SF_URL` and `SF_SHA256` in `Install.bat`. Compare the checksum with the release page.
2. Update the link and exe name in `INSTALL.txt`, and the version in `README.md` and `engines/stockfish/README.txt`.
3. Run the tests, which include real-engine tests.
4. Run `tools.check_endgames` for all positions, and again with `--folder assets/middlegames`. New evaluations can move scores across the [judging limits](DECISIONS.md#tuned-values).
5. Follow the checklist below.

### python-chess or Pillow

Change the pin in `requirements.txt`, run `Install.bat dev`, and run the tests. Never edit `.venv`. For python-chess, also check PGN round trips by hand with a file that has variations and comments.

### Antivirus checklist for an engine exe

The machine runs F-Secure, and the project is arranged so that the only exes it sees run are python.org's signed Python and launchers, and the engine.

1. Download only from the engine's official site or release page.
2. Unpack into a new, empty folder and check the SHA-256 (`Get-FileHash`).
3. Run `Unblock-File` on the exe.
4. Start one game from the program and check the F-Secure event log.
5. If an exception is needed, add only that exe, not the program folder.
6. Add no installers, services or `.dll` search paths, and nothing that writes outside the program folder.

## Releasing

There is no version number or release process beyond the zip:

```
.venv\Scripts\python.exe -m tools.make_dist
```

This writes `dist\Chessboard-<date>.zip`: the program, wheels of everything in `requirements.txt` for this Python version (`wheels/`), the launchers, `INSTALL.txt`, `README.md`, `LICENSE` and `NOTICE`. It leaves out `.venv`, `settings.json`, `error.log`, `Games/`, the engine exe, `tests/`, `tools/`, `docs/` and `.git`. `--no-wheels` makes it smaller, and `Install.bat` then downloads the libraries.

The target computer needs the same Python version and bitness because of the wheels. It unpacks the zip, runs `Install.bat` once, then `Chessboard.bat`.

Before giving it to someone:

- The tests pass, and the changed manual checks have been done.
- `Install.bat` and `INSTALL.txt` still agree.
- `LICENSE` and `NOTICE` are current, including anything new from others.

Licence obligations are in the [README](../README.md#licences-and-sharing). In short, the zip stays GPL-compliant because it is source code and leaves `stockfish.exe` out on purpose. `.bat` files and `INSTALL.txt` must keep CRLF line endings (`.gitattributes`), because `cmd.exe` can misread `goto` labels otherwise.

## Diagnosing problems

Look in `error.log` first (or `chessboard-error.log` in the temp folder).

| Symptom | Likely cause |
| --- | --- |
| "Chessboard cannot start" | The message names the problem: wrong Python, no Tk, or no Pillow or python-chess. Run `Install.bat`, and start the program from `.venv`, not with the system Python. |
| Pieces look like plain glyphs | The piece set is `unicode`, or SVG rendering failed (not Tk 9, or a bad file); `PieceImages._make_photo` falls back silently. |
| No sound | `sound` is off, a WAV is missing, or the platform has no `winsound`; all of these fail silently. |
| An opening or position is missing | A load error. Book and position errors appear as notes in the mode's dialog. Run the matching test or tool to see them all. |
| A setting keeps resetting | Its stored type differs from the default's type, or the key is not in any defaults. Check `Settings.load`. |
| A changed setting is not saved | A dict changed in place: `dirty` stays False. Assign a new dict. |
| "engine exited" | Stockfish crashed, often on an invalid position. Check that the position passes `Board.is_valid()`. |
| "no 'bestmove' from engine" | A search outlasted its timeout (`EXTRA_TIMEOUT` in `uci.py`), usually because of an overloaded machine or a wrong exe. |
| Stockfish found by tests but not in the game | `engine_path` in `settings.json` names a missing file. It takes priority over the default folder. |
| `stockfish.exe` left running | A bug: `close()` was not reached. Check that the mode's `deactivate` calls `super()`. |
| The computer stops moving | A cancelled request not followed by a new one, for example `cancel_computer_move` without `_next_turn`. |
| A typed comment disappears | A call to `position_changed` where `update_status` was meant, or a missing `save_comment`. |
| A selected piece or arrow disappears | The same: `position_changed` on another node, or a move played. |
| Save prompt missing after a result | Something wrote to the game without `GameModel`. See rule 1 in [ARCHITECTURE.md](ARCHITECTURE.md#rules-the-structure-relies-on). |
| `test_python_version` fails as XPASS | Good news: python-chess fixed it. See [above](#moving-to-a-new-python-minor-version). |
| `test_running_on_python_3_15` fails | You are running pytest on another Python. Use `.venv\Scripts\python.exe -m pytest`. |

## Keeping the docs right

Update docs in the same change as the code. They describe the present only; old reasoning goes in [DECISIONS.md](DECISIONS.md) if it is still useful, and git keeps the rest.

| When you change | Update |
| --- | --- |
| A module's job, a rule, a flow, the window layout | [ARCHITECTURE.md](ARCHITECTURE.md) |
| `Mode`, `Engine`, `ModeContext`, or how to add something | [EXTENDING.md](EXTENDING.md), and the docstrings in `modes/base.py` or `engines/base.py` |
| A file format, a setting, a PGN header | [DATA_FORMATS.md](DATA_FORMATS.md) |
| A dependency, tool, test helper, or a new failure worth recording | This file |
| A choice someone might want to undo | [DECISIONS.md](DECISIONS.md) |
| What the user sees or does | [README.md](../README.md), and `SHORTCUTS_TEXT` in `strings.py` for shortcuts |
| Installation | [INSTALL.txt](../INSTALL.txt) |

Refer to code by file and symbol name, not line number, so that references survive edits.
