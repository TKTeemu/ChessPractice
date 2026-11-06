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

    def play(self, kind, skip_if_busy=False):
        """skip_if_busy: play nothing if a sound is still playing. For sounds that can come faster
        than they play (a held arrow key): Windows queues async requests, about 160 ms each, so
        the clicks would go on for seconds after the last one was asked for."""
        if not self.enabled or winsound is None or not kind:
            return
        path = self.sounds_dir / f"{kind}.wav"
        if path.exists():
            flags = winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT
            if skip_if_busy:
                flags |= winsound.SND_NOSTOP
            try:
                winsound.PlaySound(str(path), flags)
            except RuntimeError:   # also how SND_NOSTOP says that a sound is playing
                pass
