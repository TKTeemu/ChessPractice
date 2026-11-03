import sys
import threading
import time
from pathlib import Path

import chess
import pytest

from app.engines import ENGINES, EngineError, RandomEngine, StockfishEngine, engine_class
from app.engines.base import Level
from app.engines.uci import UciClient, parse_option
from app.engines.worker import EngineWorker
from app.settings import Settings

FAKE_UCI = Path(__file__).with_name("fake_uci.py")
MATE_IN_ONE = "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1"   # Rd8#
QUICK = Level("quick", "Quick", None, 0.0)


@pytest.fixture
def settings(tmp_path):
    return Settings(tmp_path / "settings.json")


def test_registry_keys_are_unique():
    keys = [cls.key for cls in ENGINES]
    assert len(keys) == len(set(keys)) and all(cls.name for cls in ENGINES)
    assert engine_class("random") is RandomEngine and engine_class("nope") is None


def test_random_engine_plays_legal_moves():
    engine = RandomEngine(seed=1)
    board = chess.Board()
    for _ in range(30):
        move = engine.best_move(board, QUICK, threading.Event())
        assert move in board.legal_moves
        board.push(move)
        if board.is_game_over():
            break


def test_random_engine_without_moves_raises():
    with pytest.raises(EngineError):
        RandomEngine().best_move(chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"), QUICK, threading.Event())


def test_unknown_level_key_falls_back_to_first(settings):
    engine = StockfishEngine(settings)
    assert engine.level("1500").elo == 1500
    assert engine.level("no such level") is engine.levels()[0]
    assert engine.levels()[0].elo == 1320 and engine.levels()[-1].key == "max"


def test_stockfish_missing(settings, tmp_path):
    settings["engine_path"] = str(tmp_path / "missing.exe")
    assert not StockfishEngine.available(settings)
    assert "stockfish.exe" in StockfishEngine.unavailable_reason(settings)


def test_parse_option():
    name, info = parse_option("option name UCI_Elo type spin default 1320 min 1320 max 3190")
    assert name == "UCI_Elo" and info["min"] == 1320 and info["max"] == 3190
    name, info = parse_option("option name Clear Hash type button")
    assert name == "Clear Hash" and info["type"] == "button"


# --- UCI client against a fake engine -------------------------------------

@pytest.fixture
def client():
    c = UciClient([sys.executable, str(FAKE_UCI)])
    c.start()
    yield c
    c.close()


def test_uci_handshake(client):
    assert client.name == "FakeEngine"
    assert client.options["UCI_Elo"]["max"] == 3190
    client.isready()
    client.new_game()


def test_uci_go_returns_legal_move(client):
    board = chess.Board()
    board.push_san("e4")
    move = client.go(board, 0.01, threading.Event())
    assert move in board.legal_moves


def test_uci_position_from_fen_with_moves(client):
    board = chess.Board(MATE_IN_ONE)
    board.push_san("h3")
    board.push_san("h6")
    assert client.go(board, 0.01, threading.Event()) in board.legal_moves


def test_uci_close_ends_process_and_can_be_repeated(client):
    process = client.process
    client.close()
    assert process.poll() is not None
    client.close()
    with pytest.raises(EngineError):
        client.go(chess.Board(), 0.01, threading.Event())


def test_stockfish_engine_with_fake_exe_clamps_elo(settings, monkeypatch):
    engine = StockfishEngine(settings)
    monkeypatch.setattr(StockfishEngine, "find_exe", classmethod(lambda cls, s: FAKE_UCI))
    monkeypatch.setattr("app.engines.stockfish.UciClient",
                        lambda command, cwd: UciClient([sys.executable, *command], cwd=cwd))
    engine.start()
    try:
        low = Level("low", "Low", 800, 0.01, {"UCI_LimitStrength": True, "UCI_Elo": 800})
        assert engine.best_move(chess.Board(), low, threading.Event()) in chess.Board().legal_moves
        assert engine._options["UCI_Elo"] == 1320
    finally:
        engine.close()
        engine.close()


# --- Worker ---------------------------------------------------------------

def wait_result(worker, timeout=5.0):
    return worker.results.get(timeout=timeout)


def test_worker_returns_move_with_request_id():
    worker = EngineWorker(RandomEngine(seed=2))
    try:
        board = chess.Board()
        worker.request(board, QUICK, 7)
        request_id, move = wait_result(worker)
        assert request_id == 7 and move in board.legal_moves
    finally:
        worker.close()


def test_worker_reports_engine_errors():
    worker = EngineWorker(RandomEngine())
    try:
        worker.request(chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"), QUICK, 1)
        request_id, result = wait_result(worker)
        assert request_id == 1 and isinstance(result, EngineError)
    finally:
        worker.close()


def test_worker_cancel_returns_quickly():
    slow = Level("slow", "Slow", None, 30.0)
    worker = EngineWorker(RandomEngine())
    try:
        worker.request(chess.Board(), slow, 1)
        time.sleep(0.2)                  # let the search start
        worker.cancel()
        request_id, move = wait_result(worker, timeout=2.0)
        assert request_id == 1
    finally:
        worker.close()


def test_worker_skips_requests_cancelled_before_they_start():
    worker = EngineWorker(RandomEngine())
    try:
        worker.request(chess.Board(), Level("slow", "Slow", None, 30.0), 1)
        worker.request(chess.Board(), QUICK, 2)   # cancels request 1
        request_id, _ = wait_result(worker, timeout=2.0)
        assert request_id in (1, 2)
        if request_id == 1:
            assert wait_result(worker, timeout=2.0)[0] == 2
    finally:
        worker.close()


# --- Real Stockfish (skipped when not installed) ---------------------------

@pytest.fixture
def stockfish(settings):
    app_settings = Settings(Path(__file__).resolve().parent.parent / "settings.json")
    if not StockfishEngine.available(app_settings):
        pytest.skip("Stockfish not installed in engines/stockfish/")
    engine = StockfishEngine(app_settings)
    engine.start()
    engine.new_game()
    yield engine
    engine.close()


def test_stockfish_finds_mate_in_one(stockfish):
    level = stockfish.level("max")
    quick = Level(level.key, level.label, None, 0.3, level.options)
    assert stockfish.best_move(chess.Board(MATE_IN_ONE), quick, threading.Event()) == chess.Move.from_uci("d1d8")


def test_stockfish_close_ends_process(stockfish):
    process = stockfish.client.process
    stockfish.close()
    assert process.poll() is not None
