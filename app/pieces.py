"""Rendering piece images and caching them per square size."""

from pathlib import Path

import chess
import chess.svg
import pymupdf
from PIL import Image, ImageDraw, ImageFont, ImageTk

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
        key = symbol
        if key not in self._photos:
            self._photos[key] = ImageTk.PhotoImage(self.image(symbol, size))
        return self._photos[key]

    def image(self, symbol, size):
        if self.piece_set == "cburnett":
            try:
                return self._render_svg(symbol, size)
            except Exception:
                pass
        return self._render_unicode(symbol, size)

    def _svg_source(self, symbol):
        path = self.pieces_dir / "cburnett" / svg_file_name(symbol)
        if path.exists():
            return path.read_bytes()
        # Fall back to the copy of the Cburnett set bundled with python-chess
        return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'viewBox="0 0 {SVG_SIZE} {SVG_SIZE}" width="{SVG_SIZE}" height="{SVG_SIZE}">'
                f'{chess.svg.PIECES[symbol]}</svg>').encode()

    def _render_svg(self, symbol, size):
        doc = pymupdf.open(stream=self._svg_source(symbol), filetype="svg")
        try:
            page = doc[0]
            scale = size / page.rect.width
            pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=True)
            img = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
        finally:
            doc.close()
        if img.size != (size, size):
            img = img.resize((size, size), Image.LANCZOS)
        return img

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
        white = symbol.isupper()
        draw.text((size / 2, size * 0.52), UNICODE_GLYPHS[symbol.lower()], font=font, anchor="mm",
                  fill="#FFFFFF" if white else "#202020",
                  stroke_width=max(1, size // 30), stroke_fill="#000000" if white else "#E0E0E0")
        return img
