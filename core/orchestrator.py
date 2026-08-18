import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger("LLMOrchestrator")

class LLMOrchestrator:
    """
    Мозг системы (Голова Франкенштейна). 
    Управляет игровым циклом, связывает клиент, память, транслятор состояний и математические движки.
    """
    
    def __init__(self, client: Any, db: Any, engines: Any, translator: Any):
        self.client = client
        self.db = db
        self.engines = engines
        self.translator = translator
        
    async def play_match(self, table_id: str) -> None:
        """
        Непрерывный игровой цикл матча:
        1. Запрос текущего состояния матча с Арены.
        2. Анализ последних ходов соперника через транслятор.
        3. Вычисление оптимального хода математическим движком.
        4. Отправка хода на платформу.
        """
        logger.info(f"Начало активного матча за столом {table_id}. Запуск игрового цикла...")
        
        last_processed_move_index = 0
        game_type = "Chess"  # По умолчанию или определяется из данных стола
        
        try:
            while True:
                # 1. Получаем актуальное состояние стола
                state = await self.client.get_match_state(table_id)
                if not state:
                    logger.warning(f"Не удалось получить состояние стола {table_id}. Повтор через 3 секунды...")
                    await asyncio.sleep(3)
                    continue
                
                # Определяем тип игры, если он передан в состоянии стола
                game_type = state.get("game_type", game_type)
                moves_history = state.get("moves", [])
                
                # Проверяем, появились ли новые ходы от противника
                if len(moves_history) > last_processed_move_index:
                    latest_move_text = moves_history[-1]
                    logger.info(f"получен новый ход противника: {latest_move_text}")
                    
                    # 2. Переводим текст в машинный формат через транслятор (нервную систему)
                    parsed_move = self.translator.parse_move(game_type, latest_move_text)
                    
                    # 3. Передаем управление соответствующему движку (мышцам) для ответа
                    bot_move = self._calculate_response_move(game_type, state, parsed_move)
                    
                    if bot_move:
                        logger.info(f"Движок рассчитал ответный ход: {bot_move}. Отправка на Арену...")
                        success = await self.client.send_move(table_id, bot_move)
                        if success:
                            logger.info(f"Ход {bot_move} успешно принят платформой.")
                        else:
                            logger.warning(f"Платформа отклонила ход {bot_move}.")
                    
                    last_processed_move_index = len(moves_history)
                
                # Проверяем, не завершился ли матч
                if state.get("is_finished", False):
                    winner = state.get("winner", "Unknown")
                    logger.info(f"Матч на столе {table_id} завершен! Победитель: {winner}")
                    # Сохраняем результаты в базу данных для Opponent Profiling
                    opponent_id = state.get("opponent_id", "unknown_opponent")
                    await self.db.save_match(opponent_id, game_type, winner, moves_history)
                    break
                
                # Пауза между опросами состояния стола (Polling)
                await asyncio.sleep(2)
                
        except asyncio.CancelledError:
            logger.info(f"Игровой цикл за столом {table_id} был отменен.")
        except Exception as e:
            logger.error(f"Критическая ошибка в игровом цикле матча {table_id}: {e}", exc_info=True)
        finally:
            logger.info(f"Завершение работы с игровым столом {table_id}.")

    def _calculate_response_move(self, game_type: str, board_state: dict, parsed_move: Optional[dict]) -> Optional[str]:
        """Маршрутизатор вычислений к конкретным математическим движкам"""
        if game_type == "Chess":
            fen = board_state.get("fen", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
            return self.engines.get_chess_move(fen)
            
        elif game_type == "Bulls and Cows":
            history = board_state.get("history", [])
            return self.engines.get_bulls_and_cows_guess(history)
            
        elif game_type == "Sea Battle":
            opponent_id = board_state.get("opponent_id", "default_opp")
            return self.engines.get_sea_battle_shot(opponent_id, board_state)
            
        elif game_type == "Reversi":
            fen_or_board = board_state.get("board", "")
            color = board_state.get("color", "B")
            return self.engines.get_reversi_move(fen_or_board, color)
            
        else:
            logger.warning(f"Для игры '{game_type}' пока не подключен специфический движок.")
            return None