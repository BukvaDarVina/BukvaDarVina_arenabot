import asyncio
import logging
import time
from typing import Any, Optional

logger = logging.getLogger("LLMOrchestrator")

class LLMOrchestrator:
    def __init__(self, client: Any, db: Any, engines: Any, translator: Any):
        self.client = client
        self.db = db
        self.engines = engines
        self.translator = translator
        
    async def play_match(self, table_id: str) -> None:
        logger.info(f"Запуск игрового цикла за столом {table_id}...")
        
        last_processed_move_index = 0
        game_type = "chess"
        last_state_change_time = time.time()
        
        try:
            while True:
                state = await self.client.get_match_state(table_id)
                if not state:
                    await asyncio.sleep(3)
                    continue
                
                game_type = state.get("game_type", state.get("game", game_type))
                moves_history = state.get("moves", [])

                # Проверка завершения матча
                if state.get("is_finished", False) or state.get("status") in ["finished", "aborted", "abandoned"]:
                    winner = state.get("winner", "Unknown")
                    logger.info(f"Матч {table_id} завершен! Победитель: {winner}")
                    
                    # СОХРАНЯЕМ РЕЗУЛЬТАТ В БАЗУ ДАННЫХ
                    if hasattr(self.db, 'save_match'):
                        await self.db.save_match(table_id, game_type, winner, moves_history)
                    
                    await self.client.leave_table(table_id)
                    break

                # Логика определения хода (исправление проблемы первого хода)
                current_moves_len = len(moves_history)
                new_moves_available = current_moves_len > last_processed_move_index
                
                # Если сервер не отдает флаг is_my_turn, мы вычисляем сами.
                # Если история пуста и мы тут, значит мы ходим первыми.
                is_my_turn = state.get("is_my_turn", False)
                if current_moves_len == 0 and not new_moves_available:
                    is_my_turn = True

                if new_moves_available:
                    last_state_change_time = time.time() # Сброс таймера активности
                    latest_move = moves_history[-1]
                    logger.info(f"Ход противника: '{latest_move}'")
                    last_processed_move_index = current_moves_len
                    # Если противник походил, значит теперь точно наша очередь
                    is_my_turn = True 

                if is_my_turn: 
                    parsed_move = None
                    if current_moves_len > 0:
                        parsed_move = self.translator.parse_move(game_type, moves_history[-1])
                    
                    bot_move = self._calculate_response_move(game_type, state, parsed_move)
                    
                    if bot_move:
                        logger.info(f"Движок предложил ход: {bot_move}. Отправляем...")
                        success = await self.client.send_move(table_id, bot_move)
                        if success:
                            logger.info("Ход успешно принят.")
                            last_processed_move_index += 1 # Обновляем индекс заранее
                            await asyncio.sleep(2)
                        else:
                            logger.warning(f"Платформа отклонила ход {bot_move}. Повтор через 2с.")
                            await asyncio.sleep(2)

                # Таймаут: если матч висит без изменений 5 минут (300 сек) - выходим
                if time.time() - last_state_change_time > 300:
                    logger.warning(f"Таймаут: Стол {table_id} мертв более 5 минут. Покидаем его.")
                    await self.client.leave_table(table_id)
                    break

                await asyncio.sleep(2)
                
        except asyncio.CancelledError:
            logger.info(f"Игровой цикл {table_id} отменен.")
        except Exception as e:
            logger.error(f"Ошибка в матче {table_id}: {e}", exc_info=True)
            await self.client.leave_table(table_id)

    def _calculate_response_move(self, game_type: str, board_state: dict, parsed_move: Optional[dict]) -> Optional[str]:
        # Маршрутизация к движкам
        game_lower = game_type.lower()
        if "chess" in game_lower:
            fen = board_state.get("fen", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
            return self.engines.get_chess_move(fen)
        # Добавьте вызовы других движков при необходимости...
        return None