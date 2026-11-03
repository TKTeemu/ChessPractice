# Extending: modes and engines

This guide explains how to add a new **mode** (a way of using the board, such as the free board or playing the computer), a new **engine** (something that chooses moves), a new **opening** for Learn Openings and a new **endgame position** for Endgame Practice. Read [ARCHITECTURE.md](ARCHITECTURE.md) first: the layers, the rule that the model changes only through `MainWindow`, and `refresh()` all still apply.

> Status: implemented as described in [Pelikone_suunnitelma.md](plans/Pelikone_suunnitelma.md) (historical); the differences are listed at the end of this file. Update this file when the code changes.

## Overview

| Package | Layer | Contains | May use tkinter? |
| --- | --- | --- | --- |
| `app/modes/` | Controller | `Mode` subclasses and the `MODES` registry | yes |
| `app/engines/` | Logic | `Engine` subclasses, the UCI client, the background worker and the `ENGINES` registry | no |
| `app/engine_game.py`, `app/computer_game.py` | Logic | Rules for a game against the computer (turns, result, headers) | no |
| `app/commands.py` | Logic | Command names for `Mode.allows()` | no |
| `app/widgets.py` | View | Panel-style `button`, `label`, `checkbox` for a mode's panel | yes |
| `app/openings.py`, `app/learning_game.py` | Logic | The opening book and the rules of an opening-training game | no |
| `assets/openings/` | Data | The opening book, one PGN game per opening | – |
| `app/endgames.py`, `app/endgame_game.py` | Logic | The endgame positions and the rules of an endgame-practice game | no |
| `assets/endgames/` | Data | The endgame positions, one PGN file per difficulty level | – |
| `app/clock.py` | Logic | `ChessClock`: remaining time per side, flag fall | no |

`MainWindow` holds exactly one active mode in `self.mode`. It never checks which mode is active (`isinstance` or `mode.key == …`); it asks the mode questions. That is what keeps new modes from needing changes in `MainWindow`.

## The Mode interface

```python
# app/modes/base.py
@dataclass
class ModeContext:
    """What a mode may use. Passed in by MainWindow; modes do not import MainWindow."""
    root                # tk.Tk
    model               # GameModel: read freely; change through the callables below
    settings            # Settings
    app_dir             # Path of the program folder (assets/, engines/)
    play_move           # play_move(move, from_end=False); from_end: after the last move of the line
    new_game            # new_game(board=None): replace the game, then refresh
    refresh             # refresh(rebuild=False)
    set_flipped         # set_flipped(bool)
    set_mode            # set_mode(key) -> bool
    set_clocks          # set_clocks({color: (text, active, low)}) or set_clocks(None) to hide
    play_sound          # play_sound(kind), e.g. model.END
    take_back           # take_back(color) -> bool: remove moves back to color's previous turn, then refresh

class Mode:
    key = ""        # unique, stored in settings.json, e.g. "board"
    label = ""      # menu text, from strings.py
    show_details = True    # Comment & FEN open by default (until the user toggles it in this mode)
    replaces_game = False  # start() replaces the game: MainWindow offers to save the old one first
    SETTINGS = {}   # the mode's own settings and defaults, keys prefixed with the mode key

    def __init__(self, ctx: ModeContext): self.ctx = ctx

    # Life cycle
    def choose(self) -> dict | None: return {}   # the mode's dialog; None = stay in the previous mode. No side effects.
    def start(self, config: dict): pass          # begin with what choose() returned; the old mode is closed
    def confirm_leave(self) -> bool: return True # before leaving, a new game or exit; only asks
    def leave(self): pass                        # leaving was confirmed, e.g. resign the game
    def deactivate(self): pass                   # release engines, timers, threads

    # Questions MainWindow asks
    def can_move(self, color: chess.Color) -> bool: return True
    def allows(self, command: str) -> bool: return True  # command: a constant from app/commands.py
    def title(self) -> str: ...                        # shown above the board; default: label without "…"
    def subtitle(self) -> str | None: return None      # a smaller line under the title; None = hidden
    def status_text(self) -> str | None: return None   # None = the model's normal status
    def score_text(self) -> str | None: return None    # shown above the board on the right, e.g. material
    def light(self) -> str | None: return None         # success light above the board: "pending" | "success" | "fail"
    def new_game(self) -> bool: return False    # New Game button, File > New Game; True = handled
    def hint_arrows(self) -> list: return []    # [(from_sq, to_sq, "main" | "alt")] suggestion arrows

    # Notifications
    def after_move(self): pass                  # after every successful play_move, before refresh()

    # Optional UI
    def build_panel(self, parent) -> tk.Widget | None: return None   # use app/widgets.py
    def menu_items(self) -> list[MenuItem]: return []   # MenuItem(label, command, enabled)
```

A mode may call model methods (for example `GameModel.set_clock`) inside `after_move()`, because `MainWindow` refreshes the views right after it. Outside `after_move()`, call `ctx.refresh()` after changing anything.

Defaults are chosen so that the base class behaves like the free board (`BoardMode`): everything allowed, nothing extra. A new mode overrides only what differs.

### Command names for `allows()`

`MainWindow` calls `self.mode.allows(name)` before these commands and greys out the matching menu items. The names are constants in `app/commands.py` (a logic-layer module, because the game rules use them too); never write them as string literals, a typo would silently allow or block a command. `tests/test_modes.py` checks that the games' allowed sets contain only known names and that no `allows("…")` literal is left in `app/`. Add a constant (and to `ALL_COMMANDS`) if you add a command a mode might want to block.

| Constant | Command |
| --- | --- |
| `DELETE_LAST` | Ctrl+Z (delete the last move). Blocked in Play vs Computer: moves cannot be taken back. |
| `EDIT_TREE` | Promote / delete variation in the move list menu |
| `PASTE` | Paste PGN/FEN; the FEN field becomes read-only |
| `OPEN` | Open file |
| `NAVIGATE` | ← → Home End ↑ ↓ and clicks in the move list. Blocked in Play vs Computer, also after the game: it is reviewed in Board mode. |
| `EDIT_COMMENT` | Comment field (disabled when not allowed) |
| `TAKE_BACK` | `MainWindow.take_back(color)` (`ctx.take_back`): Take Back in Learn Openings and Endgame Practice (blocked there after a time-out or resignation) |

File > New Game (and the New Game button above the status line) is not a command name: `MainWindow.new_game` first calls `mode.new_game()`, and only if that returns False does it start a free-board game. The game modes (`EngineGameMode.new_game`) call `ctx.set_mode(self.key)`, which shows the mode's dialog again and then goes through the normal switch below ("Resign the game?", the save prompt).

### How MainWindow uses a mode

| Where | Call |
| --- | --- |
| `BoardView._press` (via the `can_move` callback) | `mode.can_move(piece.color)` |
| `play_move()`, after the model accepted the move | `mode.after_move()`, then `refresh(rebuild=True)` and the sound |
| `refresh()` | `mode.hint_arrows()` → `BoardView.set_hints`, `mode.title()`, `mode.subtitle()`, `mode.score_text()` and `mode.light()` above the board, `mode.status_text()`, and `allows(PASTE)` / `allows(EDIT_COMMENT)` for the FEN and comment fields |
| File menu (when opened) | `allows()` greys out Open, Paste |
| Game menu (rebuilt when opened) | one radio item per `MODES` entry, then `mode.menu_items()` |
| Game menu → other mode, or `ctx.set_mode(key)` | `set_mode(key)`, see below |
| Game menu → the active mode | `mode.new_game()` |
| `exit()` | `mode.confirm_leave()`, the save prompt, `mode.leave()`, then `mode.deactivate()` before `root.destroy()` |

`set_mode(key)` runs in this order, so that nothing of the new mode happens before the old one is closed:

1. `new = cls(ctx)`; `config = new.choose()` (the dialog; `None` = cancel). The old mode is still active and its timers still run.
2. `old.confirm_leave()` (e.g. "Resign the game?"; only asks).
3. If `new.replaces_game` and the game has unsaved changes: Save / Don't save / Cancel. Cancel here leaves everything as it was.
4. `old.leave()` (e.g. resigns, which writes the result), then the game is saved if the user chose Save.
5. `old.deactivate()`, `self.mode = new`, `new.start(config)`, the new panel, `refresh(rebuild=True)`.

The program always starts in the first mode of `MODES` (Board). `settings["mode"]` records the last mode used but is not restored, so an unfinished game against the computer is never resumed.

## Recipe: add a mode

Example: a "Solve Puzzle" mode where the user must find the move stored in a PGN.

1. **Create `app/modes/puzzle.py`** with a `Mode` subclass. Set `key` and `label`, override only what differs:

   ```python
   class PuzzleMode(Mode):
       key = "puzzle"
       label = S.MODE_PUZZLE

       def can_move(self, color):
           return color == self.solver_color
       def allows(self, command):
           return command == NAVIGATE   # from app.commands
       def after_move(self):
           ...  # compare with the solution; play the reply with self.ctx.play_move
   ```
2. **Register it** in `app/modes/__init__.py`. The order of the list is the order in the Game menu:

   ```python
   MODES = [BoardMode, VsComputerMode, LearnOpeningsMode, PuzzleMode]
   ```
3. **Text** goes in `strings.py` (`MODE_PUZZLE`, status lines, dialog text).
4. **Settings** the mode remembers go in its `SETTINGS` class variable, prefixed with the mode key (`{"puzzle_level": "easy"}`); `MainWindow` adds them to the defaults (`modes.mode_settings()`). The type of the default decides which values are accepted (`bool`, `int`, `str` or `dict`). Write them in `start(config)`, not in `choose()`.
5. **Dialog and start:** `choose()` shows the dialog and returns a dict (or `None`); `start(config)` does the work. Set `replaces_game = True` if `start` replaces the game. Panel widgets come from `app/widgets.py` (`button`, `label`, `checkbox`); colours and fonts from `theme.py`.
6. **Rules without tkinter** (whether a move solves the puzzle, scoring) go in a logic module, e.g. `app/puzzle.py`, so that pytest can test them.
7. **Tests:** `tests/test_modes.py` checks that every registered mode has a unique `key` and a `label` and that mode settings do not clash. `fake_context()` gives a `ModeContext` with a fake root whose timers the test runs itself (`ctx.root.run_timers()`), so `mode.start(config)` can be tested without windows, as the Play vs Computer and Learn Openings tests do; add a test for the new mode there.

**A mode in which the computer plays** should subclass `EngineGameMode` (`app/modes/engine_mode.py`) instead of `Mode`, and its rules should subclass `EngineGame` (`app/engine_game.py`). `EngineGame` provides the turns (`is_computer_turn`, `can_move`), `allows()` from the class sets `ALLOWED_DURING_GAME` / `ALLOWED_AFTER_GAME`, the status line, the common PGN headers (`EVENT`, Site, Date, Round, White, Black, Result), `engine_failed`, the result and the request ids. `EngineGameMode` provides `engine_choices()` (available engines and notes for the dialog), `make_engine(key)`, `start_engine(engine, level)`, `request_engine_move()`, `play_computer_move(move, delay_ms)` (a move chosen without the engine, e.g. from a book), `cancel_computer_move()`, the polling timer, engine-error handling, `deactivate()`, `new_game()` (the dialog again), `can_move`, `allows`, `status_text` and `open_in_board_mode()`. The subclass implements `choose()` and `start(config)` (create `self.game`, call `start_engine`), extends `_game_over()` if its panel must change, and overrides `computer_turn()` if the computer does not always ask the engine, and `engine_result(result)` if it asks for analyses (`worker.request(…, analyse=True)`) instead of plain moves. `VsComputerMode` uses the default (always the engine); `LearnOpeningsMode` plays from the book first; `EndgameMode` plays the stored defence first and judges the user's moves with analyses.

**A mode with a chess clock** should subclass `TimedGameMode` (`app/modes/timed_mode.py`, itself an `EngineGameMode`) with rules that subclass `ComputerGame`. It provides `start_clock()` (call it in `start`), the clock tick and flag fall, the clocks next to the names, the `[%clk]` comments in `after_move()`, `confirm_leave()` / `leave()` ("Resign the game?", then resign), `resign()` and `_update_buttons()` for the buttons in `self._buttons` (override `_button_states()` to add buttons). `VsComputerMode` and `EndgameMode` use it.

No change to `main_window.py` should be needed. If one is, it is usually a new command name for `allows()` or a new notification; add it to the base class with a neutral default so that the existing modes keep working.

## The Engine interface

```python
# app/engines/base.py
@dataclass(frozen=True)
class Level:
    key: str              # stored in settings.json, e.g. "1350"
    label: str            # shown in the dialog, e.g. "1350"
    elo: int | None       # for the PGN WhiteElo/BlackElo header; None if unknown
    think_time: float     # seconds per move
    options: dict         # engine-specific, e.g. {"UCI_LimitStrength": True, "UCI_Elo": 1350}

class Engine:
    key = ""      # e.g. "stockfish"
    name = ""     # e.g. "Stockfish"

    def __init__(self, settings, app_dir=None): ...   # cheap: starts nothing; app_dir = program folder
    @classmethod
    def available(cls, settings, app_dir) -> bool: ...   # e.g. the exe exists; must be fast, starts nothing
    @classmethod
    def unavailable_reason(cls, settings, app_dir) -> str | None: ...  # shown in the dialog
    def levels(self) -> list[Level]: ...
    def level(self, key) -> Level: ...          # unknown key -> first level
    def start(self): ...                        # start the process / load data
    def new_game(self): ...
    def best_move(self, board: chess.Board, level: Level, stop: threading.Event) -> chess.Move: ...
    can_analyse = False                         # True if analyse() is implemented
    def analyse(self, board, level, stop) -> Analysis: ...   # best move and score: Analysis(move, cp, mate, ponder)
    def close(self): ...                        # must be safe to call twice
```

Rules for implementations:

- `best_move` runs in the worker thread. It gets its own copy of the board and must not touch tkinter, the model or the settings.
- It returns a legal move for `board`. If it cannot, it raises `EngineError`; the mode then shows an error and stops the game.
- It returns soon after `stop` is set (resign, mode change, exit).
- `analyse` follows the same rules. `Analysis.cp` (centipawns) or `Analysis.mate` (mate in n; negative: the side to move is mated) is from the point of view of the side to move in `board`; `ponder` is the expected reply, if the engine gave one.
- `close()` ends any process. Leaving `stockfish.exe` running after the program exits is a bug.

### Existing engines

| Class | File | Notes |
| --- | --- | --- |
| `RandomEngine` | `random_engine.py` | Picks a random legal move. Always available; used in tests and as a fallback. |
| `StockfishEngine` | `stockfish.py` | UCI via `uci.py`. Finds the exe from `settings["engine_path"]`, or else `<app_dir>/engines/stockfish/stockfish.exe` (or the first `stockfish*.exe` there). Reads the option limits from the engine and clamps numeric options such as `UCI_Elo` into them, so a level below the engine's minimum plays at the minimum. Sends options only when they change. Can analyse. If `engines/syzygy/` holds tablebase files, sets `SyzygyPath` to it. |

### UCI client (`uci.py`)

A small client on top of `subprocess`, written instead of `chess.engine` because the vendored python-chess uses an asyncio API that is removed in Python 3.16. Every UCI engine (Stockfish, Komodo Dragon, Lc0, …) can reuse it.

- Start with `creationflags=subprocess.CREATE_NO_WINDOW` so no console window flashes under `pythonw`.
- A reader thread puts each output line in a `queue.Queue`; the client waits for `uciok`, `readyok` and `bestmove` with a timeout.
- `go movetime <ms>`; on `stop`, send `stop` and wait for `bestmove`. `search()` also returns the last exact score of the `info … score cp|mate …` lines (`parse_score`; bound scores are ignored) and the ponder move, as an `Analysis`; `go()` returns just the move.
- `close()`: `quit`, wait 1 s, then `kill()`.

### The worker (`worker.py`)

`EngineWorker` owns one engine and one thread, and starts the engine (`start()`, `new_game()`) on the first request, so the process exists only while a game is played. `request(board, level, request_id, analyse=False)` starts a search on a copy of the board; the result `(request_id, move, Analysis or EngineError)` goes into a queue. With `analyse=True` the result is an `Analysis` if the engine `can_analyse`, otherwise just the move. The mode reads it with `poll()` from a `root.after(50, …)` timer on the main thread and ignores results whose `request_id` is no longer current (`EngineGame.is_current`). `cancel()` sets the search's `stop` event; a request cancelled before it started is skipped. `close()` stops the thread and the engine process.

## The chess clock (`clock.py`)

`ChessClock(seconds_white, seconds_black, now=time.monotonic)` has no tkinter and no timer of its own: `start(color)`, `switch()` after each move, `remaining(color)`, `flagged()` and `stop()`. `format_time(seconds)` gives the display text (`29:41`, or `0:42.3` under a minute). The time source `now` is a parameter, so tests can pass a fake clock instead of waiting. The mode shows the clocks with `ctx.set_clocks()` and checks for a flag fall from a `root.after(100, …)` tick; the displayed time is always computed from `now()`, never by counting ticks. A new timed mode should reuse `ChessClock` instead of writing its own.

`ComputerGame` (in `computer_game.py`) uses the clock: the clock starts with the first move of the game, and after each move the mover's remaining time is stored in the move's comment as `[%clk 0:29:41]` (`GameModel.set_clock`). Such `[%…]` commands stay in the PGN but are hidden in the move list and the comment field (`model.visible_comment`); editing a comment keeps them.

## Recipe: add an engine

Example: another UCI engine.

1. **Create `app/engines/<name>.py`** with an `Engine` subclass. For a UCI engine, use `UciClient` from `uci.py` and override only how the exe is found and the level table.
2. **Define levels as data**, not code: a list of `Level` objects at the top of the file. Changing levels must not need changes elsewhere.
3. **Register it** in `app/engines/__init__.py`:

   ```python
   ENGINES = [StockfishEngine, OtherEngine, RandomEngine]
   ```
   The dialog shows the engines whose `available()` is True, in this order.
4. **Files:** put the exe under `engines/<name>/`. Follow the F-Secure checklist below.
5. **Licence:** add the engine's name and licence to `S.ABOUT_TEXT` and `NOTICE`.
6. **Tests:** add tests to `tests/test_engines.py` like the Stockfish ones (mate in one, `close()` ends the process, `close()` twice). Skip with `pytest.skip` when `available()` is False. A UCI engine's protocol handling can be tested against `tests/fake_uci.py`, a tiny UCI engine written in Python.

## Recipe: add an opening

Learn Openings reads every `*.pgn` file in `assets/openings/`; no code changes are needed.

1. Add a game to one of the files (or a new file). One game is one opening; its move tree is the theory:

   ```pgn
   [Event "Réti Opening"]
   [Key "reti"]
   [Group "Flank openings"]
   [GroupOrder "2"]
   [ECO "A04-A09"]
   [Side "white"]

   1. Nf3 {A flexible move: White does not yet commit to a pawn structure.}
   1... d5 (1... Nf6 2. c4 g6) 2. g3 {Line: King's Indian Attack} ...
   ```

   | Header | Meaning |
   | --- | --- |
   | `Event` | Name shown in the dialog. |
   | `Key` | Unique, stored in settings (`learn_opening`). Never change an existing key. |
   | `Group`, `GroupOrder` | Group in the dialog; groups are sorted by the first `GroupOrder` seen. Openings keep their file order. |
   | `ECO` | Shown next to the name (`A04-A09` is shown as A04–A09). |
   | `Side` | `white` or `black`: the side that makes the opening ("You play: the opening"). |
   | `Plies` | Optional: how many half-moves define the opening in the list (default 1, e.g. 3 for `1. d4 d5 2. c4`). |

2. **Variations:** the first continuation is the main line; the computer picks it most often when *Vary the computer's replies* is on (weights 2^(n−1), …, 2, 1) and always when it is off. Use standard English SAN (N, B, R, Q).
3. **Comments:** a comment after a move explains it and is copied into the game when the move is played. `{Line: Reversed Sicilian}` names the variation from that move on (shown as *Line:* in the panel); text after a semicolon is the explanation: `{Line: From's Gambit; Black gives a pawn.}`.
4. Run `python -m pytest`: `tests/test_openings.py` loads every file (illegal moves, a missing or duplicate `Key`, or a bad `Side` are reported) and checks the start moves of the openings listed in it; add new openings to its `EXPECTED` table.

The book can also be edited in Board mode: open the PGN file, change the moves and comments, and save.

## Recipe: add an endgame

Endgame Practice reads every `*.pgn` file in `assets/endgames/` (one file per level, `level1.pgn` … `level5.pgn`, by convention); no code changes are needed.

1. Add a game to the file of its level. One game is one position; the side to move is the user's side:

   ```pgn
   [Event "Saavedra Position"]
   [Key "saavedra"]
   [Difficulty "5"]
   [Goal "win"]
   [Composer "Fernando Saavedra (after Georges Barbier)"]
   [Source "Glasgow Weekly Citizen"]
   [Year "1895"]
   [SetUp "1"]
   [FEN "8/8/1KP5/3r4/8/8/8/k7 w - - 0 1"]

   {White's pawn is one step from queening, but the rook keeps checking.}
   1. c7 Rd6+ 2. Kb5 Rd5+ 3. Kb4 Rd4+ 4. Kb3 Rd3+ 5. Kc2 Rd4
   6. c8=R $1 (6. c8=Q $2 {Rc4+ 7. Qxc4 is stalemate.} 6... Rc4+ 7. Qxc4) 6... Ra4 7. Kb3 *
   ```

   | Header | Required | Meaning |
   | --- | --- | --- |
   | `Event` | yes | Name of the position, shown above the board. |
   | `Key` | yes | Unique and permanent. Never change an existing key. |
   | `Difficulty` | yes | 1–5. |
   | `DifficultyName` | in one game per level | Name of the level in the dialog (*Basic mates* …). |
   | `Goal` | yes | `win` or `draw`, for the side to move. |
   | `SetUp`, `FEN` | yes | The start position. |
   | `Composer`, `Source`, `Year` | no | Shown under the title; only when verified. Nothing known: *Classic endgame position*. |

2. **The move tree:** the main line is the solution and the computer's preferred defence. A user-side variation without a NAG is an equally good move; a variation whose first move has `$2` (?) or `$4` (??) is a known wrong try: the light turns red at once and the move's comment is shown. Computer-side variations are other defences; the computer picks the main line most often (weights 2^(n−1), …, 2, 1). Where a correct line ends, the position counts as solved (green light); after that, and anywhere outside the tree, Stockfish plays and judges. Comments explain moves; write them yourself rather than copying them from books.
3. Run `python tools\check_endgames.py --key <key>`: it checks the goal and every solution move with Stockfish, using the same rule as the game. Then `python -m pytest`: `tests/test_endgames.py` loads every file (illegal moves, a duplicate `Key`, a bad `Difficulty`, `Goal` or `FEN` are reported) and requires at least 15 positions per level.

## Adding a level

Edit the level table in the engine's file. Keep the `key` of existing levels unchanged, because `settings.json` stores it; an unknown stored key falls back to the engine's first level.

## F-Secure checklist for an engine exe

1. Download only from the engine's official site or release page.
2. Unpack into a new, empty folder; check the SHA-256 (`Get-FileHash`) against the published value.
3. `Unblock-File` the exe.
4. Start it once from the program and check the F-Secure event log.
5. If an exception is needed, add only that exe, not the whole program folder.
6. Do not add installers, services, `.dll` search paths or anything that writes outside the program folder.

## Libraries

New code should use only the standard library and the packages already listed in the README. If a new library is unavoidable:

- Pure Python and specific to this program → `python -m pip install --target vendor <package>`, and add it with a fixed version to `requirements-vendor.txt`.
- A general compiled package the program needs → the system Python, added to `requirements-global.txt` (`tools/make_dist.py` then puts its wheel in the zip, and `Asenna.bat` installs it).
- A development tool → the system Python, added to `requirements-dev.txt`.
- Add a missing-package message for it to `REQUIREMENTS` in `shakkilauta.pyw`, and its licence to `NOTICE`.
- Never a venv (it creates `python.exe` copies), and avoid packages whose command-line tools create `.exe` launchers; run tools as `python -m <module>`.

## Differences from the plan

- The default level is 1320 (the lowest), not 1350: the level table in the plan has no 1350 level, and an unknown key falls back to the first level anyway.
- Levels below the engine's `UCI_Elo` minimum are not dropped; the Elo is clamped to the minimum when the option is sent.
- `ModeContext.set_game` became `new_game(board=None)`, and `app_dir`, `set_clocks`, `play_sound` and `take_back` were added. `Mode.needs_setup` and `Mode.position_changed` were not needed; `Mode.confirm_leave`, `Mode.leave` and `Mode.new_game` were added, and the plan's `activate()` was split into `choose()` and `start(config)` so that the old mode is closed before the new one starts.
- `mode.after_move()` runs before `refresh()`, so that what it changes (clock comments, the result) is shown at once.
- In Play vs Computer, Open, Paste and the FEN field are disabled; switch to Board first. File > New Game asks "Resign the game?" and shows the dialog again.
- The engine `Random moves` is registered after Stockfish, so a game can be played without Stockfish.
- New setting `vs_start` remembers the dialog's "Start from" choice. The `vs_…` and `learn_…` settings live in the modes' `SETTINGS`, not in `settings.DEFAULTS`.

Endgame Practice, compared with [Loppupeli_suunnitelma.md](plans/Loppupeli_suunnitelma.md):

- The mode is called *Endgame Practice…* (key `end_practice`), and the success light is above the board on the right, in place of the material score, as decided in the plan's open questions.
- `Mode.light()` was added for the light, and `EngineGameMode.engine_result()` so that a mode can receive analyses. `Engine.analyse` takes a `Level` (for the engine options) instead of a think time.
- Judging: a move is a mistake only if the score falls below the limit (+150 cp for a win, −300 cp for a draw) *and* drops by at least 100 cp from the score before the move (`is_mistake`). Stockfish's NNUE scores some won endings low (bishop and knight about +180), so a fixed limit alone would turn correct moves red. When the score before the move is not known, it is analysed first.
- The engine's ponder move is used as the suggestion off the solution, so a separate analysis is needed only at the start or right after the solution ends.
- Positions: the textbook positions of levels 1–3 and Lasker–Reichhelm were set up by hand; their solution lines, where not written by hand, are Stockfish's main lines. Apart from Saavedra, Réti and Lasker–Reichhelm, levels 4 and 5 are positions found by a search with Stockfish (random realistic material, exactly one move keeps the goal; on level 5 at least twice in a row), not master games or published studies. Their source is empty, so they show *Classic endgame position*.

Learn Openings, compared with [Avausteoria_suunnitelma.md](plans/Avausteoria_suunnitelma.md):

- `details_open` is a dict `{mode key: open}` that also stores modes where the section was closed, so that `Mode.show_details` can be the default for modes not yet toggled.
- New Game in Learn Openings does not ask a separate question; the opening dialog opens, and choosing Start asks to save the current game if it has changes (Cancel keeps it, and the game goes on).
- *Theory: n/m* counts the user's book moves out of the user's moves played in a book position. A move order that transposes back into the book counts as a book move.
- The deviation arrows are shown on the current position (after the computer's reply) until the user's next move.
- New optional PGN header `Plies` for the start moves shown in the dialog.
