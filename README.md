# Chessboard – Analysis

An offline chessboard for analysing games (legal moves only, variations, comments, PGN and FEN files), for playing against the computer (Stockfish, with a chess clock) and for learning openings. Written in Python with tkinter; the user interface is in English.

Copyright (C) 2026 Teemu. Licensed under the GNU General Public License v3.0 or later; see [LICENSE](LICENSE) and [Licences and sharing](#licences-and-sharing).

**Installing on Windows 11: follow the step-by-step instructions in [INSTALL.txt](INSTALL.txt).** No programming knowledge is needed.

The first part of this file is for **using** the program; the second part, from [For developers](#for-developers), is for changing it.

## Requirements

| What | Where from | Notes |
| --- | --- | --- |
| **Python 3.15** (64-bit) with Tcl/Tk | python.org | Exactly 3.15: Python 3.16 does not work yet (see [docs/MAINTENANCE.md](docs/MAINTENANCE.md#moving-to-a-new-python-minor-version)). `python -m tkinter` opens a test window if Tk is installed. |
| Pillow and python-chess 1.11.2 | The `.venv` folder, filled by `Install.bat` | image handling; rules, PGN, FEN. A zip from `tools/make_dist.py` includes them, so this step needs no network. |
| Stockfish (optional) | `engines/stockfish/stockfish.exe`, downloaded by `Install.bat` | Play vs Computer, Learn Openings, Middlegame Practice and Endgame Practice at real strength; see [Stockfish](#stockfish) |

## Running

Double-click `Chessboard.bat`. It starts the program with the Python environment made by `Install.bat` (the `.venv` folder), without a console window.

If something the program needs is missing (Tk, Pillow, python-chess, or the right Python version), a message box says what and how to fix it. Other errors show a message and are written to `error.log` in the program folder (`chessboard-error.log` in the temp folder if the program folder is read-only). To see errors directly, run it from a console:

```
.venv\Scripts\python.exe chessboard.pyw
```

## Modes

| Mode | Use |
| --- | --- |
| **Board** | Game > Board (free analysis), the last entry in the menu. The free board: move both sides, variations, comments. The program always starts in this mode. Tick *Engine analysis* and Stockfish analyses the position shown: the score from White's point of view, the expected line and a blue arrow for the best move. Stockfish runs only while the box is ticked. Deleted moves can be restored with Ctrl+Y (Edit > Restore Deleted Moves) until a new move is played. |
| **Play vs Computer** | Game > Play vs Computer… asks for the engine, level, your colour, the start position and the clock (minutes each and an optional increment per move). No take-backs. Moves can be browsed once the game has finished. Resign ends the game; Open in Board Mode (after the game) lets you analyse it. Clock times are saved in the PGN as `[%clk]` comments. |
| **Learn Openings** | Game > Learn Openings… asks for an opening (21 openings in three groups, with search), whether you play the opening or the reply, and the engine level. The computer answers from the opening book while the position is in it, then the engine takes over. *Suggest next move* shows the book moves as blue arrows during the opening phase (until the move you choose in the dialog, 10–15). The Take Back button (or Ctrl+Z) removes your last move and the reply; ← and the ◀ button browse the moves. |
| **Middlegame Practice** | Game > Middlegame Practice… works like Endgame Practice below, with known puzzles: classic patterns and positions from famous games (levels 1 Classic patterns, 2 Famous combinations, 3 Master attacks; the clock defaults to 30 minutes, setting `mid_minutes`). Once you have played a correct line out, the puzzle is solved and the light stays green whatever happens in the rest of the game. You may play on to the end. *Suggest next move* stays available throughout: the puzzle's moves while you are on a known path, the engine's best move after that. |
| **Endgame Practice** | Game > Endgame Practice… asks only for a difficulty level (1 Basic mates … 5 Studies) and the clock (15 minutes, setting `end_minutes`). The program draws a position of that level that you have not played yet (what you have played and solved is remembered between runs, in `settings.json`), and you play the side to move against Stockfish at full strength: the computer first defends as stored in the position's solution, then with the engine. The line directly above the board says which colour you play and whose turn it is. The light above the board turns green when you solve the position (play the solution out, or reach the goal) and red when you miss it (a known wrong try, a move the engine judges to give the goal away, or the wrong result); the game goes on either way until it ends on the board or on time, and then the result is shown next to the light. *Suggest next move* shows the solution's moves (or the engine's best move) as arrows. The Take Back button (or Ctrl+Z, ← or the ◀ button) takes your move back, also after mate or stalemate, but the clock is not wound back. When there is nothing to take back, or you have already gone to an earlier move, ← and ◀ browse instead; Home, End, → and clicks in the move list always browse. Retry plays the same position again without asking to save the attempt; File > New Game shows the level dialog again and draws another position. Without Stockfish the computer plays the stored defence and then random moves, and moves off the solution are not judged. |

The **New Game** button at the top of the right-hand panel starts a new game in any mode (in the game modes it opens the mode's dialog again). The Comment & FEN section at the bottom can be folded away; it is open in Board mode by default.

Settings are kept in `settings.json` in the program folder and saved a few seconds after each change.

## Stockfish

The program runs without Stockfish (the dialogs then offer only *Random moves*). `Install.bat` downloads Stockfish 19, checks its SHA-256 and puts it in the right place. To do the same by hand:

1. From [stockfishchess.org/download](https://stockfishchess.org/download/) (GitHub release), take the Windows build `stockfish-windows-x86-64-universal.zip`. Since Stockfish 19 this one build picks the right code for the CPU itself.
2. Unpack it into a new, empty folder and compare `Get-FileHash <zip>` with the checksum on the release page.
3. Copy the exe to `engines\stockfish\stockfish.exe`, and `Copying.txt` (the GPL licence) next to it. Run `Unblock-File engines\stockfish\stockfish.exe`.

Optional: Syzygy endgame tablebases (3–5 pieces, the `*.rtbw` and `*.rtbz` files) in `engines\syzygy\` make Stockfish's judgement of small endgames exact in Endgame Practice. The program works without them.

Another location can be chosen with View > Stockfish Location. Stockfish never uses the network; the program talks to it only through pipes, and closes it when you leave the mode or exit.

## Licences and sharing

The program is free software under the **GNU GPL v3.0 or later** ([LICENSE](LICENSE)). It has to be: it is distributed together with python-chess, which is GPL-3.0. The parts made by others and their licences are listed in [NOTICE](NOTICE):

| Part | Author | Licence |
| --- | --- | --- |
| python-chess (installed into `.venv`) | Niklas Fiekas | GPL-3.0 |
| Cburnett pieces (`assets/pieces/cburnett`) | Colin M.L. Burnett | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| Stockfish (`engines/stockfish`, downloaded separately) | the Stockfish developers | GPL-3.0 |
| Pillow (installed into `.venv`) | Jeffrey A. Clark and contributors | MIT-CMU |

What this means in practice:

- **Copying to your own other computer:** no obligations; licences only concern giving the program to others.
- **Giving a copy to someone else:** keep `LICENSE` and `NOTICE` in the folder (the zip from `tools/make_dist.py` includes them). The program is Python source code, so the GPL's source-code requirement is met by the copy itself.
- **Stockfish to someone else:** leave `stockfish.exe` out and let them download it (the zip does this), or include the source code zip of the same Stockfish release. `Copying.txt` must be next to the exe in either case.
- **GitHub:** a private repository needs nothing. A public one should have `LICENSE` in it (it does), otherwise others may look at the code but not use it.
- **Selling:** the GPL does not allow forbidding others to sell copies. That has no practical effect for a free program that is not published.

The licence costs nothing: it is just the text file; nothing is registered or bought.

---

# For developers

To set up a development copy:

```
.\Install.bat dev
.venv\Scripts\python.exe -m pytest
```

A healthy test run is all passed plus exactly 1 xfailed. The developer documentation is in `docs/` in the repository (the zip from `tools/make_dist.py` leaves it out):

| Document | Read it to |
| --- | --- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | understand the structure, the rules it relies on and how a move flows through it |
| [docs/EXTENDING.md](docs/EXTENDING.md) | add a mode, an engine, a setting, a command or a library |
| [docs/DATA_FORMATS.md](docs/DATA_FORMATS.md) | add openings, middlegame puzzles and endgame positions; look up settings, saved PGN headers and permanent keys |
| [docs/MAINTENANCE.md](docs/MAINTENANCE.md) | run tests and tools, update Python or Stockfish, build the zip, diagnose problems |
| [docs/DECISIONS.md](docs/DECISIONS.md) | find out why something is the way it is before changing it |
