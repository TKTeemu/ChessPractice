# Decisions

Why the program is the way it is, for choices the code cannot explain by itself. Check here before undoing something that looks odd. When a decision changes, edit its entry.

The original plans (November 2026) are in git history under `docs/plans/`, for the full reasoning.

## Platform and tools

| Decision | Why | Revisit if |
| --- | --- | --- |
| **tkinter** for the interface | Comes with Python, adds no binaries, and a Canvas is enough for the board. PySide6/PyQt are large binary packages that may lag new Python versions; pygame would be an unnecessary dependency. | The interface outgrows Tk. |
| **python-chess** for the rules | Tested move generation, PGN, FEN and variation trees. Writing our own generator would be slow and error-prone. | |
| **One `.venv`, one way to install libraries.** `Install.bat` builds it on each computer | Libraries used to be split between the system Python and a `vendor/` folder filled with `pip --target`, because F-Secure's DeepGuard was assumed to dislike a venv. That was never tested and it cost `sys.path` patches and separate install steps. Tested in November 2026 on the developer's machine with F-Secure running: nothing was blocked, and the venv's `python.exe` and `pythonw.exe` are launchers signed by the Python Software Foundation. | F-Secure starts flagging the venv. The fallback is one `pip --target` folder holding every library. |
| **No PyInstaller or other exe packaging.** Tools run as `python -m <module>` | DeepGuard sees new, rare exe files as suspect: only python.org's signed Python and launchers and one known engine exe run. | |
| **Only Stockfish as an exe, in one known place** | A deliberate, controlled exception to "no new exes". No installer, service or registry changes, and a checksum-verified download. | |
| **Offline at run time** | An absolute requirement. Data is local, the engine talks only through pipes, and only `Install.bat` and development commands use the network. | |
| **Own UCI client** rather than `chess.engine` | `chess.engine` in python-chess 1.11.2 uses an asyncio API removed in Python 3.16. The commands needed are few, and it also lets us set `CREATE_NO_WINDOW`, which `popen_uci` does not. | python-chess is updated and the client becomes a burden. |
| **Exactly Python 3.15** | 3.16 fails at `import chess.pgn`; see [MAINTENANCE.md](MAINTENANCE.md#moving-to-a-new-python-minor-version). | python-chess is fixed. |
| **Tk's own SVG support** for pieces, rather than PyMuPDF | One package less: Tk 9 reads SVG. Pillow stays for Unicode glyphs and alpha overlays. | |
| **Stockfish** as the engine | Open source, strong, adjustable strength through `UCI_Elo`, and a single file. A Python engine would be weak and hard to calibrate. | |
| **Stockfish light settings:** `Threads=1`, `Hash=64` | The engine must not make the machine busy while the user thinks. | Analysis depth matters more. |
| **Own sounds, Cburnett pieces** | The look follows Chess.com, but its graphics and sounds are copyrighted. Sounds are synthesised by `tools/make_sounds.py`. Cburnett is CC BY-SA and credited. | |
| **GPL-3.0-or-later** | Required because the program is distributed with python-chess. | |

## Product behaviour

| Decision | Why | Revisit if |
| --- | --- | --- |
| **English interface**, all text in `strings.py` | Decided at the start, including opening names and text in saved files. | |
| **One game at a time**, no tabs | Decided by the user. | |
| **Going back and moving creates a variation** | Nothing is lost by trying a move. | |
| **No automatic saving of finished games** | Decided by the user. | |
| **Player names are not editable** | Not needed, decided by the user. | |
| **Exit asks nothing** | Reduces pop-ups: the unsaved game is not kept and a running game is not resigned. Tests guard this (`test_exit_*`). | Users lose work they wanted. |
| **The program always starts in Board mode** | An unfinished game against the computer is never resumed. | |
| **Board is last in the Game menu**, as "Board (free analysis)" | Decided by the user: it is the least interesting entry. The menu order and the start mode are therefore separate (`MODES`, `START_MODE`). | |
| **Play vs Computer: no take-backs, no browsing until the game ends** | It is a real game, with a clock. Browsing opens when it is over, and Open in Board Mode allows analysis. | |
| **Learn Openings: leaving the book does not stop the game** | The engine takes over. If suggestions are on, the book moves are named and shown as arrows until the next user move. | |
| **Learn Openings: opening phase** | Suggestions end at the move limit (default 12, range 10–15) or after two user moves outside the book. | |
| **Endgame Practice: opponent always at full strength** | Perfect defence is what is being practised, even on low levels, so there is no level picker. | Full strength proves too hard for beginners. |
| **Endgame Practice: no Resign and no question on leaving** | It is practice, not a game to give up, and Retry is pressed again and again. A running attempt is simply resigned when left. A New Game that replaces moves still offers a save. | |
| **Endgame Practice: Take Back does not wind back the clock** | Decided by the user. | |
| **Endgame Practice: the light is above the board**, in place of the material score | Decided by the user. | |
| **Endgame Practice: a line directly above the board says "You play Black · White to move"** | Requested by the user: the colour could not be seen without clicking a piece. It names both, so the user's colour is clear also during the computer's turn. | |
| **Endgame Practice: hints and take-backs do not block green** | They are shown as counters and saved in the PGN instead. | |
| **Endgame Practice: all draws by the rules end the game** | In drawing studies the game ends in exactly that way. | |
| **Drawn positions continue across runs** | `end_progress` remembers what was played; positions not yet played come first. | |

## Tuned values

| Value | Where | Why |
| --- | --- | --- |
| A mistake needs the score below `WIN_LOST_CP` (+150) or `LOSS_CP` (−300) **and** a drop of at least `DROP_CP` (100) | `endgame_game.is_mistake` | Stockfish's NNUE scores some won endings low (bishop and knight about +180), so a fixed limit alone would turn correct moves red. |
| Engine levels 1320–2800, then Maximum | `engines/stockfish.py` | 1320 has been the lowest `UCI_Elo`. The scale is calibrated against engines, so it does not match FIDE or Chess.com figures. |
| Below the minimum, a level is clamped, not dropped | `StockfishEngine._set` | Levels keep working if a release changes its limits. |
| 400 ms before book and stored replies | `BOOK_DELAY_MS`, `TREE_DELAY_MS` | So the reply is seen as a separate move. |
| Fixed time per move, not a share of the clock | `go movetime` in `uci.py` | Simple and predictable. `go wtime btime` is possible if an engine should manage its own time. |

## Content

- **English Defence is ECO A40**, not A14 as in the original list: 1.c4 e6 2.d4 b6 transposes to 1.d4 e6 2.c4 b6, and books and databases use A40.
- **Benko's Opening is in *Irregular openings*:** 1.g3 is A00 in the ECO classification.
- **Gambits are a group of their own** while there are few openings. If other 1.e4 and 1.d4 openings arrive, they can move to *Open games* and *Closed games* by changing a header.
- **Explanatory comments are our own words,** not copied from books. Moves and positions are facts.
- **Where the endgame positions come from:** the textbook positions of levels 1–3 and Lasker–Reichhelm were set up by hand, and their solution lines, where not written by hand, are Stockfish's main lines. Apart from Saavedra, Réti and Lasker–Reichhelm, levels 4 and 5 were found by a search with Stockfish (realistic material, exactly one move keeps the goal; on level 5 at least twice in a row). They are not master games or published studies, so their source is empty and they show *Classic endgame position*. Never add a source that has not been verified.

## Ideas not built

These were considered and left out, not rejected. The structure allows them.

- Endgame Practice: statistics per position, repeating failed positions, choosing a position from a list, a weaker opponent for beginners.
- Learn Openings: a repetition exercise with statistics, an engine suggestion after the book ends, more openings (just PGN files).
- Board mode: naming the opening on the board using `OpeningBook`, a position editor (today a position is set up by typing a FEN).
- Engines: easier levels through the `Skill Level` option.
- Tools: importing named lines from the CC0 `lichess-org/chess-openings` data into the book's PGN format.
