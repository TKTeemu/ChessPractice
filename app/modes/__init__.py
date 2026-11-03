"""Modes. The order of MODES is the order in the Game menu; the first one is the start mode."""

from .base import MenuItem, Mode, ModeContext
from .board import BoardMode
from .endgames import EndgameMode
from .learn_openings import LearnOpeningsMode
from .vs_computer import VsComputerMode

MODES = [BoardMode, VsComputerMode, LearnOpeningsMode, EndgameMode]


def mode_class(key):
    return next((cls for cls in MODES if cls.key == key), None)


def mode_settings():
    """The SETTINGS of every mode in one dict, for Settings(path, extra_defaults)."""
    merged = {}
    for cls in MODES:
        merged.update(cls.SETTINGS)
    return merged
