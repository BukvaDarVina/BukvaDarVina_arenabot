import pytest
from engines.bulls_cows_engine import BullsAndCowsEngine
from engines.sea_battle_engine import SeaBattleEngine
from engines.chess_engine import ChessEngine
from engines.manager import EngineManager

def test_bulls_cows_first_guess():
    """Позитив (Движок): Быки/Коровы первый ход"""
    engine = BullsAndCowsEngine()
    engine.initialize()
    guess = engine.get_next_guess([])
    assert guess == "0123"

def test_bulls_cows_boundary_one_option():
    """Граница (Движок): Быки/Коровы остался 1 вариант"""
    engine = BullsAndCowsEngine()
    engine.initialize()
    # Искусственно сужаем пул до одного ответа
    engine.possible_solutions = ["5678"]
    guess = engine.get_next_guess([{"guess": "1234", "bulls": 0, "cows": 0}])
    assert guess == "5678"

def test_bulls_cows_negative_impossible_history():
    """Негатив (Движок): Быки/Коровы ложная история от оппонента"""
    engine = BullsAndCowsEngine()
    engine.initialize()
    engine.possible_solutions = []  # Имитация отсутствия возможных решений
    guess = engine.get_next_guess([{"guess": "1234", "bulls": 4, "cows": 4}])
    assert guess == "0000"  # Фолбэк на 0000 по спецификации

def test_sea_battle_positive_start():
    """Позитив (Движок): Морской бой начало матча"""
    engine = SeaBattleEngine()
    shot = engine.get_best_shot("opp_1", {"hits": [], "misses": []})
    assert shot in ["E5", "E6", "F5", "F6"]

def test_sea_battle_boundary_centers_taken():
    """Граница (Движок): Морской бой, центры заняты"""
    engine = SeaBattleEngine()
    # Передаем состояние, где все центры уже отстреляны
    state = {"hits": ["E5", "E6"], "misses": ["F5", "F6"]}
    shot = engine.get_best_shot("opp_1", state)
    assert shot == "A1"  # Фолбэк из заглушки

def test_chess_engine_negative_no_binary():
    """Негатив (Stockfish): Нет бинарника в ОС"""
    engine = ChessEngine(executable_path="path_that_does_not_exist")
    res = engine.initialize()
    assert res is False

def test_engine_manager_invariant_chess():
    """Инвариант (Stockfish): Вызов хода до инициализации"""
    manager = EngineManager()
    manager.is_initialized = False
    res = manager.get_chess_move("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert res is None