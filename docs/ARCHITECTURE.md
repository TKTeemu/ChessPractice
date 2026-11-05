# Architecture

How the program is put together and the rules that keep it working. Read this before changing the code. To add something, continue with [EXTENDING.md](EXTENDING.md).

If this file and the code disagree, the code is right; fix this file in the same change.

## Layers

Dependencies point downwards only.

```
Controller    main_window.py  file_commands.py  modes/
                   |                |              |
Views         board_view.py  movelist_view.py  dialogs.py  widgets.py  pieces.py
                   |
Logic         model.py  fileio.py  settings.py  assets.py  commands.py  clock.py
and services  engine_game.py  computer_game.py  learning_game.py  endgame_game.py
              openings.py  endgames.py  engines/  sounds.py  strings.py  theme.py
                   |
Libraries     python-chess   Pillow   Tk   Stockfish (child process)
```

- **Logic and services must not import tkinter.** That is what lets game rules be tested without a window. No test enforces this, so check the imports when you review a change.
- **Views** read the model and report user actions through callbacks. They make no game decisions.
- **Modes** are controllers: they decide what the user may do and connect a game's rules to the window. A game's rules go in the logic layer, not in the mode.
- **`MainWindow` never asks which mode is active.** It asks the active mode questions. The one known concrete reference is `StockfishEngine.default_dir` for the engine location dialog.

## Where things are

| Path | Contents |
| --- | --- |
| [chessboard.pyw](../chessboard.pyw) | Entry point: logging, the requirements check, the error reporter, DPI awareness, `MainWindow`. |
| [Chessboard.bat](../Chessboard.bat), [Install.bat](../Install.bat), [INSTALL.txt](../INSTALL.txt) | Start the program; set it up; instructions for end users. |
| `app/` | Application code, described below. |
| `assets/` | Data read at run time: `openings/`, `endgames/`, `pieces/cburnett/`, `sounds/`. |
| `engines/stockfish/` | The downloaded `stockfish.exe` (not in git), `Copying.txt`, `README.txt`. |
| `engines/syzygy/` | Optional tablebases (not in git). |
| `tests/` | The pytest suite, described in [MAINTENANCE.md](MAINTENANCE.md#tests). |
| `tools/` | Development scripts, described in [MAINTENANCE.md](MAINTENANCE.md#tools). |
| `.venv/` | The Python environment with Pillow and python-chess, created by `Install.bat` (not in git, do not edit). |
| `settings.json`, `error.log`, `Games/`, `dist/` | Created when the program or tools run (not in git). |

### Modules in `app/`

| Module | Responsibility |
| --- | --- |
| `main_window.py` | `MainWindow`: creates the model and views; layout, menus and shortcuts; holds the active mode; brings the views up to date. |
| `file_commands.py` | `FileCommands`: open, save, paste and the clipboard. `confirm_discard` is the only place that offers to save a game before replacing it. |
| `modes/base.py` | The `Mode` interface, `ModeContext` and `MenuItem`. The authority on what each hook means. |
| `modes/__init__.py` | The `MODES` registry. Its order is the Game menu's order, and the first mode is the start mode. |
| `modes/board.py` | `BoardMode`: the free board, with optional engine analysis. |
| `modes/engine_mode.py` | `EngineGameMode`: the base of modes where the computer plays (worker, polling, delayed moves, take-back, game over). |
| `modes/timed_mode.py` | `TimedGameMode`: adds the clock tick, flag fall, `[%clk]` comments and resigning. |
| `modes/vs_computer.py`, `learn_openings.py`, `endgames.py` | The three game modes: dialog, panel and how the computer chooses its move. |
| `model.py` | `GameModel`: the game tree (a python-chess `Game`), the current node and `board`, moves, navigation, tree editing, comments, `modified`. Also `event_for`, `position_key` and `visible_comment`. |
| `engine_game.py` | `EngineGame`: turns, allowed commands, status line, common PGN headers, result, request ids. |
| `computer_game.py` | `ComputerGame(EngineGame)`: clock, material score, time-control headers, result by time or resignation. |
| `learning_game.py` | `LearningGame(EngineGame)`: book or engine reply, deviations, theory count, opening phase. |
| `endgame_game.py` | `EndgameGame(ComputerGame)`: stored defence, judging moves, success light. `is_mistake` is shared with `tools/check_endgames.py`. |
| `openings.py` | `OpeningBook`, `Opening`, `OpeningLine`, `BookMove`. |
| `endgames.py` | `EndgameCollection`, `EndgameSample`, `SolutionTree`, `SolutionMove`, `EndgameDeck`. |
| `assets.py` | `Assets`: loads the book and positions on first use and keeps them, and the deck, for the whole run. |
| `clock.py` | `ChessClock` and `format_time`, with a replaceable time source. |
| `commands.py` | Command names for `Mode.allows`. |
| `engines/` | `Engine`, `Level`, `Analysis`, `EngineError` (`base.py`), the `ENGINES` registry, `StockfishEngine`, `RandomEngine`, `UciClient` (`uci.py`), `EngineWorker` (`worker.py`). |
| `fileio.py` | PGN and FEN reading and writing, position validation, atomic writes, `load_pgn_folder`. |
| `settings.py` | `Settings` and the program-wide `DEFAULTS`. |
| `sounds.py`, `strings.py`, `theme.py` | WAV playback; all user-visible text; colours, fonts and board themes. |
| `board_view.py` | `BoardCanvas` (geometry, squares) and `BoardView` (drag, click, promotion picker, animation, the user's arrows and marks, the suggestion-arrow layer). |
| `movelist_view.py` | `MoveListView`: variations in a Text widget, right-click menu. |
| `dialogs.py` | Game picker, Play vs Computer, Learn Openings, Endgame Practice and engine location dialogs. |
| `pieces.py`, `widgets.py` | Piece images (they need a Tk root, so this is a view); panel-styled `button`, `label`, `checkbox`, `scrollbar`, and `light`. |

### Mode and game classes

Each game mode pairs a controller with a rules object held in `self.game`:

```
Mode                                       (controller, may use tkinter)
├── BoardMode                              no rules object
└── EngineGameMode                         EngineGame
    ├── LearnOpeningsMode                  LearningGame(EngineGame)
    └── TimedGameMode                      ComputerGame(EngineGame)
        ├── VsComputerMode                 ComputerGame
        └── EndgameMode                    EndgameGame(ComputerGame)
```

## Rules the structure relies on

Breaking one of these usually produces a bug far from the change. The last column names the test that guards the rule, where there is one.

| # | Rule | Why | Guard in `tests/` |
| --- | --- | --- | --- |
| 1 | The game tree and its headers change only through `GameModel` methods. | They set `modified`; a direct write leaves a stale file on disk with no save prompt. | `test_modes_do_not_write_to_the_game_directly` |
| 2 | After a change, call `position_changed()` if the position or tree changed (`rebuild=True` if the tree did), otherwise `update_status()`. | `position_changed` reloads the comment field and drops a piece being moved. `update_status` leaves them alone, so it is safe while the user is busy. | `test_a_status_update_keeps_the_selection_and_the_arrows`, `test_toggling_suggestions_keeps_the_comment_being_typed` |
| 3 | Call `save_comment()` before changing the node. | The comment field belongs to the node it was loaded from, and typed text is lost otherwise. | same as rule 2 |
| 4 | Legality comes from python-chess. The program generates no moves itself. | One tested source for the rules. | `test_model.py` |
| 5 | `Mode` question methods (`can_move`, `allows`, `title`, `status_text`, `hint_arrows`, …) have no side effects. | They are asked at any time and any number of times. React in a notification instead, as `hints_shown` does for the hint count. | `test_hints_are_counted_once_per_position` |
| 6 | tkinter is used only on the main thread; an `Engine` only on its worker thread (`close()` excepted). | Results cross through the worker's queue, read by a `root.after` poll. | none |
| 7 | A computer reply is accepted only if its request id is still current. | The game may have moved on: take-back, resignation, new game. `EngineGame.new_request` and `_finish` invalidate old ids. | `test_computer_game.py`, `test_endgame_game.py` |
| 8 | A mode's timers go through `Mode._schedule`. | `deactivate` cancels them all, so nothing fires into a closed mode. | `test_deactivate_cancels_pending_computer_moves` |
| 9 | Nothing of a new mode happens until the old mode is closed. Only `choose()` runs earlier, and it has no side effects. | The order is in [Switching modes](#switching-modes). | `test_main_window.py` |
| 10 | Text goes in `strings.py`, colours and fonts in `theme.py`, settings in `DEFAULTS` or a mode's `SETTINGS`, command names in `commands.py`. | Each can be changed in one place, and a mistyped command name would silently allow or block a command. | `test_no_command_names_as_string_literals`, `test_allowed_command_sets_use_known_names`, `test_mode_settings_are_prefixed_and_do_not_clash` |
| 11 | Saved keys never change meaning: mode, engine and level keys, opening and endgame `Key`s. | They are stored in `settings.json`. See [DATA_FORMATS.md](DATA_FORMATS.md#permanent-identifiers). | none |
| 12 | Files are written through a temporary file, and a game is never saved over a file holding games that were not loaded. | A crash or a Save must not lose data. `FileCommands.path` stays `None` for a game picked from a multi-game file or from one with skipped games. | `test_a_file_with_a_skipped_game_is_not_overwritten_by_save`, `test_fileio.py` |
| 13 | Stockfish runs only while it is needed, and closes with its mode. | Board mode without analysis, book moves and stored defences start no process, and a leftover `stockfish.exe` is a bug. | `test_analysis_is_off_by_default_and_starts_no_engine`, `test_engines.py` |
| 14 | No network use at run time, and no new exe files. | See [DECISIONS.md](DECISIONS.md). | none |

## How things flow

### Startup

`chessboard.pyw` starts logging, and stops with a message box if the Python version is wrong or a requirement cannot be imported. `MainWindow.__init__` then builds `Settings` (with `mode_settings()`), repairs hand-edited values, and creates the model, `FileCommands`, `ModeContext` and the first mode in `MODES`. An unfinished game is never resumed.

### A move

```
mouse -> BoardView -> on_move(from, to, promotion) = MainWindow.user_move
      -> MainWindow.play_move(chess.Move)
      -> GameModel.play(move)            -> event kind, or None if illegal
      -> mode.after_move()               before the views are updated
      -> MainWindow.position_changed(rebuild=True)
      -> Sounds.play(event)
```

`GameModel.play` steps into the move if it already exists at the current node, and otherwise adds a variation. Illegal moves redraw the board and play the "illegal" sound.

### A computer move

```
EngineGameMode._next_turn -> computer_turn()
    -> request_engine_move -> EngineWorker.request(tip, level, game.new_request())
worker thread: engine.best_move or analyse -> (request id, result) into a queue
main thread, every 50 ms: EngineGameMode._poll -> game.is_current(id)?
    -> engine_result(result) -> MainWindow.play_move(move, from_end=True)
```

From `play_move` on, it is the same path as a user move. Modes differ only in `computer_turn` and `engine_result`:

- **Play vs Computer:** always the engine.
- **Learn Openings:** a book move through `play_computer_move(move, 400 ms)` while the position is in the book, then the engine.
- **Endgame Practice:** the stored defence the same way; outside it, analysis requests. `EndgameMode._pending` remembers what the request was for:
  - `BASELINE`: the score before the user's move, when it is not known yet.
  - `REPLY`: the score after the move and the computer's answer, from one search.
  - `HINT`: the best move for a suggestion arrow.

The user may be browsing earlier moves while the computer thinks, so game logic works on `EngineGameMode._tip()`, the board after the last move played, not on `model.board`.

### Engine analysis in Board mode

`BoardMode.position_changed` waits `SETTLE_MS` for the position to settle, asks for a quick search and then a deep one, and keeps its own request id. The score and line go in the panel, and the best move on the board as a suggestion arrow. A failure turns analysis off and shows the error in the panel.

### Judging an endgame move

`EndgameGame.move_played` judges a move in the solution tree at once. Anything else is `pending` until `analysed` applies `is_mistake`: a move is a mistake only if the score falls below the goal's limit **and** dropped by at least `DROP_CP`. The light is computed from the judgements on request, so take-back only removes the judgements of the removed moves. [DECISIONS.md](DECISIONS.md#tuned-values) has the reason for the two-part rule.

### Take-back

```
Take Back button or Ctrl+Z -> mode.take_back()    guarded by can_take_back()
    -> cancel_computer_move()
    -> ctx.take_back(user_color) = MainWindow.take_back -> GameModel.take_back, position_changed
    -> game.took_back(tip) -> model.clear_result() -> _next_turn() -> update_status()
```

The guard comes first because cancelling the computer's move with nothing to take back would leave it never moving again. `GameModel.take_back` is not restorable with Ctrl+Y; `delete_last` and the tree-editing commands are.

### Switching modes

`MainWindow.set_mode(key, config=None, discard=False)`:

1. `new = cls(ctx)`, then `config = new.choose()` unless a `config` was passed. `None` cancels; the old mode is still running.
2. `old.confirm_leave()`, which only asks.
3. If `new.replaces_game` and not `discard`: `FileCommands.confirm_discard` offers to save when the game is modified or `old.leaving_changes_game()`. Cancelling here, or in the file dialog, changes nothing.
4. `old.leave()` (for example resign), then the save.
5. `old.deactivate()`, `self.mode = new`, the new panel, `new.start(config)`, `position_changed(rebuild=True)`.

The panel is built **before** `start`, so a panel must cope with having no game yet. Restarting a game mode (New Game, Retry) is the same switch with a new mode object, which is why what must outlive a game lives in `Assets` or `Settings`.

### Exit

`MainWindow.exit` asks nothing: it deactivates the mode, saves settings and closes. An unsaved game is not kept and a running game is not resigned. This is deliberate; see [DECISIONS.md](DECISIONS.md#product-behaviour).

## Who owns what

| Data | Owner | Lifetime |
| --- | --- | --- |
| Game tree, headers, comments | `GameModel.game` | Until replaced |
| Position shown | `GameModel.node`, `.board` (a cache) | Changes by navigation |
| Unsaved changes | `GameModel.modified` | Cleared by loading or saving |
| Restorable deletions | `GameModel._deleted` | Until a new move, a take-back or another game |
| Open file | `FileCommands.path` | Until replaced |
| Game rules state | `mode.game` | One game |
| Selection, drag, arrows, marks | `BoardView` | Until the position changes |
| Opening book, positions, deck | `ctx.assets` | The whole run |
| Settings, endgame progress | `Settings` | Disk: saved within about 2 s of a change, and at exit |

## The window

**Left, top to bottom:** the title row (`Mode.title()`, then `score_text()` and the `light()` on the right), the optional `subtitle()`, a player row, the board, a player row. Clocks come from `ctx.set_clocks`.

**Right, top to bottom:** the toolbar (New Game; Take Back if `takes_back`), the status line (`status_text()` or `model.status()`, and briefly why a command was blocked), the mode's panel (`build_panel`), the move list (takes spare height), the navigation buttons, and the collapsible Comment & FEN section. Whether that section is open is stored per mode in `settings["details_open"]`, falling back to `Mode.show_details`.

## Errors

| Where | What happens |
| --- | --- |
| Before Tk starts | `chessboard.pyw` writes the log and shows a Windows message box. |
| A Tk callback | `callback_error_reporter` logs it and shows a message, at most once every 30 s; the program keeps running. |
| An engine | The worker turns any exception into an `EngineError` result. A game mode ends the game with a message; Board mode switches analysis off. |
| A bad game in a user's PGN | Skipped and reported (`GameList.skipped`); the file is not overwritten by Save. |
| A bad game in `assets/` | Skipped and listed in `errors`, shown as a note in the mode's dialog. |
| Saving settings | Logged; `MainWindow.exit` warns the user. |
| Saving a game | An error message; the game stays modified. |

The log is `error.log` in the program folder, or `chessboard-error.log` in the temp folder if that is read-only.
