import logging
from typing import Optional, List, Dict, Any

from .chess_engine import ChessEngine
from .bulls_cows_engine import BullsAndCowsEngine
from .sea_battle_engine import SeaBattleEngine
from .reversi_engine import ReversiEngine

logger = logging.getLogger("EngineManager")

class EngineManager:
    """
    Мышцы системы. Управляет математическими движками (Stockfish, Кнут и т.д.).
    Связывает вызовы от LLM-оркестратора с конкретными алгоритмами.
    """
    
    def __init__(self):
        self.is_initialized = False
        self.chess = ChessEngine()
        self.bulls_cows = BullsAndCowsEngine()
        self.sea_battle = SeaBattleEngine()
        self.reversi = ReversiEngine()
        
    def initialize(self) -> bool:
        """Инициализация и проверка доступности всех движков."""
        logger.info("Инициализация игровых движков...")
        
        # Запуск и проверка Stockfish
        if not self.chess.initialize():
            logger.error("Ошибка инициализации Stockfish. Убедитесь, что движок установлен.")
            return False
            
        # Предрасчет для алгоритма Кнута
        self.bulls_cows.initialize()
        
        self.is_initialized = True
        logger.info("Все математические движки успешно инициализированы.")
        return True
        
    def get_chess_move(self, fen: str, depth: int = 15) -> Optional[str]:
        if not self.is_initialized:
            return None
        return self.chess.get_best_move(fen, depth)
        
    def get_bulls_and_cows_guess(self, history: List[Dict[str, Any]]) -> str:
        if not self.is_initialized:
            return "1122"
        return self.bulls_cows.get_next_guess(history)
        
    def get_sea_battle_shot(self, opponent_id: str, board_state: Dict[str, Any]) -> str:
        if not self.is_initialized:
            return "E5"
        return self.sea_battle.get_best_shot(opponent_id, board_state)

    def get_reversi_move(self, board_state: str, color: str) -> str:
        if not self.is_initialized:
            return "F5"
        return self.reversi.get_best_move(board_state, color)
        
    def shutdown(self):
        """Корректное завершение работы движков."""
        logger.info("Завершение процессов игровых движков...")
        self.chess.shutdown()