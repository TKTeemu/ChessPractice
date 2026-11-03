"""Playing event sounds with winsound (asynchronous, never blocks the UI)."""

from pathlib import Path

try:
    import winsound
except ImportError:  # not on Windows
    winsound = None

ILLEGAL = "illegal"


class Sounds:
    def __init__(self, sounds_dir, enabled=True):
        self.sounds_dir = Path(sounds_dir)
        self.enabled = enabled

    def play(self, kind):
        if not self.enabled or winsound is None or not kind:
            return
        path = self.sounds_dir / f"{kind}.wav"
        if path.exists():
            try:
                winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            except RuntimeError:
                pass
