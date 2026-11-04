# Chessboard – practising endgames (plan)

> **Historical document.** This plan has been implemented and is no longer updated. The current structure of the program is described in [ARCHITECTURE.md](../ARCHITECTURE.md) and [EXTENDING.md](../EXTENDING.md); the deviations from the plan are listed at the end of EXTENDING.md.

3.11.2026

> A continuation of the plans [Chessboard_plan.md](Chessboard_plan.md), [Engine_plan.md](Engine_plan.md) and [Opening_theory_plan.md](Opening_theory_plan.md). The current structure is described in [docs/ARCHITECTURE.md](../ARCHITECTURE.md) and [docs/EXTENDING.md](../EXTENDING.md). When the plan has been implemented, the file is moved to the `docs/plans/` folder and marked historical like the others.

## Goal and scope

A fourth mode, **Endgame Samples…**, is added to the Game menu. The program has about 100 saved endgame positions on five difficulty levels. The user chooses a difficulty level, the program draws a position, and the user plays it to the end against the computer.

| Mode | Description |
| --- | --- |
| Board, Play vs Computer…, Learn Openings… | Unchanged. |
| **Endgame Samples…** (new) | The user chooses only the difficulty level (1–5). The program draws from that level a position that has not yet been played during this run. The user plays the side to move, the computer plays the other. The computer defends as well as it can: it follows the saved defence for as long as the solution tree lasts and then plays at full strength. The **success light** in the right panel tells whether the sequence has gone right (green) or wrong (red). The game continues in either case. |

**Included:**

- the endgame positions as data files (PGN, `SetUp`/`FEN`), not in code; the solution as a move tree
- choosing the difficulty level in a pop-up dialog, drawing a position without repetition during the same run
- the opponent's **level is not chosen**: the computer plays the defence of the solution tree and after that always at full strength (Stockfish, *Maximum*). No Elo picker and no choice of engine
- a 15-minute clock (a setting); the game ends in checkmate, loss on time or stalemate (and other draws, see *Decisions*)
- the success light (grey / green / red) in the right panel
- the *Suggest next move* option
- taking back a move (*Take Back*)
- the source, composer and year of the position above the board

**Language:** the texts of the user interface and the names of the positions are in English like everywhere else (`strings.py`).

**Not included (later, the structure allows it):** statistics and repetition, choosing a specific position from a list, our own position editor, Syzygy tablebases as mandatory.

**The absolute requirement remains:** the program works offline. The positions are local files, and the evaluation is done with the local Stockfish.

**Extensibility:**

- a new position = a new game in a PGN file in the `assets/endgames/` folder, no code changes
- a new mode inherits `EngineGameMode` (or the intermediate level with a clock described below) and does not copy the thread, clock or polling code

## User interface

### Above the board: information about the position

Now there is one row above the board: the mode's title on the left (`Mode.title()`) and the score on the right (`Mode.score_text()`). A second, thinner row is added for the source information of the position:

```
Endgame Samples · Level 5 · Saavedra Position                Material: you +1
Fernando Saavedra (after G. Barbier) · Glasgow Weekly Citizen · 1895
┌───────────────────────────────────────────────┐
│ Black (Stockfish 1500)                  14:52 │
│                  (board)                      │
```

- A new `Mode.subtitle() -> str | None`, default `None`. `MainWindow.refresh()` shows it under the title row in a small, dim font (`FONT_SMALL`, `MUTED_FG`) and hides the row when the value is `None`. Other modes do not change.
- The text is composed of the PGN headers `Composer`, `Source` and `Year`; missing ones are left out. If nothing is known (e.g. the basic mates), the row says *Classic endgame position*.

### The right panel

```
┌────────────────────────────────┐
│ [ ⟲ New Game ]                 │  ← shared toolbar
│ Your move                      │  ← status line
├── mode panel ──────────────────┤
│ ●  Success                     │  ← light: grey / green / red
│ Goal: White to play and win    │
│ Level 5 · 3 of 20 played       │
│ [x] Suggest next move          │
│ [Take Back] [Resign]           │
│ [Open in Board Mode]           │
├────────────────────────────────┤
│ 1. c7    Rd6+                  │  ← move list
│ 2. Kb5   …                     │
├────────────────────────────────┤
│ |◀   ◀   ▶   ▶|   Flip         │
├────────────────────────────────┤
│ ▸ Comment & FEN                │  ← closed by default
└────────────────────────────────┘
```

- The **success light** is a small `tk.Canvas` with a circle, and a short text next to it. A new helper function `widgets.light(parent)` and a method `set_state(state)`; the colours go in `theme.py` (`LIGHT_PENDING`, `LIGHT_SUCCESS`, `LIGHT_FAIL`).

  | State | Colour | Text |
  | --- | --- | --- |
  | `pending` | grey | *In progress* |
  | `success` | green | *Solved* |
  | `fail` | red | *Missed – keep playing* |

- *Goal* tells the task: *White to play and win* / *Black to play and draw*.
- The counter *3 of 20 played* tells how many of the level's positions have already been played during this run.
- The clocks are shown next to the players' names as in Play vs Computer mode (`ctx.set_clocks`).
- Comment & FEN is closed by default (`show_details = False`); the position's comment goes there when the solution tree has one.

### The selection dialog (pop-up)

Opens when the mode is chosen from the Game menu or New Game is pressed.

```
┌ Endgame Samples ───────────────────────────────────┐
│ Difficulty:                                        │
│   ( ) 1  Basic mates                (20, 0 played) │
│   ( ) 2  Elementary endings         (20, 4 played) │
│   (•) 3  Theoretical positions      (20, 1 played) │
│   ( ) 4  Practical endgames         (20, 0 played) │
│   ( ) 5  Studies                    (20, 0 played) │
│ Time:     [15] min                                 │
│                                   [Start] [Cancel] │
└────────────────────────────────────────────────────┘
```

- The dialog has no choice of engine or level; the opponent is always Stockfish at full strength (see *The computer's opponent*). If Stockfish is not available, the dialog says that the computer plays only the saved defence and after that random moves.
- The names of the levels and the numbers of positions are read from the collection, not in code (the name of the level is in a header of the PGN file, see below).
- The latest choice is remembered in the settings. Enter = Start.

### The flow of the game

1. **Drawing.** From the positions of the chosen level, one that has not been played during this run is drawn (see *Drawing without repetition*).
2. **Start.** The game starts from the position's FEN. The user plays the side to move; the board is flipped accordingly. The clock starts from the user's first move as in Play vs Computer mode.
3. **The computer's turn.** See *The computer's opponent*: first the saved defence, then Stockfish at full strength.
4. **The user's move** is judged (see *Judging success*), and the light is updated. The game continues regardless of the colour of the light.
5. **The end of the game:** checkmate, stalemate, running out of time or another draw according to the rules. *Resign* ends the game at once. The final result is shown on the status line, and the light stays in its last state.
6. **Take Back** removes the moves up to the user's previous turn (`ctx.take_back`), cancels any engine request in progress and recalculates the light (see below). It works also after checkmate or stalemate, but not after the time has run out. The clock does not go back in time.
7. **Open in Board Mode** as in the other game modes. `Event "Endgame practice"`, `SetUp "1"`, `FEN`, `EndgameKey`, `Difficulty` and, if known, `Source`/`Composer`/`Year` are recorded in the PGN.

### Suggest next move

- A checkbox in the mode panel, the state in the settings (`end_suggest`, default `False`).
- On the user's turn an arrow is shown (`Mode.hint_arrows()`, the same hint layer as in Learn Openings):
  - **inside the solution tree:** the saved solution move as a strong arrow, alternative correct moves as thin ones
  - **outside the solution tree** (the user or the computer deviated): Stockfish's best move (see below)
- Using a hint does not change the light, but *Hints used: n* is recorded in the panel and `HintsUsed` in the PGN header. (See *Open questions* 3.)

## Judging success

This is the hardest part of the mode: the solution tree does not cover all the user's sensible moves or all the computer's replies, so a mere "does the move match the saved one" is not enough. Two layers are used.

### 1. The solution tree (the book)

The move tree saved with the position is like an opening book: the moves are looked up by position (like `OpeningLine`, so transpositions are found).

| The user's move in a position of the solution tree | Result |
| --- | --- |
| a move of the main line or of an unmarked variation | correct, the light stays / changes to the ok state |
| a variation whose move has the NAG `?` or `??` (a known wrong attempt) | **red at once**; the variation's comment is shown as an explanation |
| any other move | decided by the judge (layer 2) |

### 2. The judge (Stockfish at full strength)

The same `EngineWorker` (Stockfish, *Maximum*, thinking time ~1 s) evaluates the position after each user move when outside the solution tree. One analysis request gives both the evaluation and the engine's best reply at once, so a separate judge is not needed: the evaluation decides the light and the move is the computer's reply. The goal (`Goal`) is from the user's point of view:

| Goal | The move is a mistake (red) when the evaluation after the move is … |
| --- | --- |
| `win` | no longer winning: no mate for the user and not at least `+WIN_CP` (default +300 cp) |
| `draw` | losing: mate against the user or below `−LOSS_CP` (default −300 cp) |

- The limits have hysteresis, so that a single uncertain evaluation does not turn the light: a mistake requires a clear drop (e.g. in a `win` goal the evaluation falls below +150 cp).
- The evaluation and the reply come from the background thread at the same time; the light is updated when the computer's move appears.
- If Stockfish is not available, there is no judge: a move outside the solution tree leaves the light grey, the computer plays a random move, and the status line says *"No engine to judge moves off the solution"*.
- **Optional accuracy:** if the folder `engines/syzygy/` has Syzygy tablebases (3–5 pieces), their path is given to Stockfish (`SyzygyPath`), so that the evaluation is exact in positions with few pieces. The program works without them.

### The computer's opponent

The computer chooses its move in this order:

1. **The solution tree.** If the position is in the solution tree and it has moves for the computer's side, the computer plays one of them (the main line most probably, the variations sometimes, so that the games vary). The saved defence is usually exactly the hardest one in studies and theoretical positions.
2. **Stockfish at full strength**, when the position is outside the tree (the analysis request above).
3. **A random legal move** only if there is no Stockfish.

This way the opponent is always strong and the level does not have to be chosen. The choice of engine and the level are removed from the dialog and the settings.

### The states of the light

| Event | Light |
| --- | --- |
| the game starts | grey |
| the user makes a mistake (layer 1 or 2) | **red**, and stays red (except for Take Back) |
| the user plays the solution tree to its end without a mistake | **green** |
| the goal is reached without a mistake: `win` → the user mates; `draw` → the game ends in a draw | **green** |
| the goal is missed: `win` → stalemate, a draw or time runs out; `draw` → the user is mated or time runs out | **red** |

- Red is permanent for this attempt: later good moves do not turn it green. Green can still turn red if the user, for example, stalemates a won position.
- **Take Back** recalculates the light from the remaining moves: each judgement is saved per move, so the judgement of the taken-back move is simply removed. Take-backs are counted (*Take backs: n* in the panel and the PGN).

## The collection of positions

### File format

One PGN file per difficulty level: `assets/endgames/level1.pgn` … `level5.pgn`, about 20 positions in each. One game is one position.

```pgn
[Event "Saavedra Position"]
[Key "saavedra"]
[Difficulty "5"]
[DifficultyName "Studies"]
[Goal "win"]
[Composer "Fernando Saavedra (after Georges Barbier)"]
[Source "Glasgow Weekly Citizen"]
[Year "1895"]
[SetUp "1"]
[FEN "8/8/1KP5/3r4/8/8/8/k7 w - - 0 1"]

{White's pawn is one step from queening, but the rook keeps checking.}
1. c7 Rd6+ 2. Kb5 Rd5+ 3. Kb4 Rd4+ 4. Kb3 Rd3+ 5. Kc2 Rd4
6. c8=R! (6. c8=Q? {Rc4+ 7. Qxc4 is stalemate.} Rc4+ 7. Qxc4) 6... Ra4 7. Kb3 *
```

| Header | Required | Meaning |
| --- | --- | --- |
| `Event` | yes | The name of the position (shown in the title). |
| `Key` | yes | A unique, permanent identifier. Never changed. |
| `Difficulty` | yes | 1–5. |
| `DifficultyName` | in the first game | The name of the level for the dialog (*Basic mates* …). |
| `Goal` | yes | `win` or `draw`, from the point of view of the side to move. |
| `SetUp`, `FEN` | yes | The starting position. The side to move = the user. |
| `Composer`, `Source`, `Year` | no | Shown above the board if given. |

**The move tree:** the main line is the solution. A variation on the user's side without a NAG is an equally good alternative; a variation whose first move has `?`/`??` is a known wrong attempt (red light, a comment explains). Variations on the computer's side are alternative defences. The comments are shown in the comment field as in Learn Openings.

### Difficulty levels and the starting list

The list is a draft; each position is checked with a tool before it is added (see *Checking the data*). The source, composer and year are recorded only when they have been verified.

**Where do the positions come from?** You do not need to know them beforehand. I collect the positions myself from well-known, well-documented topics: the basic positions of textbooks (K+Q vs K, opposition, the square of the pawn), named theoretical positions (Lucena, Philidor, Vančura, Saavedra, Réti) and classic studies. These can be found in, among others, Wikipedia's endgame articles and the learning materials of chess clubs. The program does not download anything from the net while running. Stockfish checks each position (`tools/check_endgames.py`), and you can look at the finished list (name + level + goal) before the positions are taken into use. Anyone can make additions to the PGN file later.

| Level | Name | Contents (examples) | Count |
| --- | --- | --- | --- |
| 1 | Basic mates | K+Q vs K, K+R vs K, two rooks (the ladder mate), K+Q vs K avoiding stalemate, the easiest king + pawn vs king positions | ~20 |
| 2 | Elementary endings | the square of the pawn, opposition and key squares, K+2B vs K, Q vs a pawn on the 7th rank, rook vs pawn, the Philidor position (Philidor, *L'analyse des échecs*, 1777) | ~20 |
| 3 | Theoretical positions | the Lucena position (Salvio 1634), the Vančura position (1924), K+B+N vs K, Q vs R (Philidor 1777), triangulation, the Centurini position (1856), the breakthrough three pawns against three | ~20 |
| 4 | Practical endgames | endgames from well-known master games (rook, bishop and knight endgames), corresponding squares, the Lasker–Reichhelm position (1901) | ~20 |
| 5 | Studies | the Saavedra position (1895), Réti's study (1921), other classic studies (e.g. Troitsky, Kubbel, the Platov brothers, Rinck) | ~20 |

**Copyright:** chess positions and moves are facts, but the explanatory texts are written by ourselves and not copied from books. The studies are chosen mainly from classic sources (published before the 1950s).

### The collection logic (`app/endgames.py`, logic layer, no tkinter)

```python
@dataclass(frozen=True)
class EndgameSample:
    key: str; name: str; difficulty: int; goal: str        # "win" | "draw"
    fen: str; composer: str; source: str; year: str
    game: chess.pgn.Game                                   # the move tree
    def side(self) -> chess.Color                          # the side to move = the user
    def credit_text(self) -> str                           # "Composer · Source · Year" or ""

class EndgameCollection:
    @classmethod
    def load(cls, folder) -> "EndgameCollection"           # errors: [(file, error)] like OpeningBook
    def levels(self) -> list[tuple[int, str, int]]         # (level, name, number of positions)
    def samples(self, difficulty) -> list[EndgameSample]

class SolutionTree:                                        # the position's moves, lookup by position (cf. OpeningLine)
    def moves(self, board) -> list[SolutionMove]           # move, wrong (NAG ?/??), comment
    def at_end(self, board) -> bool                        # the solution has been played to the end

class EndgameDeck:
    """Drawing without repetition during the same run."""
    def __init__(self, collection, rng): ...
    def draw(self, difficulty) -> EndgameSample
    def played(self, difficulty) -> int
```

If the position lookup of `OpeningLine` is suitable as it is, `SolutionTree` uses it (or a shared helper function is separated from `openings.py`) instead of writing the lookup logic again.

### Drawing without repetition

- `EndgameDeck` keeps a shuffled deck ("shuffle bag") per level. `draw()` takes the next one from the deck; when the deck is empty, it is shuffled again so that the position just played does not come first.
- The deck lives at the **level of the mode class** (not in the mode instance, because `set_mode` creates a new object of the mode on each selection), so it survives a change of mode but is reset when the program is restarted.
- The source of randomness is given as a parameter so that the tests are repeatable.

## Architecture

### New and changed files

| File | Layer | Change |
| --- | --- | --- |
| `app/endgames.py` | logic | **New.** `EndgameSample`, `EndgameCollection`, `SolutionTree`, `EndgameDeck`. |
| `app/endgame_game.py` | logic | **New.** `EndgameGame(ComputerGame)`: rules, light, judgements (see below). |
| `app/modes/timed_mode.py` | controller | **New.** `TimedGameMode(EngineGameMode)`: the ticking of the clock, the clock displays and Resign are moved here from `VsComputerMode`. |
| `app/modes/vs_computer.py` | controller | Inherits `TimedGameMode`. The behaviour does not change. |
| `app/modes/endgames.py` | controller | **New.** `EndgameMode(TimedGameMode)`. |
| `app/modes/base.py` | controller | A new default method `subtitle()` → `None`. |
| `app/modes/__init__.py` | controller | `MODES = [BoardMode, VsComputerMode, LearnOpeningsMode, EndgameMode]` |
| `app/engines/base.py`, `stockfish.py`, `uci.py` | logic | `Engine.analyse(board, think_time, stop) -> Analysis(move, cp, mate)`; the UCI client reads the `info … score cp/mate` lines. `Engine.can_analyse` (Random: `False`). An optional `SyzygyPath`. |
| `app/engines/worker.py` | logic | `request(…, analyse=False)`: returns an `Analysis` (evaluation + best move) instead of just a move. |
| `app/main_window.py` | controller | A subtitle row above the board, `refresh()` asks `mode.subtitle()`. |
| `app/widgets.py`, `app/theme.py` | view / logic | The `light()` light and its colours. |
| `app/dialogs.py` | view | `choose_endgame()`. |
| `app/strings.py` | logic | The texts (`MODE_ENDGAMES = "Endgame Samples…"` etc.). |
| `assets/endgames/level1–5.pgn` | data | **New.** About 100 positions. |
| `tools/check_endgames.py` | tool | **New.** Checking the data with Stockfish (see below). |
| `tests/test_endgames.py`, `tests/test_endgame_game.py` | tests | **New.** |
| `docs/ARCHITECTURE.md`, `docs/EXTENDING.md` | documents | Updated; a new recipe *Add an endgame*. |

### `EndgameGame` (logic layer)

`ComputerGame` already brings the clock, running out of time, resigning and the `move_played` skeleton, so `EndgameGame` inherits it:

```python
class EndgameGame(ComputerGame):
    EVENT = S.END_EVENT
    ALLOWED_DURING_GAME = frozenset({TAKE_BACK})
    ALLOWED_AFTER_GAME = frozenset({TAKE_BACK, EDIT_COMMENT})   # no TAKE_BACK after time has run out

    def __init__(self, sample, user_color, minutes=15, now=time.monotonic): ...   # no engine/level
    # State
    light: str                    # "pending" | "success" | "fail"
    judgements: list              # one judgement per user move: "ok" | "fail" | "pending"
    take_backs: int; hints_used: int
    # Queries
    def goal_text(self) -> str
    def hints(self, board, engine_move=None) -> list   # from the solution tree, otherwise Stockfish's move
    def needs_judging(self, board) -> bool              # outside the solution tree and Stockfish in use
    def tree_reply(self, board, rng) -> chess.Move | None   # the computer's saved defence, if there is one
    # Events
    def move_played(self, board)                        # + solution tree, the end of the game → light
    def judged(self, ply, analysis)                     # the judge's result → light
    def took_back(self, board)                          # judgements are shortened, the light is recalculated,
                                                        # the clock is started for the user
    def write_headers(self, headers)                    # SetUp, FEN, EndgameKey, Difficulty, Source…
```

The judge's result is always tied to the move's ply number and the request identifier, so an old evaluation arriving after a take-back is discarded in the same way as a stale engine move.

### `EndgameMode` (controller)

- `choose()` → `choose_endgame(…)`; `start(config)` draws the position (`EndgameDeck`), creates the `EndgameGame`, `ctx.new_game(chess.Board(sample.fen))`, flips the board and starts Stockfish at full strength (no choice by the user).
- `after_move()` → `game.move_played`; then the computer's turn: `tree_reply()` first, otherwise an analysis request (the evaluation → `judged`, the best move → the computer's move).
- `title()`, `subtitle()`, `hint_arrows()`, `build_panel()` (the light, the goal, counters, Suggest, Take Back, Resign, Open in Board Mode), `menu_items()`.
- `deactivate()` closes the worker as in the base class.

### Settings (the mode's `SETTINGS`)

| Key | Default | Meaning |
| --- | --- | --- |
| `end_difficulty` | `1` | The most recently chosen difficulty level. |
| `end_minutes` | `15` | The clock in minutes (for both). |
| `end_suggest` | `False` | *Suggest next move*. |

## Checking the data

`tools/check_endgames.py` is run always when positions are added or changed (not part of the normal test run, because it is slow):

1. every FEN is legal, and the `Goal` holds: Stockfish (a long thinking time, Syzygy if available) evaluates the starting position as a win / a draw
2. every user move of the main line keeps the goal, and the attempts marked with `?` really lose it
3. prints a summary: the positions by level, missing source information, suspicious evaluations

## Tests

- `test_endgames.py`: all `assets/endgames/*.pgn` load; `Key` unique; `Difficulty` 1–5; `Goal` valid; the FEN legal and the game not already over; the moves of the solution legal; at least 15 positions on every level. `EndgameDeck`: the same position does not repeat until the level has been gone through, and the one just played does not come right at the start of the new round.
- `test_endgame_game.py`: a move of the solution tree → ok; a `?` attempt → red; the solution to the end → green; checkmate (`win`) → green; stalemate in a `win` goal → red; running out of time → red; the judge's result turns the light; a stale evaluation is discarded; Take Back restores the light; red stays red; no judge → grey outside the solution tree; `tree_reply` returns the saved defence inside the tree and `None` outside the tree. The clock with a faked time source as in `test_computer_game.py`.
- `test_engines.py`: `analyse()` returns a mate evaluation in a mating position (`info score` lines added to `fake_uci.py`).
- `test_modes.py`: the new mode is in the registry, the settings do not collide; `EndgameMode.start` with `fake_context()`; the tests of `VsComputerMode` are run as they are after the `TimedGameMode` refactoring.

## Order of implementation

Each phase is usable on its own, and the tests pass after each phase.

1. **Refactoring:** `TimedGameMode` is separated from `VsComputerMode`; `Mode.subtitle()` and the subtitle row. The behaviour does not change.
2. **The basis of judging:** `Engine.analyse`, parsing the UCI `score`, the analysis request of `EngineWorker`, tests.
3. **The collection:** `app/endgames.py`, the first ~25 positions (5 per level), `tools/check_endgames.py`, `test_endgames.py`.
4. **The mode:** `EndgameGame`, `EndgameMode`, the dialog, the light, Suggest, Take Back, the texts and settings, tests.
5. **The remaining positions** (~100), checked with the tool, in batches, one level at a time.
6. **Documents:** ARCHITECTURE.md and EXTENDING.md; this file into the `docs/plans/` folder as historical.

## Later

- Statistics per position (solved / not, take-backs) and repetition of the failed positions; remembering the drawing across runs in the settings.
- Choosing a specific position from a list (like the tree of the opening dialog).
- A choice of a weaker opponent (Elo level) for beginners, if full strength proves too hard on the lowest levels.
- Downloading Syzygy tablebases, with instructions in the README.

## Open questions

To be resolved before phase 4. The plan's default in parentheses.

1. **Name:** *Endgame Samples…* or e.g. *Endgame Practice…*? User: Endgame Practice.
2. **Other draws:** does the game end also in a threefold repetition, the 50-move rule and insufficient material, or only in checkmate, loss on time and stalemate? In drawing studies (e.g. Réti) the game naturally ends precisely in insufficient material. (All draws according to the rules end the game.)
3. **Hints and the light:** can one get the green light if one has used a *Suggest next move* hint or Take Back? (Yes; the use is shown only as counters.)
4. **The clock and Take Back:** is the clock time restored on a take-back? User: No
5. **The place of the success field:** the top of the right panel, or above the board on the right, in the place of the material situation? (The right panel.) User: Above the board on the right.
6. **The computer's defence:** the Elo choice has been removed. The computer plays the saved defence and after that at full strength. Is full strength too hard in the basic mates and on the lowest levels? (No: in these positions the perfect defence is what is being practised; a weaker opponent is on the *Later* list.)
