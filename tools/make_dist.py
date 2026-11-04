"""Build a zip of the program for copying to another computer.

    python tools\\make_dist.py               -> dist\\Chessboard-<date>.zip
    python tools\\make_dist.py --no-wheels   (without the Pillow wheel; then Install.bat needs the network)

The zip contains everything except Python itself and Stockfish: the application, the assets,
python-chess (vendor/), the Pillow wheel for this Python version (wheels/, installed offline
by Install.bat), the launchers, INSTALL.txt and the licence files. Left out: settings.json (your
own paths), error.log, Games/, the engine exe, tests, tools, __pycache__ and .git.

Stockfish is left out on purpose: GPL-3.0 requires its source code to go with the exe when it
is given to someone else. Install.bat downloads it on the recipient's computer.
"""

import argparse
import datetime
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOP = "Chessboard"   # folder name inside the zip
INCLUDE = ["app", "assets", "vendor", "chessboard.pyw", "Chessboard.bat", "Install.bat", "INSTALL.txt",
           "README.md", "LICENSE", "NOTICE", "requirements-global.txt", "requirements-vendor.txt",
           "engines/stockfish/Copying.txt", "engines/stockfish/README.txt"]
SKIP_DIRS = {"__pycache__"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def files_to_pack():
    for name in INCLUDE:
        path = ROOT / name
        if not path.exists():
            raise SystemExit(f"Missing: {path}")
        if path.is_file():
            yield path
            continue
        for item in sorted(path.rglob("*")):
            if item.is_file() and not SKIP_DIRS & set(item.relative_to(ROOT).parts) \
                    and item.suffix not in SKIP_SUFFIXES:
                yield item


def download_wheels(folder):
    """The Pillow wheel for this Python version and platform (the target needs the same)."""
    subprocess.run([sys.executable, "-m", "pip", "download", "--only-binary=:all:", "--dest", str(folder),
                    "-r", str(ROOT / "requirements-global.txt")], check=True)
    return sorted(folder.glob("*.whl"))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-wheels", action="store_true", help="do not download the Pillow wheel")
    parser.add_argument("--out", default=str(ROOT / "dist"), help="output folder (default: dist)")
    args = parser.parse_args()

    if not (ROOT / "vendor" / "chess").is_dir():
        raise SystemExit("vendor/chess is missing: python -m pip install --target vendor -r requirements-vendor.txt")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{TOP}-{datetime.date.today():%Y-%m-%d}.zip"
    files = list(files_to_pack())   # stops before writing anything if a file is missing

    with tempfile.TemporaryDirectory() as tmp:
        wheels = [] if args.no_wheels else download_wheels(Path(tmp))
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in files:
                zf.write(path, f"{TOP}/{path.relative_to(ROOT).as_posix()}")
            for wheel in wheels:
                zf.write(wheel, f"{TOP}/wheels/{wheel.name}")

    print(f"Wrote {target} ({len(files)} files, {len(wheels)} wheels, {target.stat().st_size // 1024} KB)")
    print(f"Python on the target computer: {sys.version_info.major}.{sys.version_info.minor} "
          f"({'64' if sys.maxsize > 2**32 else '32'}-bit), the same as here, because of the Pillow wheel.")
    print("Not included: Stockfish (Install.bat downloads it on the target computer, see INSTALL.txt).")


if __name__ == "__main__":
    main()
