"""Reading and writing settings.json."""

import json
from pathlib import Path

DEFAULTS = {
    "flipped": False,
    "show_coordinates": True,
    "sound": True,
    "piece_set": "cburnett",
    "board_theme": "green",
    "window_geometry": "",
    "last_directory": "",
    "mode": "board",
    "vs_minutes": 30,
    "vs_engine": "stockfish",
    "vs_level": "1320",
    "vs_color": "white",
    "vs_start": "initial",
    "engine_path": "",
    "learn_opening": "reti",
    "learn_role": "opening",
    "learn_engine": "stockfish",
    "learn_level": "1320",
    "learn_vary": True,
    "learn_suggest": True,
    "learn_suggest_moves": 12,
    "details_open": "board",
}


class Settings:
    def __init__(self, path):
        self.path = Path(path)
        self.values = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(data, dict):
            for key in DEFAULTS:
                if key in data and type(data[key]) is type(DEFAULTS[key]):
                    self.values[key] = data[key]

    def save(self):
        try:
            self.path.write_text(json.dumps(self.values, indent=2), encoding="utf-8")
        except OSError:
            pass

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = value
