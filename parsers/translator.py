import logging
from typing import Dict, Any, Optional

from .regex_parser import RegexParser

logger = logging.getLogger("GameStateTranslator")

class GameStateTranslator:
    """
    Нервная система бота. 
    Отвечает за перевод текстовых трансляций Арены в форматы, понятные математическим движкам (Мышцам)[cite: 63, 64].
    """
    
    def __init__(self):
        self.regex = RegexParser()
        # В будущем здесь можно добавить инициализацию LLM клиента для фолбэка парсинга,
        # если регулярные выражения не справятся из-за изменения формата платформы[cite: 28, 65].
        
    def parse_move(self, game_type: str, move_text: str) -> Optional[Dict[str, Any]]:
        """
        Основной метод маршрутизации. Принимает тип игры и текст хода,
        возвращает структурированный словарь для передачи в движок.
        """
        logger.debug(f"Парсинг хода для игры {game_type}: {move_text}")
        
        parsed_data = None
        
        if game_type == "Chess":
            parsed_data = self.regex.parse_chess(move_text)
        elif game_type == "Reversi":
            parsed_data = self.regex.parse_reversi(move_text)
        elif game_type == "Five in a Row":
            parsed_data = self.regex.parse_gomoku(move_text)
        elif game_type == "Bulls and Cows":
            parsed_data = self.regex.parse_bulls_cows(move_text)
        elif game_type == "Sea Battle":
            parsed_data = self.regex.parse_sea_battle(move_text)
        elif game_type == "Shashki":
            parsed_data = self.regex.parse_shashki(move_text)
        elif game_type == "Dots and Boxes":
            parsed_data = self.regex.parse_dots_boxes(move_text)
        else:
            logger.warning(f"Неизвестный тип игры для парсинга: {game_type}")
            return None
            
        if parsed_data:
            logger.info(f"Успешный парсинг ({game_type}): {parsed_data}")
            return parsed_data
        else:
            logger.error(f"Ошибка парсинга хода ({game_type}): {move_text}")
            # TODO: Вызвать LLM-фолбэк для динамического обновления промптов (RAG) [cite: 48, 49]
            return None