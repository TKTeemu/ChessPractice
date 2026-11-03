"""Move list with variations, drawn into a Text widget with one tag per move."""

import tkinter as tk

import chess

from . import strings as S
from .model import visible_comment
from .theme import (FONT as VARIATION_FONT, FONT_ITALIC, FONT_LARGE, MOVE_COMMENT_FG, MOVE_CURRENT_BG,
                    MOVE_CURRENT_FG, MOVE_NUMBER_FG, MUTED_FG as VARIATION_FG, PANEL_BG as BG, PANEL_FG as FG)

INDENT_POINTS = 13


class MoveListView(tk.Frame):
    def __init__(self, master, model, on_select, on_edit):
        super().__init__(master, bg=BG)
        self.model = model
        self.on_select = on_select    # on_select(node)
        self.on_edit = on_edit        # on_edit(action, node), action in promote/delete_variation/delete_from_here
        self.nodes = {}               # tag name -> node
        self.tags = {}                # id(node) -> tag name

        self.text = tk.Text(self, bg=BG, fg=FG, font=FONT_LARGE, wrap="word", relief="flat", bd=0,
                            padx=10, pady=8, cursor="arrow", insertwidth=0, takefocus=0,
                            tabs=("33p", "98p"), highlightthickness=0)
        scroll = tk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

        self.text.tag_configure("number", foreground=MOVE_NUMBER_FG)
        self.text.tag_configure("comment", foreground=MOVE_COMMENT_FG, font=FONT_ITALIC)
        self.text.tag_configure("current", background=MOVE_CURRENT_BG, foreground=MOVE_CURRENT_FG)
        self.text.tag_raise("current")

        self.menu = tk.Menu(self, tearoff=0)
        self._menu_node = None
        self.menu.add_command(label=S.CTX_PROMOTE, command=lambda: self._edit("promote"))
        self.menu.add_command(label=S.CTX_DELETE_VARIATION, command=lambda: self._edit("delete_variation"))
        self.menu.add_command(label=S.CTX_DELETE_FROM_HERE, command=lambda: self._edit("delete_from_here"))

        self.text.bind("<Button-1>", self._click)
        self.text.bind("<Button-3>", self._right_click)
        self.text.configure(state="disabled")

    # --- Rendering --------------------------------------------------------

    def rebuild(self):
        """Render the whole tree again (after the tree changes)."""
        self.nodes.clear()
        self.tags.clear()
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        game = self.model.game
        if visible_comment(game.comment):
            self._insert(visible_comment(game.comment) + " ", "comment")
        self._main_line(game)
        self.text.configure(state="disabled")
        self.show_current()

    def show_current(self):
        """Move the highlight to the current node (after navigation)."""
        self.text.tag_remove("current", "1.0", "end")
        tag = self.tags.get(id(self.model.node))
        if tag:
            ranges = self.text.tag_ranges(tag)
            if ranges:
                self.text.tag_add("current", ranges[0], ranges[1])
                self.text.see(ranges[0])
        elif self.model.node is self.model.game:
            self.text.see("1.0")

    def _insert(self, text, *tags):
        self.text.insert("end", text, tags)

    def _move_tag(self, node):
        tag = f"m{len(self.nodes)}"
        self.nodes[tag] = node
        self.tags[id(node)] = tag
        return tag

    def _main_line(self, game):
        board = game.board()
        node = game
        first = True
        resume_black = False   # black's move needs "N. ..." after a variation block
        while node.variations:
            child = node.variations[0]
            number = board.fullmove_number
            if board.turn == chess.WHITE:
                if not first:
                    self._insert("\n")
                self._insert(f"{number}.\t", "number")
            elif first or resume_black:
                if not first:
                    self._insert("\n")
                self._insert(f"{number}.\t…\t", "number")
            else:
                self._insert("\t")
            first = resume_black = False

            san = board.san(child.move)
            self._insert(san, "move", self._move_tag(child))
            if visible_comment(child.comment):
                self._insert("\n")
                self._insert(visible_comment(child.comment), "comment")
                resume_black = True

            alternatives = node.variations[1:]
            if alternatives:
                for alt in alternatives:
                    self._variation_block(alt, board, depth=1)
                resume_black = True

            board.push(child.move)
            node = child
        if not first:
            self._insert("\n")

    def _variation_block(self, start, board, depth):
        """A variation on its own indented line(s): ( 3. Bc4 Bc5 ... )."""
        tag = f"indent{depth}"
        indent = f"{INDENT_POINTS * depth}p"
        self.text.tag_configure(tag, lmargin1=indent, lmargin2=indent,
                                foreground=VARIATION_FG, font=VARIATION_FONT)
        self._insert("\n")
        self._insert("( ", tag)
        self._variation_moves(start, board.copy(), tag, depth)
        self._insert(")", tag)

    def _variation_moves(self, node, board, tag, depth):
        """Inline moves of a variation; nested variations go in parentheses on the same line."""
        need_number = True
        while node is not None:
            if board.turn == chess.WHITE:
                self._insert(f"{board.fullmove_number}. ", tag, "number")
            elif need_number:
                self._insert(f"{board.fullmove_number}… ", tag, "number")
            need_number = False

            self._insert(board.san(node.move), tag, "move", self._move_tag(node))
            self._insert(" ", tag)
            if visible_comment(node.comment):
                self._insert(visible_comment(node.comment) + " ", tag, "comment")
                need_number = True

            siblings = node.parent.variations
            if siblings[0] is node and len(siblings) > 1:
                for alt in siblings[1:]:
                    self._insert("( ", tag)
                    self._variation_moves(alt, board.copy(), tag, depth + 1)
                    self._insert(") ", tag)
                need_number = True

            board.push(node.move)
            node = node.variations[0] if node.variations else None

    # --- Mouse ------------------------------------------------------------

    def _node_at(self, event):
        index = self.text.index(f"@{event.x},{event.y}")
        for tag in self.text.tag_names(index):
            if tag in self.nodes:
                return self.nodes[tag]
        return None

    def _click(self, event):
        node = self._node_at(event)
        if node is not None:
            self.on_select(node)
        return "break"

    def _right_click(self, event):
        node = self._node_at(event)
        if node is None:
            return "break"
        self._menu_node = node
        is_variation = any(n.parent is not None and n.parent.variations[0] is not n
                           for n in _ancestors(node))
        state = "normal" if is_variation else "disabled"
        self.menu.entryconfigure(0, state=state)
        self.menu.entryconfigure(1, state=state)
        self.menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def _edit(self, action):
        if self._menu_node is not None:
            self.on_edit(action, self._menu_node)
            self._menu_node = None


def _ancestors(node):
    while node is not None:
        yield node
        node = node.parent
