# Chessboard – game modes and the computer opponent (plan)

> **Historical document.** This plan has been implemented and is no longer updated. The current structure of the program is described in [ARCHITECTURE.md](../ARCHITECTURE.md) and [EXTENDING.md](../EXTENDING.md).

2.11.2026

> A continuation of the original plan [Chessboard_plan.md](Chessboard_plan.md). The developer guide for adding modes and engines is in [docs/EXTENDING.md](../EXTENDING.md).

## Goal and scope

**Modes** are added to the program. After the extension there are two of them:

| Mode | Description |
| --- | --- |
| **Board mode** (*Board* in the menu) | The program as it is now: the user moves the pieces of both sides, can try out variations and write comments. |
| **Play against the computer** (*Play vs Computer* in the menu) | The user plays the colour they choose, and the engine replies. The user chooses the level and the colour. A chess clock is in use, and moves cannot be taken back. |

**Included:** choosing the mode in the *Game* menu, a new game dialog (level, colour, starting position), a chess clock (30 min for the user), the engine's moves in a background thread, resigning, recording the game result in the PGN, and opening a finished game in board mode.

**Not included:** taking back moves, hints, showing an evaluation or the best line, opening books, online play. The structure does not prevent these later.

**Absolute requirement:** the program works offline on Windows 11. Stockfish is downloaded once and is a local file after that; the program does not use the network.

**Extensibility:** a new mode = one new file in the `app/modes/` folder + a line in the registry. A new engine = one new file in the `app/engines/` folder + a line in the registry. The menus and dialogs are built from the registries automatically.

## Choice of engine: Stockfish

| Option | Pros | Cons |
| --- | --- | --- |
| **Stockfish (UCI)**, chosen | Open (GPL-3), strong, adjustable strength via `UCI_LimitStrength` + `UCI_Elo`, the NNUE network is inside the exe (a single file). | An exe file and a child process: deviates from the F-Secure principles of the original plan (see below). |
| A Python engine of our own | No exe files. | Weak, slow, hard to calibrate the levels. |

**Version:** Stockfish 19 (or the newest release). The program is not tied to a version: at startup it reads the limits of the strength setting (the min/max of the `UCI_Elo` option) from the engine. In recent versions the lower limit has been 1320, so the lowest requested level, 1320, works.

**Levels** (a data table in `app/engines/stockfish.py`, easy to change):

| Level | Setting | Thinking time |
| --- | --- | --- |
| 1320, 1500, 1650, 1800, 2000, 2200, 2400, 2600, 2800 | `UCI_LimitStrength=true`, `UCI_Elo=<level>` | 1 s / move |
| Maximum | no limit | 2 s / move |

Note: Stockfish's Elo scale is calibrated against a list of engines, so it does not correspond directly to Chess.com or FIDE figures; 1320 may feel slightly stronger against a human. If easier levels are wanted later, rows with the `Skill Level` option (0–20) can be added to the table.

**Light operation:** `Threads=1`, `Hash=64`. The engine process is started only when a Play vs Computer game begins and is closed when the mode is left or the program is closed. Board mode has no child processes at all, i.e. it works as before.

## Chess clock

| Side | Time | Behaviour |
| --- | --- | --- |
| User | 30 min for the whole game, no increment | The clock runs on the user's turn. If the time runs out, the user loses on time. An exception from the rules of chess: if the engine does not have enough material to checkmate, the game is a draw. |
| Engine | Also 30 min | Depending on the level, the engine uses 1–2 s per move, so its time practically never runs out. The clock is still shown so that the user sees the time the engine has used, and the saved game is an ordinary 30-minute game. |

- The clocks are shown next to the players' names above and below the board. The clock of the player to move is highlighted. A time under a minute is shown in red and in tenths of a second (0:42.3).
- The clock starts from White's first move. If the engine plays White, it makes the first move immediately, and the user's clock starts running.
- The clock is based on `time.monotonic()` time, not on a counter. The display is refreshed with a `root.after(100, …)` timer, but the remaining time is always calculated from the clock time, so it stays correct even if the window is dragged or minimised.
- The clock cannot be paused, and an unfinished game cannot be continued after the program is restarted.
- The engine's thinking time does not depend on the clock but on the level setting. If the engine should divide its time itself, `go wtime … btime …` can later be sent to Stockfish instead of a fixed `movetime`.
- The time is a setting (`vs_minutes`, default 30). If selectable times or an increment per move are wanted later, they are added as a time table in the same way as the levels.

## F-Secure and offline

The original principle was "no new exe files, no `subprocess` calls". Stockfish breaks this deliberately, but in a controlled way:

1. **One known exe, in one place:** `engines\stockfish\stockfish.exe`. No installer, no registry changes, no background service.
2. **Downloaded once from the official source** (stockfishchess.org → the GitHub release). The zip is extracted into its own empty folder, the SHA-256 is checked against the checksum on the release page (`Get-FileHash`), and the Mark of the Web is removed: `Unblock-File engines\stockfish\stockfish.exe`.
3. **CPU version:** for a Windows 11 machine, `stockfish-windows-x86-64-avx2.exe`. If it crashes at startup ("illegal instruction"), the `x86-64-sse41-popcnt` version is used, which works on all modern processors.
4. **No console window:** Stockfish is a console program, so it is started with the `CREATE_NO_WINDOW` flag. (python-chess's `popen_uci` does not set this itself.)
5. **No network:** Stockfish does not make network connections; the program communicates with it only through pipes (stdin/stdout).
6. **The F-Secure test** is done in phase 4: the first start is made and the event log is checked. If DeepGuard complains, only `stockfish.exe` is added as an exception, not the whole folder.
7. **Without Stockfish** the program works: the Play vs Computer dialog says that no engine was found and where to copy it. In testing, the internal *Random* engine is used, which does not need the exe.

## The UCI connection: our own thin client

python-chess has a ready-made `chess.engine`, but version 1.11.2 in the vendor folder uses the `asyncio.DefaultEventLoopPolicy` class, which is deprecated in Python 3.15 and removed in 3.16. Therefore we write a small UCI client of our own (`app/engines/uci.py`, about 120 lines) with the standard library's `subprocess`, `threading` and `queue` modules. The commands needed are few: `uci`, `setoption`, `isready`, `ucinewgame`, `position fen … moves …`, `go movetime …`, `stop`, `quit`. Moves are converted with `chess.Move.from_uci()`, and legality is checked with python-chess as before.

If a 3.16-compatible version of python-chess appears later, `UciEngine` can be changed to use it without changing anything else.

## Architecture

The existing layers remain (see [docs/ARCHITECTURE.md](../ARCHITECTURE.md)). Two packages are added:

```
app\
├── engines\                  logic layer, NO tkinter
│   ├── __init__.py           the ENGINES registry
│   ├── base.py               the Engine interface, the Level record
│   ├── uci.py                the UCI client (subprocess, CREATE_NO_WINDOW)
│   ├── stockfish.py          StockfishEngine: the level table, finding the exe
│   ├── random_engine.py      RandomEngine: for tests and as a fallback
│   └── worker.py             EngineWorker: search in a background thread, results into a queue
├── modes\                    controller layer (may use tkinter)
│   ├── __init__.py           the MODES registry
│   ├── base.py               the Mode interface and ModeContext
│   ├── board.py              BoardMode: board mode, the current behaviour
│   └── vs_computer.py        VsComputerMode: playing against the computer
├── computer_game.py          ComputerGame: the rules of the game without tkinter (testable)
├── clock.py                  ChessClock: the chess clock without tkinter (testable)
└── dialogs.py                + new_computer_game(): level, colour, starting position
engines\
└── stockfish\stockfish.exe   downloaded once, not part of the code
```

**The mode** decides what the user may do and what happens after a move. `MainWindow` stays the controller, but asks the mode:

| Place in MainWindow | Question to the mode |
| --- | --- |
| the start of a `BoardView` move | `mode.can_move(color)` – may the user move this colour now? |
| `play_move()` succeeded | `mode.after_move()` – e.g. start the engine's search |
| commands (Ctrl+Z, editing variations, paste…) | `mode.allows(command)` – is the command available? |
| `refresh()` | `mode.status_text()` – its own status line, e.g. "Computer is thinking…" |
| `refresh()` | `mode.score_text()` – text above the board on the right, e.g. the material situation |
| right panel | `mode.build_panel(parent)` – the mode's own buttons and clocks (Resign, Open in Board Mode) |
| menu | `mode.menu_items()` – the mode's own menu rows |
| changing the mode, Exit | `mode.deactivate()` – close the engine |

**The engine's move:** `VsComputerMode.after_move()` → if it is the engine's turn, `EngineWorker.request(board.copy(), level, request_id)` → the background thread asks the engine → the result goes into a queue → a `root.after(50, …)` poll reads the queue in the main thread → if `request_id` is still valid (the game has not been changed or cancelled), `MainWindow.play_move(move)`. The engine's move thus takes the same route as the user's move, so the sounds, the move list and saving work without extra code. tkinter is never called from the background thread.

## User interface

**Move animation** (in all modes): when the position advances by one move (the engine's move, a move made by clicking, or → browsing), the piece slides from the start square to the end square in 0.16 seconds. In castling the king and the rook move, and the piece to be captured stays visible until the moving piece arrives. A dragged move is not animated, because the piece is already there. Implemented in `BoardView` (`ANIM_SECONDS`).

**The `Game` menu** (choosing the mode):

```
Game
 ◉ Board
 ○ Play vs Computer…
 ─────────────
   Resign              (only during a game)
   Open in Board Mode  (only when the game has ended)
```

The mode rows come from the `MODES` registry, the mode-specific rows from `mode.menu_items()`.

**The Play vs Computer dialog:**

| Field | Options | Default (remembered in settings.json) |
| --- | --- | --- |
| Engine | the engines of the registry whose `available()` is true | Stockfish |
| Level | the engine's `levels()` | 1350 |
| Your colour | White / Black / Random | White |
| Start from | Initial position / Current position | Initial position |

**During the game:**

- The board is flipped according to the user's colour. The players' names: "You" and "Stockfish 1500".
- The user can move only their own pieces, and only when it is their turn and the board is at the end of the main line.
- In Play vs Computer mode the move history cannot be browsed (←/→, Home/End, clicking the move list), not even after the game has ended. Browsing is only in board mode; a finished game is gone through with the *Open in Board Mode* action. Editing variations, pasting and Ctrl+Z (deleting the last move) are disabled, **and moves cannot be taken back**.
- The selected mode is shown above the board (e.g. "Board" or "Play vs Computer · Stockfish 1500").
- The **material situation** is shown above the board on the right from the user's point of view: "Material: you +3", "Material: you −2" or "Material: even". Values: pawn 1, knight and bishop 3, rook 5, queen 9 (`material_balance()` in `model.py`). This is a piece count, not the engine's evaluation.
- **Resign** ends the game as a loss for the user.
- If the user tries to close the program, start a new game or change the mode during a game, the program asks "Resign the game?". *Yes* records the loss, *No* continues the game.
- When the game ends (checkmate, stalemate, draw, resignation), `Result` is recorded in the PGN header and the status line tells the final result.
- **Open in Board Mode** (only for a finished game) opens the game just played in board mode. There the game can be gone through, "what if I had played differently" moves can be tried as side variations and comments can be written, as for any opened PGN game. This cannot be done during the game, so that it does not become a way round taking moves back. Saving (Ctrl+S) works in both modes.
- PGN headers: `Event "vs Computer"`, `White`/`Black`, `Date`, `TimeControl "1800"`, `Termination` (e.g. `time forfeit`), and in addition `WhiteElo`/`BlackElo` for the engine's level. The clock time after each move is saved in the move's comment in the standard form `{[%clk 0:29:41]}`, which Lichess and ChessBase understand.

**New settings** (`settings.DEFAULTS`): `mode` ("board"), `vs_minutes` (30), `vs_engine` ("stockfish"), `vs_level` ("1350"), `vs_color` ("white"), `engine_path` ("" = look in the `engines\stockfish\` folder). The program always starts in board mode; an unfinished game against the engine is not continued automatically.

## Python libraries: what is installed where

The starting point is unchanged: **no venv**, because a Windows venv copies its own `python.exe` and `pythonw.exe` launchers into the `Scripts` folder, and F-Secure sees them as new exe files. The "local environment" here is the program's own `vendor\` folder (`pip install --target vendor`), which works like a venv but without exe files.

A second rule: for libraries that have command-line tools (console scripts), pip creates an `.exe` launcher in the `Scripts\` folder. Therefore tools are always run in the form `python -m <module>`, and new command-line tools are avoided.

**Permanently into the machine's Python** (general-purpose, compiled binaries that are updated rarely):

| Library | Why globally |
| --- | --- |
| Pillow | Already installed; a compiled package that other programs can use too. |
| PyMuPDF | Already installed; a large compiled package. |
| pytest | A development tool, not part of the program. Run `python -m pytest`. |
| pip | Managing installations. |

**Into the program's `vendor\` folder** (application-specific, pure Python, the version is pinned):

| Library | Why into vendor |
| --- | --- |
| python-chess (`chess==1.11.2`) | The core of the program. A pinned version that travels with the program folder and is not updated accidentally because of other programs. |

**The extension needs no new Python libraries.** The UCI client, the background thread and the queue are standard library (`subprocess`, `threading`, `queue`).

**Not installed:**

| Library | Reason |
| --- | --- |
| `stockfish` (PyPI) | An unnecessary wrapper; our own UCI client is smaller and more manageable. |
| PySide6/PyQt, pygame | Large binary packages, no need. |
| ruff, black and other exe-based tools | They create exe files; an F-Secure risk. |

**Can be removed:** `altgraph`, `pefile`, `pywin32-ctypes` are leftovers of PyInstaller, and the program does not use them (`python -m pip uninstall altgraph pefile pywin32-ctypes`). This is optional.

**Reproducibility:** two text files are added, with which the installation can be redone on another machine:

```
# requirements-global.txt   →  python -m pip install -r requirements-global.txt
pillow==12.3.0
pymupdf==1.28.2
pytest==9.2.0

# requirements-vendor.txt   →  python -m pip install --target vendor -r requirements-vendor.txt
chess==1.11.2
```

## Implementation phases

After each phase the program works and the tests pass.

1. **The mode framework, no visible changes.** `app/modes/` (base, board, registry). `MainWindow` asks the mode `can_move`/`allows`/`after_move`; `BoardView` gets a `can_move` callback. A Game menu with only Board. All the existing tests pass.
2. **The engine layer.** `app/engines/`: the Engine interface, RandomEngine, the UCI client, StockfishEngine, EngineWorker. Tests: RandomEngine returns a legal move; the UCI client is tested with a small fake engine written in Python (`tests/fake_uci.py`); the Stockfish tests are skipped (`pytest.skip`) if the exe is not found.
3. **Play vs Computer.** `computer_game.py` (turns, result, discarding a stale result) and `clock.py` (the chess clock), both testable without windows; `VsComputerMode`, the dialog, the clock displays, the panel buttons, the settings, the texts in `strings.py`.
4. **Stockfish and F-Secure.** Download, checksum, Unblock-File, choosing the CPU version, F-Secure's event log, manual testing of the levels (1350 and Maximum).
5. **Polish and documentation.** The Stockfish GPL-3 mention in the About window, the README installation guide, `docs/ARCHITECTURE.md` and `docs/EXTENDING.md` brought up to date.

## Testing

- **Automatic:** the Engine interface (a legal move, mate in one in a known position, `close()` closes the process), the UCI protocol with the fake engine, `ComputerGame` (whose turn, result, a stale result is discarded, Ctrl+Z blocked), `ChessClock` (switching the turn, loss on time, and a loss on time is a draw if the opponent lacks enough material to checkmate; the tests supply the clock time themselves and do not wait for real time), the mode registry (every mode has a key and a name, board mode allows everything).
- **By hand:** a game as White and as Black, a Random colour, starting from the current position, loss on time (in the test the clock is shortened with the `vs_minutes` setting), the clock stays correct even if the window is moved or minimised, resigning while the engine is thinking, changing the mode in the middle of a search, closing the program in the middle of a search (no `stockfish.exe` process is left in Task Manager), the program without Stockfish, an offline test with the network connection cut.

## Open questions

The following have been resolved by default; they can be changed before implementation:

- Moves cannot be taken back. *(decided)*
- Chess clock: 30 min for the user, no increment per move. *(decided; an increment can be added later)*
- The lowest level is 1320; easier levels can be added later with the `Skill Level` option.
