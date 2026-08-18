import pytest
from parsers.regex_parser import RegexParser
from parsers.translator import GameStateTranslator

def test_parser_chess_positive():
    """Позитив (Парсер): Валидный ход шахматы"""
    parser = RegexParser()
    res = parser.parse_chess("White plays e4")
    assert res == {"player": "White", "move": "e4"}

def test_parser_shashki_positive():
    """Позитив (Парсер): Валидный ход шашки с взятием"""
    parser = RegexParser()
    res = parser.parse_shashki("Cow-SRB plays b6–d4, taking 1 (11–12)")
    assert res == {"player": "Cow-SRB", "move": "b6–d4"}

def test_translator_invalid_move():
    """Негатив (Парсер): Некорректный текст хода"""
    translator = GameStateTranslator()
    res = translator.parse_move("Chess", "Garbage text 123")
    assert res is None  # Должен вернуть None без падения (Exception)

def test_translator_unknown_game():
    """Инвариант (Оркестратор): Неизвестная игра"""
    translator = GameStateTranslator()
    res = translator.parse_move("Monopoly", "Player rolls 5")
    assert res is None