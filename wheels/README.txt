wheels\ - library files that Install.bat installs from this folder
====================================================================

chess-1.11.2-py3-none-any.whl
  python-chess 1.11.2 by Niklas Fiekas, GPL-3.0, https://github.com/niklasf/python-chess
  PyPI has this version only as source code (chess-1.11.2.tar.gz). Building it needs
  setuptools and pip's build isolation, and build isolation does not work in the embeddable
  Python in python\ (it passes paths through PYTHONPATH, which python\python315._pth makes
  Python ignore). So the wheel is built once and kept here. It is pure Python, the same on
  every computer. Its source code is the tar.gz on PyPI:
  https://pypi.org/project/chess/1.11.2/

  Rebuilding it (with any normal Python 3.15, not the one in python\):
      python -m pip wheel --no-cache-dir --no-deps --wheel-dir wheels chess==1.11.2
  A rebuilt wheel has a different SHA-256 (it stores file times), so update the hash of
  chess in requirements.txt too.

In a distribution zip made by tools\make_dist.py this folder also holds the Pillow wheel, and
Install.bat then installs everything from here without the network.
