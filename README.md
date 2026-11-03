# Chessboard – Analysis

An offline chessboard for analysing games (legal moves only, variations, comments, PGN and FEN files), for playing against the computer (Stockfish, with a chess clock) and for learning openings. Written in Python with tkinter; the user interface is in English.

## Running

Double-click `Shakkilauta.bat`. It runs `pythonw shakkilauta.pyw`, so no console window opens.

For troubleshooting, run it from a console so errors are shown directly:

```
python shakkilauta.pyw
```

Unhandled exceptions are also written to `error.log`.

## Requirements

| Dependency | Source | Used for |
| --- | --- | --- |
| Python 3.15 with Tcl/Tk | python.org | `python -m tkinter` opens a test window if Tk is installed |
| python-chess 1.11.2 | `vendor/` folder | rules, PGN, FEN |
| Pillow | installed in Python | image handling |
| PyMuPDF | installed in Python | rendering the SVG pieces |
| pytest | installed in Python | tests |
| Stockfish (optional) | `engines/stockfish/stockfish.exe` | Play vs Computer; see below |

The exact versions are in `requirements-global.txt` and `requirements-vendor.txt`:

```
python -m pip install -r requirements-global.txt
python -m pip install --target vendor -r requirements-vendor.txt
```

python-chess is installed into the application folder instead of a venv, so that no new exe files are created on disk (F-Secure). The reasons are given in the plan:

```
python -m pip install --target vendor chess
```

## Modes

| Mode | Use |
| --- | --- |
| **Board** | The free board: move both sides, variations, comments. The program always starts in this mode. |
| **Play vs Computer** | Mode > Play vs Computer… asks for the engine, level, your colour and the start position. 30 minutes each on the clock (setting `vs_minutes`), no take-backs. Resign ends the game; Open in Board Mode (after the game) lets you analyse it. Clock times are saved in the PGN as `[%clk]` comments. |
| **Learn Openings** | Game > Learn Openings… asks for an opening (21 openings in three groups, with search), whether you play the opening or the reply, and the engine level. The computer answers from the opening book while the position is in it, then the engine takes over. *Suggest next move* shows the book moves as blue arrows during the opening phase (until move 12, setting `learn_suggest_moves`, 10–15). Take Back removes your last move and the reply. |

The **New Game** button at the top of the right-hand panel starts a new game in any mode (in the game modes it opens the mode's dialog again). The Comment & FEN section at the bottom can be folded away; it is open in Board mode by default.

## Stockfish

The program runs without Stockfish (the dialog then offers only *Random moves*). To play Stockfish, download it once:

1. From [stockfishchess.org/download](https://stockfishchess.org/download/) (GitHub release), take the Windows build `stockfish-windows-x86-64-universal.zip`. Since Stockfish 19 this one build picks the right code for the CPU itself (older releases had separate `avx2` and `sse41-popcnt` builds).
2. Unpack it into a new, empty folder and compare `Get-FileHash <zip>` with the checksum on the release page.
3. Copy the exe to `engines\stockfish\stockfish.exe`, and `Copying.txt` (the GPL licence) next to it. Run `Unblock-File engines\stockfish\stockfish.exe`.
4. Run `python -m pytest`: the Stockfish tests now run instead of being skipped.
5. Start one game and check the F-Secure event log. If an exception is needed, add only `stockfish.exe`.

Another location can be set in `settings.json` with `"engine_path"`. Stockfish never uses the network; the program talks to it only through pipes, and closes it when you leave the mode or exit.

## Tests

```
python -m pytest
```

The tests cover the model (rules, variations, navigation, take-back), files (PGN and FEN round trips), settings, modes, the chess clock, the rules of a game against the computer, the opening book and the rules of opening training, and the engines (the UCI client against a small fake engine in `tests/fake_uci.py`). The Stockfish tests are skipped when `engines/stockfish/` has no exe. The user interface has no automated tests.

## Folders

| Path | Contents |
| --- | --- |
| `shakkilauta.pyw` | entry point: paths, error log, DPI awareness, main window |
| `app/` | application code, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| `assets/pieces/cburnett/` | 12 SVG pieces |
| `assets/sounds/` | event sounds (WAV) |
| `assets/openings/` | the opening book: one PGN game per opening; see [docs/EXTENDING.md](docs/EXTENDING.md) |
| `tools/make_sounds.py` | regenerates the sounds: `python tools\make_sounds.py` |
| `tools/extract_pieces.py` | writes the SVG pieces from the data bundled with python-chess |
| `engines/stockfish/` | `stockfish.exe` (Stockfish 19, downloaded separately, not part of the code) and its licence `Copying.txt` |
| `tests/` | pytest tests |
| `vendor/` | python-chess (do not edit) |
| `Games/` | default folder for saved games |
| `settings.json` | settings, written when the program exits |

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): structure, data flow and where new code belongs.
- [Shakkilauta_suunnitelma.md](Shakkilauta_suunnitelma.md): the original plan (in Finnish) and the reasons for the technology choices.
- [docs/EXTENDING.md](docs/EXTENDING.md): how to add a mode, a chess engine or an engine level.
- [Pelikone_suunnitelma.md](Pelikone_suunnitelma.md): the plan (in Finnish) for modes and playing against the computer (Stockfish), and where Python libraries are installed.
- [Avausteoria_suunnitelma.md](Avausteoria_suunnitelma.md): the plan (in Finnish) for Learn Openings, the New Game button and the compact panel.

## Licences

python-chess: GPL-3.0 (Niklas Fiekas). Stockfish: GPL-3.0 (the Stockfish developers); it is a separate program run as a child process. Cburnett pieces: CC BY-SA 3.0 (Colin M.L. Burnett). All are credited in the program's About window.
