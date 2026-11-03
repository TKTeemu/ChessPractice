"""The board Canvas: drawing, click and drag moves, highlights, arrows and the promotion picker."""

import math
import time
import tkinter as tk

import chess
from PIL import Image, ImageDraw, ImageTk

from .theme import (ARROW_RGBA, BACKGROUND, BOARD_THEMES as THEMES, CHECK_RGB, DEFAULT_BOARD_THEME, DIM_RGBA,
                    FONT_FAMILY, HIGHLIGHT, HINT_STYLES, MARK, PROMOTION_BG, PROMOTION_OUTLINE, TARGET_RGBA)

PROMOTION_PIECES = (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
DRAG_THRESHOLD = 4         # pixels the mouse must move before a click becomes a drag
SUPERSAMPLE = 3
ANIM_SECONDS = 0.16      # how long a piece takes to slide to its new square
ANIM_FRAME_MS = 15


def blend(c1, c2, amount):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * amount):02X}" for x, y in zip(a, b))


class BoardCanvas(tk.Canvas):
    """Geometry and square drawing of the board."""

    def __init__(self, master, pieces, **kw):
        super().__init__(master, highlightthickness=0, bg=BACKGROUND, **kw)
        self.pieces = pieces
        self.flipped = False
        self.show_coords = True
        self.theme = DEFAULT_BOARD_THEME
        self.size = 0
        self.ox = self.oy = 0

    def _layout(self):
        w, h = self.winfo_width(), self.winfo_height()
        self.size = max(8, min(w, h) // 8)
        self.ox = (w - self.size * 8) // 2
        self.oy = (h - self.size * 8) // 2

    def _col_row(self, square):
        f, r = chess.square_file(square), chess.square_rank(square)
        return (7 - f, r) if self.flipped else (f, 7 - r)

    def _xy(self, square):
        col, row = self._col_row(square)
        return self.ox + col * self.size, self.oy + row * self.size

    def _center(self, square):
        x, y = self._xy(square)
        return x + self.size / 2, y + self.size / 2

    def _cell_at(self, x, y):
        if self.size <= 0:
            return None
        col, row = (x - self.ox) // self.size, (y - self.oy) // self.size
        if 0 <= col < 8 and 0 <= row < 8:
            return int(col), int(row)
        return None

    def square_at(self, x, y):
        cell = self._cell_at(x, y)
        if cell is None:
            return None
        col, row = cell
        return chess.square(7 - col, row) if self.flipped else chess.square(col, 7 - row)

    def _draw_squares(self, highlighted=(), marks=()):
        s = self.size
        light, dark = THEMES[self.theme]
        for sq in chess.SQUARES:
            x, y = self._xy(sq)
            base = dark if (chess.square_file(sq) + chess.square_rank(sq)) % 2 == 0 else light
            color = base
            if sq in highlighted:
                color = blend(color, HIGHLIGHT, 0.5)
            if sq in marks:
                color = blend(base, MARK, 0.8)
            self.create_rectangle(x, y, x + s, y + s, fill=color, outline="")

    def _draw_pieces(self, board, skip=()):
        for sq, piece in board.piece_map().items():
            if sq not in skip:
                cx, cy = self._center(sq)
                self.create_image(cx, cy, image=self.pieces.photo(piece.symbol(), self.size))

    def _draw_coords(self):
        light, dark = THEMES[self.theme]
        s = self.size
        font = (FONT_FAMILY, max(7, s // 7), "bold")
        pad = max(2, s // 20)
        for i in range(8):
            # Rank numbers in the left column, file letters in the bottom row
            rank_sq = chess.square(7 if self.flipped else 0, i)
            x, y = self._xy(rank_sq)
            color = light if (chess.square_file(rank_sq) + i) % 2 == 0 else dark
            self.create_text(x + pad, y + pad, text=str(i + 1), anchor="nw", fill=color, font=font)

            file_sq = chess.square(i, 7 if self.flipped else 0)
            x, y = self._xy(file_sq)
            color = light if (i + chess.square_rank(file_sq)) % 2 == 0 else dark
            self.create_text(x + s - pad, y + s - pad, text=chess.FILE_NAMES[i], anchor="se",
                             fill=color, font=font)


class BoardView(BoardCanvas):
    """The interactive game board. Reads the position from the model and reports moves
    through callbacks; it never changes the model itself."""

    def __init__(self, master, model, pieces, on_move, on_illegal, can_move=lambda color: True, **kw):
        super().__init__(master, pieces, **kw)
        self.model = model
        self.on_move = on_move          # on_move(from_sq, to_sq, promotion)
        self.on_illegal = on_illegal    # called when a piece is dropped on an illegal square
        self.can_move = can_move        # can_move(color): may the user pick up this colour now?

        self.selected = None
        self.targets = set()
        self.drag = None
        self.promotion = None
        self.marks = set()
        self.arrows = set()
        self.hints = ()           # (from_sq, to_sq, style) from the mode; kept when the user draws
        self._right_start = None
        self._photos = {}   # cached overlay images, keyed by name and size
        self._shown_node = None   # the node drawn last; a step forward from it is animated
        self._dropped = False     # the last move was dragged: the piece is already there
        self.anim = None          # {"pieces": [(symbol, from, to)], "captured": (symbol, sq) or None, ...}

        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._motion)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<ButtonPress-3>", self._right_press)
        self.bind("<ButtonRelease-3>", self._right_release)

    # --- Public -----------------------------------------------------------

    def position_changed(self):
        """Call after the current position changes: drops selection and annotations.
        A single move forward (played or stepped through) slides the piece to its square."""
        self.selected = None
        self.targets = set()
        self.drag = None
        self.promotion = None
        self.marks.clear()
        self.arrows.clear()
        node = self.model.node
        if node is not self._shown_node:
            self._stop_animation()
            if node.parent is not None and node.parent is self._shown_node and not self._dropped:
                self._start_animation(node.parent.board(), node.move)
            self._shown_node = node
        self._dropped = False
        self.redraw()

    def set_hints(self, hints):
        """Suggestion arrows: [(from_sq, to_sq, "main" | "alt")]. Redraws only if they changed."""
        hints = tuple(hints)
        if hints != self.hints:
            self.hints = hints
            self.redraw()

    def set_flipped(self, flipped):
        self.flipped = flipped
        self.promotion = None
        self.redraw()

    def set_theme(self, theme):
        self.theme = theme if theme in THEMES else DEFAULT_BOARD_THEME
        self.redraw()

    def set_show_coords(self, show):
        self.show_coords = show
        self.redraw()

    # --- Drawing ----------------------------------------------------------

    def redraw(self):
        self.delete("all")
        self._layout()
        s = self.size
        board = self.model.board
        last = self.model.node.move
        highlighted = {last.from_square, last.to_square} if last else set()
        if self.selected is not None:
            highlighted.add(self.selected)
        self._draw_squares(highlighted, self.marks)

        if board.is_check():
            king = board.king(board.turn)
            if king is not None:
                cx, cy = self._center(king)
                self.create_image(cx, cy, image=self._check_photo(s))

        if self.show_coords:
            self._draw_coords()

        dragged = self.drag["sq"] if self.drag and self.drag["active"] else None
        skip = {dragged}
        if self.anim:
            skip |= {to for _, _, to in self.anim["pieces"]}
            if self.anim["captured"]:
                symbol, sq = self.anim["captured"]
                cx, cy = self._center(sq)
                self.create_image(cx, cy, image=self.pieces.photo(symbol, s))
        self._draw_pieces(board, skip=skip)
        if self.anim:
            for i, (symbol, _, _) in enumerate(self.anim["pieces"]):
                self.create_image(*self._anim_position(i), tags="anim%d" % i, image=self.pieces.photo(symbol, s))

        for sq in self.targets:
            cx, cy = self._center(sq)
            occupied = board.piece_at(sq) is not None or sq == board.ep_square
            self.create_image(cx, cy, image=self._hint_photo("ring" if occupied else "dot", s))

        if self.hints:
            self.create_image(self.ox, self.oy, anchor="nw", image=self._arrow_photo("hints", self._hint_items()))
        if self.arrows:
            items = [(frm, to, ARROW_RGBA, 1.0) for frm, to in sorted(self.arrows)]
            self.create_image(self.ox, self.oy, anchor="nw", image=self._arrow_photo("arrows", items))

        if dragged is not None:
            piece = board.piece_at(dragged)
            self.create_image(self.drag["mx"], self.drag["my"], tags="drag",
                              image=self.pieces.photo(piece.symbol(), s))

        if self.promotion:
            self._draw_promotion()

    def _draw_promotion(self):
        s = self.size
        frm, to, color, options = self.promotion
        self.create_image(self.ox, self.oy, anchor="nw", image=self._dim_photo())
        for (col, row), piece_type in options:
            x, y = self.ox + col * s, self.oy + row * s
            self.create_rectangle(x, y, x + s, y + s, fill=PROMOTION_BG, outline=PROMOTION_OUTLINE)
            symbol = chess.Piece(piece_type, color).symbol()
            self.create_image(x + s / 2, y + s / 2, image=self.pieces.photo(symbol, s))

    # --- Move animation ---------------------------------------------------

    def _start_animation(self, before, move):
        piece = before.piece_at(move.from_square)
        if piece is None:
            return
        pieces = [(piece.symbol(), move.from_square, move.to_square)]
        captured = None
        if before.is_castling(move):
            # python-chess may write castling as king takes rook; show the king on its real square
            rank = chess.square_rank(move.from_square)
            kingside = before.is_kingside_castling(move)
            king_to = chess.square(6 if kingside else 2, rank)
            rook_to = chess.square(5 if kingside else 3, rank)
            if before.piece_type_at(move.to_square) == chess.ROOK:
                rook_from = move.to_square
            else:
                rook_from = chess.square(7 if kingside else 0, rank)
            pieces = [(piece.symbol(), move.from_square, king_to),
                      (before.piece_at(rook_from).symbol(), rook_from, rook_to)]
        elif before.piece_at(move.to_square) is not None:
            captured = (before.piece_at(move.to_square).symbol(), move.to_square)
        self.anim = {"pieces": pieces, "captured": captured, "start": time.monotonic(), "after": None}
        self.anim["after"] = self.after(ANIM_FRAME_MS, self._animate)

    def _stop_animation(self):
        if self.anim and self.anim["after"] is not None:
            self.after_cancel(self.anim["after"])
        self.anim = None

    def _anim_progress(self):
        t = min(1.0, (time.monotonic() - self.anim["start"]) / ANIM_SECONDS)
        return 1 - (1 - t) ** 3   # ease out: fast start, gentle landing

    def _anim_position(self, i):
        _, frm, to = self.anim["pieces"][i]
        (x1, y1), (x2, y2) = self._center(frm), self._center(to)
        p = self._anim_progress()
        return x1 + (x2 - x1) * p, y1 + (y2 - y1) * p

    def _animate(self):
        if time.monotonic() - self.anim["start"] >= ANIM_SECONDS:
            self.anim = None
            self.redraw()
            return
        for i in range(len(self.anim["pieces"])):
            self.coords("anim%d" % i, *self._anim_position(i))
            self.tag_raise("anim%d" % i)
        self.anim["after"] = self.after(ANIM_FRAME_MS, self._animate)

    # --- Cached overlay images --------------------------------------------

    def _cached(self, key, make):
        if key not in self._photos:
            self._photos[key] = ImageTk.PhotoImage(make())
        return self._photos[key]

    def _hint_photo(self, kind, s):
        def make():
            big = s * SUPERSAMPLE
            img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            if kind == "dot":
                r = big * 0.17
                draw.ellipse((big / 2 - r, big / 2 - r, big / 2 + r, big / 2 + r), fill=TARGET_RGBA)
            else:
                draw.ellipse((0, 0, big - 1, big - 1), outline=TARGET_RGBA, width=int(big * 0.09))
            return img.resize((s, s), Image.LANCZOS)
        return self._cached((kind, s), make)

    def _check_photo(self, s):
        def make():
            img = Image.new("RGBA", (s, s))
            px = img.load()
            half = s / 2
            for y in range(s):
                for x in range(s):
                    d = math.hypot(x + 0.5 - half, y + 0.5 - half) / half
                    alpha = max(0.0, min(1.0, (1.05 - d) / 0.7))
                    px[x, y] = CHECK_RGB + (int(230 * alpha),)
            return img
        return self._cached(("check", s), make)

    def _dim_photo(self):
        size = self.size * 8
        return self._cached(("dim", size), lambda: Image.new("RGBA", (size, size), DIM_RGBA))

    def _hint_items(self):
        # weaker arrows first, so that the main suggestion is drawn on top
        ordered = sorted(self.hints, key=lambda h: h[2] == "main")
        return [(frm, to) + HINT_STYLES.get(style, HINT_STYLES["alt"]) for frm, to, style in ordered]

    def _arrow_photo(self, kind, items):
        key = (kind, self.size, self.flipped, tuple(items))
        if key not in self._photos:
            # keep only one overlay of each kind in memory
            for old in [k for k in self._photos if k[0] == kind]:
                del self._photos[old]
        return self._cached(key, lambda: self._make_arrows(items))

    def _make_arrows(self, items):
        """items: [(from_sq, to_sq, rgba, width factor)]"""
        s = self.size * SUPERSAMPLE
        img = Image.new("RGBA", (s * 8, s * 8), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for frm, to, rgba, scale in items:
            (c1, r1), (c2, r2) = self._col_row(frm), self._col_row(to)
            points = [((c1 + 0.5) * s, (r1 + 0.5) * s)]
            dc, dr = c2 - c1, r2 - r1
            if sorted((abs(dc), abs(dr))) == [1, 2]:
                # Knight move: L-shaped arrow, long leg first
                if abs(dc) > abs(dr):
                    points.append(((c2 + 0.5) * s, (r1 + 0.5) * s))
                else:
                    points.append(((c1 + 0.5) * s, (r2 + 0.5) * s))
            points.append(((c2 + 0.5) * s, (r2 + 0.5) * s))
            self._draw_arrow(draw, points, s, rgba, scale)
        return img.resize((self.size * 8, self.size * 8), Image.LANCZOS)

    @staticmethod
    def _draw_arrow(draw, points, s, rgba=ARROW_RGBA, scale=1.0):
        width = s * 0.2 * scale
        head_len, head_half = s * 0.42 * scale, s * 0.3 * scale
        (x1, y1), (x2, y2) = points[-2], points[-1]
        length = math.hypot(x2 - x1, y2 - y1)
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        bx, by = x2 - ux * head_len, y2 - uy * head_len   # base of the arrow head
        shaft = points[:-1] + [(bx, by)]
        # Start a little away from the source square's centre, like on chess sites
        sx, sy = shaft[1][0] - shaft[0][0], shaft[1][1] - shaft[0][1]
        slen = math.hypot(sx, sy) or 1
        shaft[0] = (shaft[0][0] + sx / slen * s * 0.25, shaft[0][1] + sy / slen * s * 0.25)
        draw.line(shaft, fill=rgba, width=int(width), joint="curve")
        draw.polygon([(x2, y2), (bx - uy * head_half, by + ux * head_half),
                      (bx + uy * head_half, by - ux * head_half)], fill=rgba)

    # --- Mouse: moves -----------------------------------------------------

    def _press(self, e):
        if self.promotion:
            self._promotion_click(e)
            return
        self._dropped = False
        self.marks.clear()
        self.arrows.clear()
        sq = self.square_at(e.x, e.y)
        if sq is not None and self.selected is not None and sq in self.targets:
            self._try_move(self.selected, sq)
            return
        board = self.model.board
        piece = board.piece_at(sq) if sq is not None else None
        if piece and piece.color == board.turn and not board.is_game_over() and self.can_move(piece.color):
            self.drag = {"sq": sq, "x": e.x, "y": e.y, "mx": e.x, "my": e.y,
                         "active": False, "was_selected": self.selected == sq}
            self.selected = sq
            self.targets = self.model.legal_targets(sq)
        else:
            self.selected = None
            self.targets = set()
        self.redraw()

    def _motion(self, e):
        d = self.drag
        if not d:
            return
        d["mx"], d["my"] = e.x, e.y
        if not d["active"]:
            if abs(e.x - d["x"]) + abs(e.y - d["y"]) < DRAG_THRESHOLD:
                return
            d["active"] = True
            self.redraw()
        self.coords("drag", e.x, e.y)

    def _release(self, e):
        d, self.drag = self.drag, None
        if not d:
            return
        if not d["active"]:
            if d["was_selected"]:   # second click on the same piece deselects it
                self.selected = None
                self.targets = set()
                self.redraw()
            return
        sq = self.square_at(e.x, e.y)
        if sq is None or sq == d["sq"]:
            self.redraw()   # snap back, keep the selection
        elif sq in self.targets:
            self._try_move(d["sq"], sq, dropped=True)
        else:
            self.selected = None
            self.targets = set()
            self.redraw()
            self.on_illegal()

    def _try_move(self, frm, to, dropped=False):
        self.selected = None
        self.targets = set()
        self.drag = None
        if self.model.needs_promotion(frm, to):
            color = self.model.board.turn
            col, row = self._col_row(to)
            step = 1 if row == 0 else -1   # picker grows from the edge towards the centre
            options = [((col, row + i * step), pt) for i, pt in enumerate(PROMOTION_PIECES)]
            self.promotion = (frm, to, color, options)
            self.redraw()
            return
        self._dropped = dropped
        self.on_move(frm, to, None)

    def _promotion_click(self, e):
        frm, to, color, options = self.promotion
        self.promotion = None
        cell = self._cell_at(e.x, e.y)
        for pos, piece_type in options:
            if pos == cell:
                self.on_move(frm, to, piece_type)
                return
        self.redraw()   # clicked elsewhere: cancel

    # --- Mouse: annotations -----------------------------------------------

    def _right_press(self, e):
        self._right_start = self.square_at(e.x, e.y)

    def _right_release(self, e):
        start, self._right_start = self._right_start, None
        end = self.square_at(e.x, e.y)
        if start is None or end is None or self.promotion:
            return
        if start == end:
            self.marks.symmetric_difference_update({start})
        else:
            self.arrows.symmetric_difference_update({(start, end)})
        self.redraw()
