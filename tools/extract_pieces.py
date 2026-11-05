"""Write the Cburnett piece SVGs bundled with python-chess into assets/pieces/cburnett/.

Works offline: the SVG data comes from the installed python-chess package.

    python -m tools.extract_pieces
"""

from pathlib import Path

import chess.svg

from app.pieces import SVG_SIZE, svg_file_name

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "pieces" / "cburnett"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for symbol, body in chess.svg.PIECES.items():
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
               f'viewBox="0 0 {SVG_SIZE} {SVG_SIZE}" width="{SVG_SIZE}" height="{SVG_SIZE}">\n'
               f'{body}\n</svg>\n')
        (OUT_DIR / svg_file_name(symbol)).write_text(svg, encoding="utf-8")
    print(f"Pieces written to {OUT_DIR}")


if __name__ == "__main__":
    main()
