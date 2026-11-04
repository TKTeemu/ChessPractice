# Chessboard – learning opening theory (plan)

> **Historical document.** This plan has been implemented and is no longer updated. The current structure of the program is described in [ARCHITECTURE.md](../ARCHITECTURE.md) and [EXTENDING.md](../EXTENDING.md).

3.11.2026

> A continuation of the plans [Chessboard_plan.md](Chessboard_plan.md) and [Engine_plan.md](Engine_plan.md). The current structure is described in [docs/ARCHITECTURE.md](../ARCHITECTURE.md) and [docs/EXTENDING.md](../EXTENDING.md).

## Goal and scope

A third mode, **Learn Openings…**, is added to the Game menu. In addition, two improvements that concern all modes are made: an always-visible **New Game** button and a more compact right panel.

| Mode | Description |
| --- | --- |
| Board | Unchanged. |
| Play vs Computer… | Unchanged. The New Game button opens the same dialog as now. |
| **Learn Openings…** (new) | The user chooses an opening and the opponent's level. The computer plays its own side according to opening theory for as long as there is theory, and after that the engine continues the game at the chosen level. The checkbox *Suggest next move* shows the next move according to theory as an arrow. |

**Included:**

- the opening book as data files (PGN), not in code
- choosing the opening in a pop-up dialog (a grouped list, search, choice of side and level)
- the computer's moves according to theory; the user's deviation from theory is recognised
- *Suggest next move* arrows, taking back a move (*Take Back*) in the learning mode
- a shared New Game button in all modes
- making the right panel more compact

**Language:** all texts, including the opening names, are in English like the rest of the user interface (`strings.py`).

**Not included (later, the structure allows it):** the engine's suggestions after theory has ended, repetition exercises and statistics per opening, editing the opening book from the program.

**The absolute requirement remains:** the program works offline. The opening book is a local file.

**Extensibility:**

- a new opening = a new PGN file in the `assets/openings/` folder, no code changes
- a new mode = one file in the `app/modes/` folder and a line in the registry, as now; a mode that uses an engine inherits the shared `EngineGameMode` class and does not copy the thread and polling code

## User interface

### The right panel, new order

The right panel is now 360 px wide, and the move list stretches to fill all the free space. The comment and FEN fields take up space also in modes where they cannot be edited. The new order:

```
┌────────────────────────────────┐
│ [ ⟲ New Game ]                 │  ← shared toolbar, always visible
│ Your move                      │  ← status line
├── mode panel ──────────────────┤  (only if the mode has one)
│ Réti Opening · A04–A09         │
│ Line: King's Indian Attack     │
│ Theory: 5/5 moves              │
│ [x] Suggest next move          │
│ [Take Back] [Open in Board]    │
├────────────────────────────────┤
│ 1. Nf3   d5                    │  ← move list, limited height
│ 2. g3    Nf6                   │
│ 3. Bg2   …                     │
├────────────────────────────────┤
│ |◀   ◀   ▶   ▶|   Flip         │
├────────────────────────────────┤
│ ▸ Comment & FEN                │  ← collapsible, open in Board mode
└────────────────────────────────┘
```

Changes to `main_window.py`:

1. **The panel width** 360 → about 290 px (`_px(290)`). The move list's tab stops (`tabs=("33p", "98p")`) still fit; check with the longest SAN move (`exd8=Q+`).
2. **The mode panel** is moved above the move list, so that the learning controls are near the status line.
3. **Comment & FEN** is gathered into a collapsible frame. The default state comes from the mode (`Mode.show_details`, default `True`; `False` in the game modes). The user's choice is remembered per mode in the settings.
4. The move list still gets the extra space (`rowconfigure(weight=1)`), but the other parts no longer take it unnecessarily.

### The New Game button

A new game can already be started with Ctrl+N, from the menu File > New Game, or by choosing the already active mode from the Game menu, but none of these is visible on the screen. Therefore a button is added that all modes use.

- The button is on the shared toolbar at the top of the right panel, and it is built in `MainWindow`, not in the modes. It calls the same `MainWindow.new_game()` method as Ctrl+N.
- The mode decides what a new game means (`Mode.new_game()`, as now):

| Mode | New Game |
| --- | --- |
| Board | Resets the empty board to the starting position; asks about saving if the game has changed. |
| Play vs Computer | If a game is in progress: "Resign the game?". Then the same dialog opens as now (Engine, Level, Color, Start from), with the previous choices preselected. Enter starts the game with the same settings. |
| Learn Openings | If a game is in progress, a confirmation is asked. Then the opening selection dialog opens (see below), with the previous opening, side, engine and level preselected. |

Play vs Computer thus works as now; the button only makes the action visible. A separate *Change Opening…* button is not needed, because New Game opens the same dialog.

### The opening selection dialog (pop-up)

The dialog opens when the user chooses the Learn Openings… mode or presses New Game. It is not kept visible all the time.

```
┌ Learn Openings ─────────────────────────────────────┐
│ Search: [ret______]                                 │
│ ┌──────────────────────────────┬──────────────────┐ │
│ │ ▾ Irregular openings (A00)   │ Réti Opening     │ │
│ │     Anderssen's Opening 1.a3 │ A04–A09          │ │
│ │     …                        │ 1.Nf3 d5 2.g3 …  │ │
│ │ ▾ Flank openings             │ (main line, 8    │ │
│ │     Larsen's Opening   1.b3  │  moves)          │ │
│ │   ► Réti Opening       1.Nf3 │                  │ │
│ │     …                        │                  │ │
│ └──────────────────────────────┴──────────────────┘ │
│ You play:   (•) the opening (White)  ( ) the reply  │
│ Engine:     [Stockfish ▾]   Level: [1500 ▾]         │
│ [x] Vary the computer's replies                     │
│                                    [Start] [Cancel] │
└─────────────────────────────────────────────────────┘
```

- The list is a `ttk.Treeview` in which the groups are expandable nodes. The groups and their order come from the opening book, not from code.
- On the right, the main line of the selected opening is shown, so that the user sees what they are about to learn.
- *You play: the opening / the reply* means the user's choice "the one who plays the opening is the user / the computer". The colour follows from the opening: in White's openings the one playing the opening is White, in the *English Defence* it is Black. The colour is shown in parentheses.
- The choice of engine and level is the same as in the Play vs Computer dialog. The pickers are separated into a shared helper function in `dialogs.py` (`_engine_level_pickers`), which both dialogs use.
- *Vary the computer's replies*: when selected, the computer picks randomly among the theory moves with weights (the main line most often); otherwise it always plays the main line.
- The latest choice is remembered in the settings.

### Suggest next move

- The checkbox is in the mode panel and is visible all the time in the learning mode. Its state is saved in the settings (`learn_suggest`).
- When the box is checked and it is the user's turn, the theory moves are shown as arrows: the main line as a strong arrow, the other theory moves (at most 3) thinner and translucent.
- The arrows are a different colour from the arrows the user draws with the right button, and they do not disappear along with the user's arrows.
- The suggestions come from the opening book, so they exist only as long as the position is in the book.
- **The opening phase ends**, and the suggestions stop permanently for this game, when either of these holds:
  1. the move number exceeds the limit `learn_suggest_moves` (default 12; a setting that can be changed between 10 and 15), or
  2. the game is clearly outside theory: the position has dropped out of the book and does not return to the book (by a transposition) during the next two user moves.
- When the opening phase is over, the checkbox is greyed out and *(opening phase over)* is shown next to it. The choice itself is kept in the settings for the next game.
- Later, an engine suggestion (*Suggest best move*) can be added here after theory has ended (see *Later*).

### The flow of the game in the learning mode

1. The user chooses an opening. The game starts from the starting position, and the board is flipped according to the user's colour.
2. **On the computer's turn**, when the position is in the book: the computer plays the theory move after a short delay (about 0.4 s, so that the move stands out). The engine is not needed.
3. **On the computer's turn**, when the position is not in the book: the engine calculates the move in a background thread as in Play vs Computer mode. The status line says once: *"End of theory – the engine takes over."*
4. **On the user's turn**, when the position is in the book:
   - a theory move: the counter *Theory: n/n moves* grows and the name of the book variation is updated (e.g. *Line: King's Indian Attack*)
   - another move, when *Suggest next move* is **not** on: the computer plays against the user normally. The engine takes the turn immediately, and the game is not interrupted. The status line shows only a short mention *"Out of theory"*.
   - another move, when *Suggest next move* is on: the engine continues in the same way, but the status line also tells the theory moves (*"Out of theory. Book moves: Nf3, c4"*), and they are shown as arrows in the previous position until the user next moves. The user can, if they wish, take the move back (*Take Back*) and try a theory move.
5. **Comments of the book**: if the opening book's PGN has a comment attached to a move (e.g. the idea of the opening), it is shown in the comment field. This way the opening book can also teach, not just list moves.
6. **Take Back** removes the moves up to the user's previous turn (usually two half-moves) and cancels any engine request in progress.
7. There is no clock. Browsing (← →) is allowed, but moving is allowed only from the last position, as in Play vs Computer mode.
8. *Open in Board Mode* works as in Play vs Computer mode. The headers `Event "Opening training"`, `Opening` and `ECO` are recorded in the PGN.

## The opening book

### File format: PGN with variations

The openings are saved as ordinary PGN files in the `assets/openings/` folder. One game is one opening, and the move tree with its variations is the opening theory.

```pgn
[Event "Réti Opening"]
[Key "reti"]
[Group "Flank openings"]
[GroupOrder "2"]
[ECO "A04-A09"]
[Side "white"]

1. Nf3 {A flexible move: White does not yet commit to a pawn structure.}
1... d5 (1... Nf6 2. c4 g6 3. g3 Bg7 4. Bg2 O-O)
2. g3 (2. c4 d4 (2... e6 3. g3 Nf6 4. Bg2 Be7) 3. e3 Nc6)
2... Nf6 3. Bg2 c6 (3... e6 4. O-O Be7 5. d3 O-O) 4. O-O Bg4 5. d3 Nbd7 *
```

Why PGN and not JSON:

- The program already reads PGN (`fileio`, the vendored python-chess), and the variations, comments and headers are ready-made.
- The opening book can be opened and edited in the program's own Board mode and saved back. A separate editor is not needed.
- The moves are checked to be legal on loading.

Headers:

| Header | Meaning |
| --- | --- |
| `Event` | The displayed name. |
| `Key` | A permanent identifier for the settings (`learn_opening`). |
| `Group`, `GroupOrder` | The group in the dialog and the order of the groups. Within a group, the openings are shown in file order. |
| `ECO` | Shown next to the name. |
| `Side` | `white` or `black`: which side plays the opening. |

The order of the variations is a weighting: the first continuation is the main line. An optional NAG `!` or `?!` can later adjust the weights.

**Notation:** the user's list uses the Finnish notation (R = knight, L = bishop, T = rook, D = queen). The book stores standard English SAN (N, B, R, Q), because python-chess reads only that. E.g. *Réti Opening 1.Rf3* = `1. Nf3`. The conversion is done once, when the book is written.

### The starting list

Three files: two groups according to the user's original list, and the gambits as a group of their own.

`assets/openings/irregular.pgn` – the group *Irregular openings* (ECO A00):

| Key | Name | Start (SAN) | Played by |
| --- | --- | --- | --- |
| `anderssen` | Anderssen's Opening | 1. a3 | White |
| `ware` | Ware Opening | 1. a4 | White |
| `durkin` | Durkin Opening | 1. Na3 | White |
| `dunst` | Dunst Opening | 1. Nc3 | White |
| `sokolsky` | Sokolsky Opening | 1. b4 | White |
| `saragossa` | Saragossa Opening | 1. c3 | White |
| `mieses` | Mieses Opening | 1. d3 | White |
| `vant_kruijs` | Van't Kruijs Opening | 1. e3 | White |
| `barnes` | Barnes Opening | 1. f3 | White |
| `grob` | Grob's Attack | 1. g4 | White |
| `clemenz` | Clemenz Opening | 1. h3 | White |
| `desprez` | Desprez Opening | 1. h4 | White |
| `amar` | Amar Opening | 1. Nh3 | White |
| `benko` | Benko's Opening | 1. g3 | White |

`assets/openings/flank.pgn` – the group *Flank openings*:

| Key | Name | ECO | Start (SAN) | Played by |
| --- | --- | --- | --- | --- |
| `larsen` | Larsen's Opening | A01 | 1. b3 | White |
| `bird` | Bird's Opening | A02–A03 | 1. f4 | White |
| `reti` | Réti Opening | A04–A09 | 1. Nf3 | White |
| `english` | English Opening | A10–A39 | 1. c4 | White |
| `english_defence` | English Defence | A40 | 1. c4 e6 2. d4 b6 | **Black** |

`assets/openings/gambits.pgn` – the group *Gambits* (added after the original list):

| Key | Name | ECO | Start (SAN) | Played by |
| --- | --- | --- | --- | --- |
| `queens_gambit` | Queen's Gambit | D06–D69 | 1. d4 d5 2. c4 | White |
| `kings_gambit` | King's Gambit | C30–C39 | 1. e4 e5 2. f4 | White |

In both, Black decides with their second move whether to accept the gambit. Both main branches go into the book as named lines, so that the *Line:* row tells which one the user is playing:

| Opening | Named main branches (at least) |
| --- | --- |
| Queen's Gambit | *Accepted* (2…dxc4, D20–D29), *Declined* (2…e6, D30–D69; e.g. *Orthodox*, *Exchange*, *Tarrasch* 3…c5), *Slav* (2…c6, D10–D19), *Albin Countergambit* (2…e5, D08–D09) |
| King's Gambit | *Accepted* (2…exf4, C33–C39; e.g. *King's Knight's Gambit* 3.Nf3, *Bishop's Gambit* 3.Bc4), *Declined* (2…Bc5, C30), *Falkbeer Countergambit* (2…d5, C31–C32) |

In these, Black has many strong replies already on the second move, so *Vary the computer's replies* is most useful precisely here: the user has to answer both an accepted and a declined gambit. From Black's point of view (*You play: the reply*) the user practises the defence against the gambit.

The *Gambits* group is practical when there are few openings. If other 1.e4 and 1.d4 openings are added later, these two are moved to the groups *Open games (1.e4 e5)* and *Closed games (1.d4 d5)*, which is only a change of the `Group` header.

Choices made (both are changes of a single PGN header if they are to be changed later):

- **English Defence: ECO A40.** The original list had A14, but in the usual ECO classification 1.c4 e6 2.d4 b6 is read as code A40, because it transposes to the same position as 1.d4 e6 2.c4 b6. The best-known sources use A40, so the program shows the same code as books and databases.
- **Benko's Opening belongs to the group *Irregular openings*.** In the original list it was last, after the flank openings, but in the ECO classification 1.g3 is A00, like the other openings of the group.

**Depth:** for each opening, a main line of 8–12 half-moves and the 2–3 most common replies at the most important points. For the broad openings (English, Réti, Bird, Queen's Gambit, King's Gambit), the central main variations are added with names (e.g. *Symmetrical*, *Reversed Sicilian*, *From's Gambit*). A named variation is marked in a comment in the form `{Line: Reversed Sicilian}`, and the program shows the deepest name reached.

**Source of the content:** the move lines are written by hand according to standard sources. As an alternative or a supplement, Lichess's opening database (`lichess-org/chess-openings`, licence CC0) can be used: a small tool `tools/import_openings.py` converts the named lines (ECO A00–A40, C30–C39, D06–D69) of a once-downloaded TSV file into a PGN tree. The program itself does not use the network.

### The book logic (`app/openings.py`, logic layer, no tkinter)

```python
@dataclass(frozen=True)
class Opening:
    key: str
    name: str
    group: str
    eco: str
    side: chess.Color          # the one who plays the opening
    game: chess.pgn.Game       # the move tree

@dataclass(frozen=True)
class BookMove:
    move: chess.Move
    weight: int                # the main line is the largest
    line: str | None           # the name of the variation, if known
    comment: str               # a teaching comment

class OpeningBook:
    @classmethod
    def load(cls, folder) -> "OpeningBook": ...          # all *.pgn, invalid ones are skipped and reported
    def groups(self) -> list[tuple[str, list[Opening]]]: ...
    def opening(self, key) -> Opening | None: ...

class OpeningLine:
    """The theory of one opening, looked up by position."""
    def __init__(self, opening): ...                      # indexes: position key -> [BookMove]
    def moves(self, board) -> list[BookMove]: ...         # empty = not in the book
    def pick(self, board, rng, vary) -> chess.Move | None: ...
    def main_line(self) -> list[chess.Move]: ...          # for the dialog preview
```

- The lookup key is the position without move counters (`board.epd()` or `chess.polyglot.zobrist_hash`). Therefore **transpositions** (the same position via a different move order) are found automatically.
- The lookup is done only in the tree of the chosen opening. If the user moves into another opening, the game is outside theory even if the position is in the other opening.

## Architecture

### New and changed files

| File | Layer | Change |
| --- | --- | --- |
| `app/openings.py` | logic | **New.** `OpeningBook`, `Opening`, `OpeningLine`, `BookMove`. |
| `app/learning_game.py` | logic | **New.** `LearningGame`: the rules of the learning game (see below). |
| `app/modes/engine_mode.py` | controller | **New.** `EngineGameMode`: shared engine use for modes. |
| `app/modes/learn_openings.py` | controller | **New.** `LearnOpeningsMode`. |
| `app/modes/vs_computer.py` | controller | Inherits `EngineGameMode`. The behaviour does not change. |
| `app/modes/base.py` | controller | New default methods `hint_arrows()`, `show_details`; `ModeContext.take_back`. |
| `app/modes/__init__.py` | controller | `MODES = [BoardMode, VsComputerMode, LearnOpeningsMode]` |
| `app/board_view.py` | view | A separate hint-arrow layer: `set_hints(arrows)`. |
| `app/dialogs.py` | view | `choose_opening()`; the shared `_engine_level_pickers()`. |
| `app/main_window.py` | controller | The New Game button, the new panel order, hints in `refresh()`, `take_back`. |
| `app/model.py` | logic | `GameModel.take_back(color)`: removes the moves up to the given colour's previous turn. |
| `app/strings.py`, `app/settings.py` | logic | The texts and the `learn_*` settings. |
| `assets/openings/*.pgn` | data | **New.** The opening book. |
| `tests/test_openings.py`, `tests/test_learning_game.py` | tests | **New.** |
| `docs/ARCHITECTURE.md`, `docs/EXTENDING.md` | documents | Updated. |

### Additions to the Mode interface

Each addition is made in the base class with a neutral default, so Board mode does not change.

```python
class Mode:
    show_details = True     # the Comment & FEN section is open by default

    def hint_arrows(self):
        """Hint arrows for the board: [(from_sq, to_sq, style)], style "main" or "alt". Default []."""
        return []
```

```python
@dataclass
class ModeContext:
    ...
    take_back: Callable     # take_back(color): remove the moves up to this colour's previous turn, then refresh
```

- `MainWindow.refresh()` asks `mode.hint_arrows()` and passes them to `board.set_hints()`, in the same way as `title()` and `status_text()` are asked now. The mode thus does not touch the view directly.
- A new command `allows("take_back")`. In Board mode the corresponding thing is the current Ctrl+Z (`delete_last`).

### The shared engine mode `EngineGameMode`

`VsComputerMode` now contains the use of the thread, the polling timer, the request identifiers and the error handling. The learning mode needs exactly the same. They are moved to a base class:

```python
class EngineGameMode(Mode):
    """A mode in which the computer plays the other side. The subclass implements the game object and the choice of the computer's move."""

    def start_engine(self, engine_cls, level): ...        # EngineWorker, the _poll timer
    def request_engine_move(self): ...                    # worker.request(board, level, game.new_request())
    def play_computer_move(self, move, delay_ms=0): ...   # a book move or an engine move
    def deactivate(self): ...                             # timers and the worker closed
    def computer_turn(self):                              # the subclass overrides
        self.request_engine_move()
```

- `VsComputerMode.computer_turn()` = always the engine (the current behaviour).
- `LearnOpeningsMode.computer_turn()` = a book move if the position is in the book, otherwise the engine.
- The engine process is started only on the first request (as `EngineWorker` already does), so in the theory part alone Stockfish is not started at all.

A new mode that uses an engine (e.g. in the future *Solve Puzzle*, where the computer replies along the solution line) implements only its own `computer_turn()` method and its own game class.

### `LearningGame` (logic layer)

The counterpart of the `ComputerGame` class without a clock, testable without a display:

```python
class LearningGame:
    def __init__(self, line: OpeningLine, user_color, engine_label, vary, rng): ...
    # State
    in_book: bool; book_moves_played: int; user_book_hits: int
    deviation: list[BookMove] | None     # the theory moves, if the user just deviated
    current_line_name: str | None
    opening_phase: bool                  # False when the move limit is exceeded or the game is clearly out of theory
    # Queries
    def can_move(board, color, at_end) -> bool
    def allows(command) -> bool          # {"navigate", "edit_comment", "take_back"}
    def status_text(board) -> str
    def suggestions(board) -> list[BookMove]   # empty when opening_phase is False
    def computer_reply(board) -> chess.Move | None   # a book move, or None = ask the engine
    # Events
    def move_played(board_before, move, board_after)  # updates hits, the deviation, the end of theory
    def took_back(board)
    # Requests (the same pattern as ComputerGame)
    def new_request() -> int; def is_current(request_id) -> bool
    def write_headers(headers)
```

### Settings (`settings.DEFAULTS`)

| Key | Default | Meaning |
| --- | --- | --- |
| `learn_opening` | `"reti"` | The most recently chosen opening (`Key`). |
| `learn_role` | `"opening"` | `"opening"` = the user plays the opening, `"reply"` = the computer plays the opening. |
| `learn_engine` | `"stockfish"` | |
| `learn_level` | `"1320"` | |
| `learn_vary` | `True` | Varying the computer's replies. |
| `learn_suggest` | `True` | *Suggest next move*. |
| `learn_suggest_moves` | `12` | The move number after which the opening phase is over and the suggestions stop. |
| `details_open` | `"board"` | The modes in which Comment & FEN is open (a comma-separated string, because the type of a setting must match the default). |

### Tests

- `test_openings.py`: all `assets/openings/*.pgn` load, every opening has a unique `Key` and a valid `Side`; a transposition is found; `pick(vary=False)` returns the main line; the first moves of the openings match the table above.
- `test_learning_game.py`: a deviation is recognised, the end of theory is recognised, `computer_reply` returns `None` outside the book, Take Back restores the state, Black as the one playing the opening (*English Defence*) works, the opening phase ends at the move limit and when the game is two user moves outside theory, and a game that returns to the book by a transposition continues the opening phase.
- `test_modes.py`: the new mode is in the registry; `fake_context` gets a `take_back` field.
- The existing tests of the Play vs Computer mode are run as they are after the `EngineGameMode` refactoring.

## Order of implementation

Each phase is usable on its own, and the tests pass after each phase.

1. **The New Game button and making the panel compact.** Only `main_window.py` and `Mode.show_details`. A benefit at once in all modes.
2. **Refactoring:** `EngineGameMode` is separated from `VsComputerMode`; `hint_arrows()` + `BoardView.set_hints()`; `ModeContext.take_back` + `GameModel.take_back`. The behaviour does not change.
3. **The opening book:** `app/openings.py`, three PGN files for all 21 openings, `test_openings.py`.
4. **The learning mode:** `LearningGame`, `LearnOpeningsMode`, the `choose_opening()` dialog, the texts and settings, tests.
5. **Documents:** ARCHITECTURE.md and EXTENDING.md (a new recipe: *Add an opening*, `EngineGameMode` in the mode recipe).

## Later

- **A suggestion after theory (*Suggest best move*):** the suggestion continues to the end of the opening phase with the engine's best move (a second `EngineWorker` at a high level, a short thinking time). The structure is ready: `hint_arrows()` can also return the engine's move.
- **Repetition exercise:** the variations of an opening are gone through in order, and mistaken lines are repeated more often (statistics in the settings or in a JSON file of their own).
- **More openings:** other open and closed openings (e.g. Italian, Ruy Lopez, Sicilian, London System) are just new PGN files.
- **Recognising the opening in Board mode:** the same `OpeningBook` can show above the board which opening and variation is on the board.

## Decisions

The open questions of the first version, resolved on 3.11.2026:

1. **Language:** all texts, including the opening names, are in English.
2. **New Game:** opens the mode's dialog (Play vs Computer: Engine, Level, Color; Learn Openings: choosing the opening). The previous choices are preselected.
3. **Deviation from theory:** the computer continues the game normally. If *Suggest next move* is on, the theory moves are also shown on the status line and as arrows. The suggestions stop when the opening phase is over: the move limit (default 12) is exceeded, or the game has stayed outside theory for two user moves.
4. **ECO and groups:** the user did not take a position, so the usual ECO classification is followed: English Defence is A40, and Benko's Opening belongs to the group *Irregular openings*.
