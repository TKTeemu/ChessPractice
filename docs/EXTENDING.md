# Extending

How to add to the program. [ARCHITECTURE.md](ARCHITECTURE.md) explains the layers and rules these recipes rely on.

## What to change

| You want to add | Change | Python code needed? |
| --- | --- | --- |
| An opening | `assets/openings/*.pgn`, `tests/test_openings.py` | No: [format](DATA_FORMATS.md#opening-book) |
| An endgame position | `assets/endgames/level*.pgn` | No: [format](DATA_FORMATS.md#endgame-positions) |
| An engine strength level | The level table in the engine's file | One line |
| A setting | `settings.DEFAULTS` or a mode's `SETTINGS` | [Recipe](#add-a-setting) |
| A board theme or piece set | `theme.py`, `strings.py`, `pieces.py` | [Recipe](#add-a-board-theme-or-piece-set) |
| A sound | `model.py`, `tools/make_sounds.py` | [Recipe](#add-a-sound) |
| A blockable command | `commands.py`, `main_window.py` | [Recipe](#add-a-command-a-mode-can-block) |
| A way of using the board | `app/modes/`, usually a rules module | [Recipe](#add-a-mode) |
| A chess engine | `app/engines/` | [Recipe](#add-an-engine) |
| A library | `requirements.txt` or `requirements-dev.txt` | [Rules](#add-a-library) |

## Add a mode

A new mode should need no change in `main_window.py`. If it seems to, the usual answer is a new command name or a new hook on `Mode` with a neutral default, so that the existing modes keep working.

### 1. Pick a base class

| The mode … | Subclass | Rules object | Example |
| --- | --- | --- | --- |
| has no computer opponent | `Mode` | your own, if any | `BoardMode` |
| has a computer opponent, no clock | `EngineGameMode` | `EngineGame` subclass | `LearnOpeningsMode` |
| has a computer opponent and a clock | `TimedGameMode` | `ComputerGame` subclass | `VsComputerMode`, `EndgameMode` |

The base classes' defaults behave like the free board, so override only what differs.

### 2. Write the rules without tkinter

Put them in `app/<name>_game.py` so that pytest can test them without a window. An `EngineGame` subclass sets `EVENT` and the two `ALLOWED_*` sets, and implements `move_played(board)`. If moves can be taken back, it also extends `took_back(board)`.

```python
class PuzzleGame(EngineGame):
    EVENT = S.PUZZLE_EVENT
    ALLOWED_DURING_GAME = frozenset({NAVIGATE})
    ALLOWED_AFTER_GAME = frozenset({NAVIGATE, EDIT_COMMENT})

    def move_played(self, board):
        outcome = game_outcome(board)
        if outcome is not None:
            self._finish(outcome.result(), outcome_text(outcome), "normal")
```

### 3. Write the mode

```python
class PuzzleMode(EngineGameMode):
    key = "puzzle"
    label = S.MODE_PUZZLE
    SETTINGS = {"puzzle_level": "1320"}

    def choose(self):
        available, _ = self.engine_choices()
        return {"engine": available[0].key}   # a real mode shows a dialog from dialogs.py here

    def start(self, config):
        engine = self.make_engine(config["engine"])
        level = engine.level(self.ctx.settings["puzzle_level"])
        self.game = PuzzleGame(chess.WHITE, engine.name)
        self.start_game()                     # replaces the game on the board
        self.ctx.set_flipped(False)
        self.start_engine(engine, level)      # the process starts with the first request
        self._next_turn()                     # the computer moves now if it is its turn

    def after_move(self):
        self.game.move_played(self.ctx.model.board)
        if self.game.over:
            self._game_over()
        else:
            self._next_turn()
```

`EngineGameMode` has no `after_move` of its own, so an untimed mode must write one as above. `TimedGameMode` has one, and also needs `self.start_clock()` in `start`.

To have the computer choose some moves without the engine, override `computer_turn()` and call `play_computer_move(move, delay_ms)` or `request_engine_move()`. To receive scores, request with `worker.request(..., analyse=True)` and override `engine_result(result)`; see `EndgameMode`.

### 4. Register it and add its text

Add the class to `MODES` in `app/modes/__init__.py`. Put its text in `strings.py` (`MODE_PUZZLE`, status lines, dialog text). `key` must be unique and is permanent, because `settings["details_open"]` stores it.

### 5. Test it

- Rules: a `tests/test_<name>_game.py` without Tk, passing a fake `now` if there is a clock.
- Mode: `fake_context()` in [tests/test_modes.py](../tests/test_modes.py) gives a `ModeContext` with a `FakeRoot` whose timers the test runs itself, so `mode.start(config)` runs without windows.
- With the window: `make_window` and the `answers` fixture in [tests/test_main_window.py](../tests/test_main_window.py) run the real `MainWindow` with dialogs replaced. `set_mode(key, config)` skips the dialog.
- Add the rules class to `test_allowed_command_sets_use_known_names`, which lists its classes by hand.

### The `Mode` interface

[app/modes/base.py](../app/modes/base.py) is the authority. What to keep in mind for each hook:

| Hook | Called | Keep in mind |
| --- | --- | --- |
| `key`, `label`, `SETTINGS` | Class attributes | Setting names start with the first word of `key` and an underscore (`end_` for `end_practice`). A test checks this. |
| `show_details` | Panel build | Comment & FEN open by default. |
| `replaces_game` | `set_mode` | Set it if `start` replaces the game; the user is then offered a save. `EngineGameMode` sets it. |
| `takes_back`, `can_take_back`, `take_back` | Button and Ctrl+Z | With `takes_back`, Ctrl+Z calls `take_back` instead of deleting the last move. |
| `back_takes_back` | ← and ◀ | At the last move they call `take_back` whenever `can_take_back()`; otherwise they browse. |
| `choose` | First in a switch | No side effects, since the old mode is still running. Write remembered choices in `start`. Returning `None` cancels. |
| `start(config)` | After the old mode closed | The panel already exists. |
| `confirm_leave` | Before leaving | Only asks. False cancels. |
| `leaving_changes_game`, `leave` | Before leaving | `leave` may change the game (a resignation); say so in `leaving_changes_game`, so that the save prompt is offered. |
| `deactivate` | Leaving, exit | Call `super()`. Release workers. Not preceded by `leave` at exit. |
| `can_move`, `allows`, `title`, `subtitle`, `status_text`, `score_text`, `light`, `light_text`, `hint_arrows` | Any time | No side effects. `hint_arrows` runs on every status update, so keep it cheap. |
| `new_game` | New Game button, Ctrl+N | Return True if handled. Game modes call `ctx.set_mode(self.key)`, which shows the dialog again. |
| `after_move` | After the model accepted a move, before the views update | No `ctx.update_status()` needed here. Do not call `ctx.play_move` directly from it; use `play_computer_move`, which goes through a timer. |
| `position_changed` | Whenever the position or tree changed | |
| `hints_shown(hints)` | After the arrows were put on the board | The place for side effects of showing them. |
| `build_panel(parent)` | Before `start`, **and again** when the engine location changes | May run with no game, or mid-game. Create widgets from current state, and guard updates (`if not self._labels or self.game is None`). Use `widgets.py`. |
| `menu_items` | Game menu opens | `MenuItem(label, command, enabled)`. |
| `_schedule(name, ms, callback)` | Your timers | Replaces a waiting timer of the same name. `deactivate` cancels them all. |

Outside `after_move`, call `ctx.update_status()` after changing what a mode reports. Change the game only through `ctx.model` methods (`set_comment`, `set_clock`, `set_headers`, `clear_result`) or `ctx.new_game`. Headers passed to `ctx.new_game` do not count as a modification.

### Traps in game modes

- **Use `_tip()` for game logic, not `model.board`.** The user may be browsing earlier moves. Engine moves use `play_move(move, from_end=True)` for the same reason.
- **`EndgameGame.analysed` assumes the user moves first:** `ply % 2 == 0` means it is the user's turn. It holds because the user plays the side to move in the position's FEN, and the board is created fresh from that FEN. A new game type where the computer moves first needs its own parity.
- **New commands are blocked in game modes by default**, because `EngineGame.allows` is a membership test on the `ALLOWED_*` sets.
- **A mode object is replaced on every restart**, so anything that must survive a restart goes in `ctx.assets` or settings.
- **`EngineGameMode.open_in_board_mode` names the key `"board"`.** Changing that key means changing this call and tests as well.

## Add a command a mode can block

1. Add a constant to [app/commands.py](../app/commands.py) and to `ALL_COMMANDS`. Never write command names as string literals.
2. In `MainWindow`, guard the command with `if not self.allowed(NAME): return`, which also explains the block on the status line. Register a menu item with `guarded(...)` in `_build_menu`, so that it greys out.
3. Add the constant to the `ALLOWED_*` sets of each game class that should allow it.

| Constant | Controls |
| --- | --- |
| `DELETE_LAST` | Ctrl+Z, in a mode without `takes_back` |
| `EDIT_TREE` | Promote and delete in the move list menu; restoring deleted moves (Ctrl+Y) |
| `PASTE` | Paste; typing a FEN (the FEN field is read-only otherwise) |
| `OPEN` | File > Open |
| `NAVIGATE` | Arrow keys, Home, End, the navigation buttons, move list clicks |
| `EDIT_COMMENT` | The comment field |
| `TAKE_BACK` | `MainWindow.take_back`, used by Take Back in game modes |

## Add an engine

The contract is in [app/engines/base.py](../app/engines/base.py):

- `available` and `unavailable_reason` are fast and start nothing. `__init__` is cheap too; the process starts in `start`, on the worker thread, at the first request.
- `best_move(board, level, stop)` runs on the worker thread with its own board copy. It must not touch tkinter, the model or settings. It returns a legal move or raises `EngineError`, and returns soon after `stop` is set.
- `analyse` follows the same rules and returns an `Analysis`. `cp` and `mate` are from the side to move's point of view. Set `can_analyse = True` if it is implemented.
- `close` ends any process, and is safe to call twice and from any thread.

Steps:

1. Create `app/engines/<name>.py`. Define levels as a data table at the top, as `Level(key, label, elo, think_time, options)`.
2. For a UCI engine, use `UciClient`. `StockfishEngine` currently holds the exe lookup and option clamping, and its `settings["engine_path"]` and messages are Stockfish's. Move the shared parts into a `UciEngine` base when a second UCI engine arrives, rather than copying them.
3. Add the class to `ENGINES` in [app/engines/\_\_init\_\_.py](../app/engines/__init__.py). Order matters:
   - Dialogs list available engines in this order.
   - Board analysis and Endgame Practice use the first one with `can_analyse`.
   - `RandomEngine` stays in the list: `EndgameMode._engine` relies on at least one engine always being available.
4. Put the exe under `engines/<name>/` and follow the [antivirus checklist](MAINTENANCE.md#antivirus-checklist-for-an-engine-exe). `.gitignore` already excludes `engines/**/*.exe`.
5. Add the licence to `S.ABOUT_TEXT` and `NOTICE`. Check what the licence requires when the exe is given to others.
6. Add tests to [tests/test_engines.py](../tests/test_engines.py), like the Stockfish ones: mate in one, `close` ends the process, `close` twice. Skip with `pytest.skip` when `available()` is False. Test protocol handling against [tests/fake_uci.py](../tests/fake_uci.py), which needs no real engine.

**A new strength level** is a line in the level table. Keep existing keys unchanged, because `settings.json` stores them; an unknown key falls back to the first level. `StockfishEngine` clamps integer options into the limits the engine reports, so a level below its `UCI_Elo` minimum plays at the minimum.

## Add a setting

1. Add the key and default: a mode's `SETTINGS` if one mode owns it, otherwise `DEFAULTS` in [app/settings.py](../app/settings.py).
2. Choose the default's type carefully. On load, a stored value of a different type is ignored, so changing a setting's type later resets it for users. Keys no longer in the defaults are dropped from the file at the next save.
3. Read and write with `settings[key]`. Assignment is what sets `dirty`, so **replace a dict, never change it in place**: `settings["end_progress"] = {**progress, key: state}`.
4. A choice in a dialog is written in `start(config)`, not in `choose()`. `VsComputerMode` and `LearnOpeningsMode` list theirs in `CHOICES`.
5. Add it to the [settings table](DATA_FORMATS.md#settingsjson).

`Settings.__setitem__` does not check keys or types; only loading does. A mistyped key is not caught when written, but it is lost when the file is read back.

## Add a board theme or piece set

- **Board theme:** add colours to `BOARD_THEMES` in `theme.py` and the label to `BOARD_THEMES` in `strings.py`, under the same key.
- **Piece set:** add the label to `PIECE_SETS` in `strings.py`. `PieceImages._make_photo` treats `"cburnett"` as SVG and everything else as Unicode glyphs, and `_svg_source` names the `cburnett` folder, so a new SVG set needs a change in both. Add the artwork's licence to `NOTICE` and `S.ABOUT_TEXT`.

Our own artwork or freely licensed artwork only; see [DECISIONS.md](DECISIONS.md#platform-and-tools).

## Add a sound

Add the kind to the constants in `model.py`, in the priority order of `event_for`, which picks the first match. Generate the WAV in `tools/make_sounds.py`. `Sounds.play` looks for `assets/sounds/<kind>.wav` and silently skips a missing file.

## Add a library

Prefer the standard library and the packages already used. If one is unavoidable:

| Kind | Listed in |
| --- | --- |
| Needed to run the program | `requirements.txt`, pinned; `make_dist.py` then packs its wheel |
| Development tool | `requirements-dev.txt`, pinned |

Run `Install.bat dev` to install it into `.venv`. For a library the program needs, also add a message to `REQUIREMENTS` in `chessboard.pyw`, add it to the import checks in `Install.bat`, and add its licence to `NOTICE`. Avoid packages that need their `.exe` launchers; run tools as `python -m <module>`. The reasons are in [DECISIONS.md](DECISIONS.md#platform-and-tools).

## Before you finish

- [ ] `.venv\Scripts\python.exe -m pytest` passes, with one expected xfail.
- [ ] Logic-layer changes import no tkinter.
- [ ] New text is in `strings.py`, colours in `theme.py`, command names in `commands.py`.
- [ ] No permanent identifier changed ([list](DATA_FORMATS.md#permanent-identifiers)).
- [ ] Run the [manual checks](MAINTENANCE.md#manual-checks) that apply.
- [ ] The docs are updated ([which ones](MAINTENANCE.md#keeping-the-docs-right)).
