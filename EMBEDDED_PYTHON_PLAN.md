# Plan: a private Python inside the Chessboard folder

Status: implemented 2026-11-09 (spike results in docs/DECISIONS.md). Date: 2026-11-09.

## Goal

`Install.bat` sets up everything Chessboard needs **inside the Chessboard folder**, and nothing
outside it:

- A user who has never heard of Python double-clicks `Install.bat` and is done. No Python
  installer opens, nothing needs ticking, and there is no "Add python.exe to PATH".
- A user who already has Python (any version, on PATH or not, with `PYTHONPATH`/`PYTHONHOME`
  set or not) is not affected, and their Python cannot affect Chessboard.
- Nothing is written to the registry, Start menu, "Installed apps", `%APPDATA%` or `PATH`.
  To remove Chessboard, delete its folder.

How: download the official **Windows embeddable package** of Python 3.15 from python.org, unpack
it into the folder `python\`, add **Tcl/Tk + tkinter** to it from the official `tcltk.msi` of the
same release, and install Pillow and python-chess into it. The `.venv` goes away.

## Today vs. after

| | Today | After |
| --- | --- | --- |
| Python | Installed system-wide by the user with the python.org installer (`Install.bat` opens it) | `python\` in the Chessboard folder, unpacked by `Install.bat` |
| tkinter / Tcl/Tk | Comes with the full installer | Extracted from `tcltk.msi` into `python\` |
| Libraries | `.venv\Lib\site-packages` | `python\Lib\site-packages` |
| Start | `.venv\Scripts\pythonw.exe chessboard.pyw` | `python\pythonw.exe chessboard.pyw` |
| User steps in INSTALL.txt | 4 (one of them is the Python installer) | 3: unpack, `Install.bat`, `Chessboard.bat` |
| Removing | Delete the folder, then uninstall Python separately | Delete the folder |

## Target layout

```
Chessboard\
  Install.bat, Chessboard.bat, chessboard.pyw, app\, assets\, engines\ ...
  setup\
    python315._pth          our version of the path file, copied over the one in the zip
  python\                   not in git; created by Install.bat
    python.exe, pythonw.exe, python315.dll, python315.zip (standard library), *.pyd, vcruntime*.dll
    python315._pth          from setup\
    DLLs\                   _tkinter.pyd, tcl/tk DLLs        (from tcltk.msi)
    tcl\                    Tcl/Tk script libraries          (from tcltk.msi)
    Lib\tkinter\            the tkinter package              (from tcltk.msi)
    Lib\site-packages\      pip, Pillow, python-chess (+ pytest with "dev")
```

### `setup\python315._pth`

```
python315.zip
.
DLLs
Lib
Lib\site-packages
..
import site
```

The `._pth` file is what makes this work, so each line is there for a reason:

- With a `._pth` file present, Python ignores `PYTHONPATH`, `PYTHONHOME` and the registry. That
  is what keeps another Python on the computer from interfering.
- `DLLs`, `Lib` and `Lib\site-packages` make tkinter and the libraries importable.
- `..` is the Chessboard folder. **This one is needed.** A `._pth` file also stops Python from
  adding the script's own folder to `sys.path`, so without `..` the `import app` in
  `chessboard.pyw` fails, and so do `python -m tools.make_dist` and `-m pytest`.
- `import site` lets pip work and processes `.pth` files in site-packages. The spike checks that
  it does not also add the user's own site-packages (`%APPDATA%\Python\Python315\...`). If it
  does, the launchers pass `-s`.

## Phase 0: spike (by hand, before changing any script)

Each item below is an assumption the plan depends on. Check them on the development machine
with a scratch folder, and write down the results (they become entries in `docs/DECISIONS.md`):

1. **Embeddable zip exists and is signed.** `python-3.15.2-embed-amd64.zip` is on
   `https://www.python.org/ftp/python/3.15.2/`. `python.exe`/`pythonw.exe` carry the PSF
   Authenticode signature (`Get-AuthenticodeSignature`).
2. **`tcltk.msi` extracts without admin rights and without registering.**
   `https://www.python.org/ftp/python/3.15.2/amd64/tcltk.msi` →
   `msiexec /a tcltk.msi /qn TARGETDIR=<absolute path to python\>`, run as a normal user.
   Check that UAC does not prompt, that nothing shows up in "Installed apps", and which files land
   where. The files can be listed first with `msiexec /a` to a scratch folder.
3. **Tk actually starts:** `python\python.exe -c "import tkinter; tkinter.Tk().destroy()"` and
   `python -m tkinter`. If Tcl cannot find its library, `_tkinter` may need `TCL_LIBRARY`.
   Prefer moving the files to where `_tkinter` looks over setting environment variables.
4. **SVG pieces render:** `pieces.py` relies on Tk 9 reading SVG. Start the program and look at
   the board.
5. **pip bootstraps from a pinned wheel:**
   `python\python.exe pip-XX-py3-none-any.whl/pip install --no-index pip-XX-py3-none-any.whl`
   (pip runs from its own wheel). This needs no `get-pip.py`, whose content changes without a
   version number and cannot be pinned with a checksum.
6. **python-chess installs.** PyPI has 1.11.2 only as source code. Building it needs setuptools
   and pip's build isolation, and build isolation passes paths through `PYTHONPATH`, **which a
   `._pth` file ignores**. Expect this to fail. Fallbacks, in order of preference:
   - a. Commit `wheels\chess-1.11.2-py3-none-any.whl` to the repo. It is pure Python, the same on
     every computer, about 150 KB, and GPL source, so committing it is allowed. Build it once
     with `pip wheel` on a normal Python. Install from it with `--no-index --find-links wheels`.
   - b. `--no-build-isolation` after installing a pinned setuptools.
7. **Pillow** has a `cp315-win_amd64` wheel for the pinned version, and `PIL.ImageTk` works with
   the extracted Tk.
8. **Isolation from another Python:** with Python 3.12 on `PATH` and `PYTHONHOME`/`PYTHONPATH`
   pointing at it, `python\python.exe -c "import sys; print(sys.path, sys.flags)"` shows only
   the `._pth` entries. Check `site.ENABLE_USER_SITE` too.
9. **F-Secure DeepGuard** (see DECISIONS.md) lets `python\pythonw.exe` and `stockfish.exe` run
   from the new place.
10. **Awkward paths:** the folder under a path with spaces and with ä/ö (`C:\Users\Jääskeläinen\
    Documents\Chess Board\`), and the folder moved after installing. Embeddable Python has no
    absolute paths baked in, so moving it should keep working, unlike a venv.

If item 2 fails (msiexec blocked or asks for admin), the fallback source of Tcl/Tk is the full
Python zip from python.org's Install Manager index (`python-3.15.2-amd64.zip`, which includes
Tcl/Tk), unpacked with `tar.exe`. Note: if that works, it could replace the embeddable package plus
msi entirely (one download, everything included). The spike should compare the two. This
plan keeps the embeddable package as the main option, as requested.

## Phase 1: `Install.bat`

Keep what works today: idempotent steps, `[n/N]` progress, `curl.exe` with `--retry`, a SHA-256
check of every download with `certutil`, plain-language messages, the "still inside the zip"
check, and the `dev` argument. The Stockfish part is unchanged except that it runs the check
with `python\python.exe` instead of `%PY%`.

New variables at the top (one place to update per Python release):

```
PY_VERSION=3.15.2
PY_EMBED_URL / PY_EMBED_SHA256
TCLTK_URL / TCLTK_SHA256
PIP_WHEEL_URL / PIP_WHEEL_SHA256
PY_DIR=python
PY_EXE=python\python.exe
```

Steps:

1. **[1/4] Python** (download about 12 MB).
   Skip if `python\python.exe` exists and reports exactly `PY_VERSION`.
   Otherwise remove any half-made `python\`, download the zip into a fresh folder under
   `%TEMP%\ChessboardSetup\`, check its SHA-256, unpack it with `tar.exe -xf` into `python\`, and copy
   `setup\python315._pth` over the zip's own `._pth`.
   A version change (e.g. 3.15.2 → 3.15.3) means: rebuild `python\` from scratch.
2. **[2/4] Tcl/Tk** (download about 4 MB).
   Skip if `python\python.exe -c "import tkinter; tkinter.Tcl()"` succeeds.
   Otherwise download `tcltk.msi`, check it, and run `msiexec /a ... /qn TARGETDIR="%CD%\python"`
   (needs an absolute path). Then delete the copy of the `.msi` that an administrative install
   leaves in the target, and remove `Lib\idlelib`, `Lib\turtledemo` and `Lib\test` if they came
   along (not needed).
3. **[3/4] Libraries.**
   If pip is missing, download the pinned pip wheel, check it, and install pip from itself. Then
   `python\python.exe -m pip install --disable-pip-version-check --no-warn-script-location
   --quiet %PIP_SOURCE% -r %REQUIREMENTS%`. Install `chess` from the committed `wheels\` (see
   spike 6), and Pillow from PyPI or from the `wheels\` of a distribution zip. Consider adding
   `--require-hashes` with hashes in `requirements.txt`, which pins the downloads the same way as
   Python and Stockfish.
   **Final check:** `python\python.exe -c "import tkinter, PIL.ImageTk, chess.pgn; tkinter.Tcl()"`.
   `tkinter.Tcl()` checks that the Tcl library loads, not only that the module imports.
4. **[4/4] Stockfish**: as today.

**Cleanup of the old setup:** if `.venv\` exists and the new check in step 3 passed, delete
`.venv\` and say so in one line ("The old Python environment .venv was removed; it is no longer
needed."). Do not offer to uninstall a system Python: the user may need it for something else.
INSTALL.txt says how to remove it.

**Removed:** `:find_python`, `:no_python`, `:recheck_python`, `:python_installed`,
`:python_browser` and all text about the Python installer, PATH and "Install Now".

**New failure messages**, in the same style as today:
- Download failed or checksum wrong → "Check your internet connection and run Install.bat again."
- msiexec failed → name the step and point to INSTALL.txt "If something goes wrong".
- Folder not writable (e.g. unpacked under `C:\Program Files`) → "Move the Chessboard folder to
  Documents and run Install.bat again." Test once at the start by creating and deleting a file.

## Phase 2: other files

| File | Change |
| --- | --- |
| `Chessboard.bat` | Check and start `python\python.exe` / `python\pythonw.exe` (add `-s` if spike 8 requires it). Same "not set up yet" message. |
| `chessboard.pyw` | The tkinter message says "Reinstall Python 3.15 with tcl/tk"; change it to "Run Install.bat again." `REQUIRED_PYTHON` stays. |
| `setup\python315._pth` | New, see above. |
| `wheels\chess-1.11.2-py3-none-any.whl` | New, if spike 6 chooses fallback a. Add a `README.txt` in `wheels\` saying where the wheel came from and how to rebuild it. |
| `.gitignore` | Add `python/`. Keep `.venv/` for a while, so that old folders do not show up as untracked. |
| `tools/make_dist.py` | Use `python\python.exe` instead of `.venv`. Include `setup\` and the committed wheel. The Pillow wheel is still built for the offline zip. **Decision:** also offer `--with-python`, which puts the prepared `python\` folder in the zip for fully offline installs. That adds the PSF licence (`python\LICENSE.txt`) and the Tcl/Tk licence to `NOTICE`. |
| `requirements*.txt` | Comments: "Install.bat installs these into python\". Optionally add hashes. |
| `tests/test_python_version.py` | Add a test that `sys.executable` is under the repo's `python\` when running from it (skip otherwise, so a developer can still run pytest with their own Python). |

## Phase 3: documentation

- **INSTALL.txt:** remove "STEP 2: INSTALL PYTHON 3.15" completely. Step 3 becomes Step 2 and says
  it downloads "the parts Chessboard needs, about 100 MB in total". Remove the troubleshooting
  entry "Python 3.15 is not installed even though you installed it". Add "Install.bat says the
  folder is not writable" and "Your antivirus blocks python.exe". "Removing Chessboard" becomes:
  delete the folder. A user who installed Python 3.15 only for Chessboard can remove it now (a
  short note).
- **Chessboard_Installation.pdf:** this is the same guide as a PDF. Regenerate it from the new
  INSTALL.txt, or remove it.
- **README.md:** requirements table: "Python 3.15, downloaded into `python\` by `Install.bat`, no
  separate installation". The console command becomes `python\python.exe chessboard.pyw`.
- **docs/MAINTENANCE.md:** every `.venv\Scripts\python.exe` becomes `python\python.exe`. "A new
  Python 3.15.x" lists the new variables (embeddable zip, tcltk.msi, their checksums) and says to
  delete `python\` and run `Install.bat dev`. "Moving to a new Python minor version" adds:
  rename `setup\python315._pth` and its first line. The paragraph about pip's `.exe` launchers
  now refers to `python\Scripts`. Those launchers still hard-code their path, and the project
  still does not use them.
- **docs/DECISIONS.md:** replace the row "One `.venv`, one way to install libraries" with "A
  private embeddable Python in `python\`": why (no installer for non-technical users, no clash
  with an existing Python, removal by deleting a folder), what was tried in the spike, and what
  would make us reconsider (python.org stops publishing the embeddable zip or `tcltk.msi`, or
  DeepGuard flags it).
- **docs/ARCHITECTURE.md, docs/EXTENDING.md:** `.venv` → `python\`. In EXTENDING, the checklist
  for a new library adds: "must have a wheel, or be pure Python with a wheel committed to
  `wheels\`" (source-only packages do not build in embeddable Python).

## Phase 4: verification

Run the full `Install.bat` → `Chessboard.bat` → play a game vs Stockfish in each case. Windows
Sandbox gives a clean Windows 11 for the first rows.

| # | Situation | Expected |
| --- | --- | --- |
| 1 | Clean Windows 11, no Python ever installed | Works. No UAC prompt. Nothing new in "Installed apps", Start menu or PATH. |
| 2 | Python 3.12 on PATH, `PYTHONPATH` and `PYTHONHOME` set to it | Works; `sys.path` in the program shows only `python\` paths. |
| 3 | Python 3.15 installed system-wide (today's users) | Works. The system Python is untouched and unused. |
| 4 | Existing folder with an old `.venv` (upgrade) | `.venv` removed, the program starts with `python\`. Settings and `Games\` kept. |
| 5 | Folder under a path with spaces and ä/ö | Works. |
| 6 | Folder moved after installing | `Chessboard.bat` still works without running `Install.bat` again. |
| 7 | `Install.bat` run a second time | Every step says "already there". No downloads. |
| 8 | Network cut during each download | Clear message. The next run repairs it. |
| 9 | Zip from `make_dist --with-python`, offline | Works with no network apart from Stockfish. |
| 10 | `Install.bat dev`, then `python\python.exe -m pytest` | All passed + 1 xfailed, as today. |
| 11 | F-Secure DeepGuard running | Nothing blocked. |
| 12 | Folder in `C:\Program Files` | Clear "move the folder" message. |

## Open decisions

1. **Folder name:** `python\` (clear when looking at the files) or `runtime\` (does not invite
   users to "run Python" there). Proposed: `python\`.
2. **python-chess source:** commit the wheel to `wheels\` (proposed) or build it at install time.
   Depends on spike 6.
3. **Embeddable + `tcltk.msi`** (as requested) **vs. the full Install Manager zip** (one download,
   Tcl/Tk included). Depends on spikes 2 and 3. Keep the embeddable package unless msiexec turns
   out to be a problem.
4. **Hash-pinned `requirements.txt`:** yes/no. Proposed: yes, which matches how Python and
   Stockfish are checked.
5. **`make_dist --with-python`:** worth it for offline installs, or keep the zip small.

## Order of work

1. Spike (Phase 0), with the results written into DECISIONS.md. Stop here and decide the open
   points.
2. `setup\python315._pth` and, if chosen, the committed chess wheel.
3. `Install.bat` and `Chessboard.bat`. Test rows 1, 3, 4 and 7.
4. `chessboard.pyw` message, `.gitignore`, `make_dist.py`, tests.
5. Documentation and the PDF.
6. Full verification table, then one commit per step above.
