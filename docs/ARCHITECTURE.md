# Architecture

This document describes how the program is built and where new code belongs. How to add a mode or a chess engine is in [EXTENDING.md](EXTENDING.md).

## Layers

The program has three layers. Dependencies only point downwards.

| Layer | Modules | May use tkinter? |
| --- | --- | --- |
| Controller | `main_window.py`, `modes/` | yes |
| Views | `board_view.py`, `movelist_view.py`, `dialogs.py`, `pieces.py`, `widgets.py` | yes |
| Logic and services | `model.py`, `engine_game.py`, `computer_game.py`, `learning_game.py`, `openings.py`, `endgame_game.py`, `endgames.py`, `clock.py`, `commands.py`, `engines/`, `fileio.py`, `settings.py`, `sounds.py`, `strings.py`, `theme.py` | no |

The logic layer does not import tkinter and knows nothing about windows, so it can be tested with pytest without a display. `pieces.py` belongs to the views because it creates Tk images (`tk.PhotoImage`), which need a Tk root window.

## Modules

| Module | Responsibility |
| --- | --- |
| `model.py` | `GameModel`: the game tree (a python-chess `Game`), the current node and its `board`, moves, navigation, editing variations, comments, the `modified` flag. Also helper functions such as classifying a move for sounds (`event_for`). |
| `fileio.py` | Reading and writing PGN and FEN (UTF-8, or Windows-1252 for old files; saves go through a temporary file), rejecting invalid positions, skipping and reporting bad games (`GameList.skipped`), interpreting pasted clipboard text, and `load_pgn_folder`, which the opening book and the endgame positions both load through. |
| `settings.py` | `settings.json`. Only keys in the defaults are accepted (`DEFAULTS` plus each mode's `SETTINGS`), and a value's type must match the default's type (`bool`, `int`, `str` or `dict`). `MainWindow` saves the file a few seconds after a change (`Settings.dirty`) and at exit; a failed save is logged to `error.log`. |
| `sounds.py` | Playing WAV sounds asynchronously (`winsound`). |
| `strings.py` | All user-visible text. |
| `theme.py` | Colours, fonts and board themes of all views. |
| `commands.py` | The command names a mode can allow or block (`NAVIGATE`, `TAKE_BACK`, …) and `ALL_COMMANDS`. |
| `pieces.py` | Piece images: Cburnett SVGs drawn by Tk itself (Tk 9 reads SVG) or Unicode glyphs via Pillow, cached per square size. |
| `widgets.py` | `button`, `label` and `checkbox` in the style of the right-hand panel, for `MainWindow` and the modes' panels, and `light` (the success light above the board). |
| `board_view.py` | `BoardCanvas` (geometry and square drawing) and `BoardView` (the game board: drag, click, promotion picker, arrows and square marks, and a separate layer of suggestion arrows set by the mode with `set_hints`). |
| `movelist_view.py` | The move list with variations in a Text widget, one tag per move; right-click menu. |
| `dialogs.py` | Choosing a game from a multi-game PGN, the Play vs Computer dialog, the Learn Openings dialog (`choose_opening`) and the Endgame Practice dialog (`choose_endgame`); both game dialogs share `_engine_level_pickers`, which finds the chosen engine and level by position, not by label. |
| `main_window.py` | `MainWindow`: creates the model and views; menus, keyboard shortcuts, the New Game and Take Back buttons, the title area above the board (title, subtitle, score or success light) and the collapsible Comment & FEN section; holds the active mode and asks it what is allowed. |
| `file_commands.py` | `FileCommands`: opening, saving and pasting, the clipboard, and `confirm_discard`, the one place that offers to save a game before it is replaced. |
| `assets.py` | `Assets`: the opening book and the endgame positions and deck, loaded when first needed and kept while the program runs; modes get it through `ModeContext`. |
| `modes/` | `Mode` interface and `MODES` registry; `BoardMode` (the free board, with optional engine analysis), `EngineGameMode` (shared base of modes where the computer plays: engine choice, worker, polling, delayed moves, the questions answered from the game, Take Back, Open in Board Mode), `TimedGameMode` (base of the modes with a chess clock: clock tick, clocks, resigning), `VsComputerMode` (play the computer: dialog), `LearnOpeningsMode` (opening training: book replies, suggestion arrows) and `EndgameMode` (endgame practice: level dialog, Retry, saved progress, stored defence, engine analyses that judge the user's moves, success light). |
| `engine_game.py` | `EngineGame`: the shared rules of a game against the computer (turns, allowed commands, status line, common PGN headers, result, stale computer replies via request ids). |
| `computer_game.py` | `ComputerGame(EngineGame)`: clock, material score, time-control headers, result by time or resignation. |
| `openings.py` | `OpeningBook` (loads `assets/openings/*.pgn`), `Opening`, `OpeningLine` (book moves looked up by position, so transpositions are found) and `BookMove`. |
| `learning_game.py` | `LearningGame(EngineGame)`: rules of an opening-training game (book or engine reply, deviations, theory count, the opening phase that limits suggestions, take-back). |
| `endgames.py` | `EndgameCollection` (loads `assets/endgames/*.pgn`), `EndgameSample` (one position), `SolutionTree` (the solution looked up by position, with wrong tries and line ends) and `EndgameDeck` (drawing positions without repeats, going on from the positions played in earlier runs). |
| `endgame_game.py` | `EndgameGame(ComputerGame)`: rules of an endgame-practice game (stored defence, judging each user move by the solution or by the engine's score, the success light, take-back), and `is_mistake`, the judging rule also used by `tools/check_endgames.py`. |
| `clock.py` | `ChessClock` and `format_time`, driven by a time source that tests can replace. |
| `engines/` | `Engine` interface and `ENGINES` registry; `StockfishEngine`, `RandomEngine`, the UCI client (`uci.py`) and `EngineWorker` (searches in a background thread). |

## Rules the structure relies on

1. **The model changes only through its own methods.** They set `GameModel.modified`, so nothing outside the class writes to `model.game`, its nodes or its headers (`tests/test_main_window.py` checks this for the modes). Views read the model (`model.board`, `model.node`, `model.game`) but report user actions through callbacks: `BoardView(on_move, on_illegal)`, `MoveListView(on_select, on_edit)`.
2. **Every change is followed by one of two `MainWindow` methods.** `position_changed()` is for a new current position or a changed game tree: it updates the board, move list, FEN field and comment, and then calls `update_status()`. Use `position_changed(rebuild=True)` when the game tree changed (new move, deletion, comment); plain navigation does not need it. `update_status()` is for when only what the mode says changed: the status line, title, score, buttons, player names, window title and suggestion arrows. It never reloads the comment field or drops a piece being moved, so it can be called while the user is doing something.
3. **The comment is saved before the node changes.** Commands call `save_comment()` first, because the comment field belongs to the node that was current when the field was filled.
4. **The rules live in python-chess.** The program does no move generation of its own; `GameModel` checks legality against `board.legal_moves`.
5. **Text goes in `strings.py`, colours and fonts in `theme.py`, settings in `settings.DEFAULTS` (or a mode's `SETTINGS`).** That way language, appearance and settings can each be changed in one place. Panels use the helpers in `widgets.py` instead of repeating style parameters.

## How a move flows

```
mouse → BoardView._press/_release
      → (promotion? BoardView shows the picker)
      → on_move(from, to, promotion) = MainWindow.user_move
      → MainWindow.play_move(chess.Move)
      → GameModel.play(move)          → event ("move", "capture", …) or None
      → MainWindow.position_changed(rebuild=True)
      → Sounds.play(event)
```

`GameModel.play` creates a new variation if the move does not yet exist from the current node; otherwise it just steps into the existing one. An illegal move returns `None`, so the board is redrawn and the "illegal" sound plays.

## State

| Data | Where |
| --- | --- |
| Game tree, headers, comments | `GameModel.game` |
| Position shown | `GameModel.node`, with `GameModel.board` as a cache |
| Unsaved changes | `GameModel.modified` |
| Deleted moves that can be restored | `GameModel._deleted`, until a new move is played or another game is loaded |
| Open file | `FileCommands.path` (`None` for a new game, one picked from a multi-game file, or one from a file with games that could not be read) |
| Selection, drag, arrows, marks | `BoardView`, cleared when the position changes (not by other updates) |
| Settings | `Settings`, saved a few seconds after a change and when the program exits |

## Above the board

The title row shows `Mode.title()` on the left and, on the right, `Mode.score_text()` (e.g. the material in Play vs Computer) and the success light when `Mode.light()` is not None (Endgame Practice). A second, smaller row below it shows `Mode.subtitle()` (where an endgame position comes from) and is hidden when it is None. Below them are the player names with the clocks, then the board.

## Right-hand panel

From top to bottom: the shared toolbar (New Game, the same in every mode; it calls `MainWindow.new_game`, which lets the mode decide what a new game means; and Take Back in a mode with `takes_back`), the status line, where a blocked action is also explained for a moment, the mode's own panel (`Mode.build_panel`, hidden if None), the move list (gets the spare height), the navigation buttons, and the collapsible Comment & FEN section. Whether that section is open is remembered per mode in `settings["details_open"]` (e.g. `{"board": true, "vs_computer": false}`); a mode not listed there uses `Mode.show_details`.

## Modes and engines

The program has modes (Board, the current free board, with optional engine analysis; Play vs Computer, with a chess clock and no take-backs; Learn Openings, where the computer plays from an opening book; Endgame Practice, where the user plays a stored endgame position against Stockfish at full strength) and chess engines (Stockfish over UCI). The opening-training plan is in [Opening_theory_plan.md](plans/Opening_theory_plan.md) and the endgame-practice plan in [Endgame_plan.md](plans/Endgame_plan.md) (in Finnish). The plan, with the reasons for the choices, is in [Engine_plan.md](plans/Engine_plan.md) (in Finnish); both are historical. The interfaces and step-by-step instructions for adding a mode, an engine or a level are in [EXTENDING.md](EXTENDING.md).

In short: `app/modes/` (controller layer) decides what the user may do and what happens after a move, with the rules of a game in the logic layer (`engine_game.py` and its subclasses); `app/engines/` (logic layer, no tkinter) chooses moves in a background thread. `MainWindow` asks the active mode (`can_move`, `allows`, `after_move`, `status_text`) instead of checking which mode is active, and engine moves go through `MainWindow.play_move` like user moves.

An engine move arrives like this:

```
VsComputerMode.after_move → EngineGameMode.request_engine_move → EngineWorker.request(board copy, level, request id)
  worker thread: Engine.best_move → (request id, move) into a queue
  main thread, root.after(50): EngineGameMode._poll → still the current request?
      → MainWindow.play_move(move, from_end=True) → same path as a user move
```

In Endgame Practice, `EndgameMode.computer_turn` first asks the solution tree (`EndgameGame.tree_reply`, played after 400 ms). Outside the tree it asks the worker for an analysis (`request(…, analyse=True)`): the `Analysis` gives the score that judges the user's move (`EndgameGame.analysed`) and the computer's reply in one search. If no score is known for the position before the user's move (the first move off the solution), a baseline analysis of that position is requested first. The analysis's ponder move is kept as the suggestion for the user's next move.

In Learn Openings, `LearnOpeningsMode.computer_turn` first asks the book (`LearningGame.computer_reply`); a book move is played with `play_computer_move(move, 400 ms)` through the same request-id check, and only outside the book is the engine asked.

In Board mode with *Engine analysis* ticked, `BoardMode.position_changed` waits a moment for the position to settle and then asks the worker for a quick analysis and, after that, a longer one. A result counts only if its request id is still the latest; the score and line go in the mode's panel and the best move on the board as a suggestion arrow.

Stockfish runs as a child process (`engines/stockfish/stockfish.exe`, started with `CREATE_NO_WINDOW`) only while a game against it is in progress, or while the analysis box is ticked, and only from the first engine request; Board mode without analysis, the book part of Learn Openings and the stored defence of Endgame Practice start no processes.

## Differences from the plan

- The application lives in `C:\Users\Omistaja\.local\ChessBoard`, not in the plan's `C:\Users\Omistaja\Chessboard`.
- The material difference is shown in Play vs Computer, above the board on the right. Captured pieces are not shown.
- The repository includes tools not in the plan: `tools/extract_pieces.py` and `tools/make_dist.py`.
- The pieces are drawn with Tk's own SVG support instead of PyMuPDF (one package less to install).
