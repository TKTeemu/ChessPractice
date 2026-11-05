"""All user-visible text in one place."""

APP_TITLE = "Chessboard – Analysis"
UNTITLED = "Untitled"

# Menus
MENU_FILE = "File"
MENU_EDIT = "Edit"
MENU_VIEW = "View"
MENU_GAME = "Game"
MENU_HELP = "Help"

FILE_NEW = "New Game"
FILE_OPEN = "Open…"
FILE_SAVE = "Save"
FILE_SAVE_AS = "Save As…"
FILE_SAVE_FEN = "Save Position (FEN)…"
FILE_COPY_PGN = "Copy PGN"
FILE_COPY_FEN = "Copy FEN"
FILE_PASTE = "Paste PGN/FEN"
FILE_EXIT = "Exit"

EDIT_DELETE_LAST = "Delete Last Move"
EDIT_RESTORE = "Restore Deleted Moves"

VIEW_FLIP = "Flip Board"
VIEW_COORDS = "Show Coordinates"
VIEW_SOUND = "Sound"
VIEW_PIECE_SET = "Piece Set"
VIEW_BOARD_THEME = "Board Theme"
VIEW_ENGINE_PATH = "Stockfish Location…"

PIECE_SETS = {"cburnett": "Cburnett", "unicode": "Unicode"}
BOARD_THEMES = {"green": "Green", "brown": "Brown", "blue": "Blue"}

MODE_BOARD = "Board"
MODE_VS_COMPUTER = "Play vs Computer…"
MODE_LEARN_OPENINGS = "Learn Openings…"
MODE_ENDGAMES = "Endgame Practice…"
MODE_RESIGN = "Resign"
MODE_OPEN_IN_BOARD = "Open in Board Mode"
MODE_TAKE_BACK = "Take Back"

HELP_SHORTCUTS = "Keyboard Shortcuts"
HELP_ABOUT = "About"

# Buttons and labels
BTN_FIRST = "|◀"
BTN_PREV = "◀"
BTN_NEXT = "▶"
BTN_LAST = "▶|"
BTN_FLIP = "Flip"
BTN_NEW_GAME = "⟲ New Game"
DETAILS_OPEN = "▾ Comment & FEN"
DETAILS_CLOSED = "▸ Comment & FEN"
BTN_OK = "OK"
BTN_CANCEL = "Cancel"
BTN_COPY = "Copy"
LABEL_FEN = "FEN"
LABEL_COMMENT = "Comment"

# Move list context menu
CTX_PROMOTE = "Promote to Main Line"
CTX_DELETE_VARIATION = "Delete Variation"
CTX_DELETE_FROM_HERE = "Delete from Here"

# Status line
STATUS_WHITE_TO_MOVE = "White to move"
STATUS_BLACK_TO_MOVE = "Black to move"
STATUS_CHECK = "Check"
STATUS_CHECKMATE_WHITE = "Checkmate – White wins"
STATUS_CHECKMATE_BLACK = "Checkmate – Black wins"
STATUS_STALEMATE = "Stalemate – Draw"
STATUS_DRAW_INSUFFICIENT = "Draw – insufficient material"
STATUS_DRAW_REPETITION = "Draw – threefold repetition"
STATUS_DRAW_FIFTY = "Draw – 50-move rule"
STATUS_DRAW_FIVEFOLD = "Draw – fivefold repetition"
STATUS_DRAW_SEVENTYFIVE = "Draw – 75-move rule"

# Game chooser for multi-game PGN files
CHOOSE_GAME_TITLE = "Choose Game"
CHOOSE_GAME_PROMPT = "This file contains {count} games. Choose one:"

# File dialogs
FILETYPE_PGN = "PGN Game"
FILETYPE_FEN = "FEN Position"
FILETYPE_ALL = "All Files"

# Defaults written to PGN headers
DEFAULT_EVENT = "Analysis"
DEFAULT_WHITE = "White"
DEFAULT_BLACK = "Black"
UNKNOWN = "?"

# Messages
UNSAVED_TITLE = "Unsaved Changes"
UNSAVED_PROMPT = "Save changes to the current game?"
ERROR_TITLE = "Error"
ERROR_OPEN = "Could not open file:\n{error}"
ERROR_SAVE = "Could not save file:\n{error}"
ERROR_NO_GAMES = "No games found in the file."
ERROR_PASTE = "The clipboard does not contain a valid PGN or FEN."
ERROR_FEN = "Invalid FEN:\n{error}"
ERROR_INVALID_POSITION = ("not a valid chess position (for example a missing king, or the side "
                          "not to move is in check)")
GAME_SKIPPED = "Game {number}: {error}"
WARNING_TITLE = "Some Games Were Skipped"
WARNING_GAMES_SKIPPED = "{count} game(s) could not be read and were left out:\n{details}"
WARNING_MORE = "… and {count} more"
BLOCKED_BROWSE = "Moves can be browsed when the game has finished."
BLOCKED_IN_GAME = "Not available during this game. Switch to Board mode first."
ERROR_SETTINGS = "Could not save the settings to\n{path}\nThe details are in error.log."

SHORTCUTS_TITLE = "Keyboard Shortcuts"
SHORTCUTS_TEXT = """\
← / →\tMove back / forward
Home / End\tGo to start / end
↑ / ↓\tSwitch between variations
F\tFlip board
Ctrl+Z\tDelete last move (Learn Openings, Endgame Practice: take back)
Ctrl+Y\tRestore deleted moves
Ctrl+N\tNew game
Ctrl+O\tOpen
Ctrl+S\tSave
Ctrl+C\tCopy PGN
Ctrl+V\tPaste PGN or FEN"""

ABOUT_TITLE = "About"
ABOUT_TEXT = """\
Chessboard – Analysis

An offline chessboard for analysing games.
Copyright (C) 2026 Teemu. Free software under the GNU GPL v3 or later;
see the files LICENSE and NOTICE in the program folder.

Chess rules: python-chess by Niklas Fiekas (GPL-3.0).
Computer opponent: Stockfish by the Stockfish developers (GPL-3.0),
stockfishchess.org. Stockfish is a separate program in the engines folder.
Pieces: Cburnett set by Colin M.L. Burnett (CC BY-SA 3.0)."""

# Stockfish location dialog
ENGINE_PATH_TITLE = "Stockfish Location"
ENGINE_PATH_CURRENT = "The program uses:\n{path}"
ENGINE_PATH_DEFAULT = "the default place,\n{folder}"
ENGINE_PATH_CHOOSE = "Choose File…"
ENGINE_PATH_RESET = "Use Default"
FILETYPE_EXE = "Programs"

# Engine analysis in Board mode
BOARD_ANALYSIS = "Engine analysis"
BOARD_NO_ENGINE = "(Stockfish was not found)"
BOARD_ANALYSING = "Analysing…"
BOARD_ANALYSIS_LINE = "{score}   {line}"
BOARD_ANALYSIS_ERROR = "Analysis stopped: {error}"

# Engines and levels
ENGINE_STOCKFISH = "Stockfish"
ENGINE_RANDOM = "Random moves"
LEVEL_MAXIMUM = "Maximum"
LEVEL_RANDOM = ""
LEVEL_NONE = "–"   # shown in the dialog for a level without a label
STOCKFISH_MISSING = ("Stockfish was not found. Run Install.bat, or copy stockfish.exe into\n{folder}\n"
                     "(see INSTALL.txt), or choose its location with View > Stockfish Location.")

# Play vs Computer dialog
VS_TITLE = "Play vs Computer"
VS_ENGINE = "Engine"
VS_LEVEL = "Level"
VS_COLOR = "Your colour"
VS_START = "Start from"
VS_COLORS = {"white": "White", "black": "Black", "random": "Random"}
VS_STARTS = {"initial": "Initial position", "current": "Current position"}
VS_NOTE = "Moves cannot be taken back during the game."
VS_PLAY = "Play"
VS_TIME = "Time"
VS_MINUTES = "min, plus"
VS_INCREMENT = "s per move"
VS_START_FINISHED = "The current position is already finished. Choose the initial position."

# Play vs Computer game
VS_EVENT = "vs Computer"
VS_YOU = "You"
VS_YOUR_MOVE = "Your move"
VS_THINKING = "Computer is thinking…"
VS_SCORE_AHEAD = "Material: you +{points}"
VS_SCORE_BEHIND = "Material: you −{points}"
VS_SCORE_EVEN = "Material: even"
VS_RESIGNED = "You resigned – {engine} wins"
VS_TIMEOUT_YOU_LOSE = "Time out – {engine} wins"
VS_TIMEOUT_YOU_WIN = "{engine} ran out of time – you win"
VS_TIMEOUT_DRAW = "Time out – draw (no mating material)"
VS_ENGINE_ERROR = "Engine error – game stopped: {error}"
VS_RESIGN_TITLE = "Game in Progress"
VS_RESIGN_PROMPT = "Resign the game?"
VS_ENGINE_ERROR_TITLE = "Engine Error"

# Learn Openings dialog
LEARN_TITLE = "Learn Openings"
LEARN_SEARCH = "Search:"
LEARN_YOU_PLAY = "You play:"
LEARN_ROLES = {"opening": "the opening ({color})", "reply": "the reply ({color})"}
LEARN_VARY = "Vary the computer's replies"
LEARN_START = "Start"
LEARN_SUGGEST_UNTIL = "Suggest moves until move"
LEARN_MAIN_LINE = "Main line ({count} moves):"
LEARN_NO_BOOK = "No openings were found in\n{folder}"
LEARN_BOOK_ERRORS = "Some opening files were skipped:\n{errors}"
COLOR_NAMES = {True: "White", False: "Black"}

# Learn Openings game
LEARN_EVENT = "Opening training"
LEARN_LINE = "Line: {name}"
LEARN_THEORY = "Theory: {hits}/{total} moves"
LEARN_SUGGEST = "Suggest next move"
LEARN_PHASE_OVER = "(opening phase over)"
LEARN_OUT_OF_THEORY = "Out of theory"
LEARN_OUT_OF_THEORY_BOOK = "Out of theory. Book moves: {moves}"
LEARN_END_OF_THEORY = "End of theory – the engine takes over."

# Endgame Practice dialog
END_TITLE = "Endgame Practice"
END_DIFFICULTY = "Difficulty:"
END_LEVEL_COUNT = "({count}, {played} played, {solved} solved)"
END_TIME = "Time:"
END_MINUTES = "min"
END_START = "Start"
END_NO_POSITIONS = "No endgame positions were found in\n{folder}"
END_FILE_ERRORS = "Some positions were skipped:\n{errors}"
END_NO_ENGINE = ("Stockfish was not found: the computer plays the stored defence and then random\n"
                 "moves, and moves off the solution are not judged.")

# Endgame Practice game
END_EVENT = "Endgame practice"
END_LEVEL = "Level {level}"
END_CLASSIC = "Classic endgame position"
END_GOALS = {"win": "Goal: {color} to play and win", "draw": "Goal: {color} to play and draw"}
END_PLAYED = "Level {level} · {played} of {total} played · {solved} solved"
END_RETRY = "Retry"
END_NEXT = "Next Position"
END_COUNTERS = "Hints used: {hints} · Take backs: {take_backs}"
END_WRONG_TRY = "Missed – a known wrong try"
END_MISTAKE = "Missed – the engine says the goal is gone"
END_NO_JUDGE = "No engine to judge moves off the solution"
LIGHT_TEXTS = {"pending": "In progress", "success": "Solved", "fail": "Missed – keep playing"}
