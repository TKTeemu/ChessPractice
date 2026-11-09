"""Build a zip of the program for copying to another computer.

    python\\python.exe -m tools.make_dist                -> dist\\Chessboard-<date>.zip
    python\\python.exe -m tools.make_dist --no-wheels    (Install.bat then needs the network)
    python\\python.exe -m tools.make_dist --with-python  (fully offline, apart from Stockfish)

The zip contains the application, the assets, setup\\ and wheels\\ (with the committed
python-chess wheel), the launchers, INSTALL.txt and the licence files, plus a wheel of
everything in requirements.txt (Install.bat then installs offline). Left out: python\\
(Install.bat downloads it on the target computer, unless --with-python), .venv, settings.json
(your own paths), error.log, Games/, the engine exe, tests, tools, __pycache__ and .git.

--with-python also puts the prepared python\\ folder in the zip, with only the libraries of
requirements.txt (not pip or the test tools), and the licences of Python and Tcl/Tk.
Install.bat then finds everything in place and downloads nothing but Stockfish.

Stockfish is left out on purpose: GPL-3.0 requires its source code to go with the exe when it
is given to someone else. Install.bat downloads it on the recipient's computer.
"""

import argparse
import datetime
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOP = "Chessboard"   # folder name inside the zip
PY_DIR = ROOT / "python"
PYTHON = PY_DIR / "python.exe"
INCLUDE = ["app", "assets", "setup", "wheels", "chessboard.pyw", "Chessboard.bat", "Install.bat",
           "INSTALL.txt", "README.md", "LICENSE", "NOTICE", "requirements.txt",
           "engines/stockfish/Copying.txt", "engines/stockfish/README.txt"]
SKIP_DIRS = {"__pycache__"}
SKIP_SUFFIXES = {".pyc", ".pyo"}
# Not copied from python\ with --with-python: the libraries are installed fresh instead
PYTHON_SKIP = {"Lib/site-packages", "Scripts"}
# The Tcl/Tk licences are inside these zips of python\tcl; --with-python copies them out
TCLTK_LICENCES = {"libtcl": "tcl_library/license.terms", "libtk": "tk_library/license.terms"}


def walk(folder, skip=()):
    for item in sorted(folder.rglob("*")):
        relative = item.relative_to(folder).as_posix()
        if item.is_file() and not SKIP_DIRS & set(item.relative_to(folder).parts) \
                and item.suffix not in SKIP_SUFFIXES \
                and not any(relative == s or relative.startswith(s + "/") for s in skip):
            yield item


def files_to_pack():
    for name in INCLUDE:
        path = ROOT / name
        if not path.exists():
            raise SystemExit(f"Missing: {path}")
        yield from [path] if path.is_file() else walk(path)


def pip(*args):
    # --isolated: the pip settings of another Python on this computer are not used
    subprocess.run([str(PYTHON), "-m", "pip", *args[:1], "--isolated", "--disable-pip-version-check",
                    "--only-binary", ":all:", "--find-links", str(ROOT / "wheels"), *args[1:]],
                   check=True)


def build_wheels(folder):
    """Wheels of requirements.txt for the Python of python\\ (the target gets the same):
    Pillow from PyPI, python-chess from wheels\\."""
    pip("wheel", "--wheel-dir", str(folder), "-r", str(ROOT / "requirements.txt"))
    return sorted(folder.glob("*.whl"))


def install_libraries(wheels, site_packages):
    """requirements.txt into a fresh site-packages for --with-python, offline from wheels."""
    pip("install", "--no-index", "--find-links", str(wheels), "--no-warn-script-location",
        "--quiet", "--target", str(site_packages), "-r", str(ROOT / "requirements.txt"))


def tcltk_licences():
    """(name in the zip, text) of the Tcl and Tk licences, from python\\tcl."""
    for prefix, member in TCLTK_LICENCES.items():
        archives = sorted((PY_DIR / "tcl").glob(f"{prefix}*.zip"))
        if not archives:
            raise SystemExit(f"Missing: {PY_DIR / 'tcl'}\\{prefix}*.zip (run Install.bat)")
        with zipfile.ZipFile(archives[-1]) as zf:
            yield f"python/tcl/{prefix[3:]}-license.terms", zf.read(member)


PYTHON_NOTICE = """\r
This zip includes the folder python: Python {version} (the Windows embeddable package from\r
python.org, licence in python/LICENSE.txt) with Tcl/Tk from python.org's tcltk.msi (licences in\r
python/tcl/tcl-license.terms and python/tcl/tk-license.terms).\r
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-wheels", action="store_true", help="do not include the wheels")
    parser.add_argument("--with-python", action="store_true",
                        help="include python\\ with the libraries, for fully offline installs")
    parser.add_argument("--out", default=str(ROOT / "dist"), help="output folder (default: dist)")
    args = parser.parse_args()

    if not PYTHON.is_file():
        raise SystemExit("python\\ is missing: run Install.bat dev")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    suffix = "-offline" if args.with_python else ""
    target = out / f"{TOP}-{datetime.date.today():%Y-%m-%d}{suffix}.zip"
    files = list(files_to_pack())   # stops before writing anything if a file is missing
    committed = {path.name for path in files}

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        wheels = []
        if not args.no_wheels or args.with_python:
            wheels = build_wheels(tmp / "wheels")
        extra = [w for w in wheels if w.name not in committed] if not args.no_wheels else []
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in files:
                if path == ROOT / "NOTICE" and args.with_python:
                    version = subprocess.run([str(PYTHON), "-c", "import sys; print(sys.version.split()[0])"],
                                             capture_output=True, text=True, check=True).stdout.strip()
                    text = path.read_text(encoding="utf-8") + PYTHON_NOTICE.format(version=version)
                    zf.writestr(f"{TOP}/NOTICE", text.encode("utf-8"))
                    continue
                zf.write(path, f"{TOP}/{path.relative_to(ROOT).as_posix()}")
            for wheel in extra:
                zf.write(wheel, f"{TOP}/wheels/{wheel.name}")
            python_files = 0
            if args.with_python:
                for path in walk(PY_DIR, skip=PYTHON_SKIP):
                    zf.write(path, f"{TOP}/python/{path.relative_to(PY_DIR).as_posix()}")
                    python_files += 1
                site_packages = tmp / "site-packages"
                install_libraries(tmp / "wheels", site_packages)
                for path in walk(site_packages):
                    zf.write(path, f"{TOP}/python/Lib/site-packages/{path.relative_to(site_packages).as_posix()}")
                    python_files += 1
                for name, text in tcltk_licences():
                    zf.writestr(f"{TOP}/{name}", text)

    with_python = f", {python_files} files of python\\" if args.with_python else ""
    print(f"Wrote {target} ({len(files)} files, {len(extra)} wheels{with_python}, "
          f"{target.stat().st_size // 1024} KB)")
    if not args.with_python:
        print("The wheels are for Python 3.15, 64-bit Windows: the Python that Install.bat downloads.")
    print("Not included: Stockfish (Install.bat downloads it on the target computer, see INSTALL.txt).")


if __name__ == "__main__":
    main()
