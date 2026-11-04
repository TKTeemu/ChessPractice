# Chessboard – Analysis

An offline chessboard for analysing games (legal moves only, variations, comments, PGN and FEN files), for playing against the computer (Stockfish, with a chess clock) and for learning openings. Written in Python with tkinter; the user interface is in English.

Copyright (C) 2026 Teemu. Licensed under the GNU General Public License v3.0 or later; see [LICENSE](LICENSE) and [Licences and sharing](#licences-and-sharing).

The first part of this file is for **using** the program; the second part, from [For developers](#for-developers), is for changing it.

## Requirements

| What | Where from | Notes |
| --- | --- | --- |
| **Python 3.15** (64-bit) with Tcl/Tk | python.org | Exactly 3.15: Python 3.16 does not work yet (see [Python version](#python-version)). `python -m tkinter` opens a test window if Tk is installed. |
| Pillow | `Install.bat` | image handling; the only package installed into Python |
| python-chess 1.11.2 | `vendor/` folder | rules, PGN, FEN; comes with the program folder |
| Stockfish (optional) | `engines/stockfish/stockfish.exe` | Play vs Computer, Learn Openings and Endgame Practice at real strength; see [Stockfish](#stockfish) |

## Running

Double-click `Chessboard.bat`. It starts the program with the Python launcher (`pyw -3.15`) if it is installed, otherwise with `pythonw` from PATH, so no console window opens.

If something the program needs is missing (Tk, Pillow, python-chess), a message box says what and how to fix it. Other errors are written to `error.log` in the program folder. To see errors directly, run it from a console:

```
py -3.15 chessboard.pyw
```

## Modes

| Mode | Use |
| --- | --- |
| **Board** | The free board: move both sides, variations, comments. The program always starts in this mode. |
| **Play vs Computer** | Game > Play vs Computer… asks for the engine, level, your colour and the start position. 30 minutes each on the clock (setting `vs_minutes`), no take-backs. Resign ends the game; Open in Board Mode (after the game) lets you analyse it. Clock times are saved in the PGN as `[%clk]` comments. |
| **Learn Openings** | Game > Learn Openings… asks for an opening (21 openings in three groups, with search), whether you play the opening or the reply, and the engine level. The computer answers from the opening book while the position is in it, then the engine takes over. *Suggest next move* shows the book moves as blue arrows during the opening phase (until move 12, setting `learn_suggest_moves`, 10–15). ← (or the ◀ button, or Game > Take Back) removes your last move and the reply. |
| **Endgame Practice** | Game > Endgame Practice… asks only for a difficulty level (1 Basic mates … 5 Studies) and the clock (15 minutes, setting `end_minutes`). The program draws a position of that level that you have not played since the program was started, and you play the side to move against Stockfish at full strength: the computer first defends as stored in the position's solution, then with the engine. The light above the board turns green when you solve the position (play the solution out, or reach the goal) and red when you miss it (a known wrong try, a move the engine judges to give the goal away, or the wrong result); the game goes on either way. *Suggest next move* shows the solution's moves (or the engine's best move) as arrows. ← (or the ◀ button) takes your move back, also after mate or stalemate, but the clock is not wound back. Without Stockfish the computer plays the stored defence and then random moves, and moves off the solution are not judged. |

The **New Game** button at the top of the right-hand panel starts a new game in any mode (in the game modes it opens the mode's dialog again). The Comment & FEN section at the bottom can be folded away; it is open in Board mode by default.

Settings are kept in `settings.json` in the program folder and saved a few seconds after each change.

## Stockfish

The program runs without Stockfish (the dialogs then offer only *Random moves*). To play Stockfish, download it once:

1. From [stockfishchess.org/download](https://stockfishchess.org/download/) (GitHub release), take the Windows build `stockfish-windows-x86-64-universal.zip`. Since Stockfish 19 this one build picks the right code for the CPU itself.
2. Unpack it into a new, empty folder and compare `Get-FileHash <zip>` with the checksum on the release page.
3. Copy the exe to `engines\stockfish\stockfish.exe`, and `Copying.txt` (the GPL licence) next to it. Run `Unblock-File engines\stockfish\stockfish.exe`.

Optional: Syzygy endgame tablebases (3–5 pieces, the `*.rtbw` and `*.rtbz` files) in `engines\syzygy\` make Stockfish's judgement of small endgames exact in Endgame Practice. The program works without them.

Another location can be set in `settings.json` with `"engine_path"`. Stockfish never uses the network; the program talks to it only through pipes, and closes it when you leave the mode or exit.

## Licences and sharing

The program is free software under the **GNU GPL v3.0 or later** ([LICENSE](LICENSE)). It has to be: it is distributed together with python-chess, which is GPL-3.0. The parts made by others and their licences are listed in [NOTICE](NOTICE):

| Part | Author | Licence |
| --- | --- | --- |
| python-chess (`vendor/chess`) | Niklas Fiekas | GPL-3.0 |
| Cburnett pieces (`assets/pieces/cburnett`) | Colin M.L. Burnett | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| Stockfish (`engines/stockfish`, downloaded separately) | the Stockfish developers | GPL-3.0 |
| Pillow (installed into Python) | Jeffrey A. Clark and contributors | MIT-CMU |

What this means in practice:

- **Copying to your own other computer:** no obligations; licences only concern giving the program to others.
- **Giving a copy to someone else:** keep `LICENSE` and `NOTICE` in the folder (the zip from `tools/make_dist.py` includes them). The program is Python source code, so the GPL's source-code requirement is met by the copy itself.
- **Stockfish to someone else:** leave `stockfish.exe` out and let them download it (the zip does this), or include the source code zip of the same Stockfish release. `Copying.txt` must be next to the exe in either case.
- **GitHub:** a private repository needs nothing. A public one should have `LICENSE` in it (it does), otherwise others may look at the code but not use it.
- **Selling:** the GPL does not allow forbidding others to sell copies. That has no practical effect for a free program that is not published.

The licence costs nothing: it is just the text file; nothing is registered or bought.

---

# For developers

## Installing for development

```
py -3.15 -m pip install -r requirements-global.txt
py -3.15 -m pip install -r requirements-dev.txt
py -3.15 -m pip install --target vendor -r requirements-vendor.txt
```

| File | Installed into | Contents |
| --- | --- | --- |
| `requirements-global.txt` | the system Python | what the program needs to run (Pillow) |
| `requirements-dev.txt` | the system Python | tests (pytest) |
| `requirements-vendor.txt` | `vendor/` | python-chess |

python-chess is installed into the program folder instead of a venv, so that no new exe files are created on disk (F-Secure); the reasons are in [docs/plans/Engine_plan.md](docs/plans/Engine_plan.md). `vendor/`, the engine exe files and `engines/syzygy/` are not in git (`.gitignore`), so a fresh clone needs the commands above and the network. `engines/stockfish/` itself is in git with its `README.txt` and `Copying.txt`; only `stockfish.exe` has to be downloaded.

The Cburnett pieces are drawn with Tk's own SVG support (Tk 9), so no SVG library is needed.

## Copying the program to another computer

```
py -3.15 tools\make_dist.py
```

writes `dist\Chessboard-<date>.zip`: the program, `vendor/`, the Pillow wheel for this Python version (`wheels/`), `Install.bat`, `Chessboard.bat`, `LICENSE` and `NOTICE`. Left out: `settings.json` (your own paths), `error.log`, `Games/`, `engines/` (Stockfish), tests, tools and `.git`. On the other computer: install Python 3.15 (same bitness), unpack the zip, run `Install.bat` once (installs Pillow from `wheels/`, no network needed), then `Chessboard.bat`. `--no-wheels` makes a smaller zip; `Install.bat` then downloads Pillow.

## Python version

Python 3.16 removes `asyncio.DefaultEventLoopPolicy`. The program's own UCI client (`app/engines/uci.py`) does not use it, but the vendored python-chess 1.11.2 does in `chess.engine`, and `chess.pgn` imports `chess.engine`; on 3.16 the program would stop at `import chess.pgn`. `tests/test_python_version.py` watches for this: it is reported as *xfailed* until python-chess is fixed, and fails (XPASS) once an updated python-chess no longer warns. Then update `requirements-vendor.txt`, remove the xfail marker, and relax the 3.15 requirement here and in `chessboard.pyw` / `Chessboard.bat`.

## F-Secure

The program creates no exe files: no venv, and packages are run as `python -m <module>`. Stockfish is the only exe; after installing it, start one game and check the F-Secure event log. If an exception is needed, add only `stockfish.exe`. The checklist is in [docs/EXTENDING.md](docs/EXTENDING.md#f-secure-checklist-for-an-engine-exe).

## Tests

```
py -3.15 -m pytest
```

The tests cover the model (rules, variations, navigation, take-back), files (PGN and FEN round trips), settings, modes (including games started with `start(config)` against a fake window), the chess clock, the rules of a game against the computer, the opening book and the rules of opening training, the endgame positions (every file loads, the levels, drawing without repeats) and the rules of endgame practice (the success light, the engine as judge, take-back), and the engines (the UCI client against a small fake engine in `tests/fake_uci.py`). The Stockfish tests are skipped when `engines/stockfish/` has no exe. The windows themselves have no automated tests.

## Folders

| Path | Contents |
| --- | --- |
| `chessboard.pyw` | entry point: paths, requirement check, error log, DPI awareness, main window |
| `Chessboard.bat`, `Install.bat` | start the program; install Pillow |
| `app/` | application code, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| `assets/pieces/cburnett/` | 12 SVG pieces |
| `assets/sounds/` | event sounds (WAV) |
| `assets/openings/` | the opening book: one PGN game per opening; see [docs/EXTENDING.md](docs/EXTENDING.md) |
| `tools/make_dist.py` | builds the zip for another computer |
| `tools/make_sounds.py` | regenerates the sounds: `python tools\make_sounds.py` |
| `tools/check_endgames.py` | checks the positions in `assets/endgames/` with Stockfish (goal, solution, wrong tries): `python tools\check_endgames.py` |
| `tools/extract_pieces.py` | writes the SVG pieces from the data bundled with python-chess |
| `engines/stockfish/` | `stockfish.exe` (downloaded separately, not part of the code), its licence `Copying.txt` and a `README.txt` placeholder note |
| `tests/` | pytest tests |
| `vendor/` | python-chess (do not edit) |
| `docs/` | developer documentation; `docs/plans/` holds the original plans (historical) |
| `Games/` | default folder for saved games |
| `settings.json` | settings |

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): structure, data flow and where new code belongs.
- [docs/EXTENDING.md](docs/EXTENDING.md): how to add a mode, a chess engine, an opening, an endgame position or an engine level.
- [docs/plans/](docs/plans/): the original plans, kept for the reasons behind the choices: [Chessboard_plan.md](docs/plans/Chessboard_plan.md) (technology choices), [Engine_plan.md](docs/plans/Engine_plan.md) (modes, Stockfish, where libraries are installed), [Opening_theory_plan.md](docs/plans/Opening_theory_plan.md) (Learn Openings), [Endgame_plan.md](docs/plans/Endgame_plan.md) (Endgame Practice).
