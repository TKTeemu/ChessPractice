"""Sounds, with winsound replaced: what is asked of Windows, not what is heard."""

from pathlib import Path
from types import SimpleNamespace

from app import sounds as sounds_module
from app.sounds import Sounds

SOUNDS_DIR = Path(__file__).resolve().parent.parent / "assets" / "sounds"


def fake_winsound(monkeypatch, busy=False):
    played = []

    def play_sound(path, flags):
        if busy and flags & fake.SND_NOSTOP:
            raise RuntimeError("Failed to play sound")   # what SND_NOSTOP does while a sound plays
        played.append(flags)

    fake = SimpleNamespace(SND_FILENAME=1, SND_ASYNC=2, SND_NODEFAULT=4, SND_NOSTOP=8, PlaySound=play_sound)
    monkeypatch.setattr(sounds_module, "winsound", fake)
    return fake, played


def test_a_played_move_interrupts_whatever_is_playing(monkeypatch):
    fake, played = fake_winsound(monkeypatch, busy=True)
    Sounds(SOUNDS_DIR).play("move")
    assert len(played) == 1 and not played[0] & fake.SND_NOSTOP


def test_a_browsing_sound_is_skipped_while_another_plays(monkeypatch):
    _, played = fake_winsound(monkeypatch, busy=True)
    Sounds(SOUNDS_DIR).play("move", skip_if_busy=True)   # no exception, and no request in the queue
    assert played == []


def test_a_browsing_sound_plays_when_nothing_else_does(monkeypatch):
    fake, played = fake_winsound(monkeypatch)
    Sounds(SOUNDS_DIR).play("move", skip_if_busy=True)
    assert len(played) == 1 and played[0] & fake.SND_ASYNC
