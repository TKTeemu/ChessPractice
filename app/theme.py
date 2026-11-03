"""Colours shared by several views. Values only: no tkinter here."""

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
