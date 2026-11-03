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


def test_extra_defaults_and_dict_values(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"mine": 5, "details_open": {"board": False}}), encoding="utf-8")
    s = Settings(path, {"mine": 1})
    assert s["mine"] == 5 and s["details_open"] == {"board": False}


def test_old_string_value_of_a_dict_setting_falls_back_to_default(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"details_open": "board,!vs_computer"}), encoding="utf-8")
    assert Settings(path)["details_open"] == {}


def test_dirty_only_after_a_real_change(tmp_path):
    s = Settings(tmp_path / "settings.json")
    assert not s.dirty
    s["sound"] = True              # same as the default
    assert not s.dirty
    s["sound"] = False
    assert s.dirty
    assert s.save() and not s.dirty
    assert not (tmp_path / "settings.json.tmp").exists()


def test_save_failure_is_reported_not_swallowed(tmp_path):
    s = Settings(tmp_path / "missing folder" / "settings.json")
    s["sound"] = False
    assert s.save() is False and s.dirty
