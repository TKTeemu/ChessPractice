import chess

from app.clock import ChessClock, format_time


class FakeTime:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def test_clock_runs_only_for_the_side_to_move():
    now = FakeTime()
    clock = ChessClock(60, 60, now)
    now.t += 5
    assert clock.remaining(chess.WHITE) == 60   # not started yet
    clock.start(chess.WHITE)
    now.t += 10
    assert clock.remaining(chess.WHITE) == 50 and clock.remaining(chess.BLACK) == 60
    clock.switch()
    now.t += 4
    assert clock.remaining(chess.WHITE) == 50 and clock.remaining(chess.BLACK) == 56
    clock.switch()
    assert clock.running == chess.WHITE


def test_flag_and_stop():
    now = FakeTime()
    clock = ChessClock(30, 30, now)
    clock.start(chess.BLACK)
    now.t += 29.9
    assert clock.flagged() is None
    now.t += 0.2
    assert clock.flagged() == chess.BLACK and clock.remaining(chess.BLACK) == 0
    clock.stop()
    now.t += 100
    assert clock.flagged() is None and clock.remaining(chess.WHITE) == 30


def test_format_time():
    assert format_time(1800) == "30:00"
    assert format_time(1781.9) == "29:41"
    assert format_time(3900) == "1:05:00"
    assert format_time(42.37) == "0:42.3"
    assert format_time(0) == "0:00.0"


def test_increment_is_added_to_the_mover():
    t = [0.0]
    clock = ChessClock(100, 100, lambda: t[0], increment=5)
    clock.start(chess.WHITE)
    t[0] = 10
    clock.switch()
    assert clock.remaining(chess.WHITE) == 95 and clock.running == chess.BLACK


def test_no_increment_after_the_flag_has_fallen():
    t = [0.0]
    clock = ChessClock(10, 10, lambda: t[0], increment=5)
    clock.start(chess.WHITE)
    t[0] = 11
    clock.switch()
    assert clock.remaining(chess.WHITE) == 0
