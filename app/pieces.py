"""Rendering piece images and caching them per square size."""

import tkinter as tk
from pathlib import Path

import chess
import chess.svg
from PIL import Image, ImageDraw, ImageFont, ImageTk

from .theme import UNICODE_BLACK, UNICODE_WHITE

SVG_SIZE = 45  # Cburnett pieces are drawn on a 45x45 grid
UNICODE_GLYPHS = {"k": "♚", "q": "♛", "r": "♜", "b": "♝", "n": "♞", "p": "♟"}
UNICODE_FONTS = ("seguisym.ttf", "C:/Windows/Fonts/seguisym.ttf")


def svg_file_name(symbol):
    return ("w" if symbol.isupper() else "b") + symbol.upper() + ".svg"


class PieceImages:
    def __init__(self, pieces_dir, piece_set="cburnett"):
        self.pieces_dir = Path(pieces_dir)
        self.piece_set = piece_set
        self._photos = {}
        self._size = None

    def set_piece_set(self, piece_set):
        if piece_set != self.piece_set:
            self.piece_set = piece_set
            self._photos.clear()

    def photo(self, symbol, size):
        """Tk image for a piece symbol ('P', 'k', ...) at the given square size."""
        if size != self._size:
            self._photos.clear()  # keep only the current size in memory
            self._size = size
        if symbol not in self._photos:
            self._photos[symbol] = self._make_photo(symbol, size)
        return self._photos[symbol]

    def _make_photo(self, symbol, size):
        if self.piece_set == "cburnett":
            try:
                return self._render_svg(symbol, size)
            except (tk.TclError, OSError, KeyError):
                pass
        return ImageTk.PhotoImage(self._render_unicode(symbol, size))

    def _svg_source(self, symbol):
        path = self.pieces_dir / "cburnett" / svg_file_name(symbol)
        if path.exists():
            return path.read_text(encoding="utf-8")
        # Fall back to the copy of the Cburnett set bundled with python-chess
        return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'viewBox="0 0 {SVG_SIZE} {SVG_SIZE}" width="{SVG_SIZE}" height="{SVG_SIZE}">'
                f'{chess.svg.PIECES[symbol]}</svg>')

    def _render_svg(self, symbol, size):
        """Tk 9 reads SVG itself (nanosvg), so no extra library is needed."""
        return tk.PhotoImage(data=self._svg_source(symbol), format=f"svg -scale {size / SVG_SIZE}")

    def _render_unicode(self, symbol, size):
        font = None
        for name in UNICODE_FONTS:
            try:
                font = ImageFont.truetype(name, int(size * 0.8))
                break
            except OSError:
                continue
        if font is None:
            font = ImageFont.load_default()
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        fill, outline = UNICODE_WHITE if symbol.isupper() else UNICODE_BLACK
        draw.text((size / 2, size * 0.52), UNICODE_GLYPHS[symbol.lower()], font=font, anchor="mm",
                  fill=fill, stroke_width=max(1, size // 30), stroke_fill=outline)
        return img
