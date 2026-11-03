"""BoardMode: the free board. Both sides can be moved; variations and comments work."""

from .. import strings as S
from .base import Mode


class BoardMode(Mode):
    key = "board"
    label = S.MODE_BOARD
