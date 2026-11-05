"""Reading and writing settings.json."""

import json
import logging
import os
from pathlib import Path

# Settings of the program itself. A mode's own settings are in its SETTINGS class variable
# (app/modes/) and are added with Settings(path, extra_defaults).
DEFAULTS = {
    "flipped": False,
    "show_coordinates": True,
    "sound": True,
    "piece_set": "cburnett",
    "board_theme": "green",
    "window_geometry": "",
    "last_directory": "",
    "engine_path": "",
    "details_open": {},   # mode key -> bool; a mode not listed uses Mode.show_details
}


class Settings:
    """Only keys in the defaults are accepted, and a value's type must match the default's.
    `dirty` is True after a change that has not been saved yet."""

    def __init__(self, path, extra_defaults=None):
        self.path = Path(path)
        self.defaults = {**DEFAULTS, **(extra_defaults or {})}
        self.values = {key: _copy(value) for key, value in self.defaults.items()}
        self.dirty = False
        self.load()

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(data, dict):
            for key, default in self.defaults.items():
                if key in data and type(data[key]) is type(default):
                    self.values[key] = data[key]

    def save(self):
        """Write the file (through a temporary file, so a crash cannot leave half a file).
        Returns False and logs the error if it could not be written."""
        tmp = self.path.with_name(self.path.name + ".tmp")
        try:
            tmp.write_text(json.dumps(self.values, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            logging.exception("Could not save %s", self.path)
            return False
        self.dirty = False
        return True

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        if self.values.get(key) != value:
            self.values[key] = value
            self.dirty = True


def _copy(value):
    return dict(value) if isinstance(value, dict) else value
