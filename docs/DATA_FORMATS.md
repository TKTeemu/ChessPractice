# Data formats

The files the program reads and writes, and what must stay compatible. Opening and endgame files need no code changes: add a game and the program finds it.

## Permanent identifiers

These are stored in users' `settings.json`. Never rename or reuse one.

| Identifier | Stored in | If it disappears |
| --- | --- | --- |
| Mode `key` | `details_open` | The mode's section falls back to `Mode.show_details`. |
| Engine `key` | `vs_engine`, `learn_engine` | The dialog falls back to the first available engine. |
| Level `key` | `vs_level`, `learn_level` | Falls back to the engine's first level. |
| Opening `Key` | `learn_opening` | The dialog no longer preselects it. |
| Endgame `Key` | `end_progress`, and the `EndgameKey` header of saved games | The user's progress on that position is lost. |
| Board theme, piece set key | `board_theme`, `piece_set` | `MainWindow._repair_settings` resets to the default. |

## Opening book

`assets/openings/*.pgn`, loaded by `OpeningBook.load`. One game is one opening, and its move tree is the theory. A game with an error is skipped and named as a note in the dialog.

```pgn
[Event "Réti Opening"]
[Key "reti"]
[Group "Flank openings"]
[GroupOrder "2"]
[ECO "A04-A09"]
[Side "white"]

1. Nf3 {A flexible move: White does not yet commit to a pawn structure.}
1... d5 (1... Nf6 2. c4 g6) 2. g3 {Line: King's Indian Attack} *
```

| Header | Required | Meaning |
| --- | --- | --- |
| `Event` | yes | The name in the dialog. |
| `Key` | yes | Unique and permanent. |
| `Side` | yes | `white` or `black`: the side that makes the opening ("You play: the opening"). |
| `Group` | no | The dialog's group; default *Other openings*. |
| `GroupOrder` | no | Groups sort by the first number seen for that group. Within a group, openings keep file order. |
| `ECO` | no | Shown next to the name; `A04-A09` displays as A04–A09. |
| `Plies` | no | How many half-moves define the opening in the list (default 1, e.g. 3 for `1. d4 d5 2. c4`). |

**Move tree:** use standard English SAN (N, B, R, Q). At each node the first continuation is the main line. With *Vary the computer's replies* on, the computer picks with weights 2^(n−1), …, 2, 1; with it off, always the main line.

**Lookup is by position**, without move counters, so transpositions are found. If the same position is reached by two routes, the first occurrence of each move sets its weight and comment. Only the chosen opening's tree is searched.

**Comments:**

| Form | Effect |
| --- | --- |
| `{An explanation.}` | Copied into the game's comment when the move is played. |
| `{Line: Reversed Sicilian}` | Names the variation from this move on (*Line:* in the panel). |
| `{Line: From's Gambit; Black gives a pawn.}` | Both: the name, then the explanation. |

**After editing,** run `.venv\Scripts\python.exe -m pytest tests/test_openings.py`. It fails on load errors. A new or removed opening must also be changed in its `EXPECTED` table, which lists every key with its group, start moves and side.

The book can also be edited in Board mode: open the PGN file, change it and save. Explanatory comments must be your own words, not copied from books.

## Endgame positions

`assets/endgames/*.pgn`, by convention `level1.pgn` … `level5.pgn`, loaded by `EndgameCollection.load`. One game is one position. **The side to move in the FEN is the user's side.**

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
| `Event` | yes | The name above the board. |
| `Key` | yes | Unique and permanent. |
| `Difficulty` | yes | 1–5 (`DIFFICULTIES` in `endgames.py`). |
| `DifficultyName` | one game per level | The level's name in the dialog; the first one found wins. |
| `Goal` | yes | `win` or `draw`, for the side to move. |
| `SetUp`, `FEN` | yes | `SetUp` must be `1`. The position must be valid and not already over. |
| `Composer`, `Source`, `Year` | no | Shown under the title. Fill in only what has been verified; with none of them it reads *Classic endgame position*. |

The comment before the first move is the position's introduction.

**Move tree:**

| In the tree | Meaning |
| --- | --- |
| Main line | The solution, and the computer's preferred defence. |
| User-side variation, no `?`/`??` | An equally good move. |
| User-side variation whose first move has `$2` (`?`) or `$4` (`??`) | A known wrong try: the light turns red at once and the comment explains why. A line under a wrong try never counts as solved. |
| Computer-side variation | Another defence; picked with the same weights as the opening book. |
| The end of a correct line | The position counts as solved (green). After that, and outside the tree, the engine plays and judges. |

Other NAGs such as `$1` have no effect.

**After editing:**

```
.venv\Scripts\python.exe -m tools.check_endgames --key <key>
.venv\Scripts\python.exe -m pytest tests/test_endgames.py
```

The tool checks the goal and every solution move with Stockfish, by the same `is_mistake` rule as the game. The tests require all five levels to exist, each with a name and at least 15 positions.

## settings.json

Created in the program folder, not in git and left out of the zip. Only keys in the defaults are loaded, and a value of the wrong type is ignored. Defaults are in `settings.DEFAULTS` and each mode's `SETTINGS`.

| Key | Default | Meaning |
| --- | --- | --- |
| `flipped` | `false` | Board orientation. |
| `show_coordinates` | `true` | |
| `sound` | `true` | |
| `piece_set` | `"cburnett"` | `cburnett` or `unicode`. |
| `board_theme` | `"green"` | `green`, `brown` or `blue`. |
| `window_geometry` | `""` | Tk geometry string. An off-screen position is dropped on load. |
| `last_directory` | `""` | For file dialogs. |
| `engine_path` | `""` | Stockfish location; empty means `engines/stockfish/`. |
| `details_open` | `{}` | Mode key → Comment & FEN open. |
| `board_analysis` | `false` | Engine analysis in Board mode. |
| `vs_minutes`, `vs_increment` | `30`, `0` | Clock (the dialog allows 1–180 minutes, 0–60 s). |
| `vs_engine`, `vs_level` | `"stockfish"`, `"1320"` | |
| `vs_color` | `"white"` | `white`, `black` or `random`. |
| `vs_start` | `"initial"` | `initial` or `current`. |
| `learn_opening` | `"reti"` | Opening `Key`. |
| `learn_role` | `"opening"` | `opening` or `reply`. |
| `learn_engine`, `learn_level` | `"stockfish"`, `"1320"` | |
| `learn_vary` | `true` | Vary the computer's replies. |
| `learn_suggest` | `true` | Suggest next move. |
| `learn_suggest_moves` | `12` | Last move of the opening phase (the dialog allows 10–15). |
| `end_difficulty` | `1` | Last level chosen. |
| `end_minutes` | `15` | Clock (the dialog allows 1–180). |
| `end_suggest` | `false` | Suggest next move. |
| `end_progress` | `{}` | Endgame `Key` → `played` or `solved`. Solved stays solved. |

## Saved games

Games are standard PGN in UTF-8. On reading, a file that is not valid UTF-8 is read as Windows-1252, so old files do not lose letters. FEN files hold one line. Single positions must pass `Board.is_valid()`, because Stockfish can crash on an invalid one.

Headers the program writes on top of the standard seven:

| Mode | Headers |
| --- | --- |
| All game modes, once over | `Result`; `Termination` when known (`normal`, `time forfeit`, `abandoned`) |
| Play vs Computer | `Event "vs Computer"`, `TimeControl` (`1800` or `300+3`), `WhiteElo` or `BlackElo` for the engine if known |
| Learn Openings | `Event "Opening training"`, `Opening`, `ECO` |
| Endgame Practice | `Event "Endgame practice"`, `SetUp`, `FEN`, `EndgameKey`, `Difficulty`, `Composer`, `Source`, `Year` when known, `TimeControl`, and once over `HintsUsed`, `TakeBacks` |

The clock is stored per move as a `[%clk 0:29:41]` comment command. Commands in `[%…]` stay in the file but are hidden in the move list and comment field (`visible_comment`), and editing a comment keeps them (`GameModel.set_comment`).
