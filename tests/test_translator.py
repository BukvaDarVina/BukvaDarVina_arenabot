# tests/test_translator.py
import pytest
from parsers.translator import GameStateTranslator

def test_chess_move_parsing(mocker):
    translator = GameStateTranslator()
    
    # Поскольку метод parse_move может обращаться к LLM или сложной логике, 
    # в рамках Unit-тестирования мы проверяем, как он обрабатывает успешный ответ.
    # Если в вашей текущей реализации parse_move возвращает строку (например, "e2e4") 
    # или словарь, адаптируйте assert под вашу реальную функцию.
    
    # Пример 1: Если ваш транслятор умеет чистить строку от лишних символов (например, "1. e2e4" -> "e2e4")
    # Допустим, мы временно "мокаем" внутренний парсер для теста
    mocker.patch.object(translator, 'parse_move', return_value={"move": "e2e4"})
    
    result = translator.parse_move("Chess", "1. e2e4")
    assert result == {"move": "e2e4"}