import asyncio
import time
import logging
import random
from typing import Optional, Any, Dict

logger = logging.getLogger("LLMOrchestrator")

class LLMOrchestrator:
    def __init__(self, client, engines, db, translator):
        self.client = client
        self.engines = engines
        self.db = db
        self.translator = translator
        self._last_seen_moves_len = 0

    async def play_match(self, table_id: str) -> None:
        logger.info(f"Запуск игрового цикла за столом {table_id}...")
        
        last_sent_move_count = -1
        game_type = "Chess"
        last_state_change_time = time.time()
        
        my_agent_name = "Frank_by_DVB"
        try:
            me_resp = await self.client.client.get("/api/keys/me", headers=self.client._get_auth_headers())
            if me_resp.status_code == 200:
                my_agent_name = me_resp.json().get("agent", my_agent_name)
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

                game_type = state.get("game_type", state.get("game", game_type))
                moves_history = state.get("moves", [])
                current_moves_len = len(moves_history)
                
                if state.get("is_finished", False) or status in ["finished", "aborted", "abandoned"]:
                    winner = state.get("winner", "Unknown")
                    logger.info(f"Матч {table_id} завершен! Победитель: {winner}")
                    if hasattr(self.db, 'save_match'):
                        await self.db.save_match(table_id, game_type, winner, moves_history)
                    await self.client.leave_table(table_id)
                    break

                is_my_turn = state.get("yourTurn", False)
                
                if current_moves_len != last_sent_move_count:
                    last_sent_move_count = -1

                # Фоновая генерация реплик через Ollama при появлении новых ходов
                if current_moves_len > 0 and current_moves_len != self._last_seen_moves_len:
                    self._last_seen_moves_len = current_moves_len
                    latest_move = moves_history[-1]
                    logger.info(f"Соперник походил: '{latest_move}'. Всего ходов в партии: {current_moves_len}")
                    
                    async def speak():
                        comment = await self.client.generate_chat_comment(game_type, str(latest_move), "игрок")
                        if comment:
                            await self.client.send_chat_message(table_id, comment)
                    
                    asyncio.create_task(speak())

                if is_my_turn and last_sent_move_count != current_moves_len:
                    logger.info(f"Очередь нашего хода! Ходов в истории: {current_moves_len}")
                    
                    parsed_move = None
                    if current_moves_len > 0:
                        try:
                            parsed_move = self.translator.parse_move(game_type, moves_history[-1])
                        except Exception:
                            pass
                    
                    bot_move = self._calculate_response_move(game_type, state, parsed_move)
                    
                    if bot_move:
                        logger.info(f"Отправляем ход на сервер: {bot_move}")
                        success = await self.client.send_move(table_id, bot_move)
                        if success:
                            logger.info("Ход успешно отправлен.")
                            last_sent_move_count = current_moves_len
                            last_state_change_time = time.time()
                            await asyncio.sleep(3)
                        else:
                            logger.warning("Сервер отклонил ход. Повтор через 2с...")
                            await asyncio.sleep(2)
                    else:
                        logger.warning("Движок не смог рассчитать ход.")
                else:
                    await asyncio.sleep(2)

                if time.time() - last_state_change_time > 300:
                    logger.warning(f"Таймаут: Игра на столе {table_id} зависла на 5 минут.")
                    await self.client.leave_table(table_id)
                    break
                
        except asyncio.CancelledError:
            logger.info(f"Игровой цикл стола {table_id} отменен.")
        except Exception as e:
            logger.error(f"Критическая ошибка в матче {table_id}: {e}", exc_info=True)
            await self.client.leave_table(table_id)

    def _calculate_response_move(self, game_type: str, board_state: dict, parsed_move: Optional[dict]) -> Any:
        game_lower = game_type.lower()
        legal_moves = board_state.get("legal_moves", [])
        
        # 1. Шахматы
        if "chess" in game_lower:
            fen = board_state.get("fen")
            if legal_moves:
                selected_move = None
                if fen:
                    try:
                        raw_move = self.engines.get_chess_move(fen)
                        if raw_move and len(raw_move) >= 4:
                            f_from, f_to = raw_move[0:2], raw_move[2:4]
                            promo = raw_move[4] if len(raw_move) == 5 else None
                            
                            for lm in legal_moves:
                                if lm.get("from") == f_from and lm.get("to") == f_to:
                                    if promo and lm.get("promotion") != promo:
                                        continue
                                    selected_move = lm
                                    break
                    except Exception as e:
                        logger.error(f"Ошибка Stockfish: {e}")
                
                if not selected_move:
                    selected_move = legal_moves[0]
                
                if "type" not in selected_move:
                    selected_move["type"] = "move"
                return selected_move

        # 2. Быки и Коровы
        elif "bulls" in game_lower or "cows" in game_lower:
            if board_state.get("phase") == "setup" and not board_state.get("mySecret"):
                secret = "".join(random.sample("0123456789", 4))
                return {"type": "set_secret", "number": secret}
            else:
                guess = self.engines.get_bulls_cows_move(board_state.get("oppGuesses", []))
                if not guess:
                    guess = "".join(random.sample("0123456789", 4))
                return {"type": "guess", "number": str(guess)}

        # 3. Морской бой
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

        # 4. Шашки и Реверси
        elif any(g in game_lower for g in ["checkers", "shashki", "reversi"]):
            if legal_moves:
                return random.choice(legal_moves)
            if "reversi" in game_lower:
                return {"type": "pass"}

        # 5. Пятнашки
        elif "fifteen" in game_lower:
            return {"type": "progress", "placed": random.randint(1, 15), "moves": random.randint(10, 100)}

        # 6. Артиллерия
        elif "artillery" in game_lower:
            return {"type": "fire", "angle": random.randint(10, 170), "power": random.randint(20, 100)}

        # 7. Камень-Ножницы-Бумага
        elif "rps" in game_lower or "rock" in game_lower:
            moves = ["r", "p", "s"]
            if "rpsls" in game_lower or "lizard" in game_lower:
                moves.extend(["l", "v"])
            return {"type": "throw", "v": random.choice(moves)}

        # 8. Дурак
        elif "durak" in game_lower:
            role = board_state.get("role")
            hand = board_state.get("hand", [])
            table = board_state.get("table", [])
            can_attack = board_state.get("canAttack", False)
            
            def get_card_id(card_obj_or_int):
                if isinstance(card_obj_or_int, dict):
                    return card_obj_or_int.get("id", 0)
                return int(card_obj_or_int)

            if role == "defender":
                unbeaten_idx = None
                for idx, bout in enumerate(table):
                    if bout.get("d") is None:
                        unbeaten_idx = idx
                        break
                
                if unbeaten_idx is not None:
                    target_card = get_card_id(table[unbeaten_idx]["a"])
                    target_suit = target_card // 9
                    target_power = target_card % 9
                    trump_suit = board_state.get("trump", {}).get("suit", 0)
                    
                    best_card = None
                    for card in hand:
                        c_id = get_card_id(card)
                        c_suit = c_id // 9
                        c_power = c_id % 9
                        if (c_suit == target_suit and c_power > target_power) or (c_suit == trump_suit and target_suit != trump_suit):
                            best_card = c_id
                            break
                    
                    if best_card is not None:
                        return {"type": "defend", "idx": unbeaten_idx, "card": best_card}
                    else:
                        return {"type": "take"}
                
                return {"type": "done"}

            elif role == "attacker" or can_attack:
                if not table:
                    if hand:
                        return {"type": "attack", "card": get_card_id(hand[0])}
                else:
                    table_ranks = set()
                    for bout in table:
                        if "a" in bout and bout["a"] is not None:
                            table_ranks.add(get_card_id(bout["a"]) % 9)
                        if "d" in bout and bout["d"] is not None:
                            table_ranks.add(get_card_id(bout["d"]) % 9)
                    
                    for card in hand:
                        c_id = get_card_id(card)
                        if c_id % 9 in table_ranks:
                            return {"type": "attack", "card": c_id}
                
                return {"type": "done"}

            return {"type": "done"}

        # Правило (The Rule)
        elif "rule" in game_lower:
            phase = board_state.get("phase")
            role = board_state.get("role")
            rules_list = board_state.get("rules", [{"id": "even"}])
            
            if role == "picker" and phase == "choose":
                # Если мы загадываем правило, выбираем первое попавшееся из списка
                return {"type": "choose_rule", "rule": rules_list[0].get("id", "even")}
                
            elif phase == "probe":
                if role == "guesser":
                    probes_left = board_state.get("probesLeft", 10)
                    
                    # ВАЖНО: Если попытки пробы исчерпаны (probesLeft == 0), 
                    # мы обязаны сделать финальную догадку (guess), иначе игра зависнет!
                    if probes_left <= 0:
                        # Выбираем случайное правило из доступного открытого списка правил
                        chosen_rule_id = random.choice(rules_list).get("id", "even")
                        logger.info(f"попытки закончились. Делаем финальный guess правила: {chosen_rule_id}")
                        return {"type": "guess", "rule": chosen_rule_id}
                    else:
                        # Иначе продолжаем зондировать случайным числом от 1 до 100
                        return {"type": "probe", "n": random.randint(1, 100)}
                else:
                    # Если мы picker в фазе probe, мы просто ждем ходов соперника
                    return {"type": "pass"}
            else:
                # Фоллбек-догадка
                fallback_rule = rules_list[0].get("id", "even")
                return {"type": "guess", "rule": fallback_rule}

        # 9. Остальные игры / Универсальный Fallback
        elif "mind" in game_lower:
            return {"type": "play"}
        elif "onewave" in game_lower or "wave" in game_lower:
            options = board_state.get("options", ["0"])
            return {"type": "pick", "v": random.choice(options)}
        elif "karateka" in game_lower:
            return {"type": "act", "a": random.choice(["strike", "grab", "block"])}
        elif "pact" in game_lower:
            if board_state.get("phase") == "promise":
                return {"type": "promise", "p": random.choice(["cooperate", "betray", "alternate"])}
            return {"type": "move", "m": random.choice(["c", "d"])}
        elif "gomoku" in game_lower or "five" in game_lower:
            return {"type": "move", "r": random.randint(0, 14), "c": random.randint(0, 14)}
        elif "dots" in game_lower or "boxes" in game_lower:
            n = board_state.get("n", 4)
            return {"type": "edge", "kind": random.choice(["h", "v"]), "r": random.randint(0, n-1), "c": random.randint(0, n-1)}
        elif "tank" in game_lower:
            return {"type": "move", "dx": random.choice([-1, 1]), "dy": random.choice([-1, 0, 1])}
        elif "three" in game_lower or "fronts" in game_lower:
            return {"type": "split", "a": 4, "b": 4, "c": 5}

        if legal_moves:
            fallback = random.choice(legal_moves)
            if isinstance(fallback, dict) and "type" not in fallback:
                fallback["type"] = "move"
            return fallback

        return {"type": "pass"}