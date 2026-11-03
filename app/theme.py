"""Colours and fonts shared by the views. Values only: no tkinter here."""

# Board square colours: theme key -> (light, dark). Keys match strings.BOARD_THEMES.
BOARD_THEMES = {
    "green": ("#EEEED2", "#769656"),
    "brown": ("#F0D9B5", "#B58863"),
    "blue": ("#DEE3E6", "#8CA2AD"),
}
DEFAULT_BOARD_THEME = "green"

BACKGROUND = "#302E2B"     # window and board surround
PANEL_BG = "#262522"       # right-hand panel and move list
PANEL_FG = "#E8E6E3"
MUTED_FG = "#A9A7A3"       # field labels and variations
BUTTON_BG = "#3C3A37"
BUTTON_ACTIVE = "#4F4C49"
ENTRY_BG = "#1E1D1B"

# Chess clocks next to the player names (Play vs Computer)
CLOCK_BG = "#262522"
CLOCK_FG = "#A9A7A3"
CLOCK_ACTIVE_BG = "#E8E6E3"   # the side whose clock is running
CLOCK_ACTIVE_FG = "#1E1D1B"
CLOCK_LOW_FG = "#E04B3A"      # under a minute

# Move list
MOVE_NUMBER_FG = "#8B8987"
MOVE_COMMENT_FG = "#7FA650"
MOVE_CURRENT_BG = "#4B4847"
MOVE_CURRENT_FG = "#FFFFFF"

# Board overlays
HIGHLIGHT = "#F7EC5A"      # last move and selected square (blended 50 %)
MARK = "#EB6150"           # right-click square marks (blended 80 %)
ARROW_RGBA = (255, 170, 0, 205)
# Suggestion arrows set by the mode: (colour, width factor) per style
HINT_STYLES = {"main": ((40, 140, 230, 215), 1.0), "alt": ((40, 140, 230, 110), 0.6)}
TARGET_RGBA = (0, 0, 0, 40)   # dots and rings on the squares a picked-up piece can go to
CHECK_RGB = (230, 30, 30)
DIM_RGBA = (0, 0, 0, 90)      # over the board while the promotion picker is open
PROMOTION_BG = "#FFFFFF"
PROMOTION_OUTLINE = "#C0C0C0"
# Unicode pieces: (fill, outline) per colour
UNICODE_WHITE = ("#FFFFFF", "#000000")
UNICODE_BLACK = ("#202020", "#E0E0E0")

# Dialogs use the system colours, except for these
DIALOG_MUTED_FG = "#555555"
DIALOG_WARNING_FG = "#A03020"   # e.g. "Stockfish was not found"

# Fonts
FONT_FAMILY = "Segoe UI"
MONO_FAMILY = "Consolas"
FONT_SMALL = (FONT_FAMILY, 9)
FONT_SMALL_BOLD = (FONT_FAMILY, 9, "bold")
FONT = (FONT_FAMILY, 10)
FONT_BOLD = (FONT_FAMILY, 10, "bold")
FONT_ITALIC = (FONT_FAMILY, 10, "italic")
FONT_LARGE = (FONT_FAMILY, 11)
FONT_LARGE_BOLD = (FONT_FAMILY, 11, "bold")
FONT_STATUS = (FONT_FAMILY, 12, "bold")
FONT_MONO_SMALL = (MONO_FAMILY, 9)
FONT_CLOCK = (MONO_FAMILY, 15, "bold")
