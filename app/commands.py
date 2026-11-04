"""Command names for Mode.allows(). Logic layer: the game rules use them too, so they live
here rather than in app/modes/.

MainWindow asks mode.allows(name) before each of these commands. A typo in a string would
silently allow or block a command; use these constants instead.
"""

DELETE_LAST = "delete_last"     # Ctrl+Z: delete the last move
EDIT_TREE = "edit_tree"         # promote / delete variations in the move list menu
PASTE = "paste"                 # paste PGN/FEN, and typing a FEN into the FEN field
OPEN = "open"                   # File > Open
NAVIGATE = "navigate"           # ← → Home End ↑ ↓ and clicks in the move list
EDIT_COMMENT = "edit_comment"   # the comment field
TAKE_BACK = "take_back"         # MainWindow.take_back(color): ← / ◀ and Take Back in a game mode

ALL_COMMANDS = frozenset({DELETE_LAST, EDIT_TREE, PASTE, OPEN, NAVIGATE, EDIT_COMMENT, TAKE_BACK})
