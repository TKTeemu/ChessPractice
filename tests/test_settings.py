import json

from app.settings import DEFAULTS, Settings


def test_missing_file_gives_defaults(tmp_path):
    assert Settings(tmp_path / "settings.json").values == DEFAULTS


def test_wrong_types_and_unknown_keys_are_ignored(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"sound": "yes", "flipped": True, "extra": 1}), encoding="utf-8")
    s = Settings(path)
    assert s["sound"] is True and s["flipped"] is True and "extra" not in s.values


def test_save_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    s = Settings(path)
    s["board_theme"] = "blue"
    s.save()
    assert Settings(path)["board_theme"] == "blue"
