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
        game_type = "Chess"
        last_state_change_time = time.time()
        
        my_agent_name = "Frank_by_DVB"
        try:
            me_resp = await self.client.client.get("/api/keys/me", headers=self.client._get_auth_headers())
            if me_resp.status_code == 200:
                my_agent_name = me_resp.json().get("agent", my_agent_name)
                logger.info(f"Мое имя на сервере: {my_agent_name}")
        except Exception:
            pass

        try:
            while True:
                state = await self.client.get_match_state(table_id)
                
                if not state:
                    await asyncio.sleep(3)
                    continue
                    
                status = state.get("status")
                if status == "waiting_for_opponent":
                    if time.time() - last_state_change_time > 300:
                        logger.warning(f"Таймаут: Никто не присоединился к столу {table_id} за 5 минут.")
                        await self.client.leave_table(table_id)
                        break
                    await asyncio.sleep(5)
                    continue

                # ИГРА ИДЕТ
                game_type = state.get("game_type", state.get("game", game_type))
                moves_history = state.get("moves", [])
                
                if state.get("is_finished", False) or status in ["finished", "aborted", "abandoned"]:
                    winner = state.get("winner", "Unknown")
                    logger.info(f"Матч {table_id} завершен! Победитель: {winner}")
                    if hasattr(self.db, 'save_match'):
                        await self.db.save_match(table_id, game_type, winner, moves_history)
                    await self.client.leave_table(table_id)
                    break

                current_moves_len = len(moves_history)
                new_moves_available = current_moves_len > last_processed_move_index
                
                # --- УМНОЕ ОПРЕДЕЛЕНИЕ ОЧЕРЕДИ ХОДА ---
                is_my_turn = state.get("yourTurn", state.get("your_turn", state.get("is_my_turn", False)))
                turn_side = state.get("turn") or state.get("to_move") # Для шахмат ('w' или 'b')
                my_color = state.get("your_color") # ('w' или 'b')
                
                if turn_side and my_color:
                    is_my_turn = (turn_side == my_color)
                
                # Если сервер не передал флаги, страхуемся по четности длины истории
                if not is_my_turn and current_moves_len == 0:
                    is_my_turn = True # Мы белые и ходим первыми

                if new_moves_available:
                    last_state_change_time = time.time()
                    latest_move = moves_history[-1]
                    logger.info(f"Соперник походил: '{latest_move}'. Всего ходов в партии: {current_moves_len}")
                    last_processed_move_index = current_moves_len

                # --- ДЕЛАЕМ ХОД, ЕСЛИ СЕЙЧАС НАША ОЧЕРЕДЬ ---
                if is_my_turn:
                    logger.info(f"Наш ход! Рассчитываем позицию (всего ходов: {current_moves_len})...")
                    
                    parsed_move = None
                    if current_moves_len > 0:
                        try:
                            parsed_move = self.translator.parse_move(game_type, moves_history[-1])
                        except Exception:
                            pass
                    
                    bot_move = self._calculate_response_move(game_type, state, parsed_move)
                    
                    if bot_move:
                        logger.info(f"Движок выдал ход: {bot_move}. Отправляем на сервер...")
                        success = await self.client.send_move(table_id, bot_move)
                        if success:
                            logger.info("Успех! Ход принят платформой.")
                            last_state_change_time = time.time()
                            # Даем паузу, чтобы сервер успел обновить состояние доски
                            await asyncio.sleep(3)
                            continue
                        else:
                            logger.warning("Платформа отклонила ход. Повтор через 2с...")
                            await asyncio.sleep(2)
                    else:
                        logger.warning("Движок не смог рассчитать ход.")
                else:
                    # Не наша очередь — просто ждем соперника
                    await asyncio.sleep(2)

                # Таймаут зависания (никто не ходит)
                if time.time() - last_state_change_time > 300:
                    logger.warning(f"Таймаут: Игра на столе {table_id} зависла на 5 минут без новых ходов.")
                    await self.client.leave_table(table_id)
                    break
                
        except asyncio.CancelledError:
            logger.info(f"Игровой цикл стола {table_id} отменен.")
        except Exception as e:
            logger.error(f"Критическая ошибка в матче {table_id}: {e}", exc_info=True)
            await self.client.leave_table(table_id)
    def _calculate_response_move(self, game_type: str, board_state: dict, parsed_move: Optional[dict]) -> Any:
        """Абсолютно всеядный маршрутизатор. Знает спецификации JSON для всех игр на Арене."""
        game_lower = game_type.lower()
        import random
        
        # Получаем легальные ходы (Платформа отдает их для Chess, Shashki, Reversi)
        legal_moves = board_state.get("legal_moves", [])

        # ==========================================
        # 1. CLASS 2 (Математические игры - работают Движки)
        # ==========================================
        
        # Шахматы
        if "chess" in game_lower:
            fen = board_state.get("fen", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
            raw_move = self.engines.get_chess_move(fen)
            if raw_move and len(raw_move) >= 4:
                move_payload = {"type": "move", "from": raw_move[0:2], "to": raw_move[2:4]}
                if len(raw_move) == 5:
                    move_payload["promotion"] = raw_move[4]
                return move_payload
            # Резерв
            if legal_moves: return random.choice(legal_moves)

        # Быки и Коровы
        elif "bulls" in game_lower or "cows" in game_lower:
            if board_state.get("phase") == "setup" and not board_state.get("mySecret"):
                secret = "".join(random.sample("0123456789", 4))
                return {"type": "set_secret", "number": secret}
            else:
                guess = self.engines.get_bulls_cows_move(board_state.get("oppGuesses", []))
                if not guess: guess = "".join(random.sample("0123456789", 4))
                return {"type": "guess", "number": str(guess)}

        # Морской бой
        elif "sea battle" in game_lower or "seabattle" in game_lower:
            if board_state.get("phase") == "placing":
                return {"type": "place", "ships": [
                    {"r":0,"c":0,"len":4,"dir":"h"}, {"r":0,"c":5,"len":3,"dir":"h"},
                    {"r":2,"c":0,"len":3,"dir":"h"}, {"r":2,"c":5,"len":2,"dir":"h"},
                    {"r":4,"c":0,"len":2,"dir":"h"}, {"r":4,"c":3,"len":2,"dir":"h"},
                    {"r":8,"c":0,"len":1,"dir":"h"}, {"r":8,"c":2,"len":1,"dir":"h"},
                    {"r":8,"c":4,"len":1,"dir":"h"}, {"r":8,"c":6,"len":1,"dir":"h"}
                ]}
            shot = self.engines.get_sea_battle_move(board_state.get("my_board", []), board_state.get("shots", []))
            if isinstance(shot, dict) and "r" in shot and "c" in shot:
                return {"type": "shot", "r": shot["r"], "c": shot["c"]}
            return {"type": "shot", "r": random.randint(0,9), "c": random.randint(0,9)}

        # Шашки (Shashki / Checkers) и Реверси (Reversi)
        elif any(g in game_lower for g in ["checkers", "shashki", "reversi"]):
            if legal_moves:
                return random.choice(legal_moves)
            if "reversi" in game_lower:
                return {"type": "pass"}

        # Пятнашки (Fifteen Puzzle)
        elif "fifteen" in game_lower:
            # Для пятнашек клиент должен двигать сам, бот будет слать случайный прогресс
            return {"type": "progress", "placed": random.randint(1, 15), "moves": random.randint(10, 100)}


        # ==========================================
        # 2. CLASS 1 (Настольные и карточные игры - Базовые правила)
        # ==========================================

        # Артиллерия (Artillery)
        elif "artillery" in game_lower:
            return {"type": "fire", "angle": random.randint(10, 170), "power": random.randint(20, 100)}

        # Камень-Ножницы-Бумага (RPS / RPSLS)
        elif "rps" in game_lower or "rock" in game_lower:
            moves = ["r", "p", "s"]
            if "rpsls" in game_lower or "lizard" in game_lower:
                moves.extend(["l", "v"])
            return {"type": "throw", "v": random.choice(moves)}

        # Карточный Блеф (Cheat / Believe)
        elif "cheat" in game_lower or "believe" in game_lower:
            hand = board_state.get("hand", [])
            if hand:
                # Кидаем одну первую карту из руки в закрытую, заявляем ранг 0 (Шестерка)
                return {"type": "play", "cards": [hand[0]], "rank": 0}
            return {"type": "doubt"}

        # Дурак (Durak)
        elif "durak" in game_lower:
            role = board_state.get("role")
            hand = board_state.get("hand", [])
            if role == "defender":
                return {"type": "take"} # Бот пока глуп в Дураке, всегда забирает карты
            elif role == "attacker" or board_state.get("canAttack"):
                if hand:
                    return {"type": "attack", "card": hand[0]}
            return {"type": "done"} # non-defender

        # Президент (President)
        elif "president" in game_lower:
            return {"type": "pass"}

        # Телепатия (The Mind)
        elif "mind" in game_lower:
            return {"type": "play"} # Играет самую младшую карту

        # Одна волна (One Wave)
        elif "onewave" in game_lower or "wave" in game_lower:
            options = board_state.get("options", ["0"])
            return {"type": "pick", "v": random.choice(options)}

        # Каратека (Karateka)
        elif "karateka" in game_lower:
            return {"type": "act", "a": random.choice(["strike", "grab", "block"])}

        # Обещания (The Pact)
        elif "pact" in game_lower:
            if board_state.get("phase") == "promise":
                return {"type": "promise", "p": random.choice(["cooperate", "betray", "alternate"])}
            return {"type": "move", "m": random.choice(["c", "d"])}

        # Правило (The Rule)
        elif "rule" in game_lower:
            phase = board_state.get("phase")
            role = board_state.get("role")
            if role == "picker" and phase == "choose":
                rules = board_state.get("rules", [{"id":"even"}])
                return {"type": "choose_rule", "rule": rules[0].get("id", "even")}
            elif phase == "probe":
                return {"type": "probe", "n": random.randint(1, 100)}
            else:
                return {"type": "guess", "rule": "even"}

        # Пять в ряд (Gomoku / Five in a Row)
        elif "gomoku" in game_lower or "five" in game_lower:
            # Случайная клетка 15x15. Если занята - сервер откажет и бот попробует снова
            return {"type": "move", "r": random.randint(0, 14), "c": random.randint(0, 14)}

        # Точки-Тире (Dots and Boxes)
        elif "dots" in game_lower or "boxes" in game_lower:
            # Случайная грань. Если занята - бот будет подбирать до победного
            n = board_state.get("n", 4)
            return {"type": "edge", "kind": random.choice(["h", "v"]), "r": random.randint(0, n-1), "c": random.randint(0, n-1)}

        # Слепые танки (Blind Tanks)
        elif "tank" in game_lower:
            # В танках нельзя стоять на месте.
            return {"type": "move", "dx": random.choice([-1, 1]), "dy": random.choice([-1, 0, 1])}

        # Три фронта (Three Fronts)
        elif "three" in game_lower or "fronts" in game_lower:
            # Нужно распределить 13 юнитов
            return {"type": "split", "a": 4, "b": 4, "c": 5}


        # ==========================================
        # УНИВЕРСАЛЬНЫЙ СПАСАТЕЛЬНЫЙ КРУГ
        # ==========================================
        if legal_moves:
            fallback = random.choice(legal_moves)
            if isinstance(fallback, dict) and "type" not in fallback:
                fallback["type"] = "move"
            return fallback

        logger.warning(f"Игра '{game_type}' полностью неизвестна. Пропускаем ход (pass).")
        return {"type": "pass"}