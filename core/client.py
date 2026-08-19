import logging
import httpx
import re
import os
import random
import string
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ArenaClient")

class ArenaClient:
    def __init__(self, base_url: str, agent_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token_file = "data/token.txt"
        
        # Пытаемся загрузить токен: сначала из ENV, затем из файла
        self.token = agent_token or self._load_token_from_file()
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=15.0)
        
    def _load_token_from_file(self) -> Optional[str]:
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, "r") as f:
                    token = f.read().strip()
                    if token.startswith("ak_"):
                        return token
        except Exception:
            pass
        return None

    def _save_token_to_file(self, token: str):
        try:
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, "w") as f:
                f.write(token)
        except Exception as e:
            logger.warning(f"Не удалось сохранить токен в файл: {e}")

    def _get_auth_headers(self) -> dict:
        headers = {}
        if self.token:
            safe_token = str(self.token).encode("ascii", errors="ignore").decode("ascii")
            if safe_token.startswith("ak_"):
                headers["Authorization"] = f"Bearer {safe_token}"
                headers["X-Agent-Token"] = safe_token
        return headers

    async def fetch_documents(self, docs: List[str]) -> None:
        for doc in docs:
            try:
                path = doc if doc.startswith("/") else f"/{doc}"
                response = await self.client.get(path)
                if response.status_code == 200:
                    logger.info(f"Документ {path} успешно прочитан.")
            except httpx.RequestError as e:
                logger.error(f"Ошибка сети при запросе документа {doc}: {e}")

    async def register_agent(self, agent_name: str = "ArenaChampionBot") -> bool:
        """Если токен есть, пропускаем регистрацию, чтобы не ловить 429 Too Many Requests"""
        if self.token and str(self.token).startswith("ak_"):
            logger.info(f"Используется существующий валидный токен: {self.token[:10]}...")
            return True

        base_name = agent_name
        for attempt in range(5):
            current_name = base_name if attempt == 0 else f"{base_name}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=4))}"
            payload = {"agent": current_name, "owner": "BukvaDarVina", "runtime": "Python 3.14", "model": "LLM Orchestrator + Stockfish"}
            
            try:
                logger.info(f"Регистрация агента '{current_name}' на /api/keys...")
                response = await self.client.post("/api/keys", json=payload, headers={"Content-Type": "application/json"})
                
                if response.status_code in (200, 201):
                    data = response.json()
                    token = data.get("key") or data.get("token")
                    if token and str(token).startswith("ak_"):
                        self.token = token
                        self._save_token_to_file(token)
                        logger.info(f"Успешная регистрация! Получен ключ: {token[:10]}...")
                        return True
                elif response.status_code == 409:
                    logger.warning(f"Имя '{current_name}' занято (409 Conflict). Пробуем другое...")
                    continue
                elif response.status_code == 429:
                    logger.error("КРИТИЧНАЯ ОШИБКА: Лимит токенов исчерпан (429). Задайте токен вручную в docker-compose.yml!")
                    break
            except Exception as e:
                logger.error(f"Ошибка при попытке регистрации агента: {e}")
                break
        return False

    async def get_current_seated_table(self) -> Optional[str]:
        try:
            response = await self.client.get("/api/keys/me", headers=self._get_auth_headers())
            if response.status_code == 200:
                data = response.json()
                seated = data.get("seated_at") or data.get("match") or data.get("table")
                if seated:
                    logger.info(f"Мы уже находимся за активным столом: {seated}")
                    return seated
        except Exception:
            pass
        return None

    async def leave_table(self, table_id: str) -> bool:
        """Покидает стол, чтобы не зависнуть навсегда"""
        try:
            response = await self.client.post(f"/api/matches/{table_id}/leave", headers=self._get_auth_headers())
            if response.status_code in (200, 201):
                logger.info(f"Успешно покинули матч {table_id}.")
                return True
            else:
                logger.warning(f"Не удалось покинуть стол {table_id}. Статус: {response.status_code}")
        except Exception as e:
            logger.error(f"Ошибка при выходе из стола: {e}")
        return False

    async def get_open_tables(self) -> List[Dict[str, Any]]:
        try:
            response = await self.client.get("/", headers=self._get_auth_headers())
            if response.status_code == 200:
                html_content = response.text
                tables = []
                if "Open tables" in html_content:
                    parts = html_content.split("Open tables")
                    section = parts[1].split("Playing now")[0] if "Playing now" in parts[1] else parts[1]
                    match_links = re.findall(r'href=["\'](?:/m/|/api/tables/|/table/|/game/)([\w\-_]+)["\']', section)
                    for table_id in set(match_links):
                        if table_id not in ["leaderboard", "games", "agents", "api", "login", "register"]:
                            tables.append({"id": table_id, "is_rated": False})
                return tables
        except Exception as e:
            logger.error(f"Ошибка при запросе лобби: {e}")
        return []

    async def create_table(self, game_type: Optional[str] = None) -> Optional[str]:
        """Создает стол для указанной игры, а если не указана — берет случайную!"""
        try:
            headers = self._get_auth_headers()
            
            seated = await self.get_current_seated_table()
            if seated:
                return seated

            # Если игру не передали жестко, запрашиваем список у платформы и берем любую
            if not game_type:
                games_resp = await self.client.get("/api/games", headers=headers)
                if games_resp.status_code == 200:
                    games_data = games_resp.json()
                    if isinstance(games_data, list) and games_data:
                        import random
                        # Берем случайную игру из списка доступных!
                        game_info = random.choice(games_data)
                        game_type = game_info.get("name", "chess").lower()
                    elif isinstance(games_data, dict) and "games" in games_data:
                        available = games_data["games"]
                        if available:
                            import random
                            chosen = random.choice(available)
                            game_type = chosen.lower() if isinstance(chosen, str) else chosen.get("name", "chess").lower()
            
            # Если Апи недоступно, фоллбек на шахматы
            game_type = game_type or "chess"

            payload = {"game": game_type.lower()}
            logger.info(f"Случайный выбор! Создаем стол для игры: '{payload['game']}'...")
            
            response = await self.client.post("/api/tables", json=payload, headers=headers)
            if response.status_code in (200, 201):
                data = response.json()
                return data.get("id") or data.get("table_id") or data.get("match") or data.get("match_id")
            elif response.status_code == 409:
                match = re.search(r'match\s+([A-Z0-9]+)', response.text)
                if match:
                    return match.group(1)
        except Exception as e:
            logger.error(f"Ошибка при создании стола: {e}")
        return None

    async def sit_at_table(self, table_id: str) -> bool:
        try:
            response = await self.client.post(f"/api/tables/{table_id}/join", headers=self._get_auth_headers())
            return response.status_code in (200, 201)
        except Exception:
            return False
            
    async def get_match_state(self, table_id: str) -> Optional[Dict[str, Any]]:
        """Получает состояние матча и разворачивает вложенный ключ 'state', если он есть"""
        headers = self._get_auth_headers()
        last_response = None
        
        # 1. Пробуем эндпоинт столов
        try:
            response = await self.client.get(f"/api/tables/{table_id}", headers=headers)
            if response.status_code == 200:
                data = response.json()
                return self._flatten_state(data)
            last_response = response
        except Exception:
            pass
            
        # 2. Пробуем эндпоинт матчей
        try:
            response = await self.client.get(f"/api/matches/{table_id}", headers=headers)
            if response.status_code == 200:
                data = response.json()
                return self._flatten_state(data)
            last_response = response
        except Exception:
            pass
            
        if last_response is not None and last_response.status_code == 404:
            return {"status": "waiting_for_opponent", "is_finished": False}
            
        return None

    def _flatten_state(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Разворачивает вложенный словарь state в корневой уровень"""
        if not isinstance(data, dict):
            return {}
        if "state" in data and isinstance(data["state"], dict):
            flattened = {**data}
            # Переносим все поля из вложенного state наверх
            flattened.update(data["state"])
            return flattened
        return data

    async def send_move(self, table_id: str, move: Any) -> bool:
        """Отправляет ход на сервер в чистом виде, без лишних оберток"""
        headers = self._get_auth_headers()
        match_url = f"/api/matches/{table_id}/move"
        
        # Если движок уже вернул словарь (например, {'type': 'move', 'from': 'e2', 'to': 'e4'}),
        # мы отправляем его НАПРЯМУЮ, как есть!
        # Если это строка (например, 'e2e4'), оборачиваем в стандартный формат.
        if isinstance(move, dict):
            payload = move
        else:
            payload = {"type": "move", "move": move}
            
        try:
            logger.info(f"Отправка хода на {match_url} с payload: {payload}")
            response = await self.client.post(match_url, json=payload, headers=headers)
            
            if response.status_code in (200, 201):
                logger.info(f"Ответ сервера на ход: {response.text}")
                return True
            else:
                logger.warning(f"Сервер отклонил ход! Статус: {response.status_code}, Ответ: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Ошибка сети при отправке хода: {e}")
            return False
        
    async def close(self) -> None:
        await self.client.aclose()