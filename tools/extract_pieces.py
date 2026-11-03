"""Write the Cburnett piece SVGs bundled with python-chess into assets/pieces/cburnett/.

Works offline: the SVG data comes from the vendored python-chess package.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))

import chess.svg  # noqa: E402

from app.pieces import SVG_SIZE, svg_file_name  # noqa: E402

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
