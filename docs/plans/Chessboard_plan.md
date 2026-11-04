# Chessboard – plan for the analysis application

> **Historical document.** This plan has been implemented and is no longer updated. The current structure of the program is described in [ARCHITECTURE.md](../ARCHITECTURE.md) and [EXTENDING.md](../EXTENDING.md).

2.11.2026

> This is the original plan. The current structure of the implementation, the deviations from the plan and the instructions for adding an engine are in [docs/ARCHITECTURE.md](../ARCHITECTURE.md); the user guide is in [README.md](../../README.md).

## Goal and scope

Build an offline chessboard written in Python for analysing games: only legal moves, free movement in the move history and saving to standard formats. The look and feel follow Chess.com, but the graphics and sounds are our own, because Chess.com's material is protected by copyright.

**Included:**

- Enforcement of legal moves (including castling, en passant, promotion, checkmate, stalemate, repetitions and the 50-move rule)
- The user makes the moves for both sides
- Board flip: White or Black at the bottom
- Move history, going back and forward, side variations
- Saving and opening games (PGN) and positions (FEN)
- Setting up your own position with FEN notation
- Chess.com-style sounds

**Not included:** a chess engine, move evaluation, a network connection, an exe package.

**Language:** The user interface is entirely in English: menus, buttons, status line, dialogs and error messages. The wording of saved files is also in English (PGN headers, texts added by the program, settings.json keys, error.log). All visible texts are collected in one module, `app/strings.py`, so they are easy to edit.

## Technology choices

Basic idea: as few new dependencies as possible. Almost everything comes from the Python standard library or from packages that are already installed; the only addition is the pure-Python library python-chess.

| Area | Choice | Rationale |
| --- | --- | --- |
| User interface | tkinter (standard library) | Comes with Python, no installation and no new binaries. A Canvas is enough for drawing and dragging the board. |
| Chess rules | python-chess (`pip install chess`) | Tested legal move generation, PGN and FEN support, variation tree. Pure Python, works on 3.15. |
| Images | Pillow 12.3 (installed) | Scaling the piece images to the square size, and transparency. |
| Rendering SVG pieces | PyMuPDF 1.28 (installed) | Opens SVG files and renders them to PNG without additional libraries. |
| Sounds | winsound (standard library) | Plays WAV files asynchronously (`SND_ASYNC`), no dependencies. |
| Settings | json (standard library) | A readable settings file. |
| Tests | pytest 9.2 (installed) | Unit tests for the rules and file logic. |

Before starting, check that the Python installation includes Tcl/Tk: `python -m tkinter` opens a small test window. If it does not, modify the Python installation and select Tcl/Tk.

Alternatives not chosen: PySide6/PyQt (a large binary package, wheels may not yet exist for 3.15, F-Secure risk) and pygame (an unnecessary dependency). Writing our own move generator would be possible, but error-prone and slow to do.

## F-Secure compatibility

The application is always run with python.org's signed `pythonw.exe`, and no new exe file is created on disk. F-Secure's DeepGuard then sees only a familiar, signed program reading text files.

**The most important detail: no venv.** A Windows venv copies its own `python.exe` and `pythonw.exe` launchers into the `Scripts` folder. In F-Secure's eyes they are new, rare exe files, which is exactly what we want to avoid. Therefore python-chess is installed into a subfolder of the application folder:

```
python -m pip install --target vendor chess
```

The program adds the `vendor` folder to `sys.path` at startup. python-chess has no command-line tools, so this creates no exe files.

**Other rules:**

- No PyInstaller or other exe packaging (altgraph and pefile on the machine are leftovers of PyInstaller; they are not used).
- No network traffic, no registry modifications, no background processes, no `subprocess` calls. The program writes only to its own folder and to the save files the user chooses.
- The sound and image files are created or copied locally. If a file is downloaded from the net (e.g. a zip), its "Mark of the Web" is removed: file properties → Unblock, or `Unblock-File` in PowerShell.
- Starting with a .bat file is plain text and calls the already installed Python.
- If F-Secure still complains, the application folder can be added to F-Secure's exclusions, but the goal is that this is not needed.

## Functions and user interface

As on Chess.com, the window is divided into two parts: the board on the left, the move list and controls on the right. The board scales with the window size.

**Board**

- Moving by dragging or by two clicks (from-square and to-square)
- Legal targets of the selected piece: a dot on an empty square, a ring around a capturable piece
- The latest move is highlighted in yellowish, a king in check in red
- Illegal move: the piece returns to its place and an "illegal" sound plays
- Promotion: a small menu (Q, R, B, N) over the target square
- Coordinates (a–h, 1–8) at the edges of the squares, rotating with the board
- Analysis markings: right-click highlights a square, right-drag draws an arrow; left-click clears
- Above and below the board: the players' names and captured pieces, and the material difference (+2 etc.)

**Right panel**

- Move list in pairs (1. e4 e5 2. Nf3 …), the current move highlighted, a click jumps to the move
- Side variations indented in parentheses; right-click menu: Promote to Main Line, Delete Variation, Delete from Here
- Navigation: |◀ ◀ ▶ ▶| and a Flip Board button
- A comment field for the selected move (saved in the PGN)
- Status line: White to move / Black to move, Check, Checkmate, Stalemate, Draw (threefold repetition, 50-move rule, insufficient material)
- A FEN line for copying

**Going back and variations:** When the user goes back and makes a different move, a new side variation is created by default and nothing is lost. If the same move already exists, the program just moves to it. Ctrl+Z removes the latest move entirely.

**Menus:** File (New Game, Open…, Save, Save As…, Copy PGN, Copy FEN, Paste PGN/FEN, Exit), View (Flip Board, Show Coordinates, Sound, Piece Set, Board Theme), Game (the modes Board and Play vs Computer…, and the active mode's own actions), Help (Keyboard Shortcuts, About).

**Keyboard shortcuts**

| Key | Function |
| --- | --- |
| ← / → | Move back / forward |
| Home / End | To the start / to the end |
| ↑ / ↓ | Between variations |
| F | Flip the board |
| Ctrl+Z | Delete the latest move |
| Ctrl+N / Ctrl+O / Ctrl+S | New / Open / Save |
| Ctrl+C / Ctrl+V | Copy / paste PGN or FEN |

## File formats

Games are saved in PGN format and single positions in FEN format. Both are international text standards that open in Notepad as well as in Chess.com, Lichess and ChessBase.

| What is saved | Format | Extension | Contents |
| --- | --- | --- | --- |
| Game | PGN (Portable Game Notation) | .pgn | Header information, moves, variations, comments |
| Position | FEN (Forsyth–Edwards Notation) | .fen | One line: position, side to move, castling, en passant, move counters |
| Game from a custom position | PGN + `[SetUp "1"]` and `[FEN "…"]` | .pgn | Same as a game, with the starting position included |

An example PGN file:

```
[Event "Analysis"]
[Site "?"]
[Date "2026.11.02"]
[Round "?"]
[White "White"]
[Black "Black"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 (3. Bc4 Bc5) 3... a6 {Morphy Defence} *
```

Files are saved with UTF-8 encoding. When a multi-game PGN is opened, a list is shown from which the game is chosen. Moves are shown and saved in standard English algebraic notation (K, Q, R, B, N). The texts written by the program are in English: the default values of the header fields (Event "Analysis", White "White", Black "Black", unknown information "?") and the file types of the save dialogs (PGN Game, FEN Position). Comments and names written by the user are saved as they are.

## Sounds and piece graphics

Chess.com's sounds and pieces cannot be copied, so we make our own in a similar style. The sounds are synthesised with Python, so they need no downloads and no licences.

**Sounds:** `tools/make_sounds.py` creates the WAV files with the standard library's `wave` and `math` modules: a short, decaying wooden "click" (a noise burst + a low resonance), varied according to the event.

| Event | Sound |
| --- | --- |
| Move | A short wooden click |
| Capture | A sharper, harder click |
| Castling | Two quick clicks |
| Check | A click + a high beep |
| Promotion | A rising two-tone |
| End of the game (checkmate, stalemate, draw) | A soft harmonic signal |
| Illegal move | A low, short "thud" |

The sound is played with `winsound.PlaySound(…, SND_FILENAME | SND_ASYNC)`, so the user interface does not stop. When moving in the move history, the sound of that move is played, as on Chess.com. The sounds can be switched off.

**Pieces:** two options, both offline.

1. **Default: the Cburnett set** (the SVG pieces from Wikimedia Commons that Lichess also uses; the licence permits use, and the author is credited in the About window). The 12 SVG files are fetched once and saved in the `assets/pieces/` folder. PyMuPDF renders them to PNG according to the square size, and Pillow handles the cache.
2. **Fallback set: Unicode characters** (♔♕♖♗♘♙) drawn with Pillow from Windows' Segoe UI Symbol font, with an outline. Works without any downloaded file.

**Board colours:** by default a Chess.com-like green–cream (#769656 / #EEEED2), plus brown and blue themes.

## Architecture and folder structure

The application is divided into a model (the game state and rules) and a view (tkinter). The model knows nothing about the user interface, so it can be tested with pytest without windows.

```
C:\Users\Omistaja\Chessboard\
├── Chessboard.bat          launcher
├── chessboard.pyw          main program (pythonw, no console window)
├── settings.json            settings (created on the first run)
├── app\
│   ├── model.py             GameModel: python-chess game tree, current node, moves, variations
│   ├── fileio.py            reading and writing PGN/FEN
│   ├── board_view.py        the board Canvas: drawing, dragging, highlights, arrows, promotion menu
│   ├── movelist_view.py     the move list and variations (a Text widget with tags)
│   ├── main_window.py       window, menus, keyboard shortcuts, status line
│   ├── dialogs.py           the game selection and game information dialogs
│   ├── pieces.py            rendering and caching the piece images
│   ├── sounds.py            playing the sounds
│   ├── settings.py          reading/saving the settings
│   ├── strings.py           all texts visible to the user
│   └── theme.py             shared colours and board themes
├── assets\
│   ├── pieces\cburnett\     12 SVG files
│   └── sounds\              move.wav, capture.wav, castle.wav, check.wav, promote.wav, end.wav, illegal.wav
├── tools\
│   └── make_sounds.py       sound generation
├── vendor\                  python-chess (pip --target)
├── tests\                   pytest tests
└── Games\                   default folder for saves
```

**Data flow:** the view sends the user's action (e.g. the move e2→e4) to the model. The model checks legality, updates the game tree and returns an event (move, capture, check…). The main window updates the board and the move list and plays the sound that matches the event. This keeps the rules in one place and the user interface thin.

## Installation and startup

Installation is a one-time job and takes a few minutes; an internet connection is needed only to fetch python-chess and the piece sets.

1. Create the folder `C:\Users\Omistaja\Chessboard` and copy the application files there.
2. Check Tk: `python -m tkinter` (a small window opens).
3. Install python-chess into the application folder (no venv, see the F-Secure section):

   ```
   cd C:\Users\Omistaja\Chessboard
   python -m pip install --target vendor chess
   ```
4. Create the sounds: `python tools\make_sounds.py`
5. Start by double-clicking `Chessboard.bat` (or `chessboard.pyw` directly).

`Chessboard.bat`:

```
@echo off
cd /d "%~dp0"
start "" pythonw chessboard.pyw
```

`pythonw` starts the program without a black console window. A desktop shortcut can be made to the .bat file. For troubleshooting, the program can be run with the command `python chessboard.pyw`, in which case error messages appear in the console; errors are also written to the `error.log` file.

## Implementation phases and testing

The implementation proceeds in seven phases so that after each one there is a usable program. Phases 1–4 are already enough to replace a physical board.

1. **Base:** folder structure, python-chess in the vendor folder, Tk check, an empty window started with the .bat launcher. Test that F-Secure does not react.
2. **Board and moves:** drawing the board, pieces, click and drag moves, legal targets, promotion menu, board flip.
3. **History:** move list, navigation with buttons and arrow keys, going back, creating and managing variations.
4. **Saving:** saving and opening PGN and FEN, clipboard, game information.
5. **Sounds:** generating the sounds and playing them according to events.
6. **Analysis tools:** arrows and square highlights, comments, captured pieces and material difference.
7. **Polish:** settings (theme, piece set, sounds), remembering the window size, error log, About window.

**Testing**

- pytest for the model: the numbers of legal moves from known positions (perft-style checks), castling, en passant, promotion, checkmate and stalemate
- A PGN round trip: open → save → open again, variations and comments are preserved
- A FEN round trip
- By hand: a famous game (e.g. Morphy–Duke and Count, 1858) is entered on the board and the move list is compared with the known PGN
- F-Secure: the whole installation and the first start are run in a clean folder and F-Secure's event log is checked

**Open questions**

- Is one game at a time enough, or are tabs needed for several games? => One game at a time is enough.
