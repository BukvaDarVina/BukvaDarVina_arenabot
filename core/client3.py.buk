import logging
import httpx
import re
import os
import random
import string
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ArenaClient")

class ArenaClient:
    """Реальный HTTP Клиент для взаимодействия с arena.roomcomm.xyz"""
    
    def __init__(self, base_url: str, agent_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token_file = "data/token.txt"
        
        self.token = agent_token or self._load_token_from_file()
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=15.0)
        
    def _load_token_from_file(self) -> Optional[str]:
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, "r") as f:
                    token = f.read().strip()
                    if token.startswith("ak_"):
                        logger.info("Загружен сохраненный токен агента из локального файла.")
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
        """Читает документацию платформы"""
        for doc in docs:
            try:
                path = doc if doc.startswith("/") else f"/{doc}"
                response = await self.client.get(path)
                if response.status_code == 200:
                    logger.info(f"Документ {path} успешно прочитан.")
            except httpx.RequestError as e:
                logger.error(f"Ошибка сети при запросе документа {doc}: {e}")

    async def register_agent(self, agent_name: str = "ArenaChampionBot") -> bool:
        """Если токен уже задан, пропускаем регистрацию"""
        if self.token and str(self.token).startswith("ak_"):
            logger.info(f"Используется захардкоженный токен: {self.token[:10]}...")
            return True

        base_name = agent_name
        for attempt in range(5):
            current_name = base_name if attempt == 0 else f"{base_name}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=4))}"
            
            payload = {
                "agent": current_name,
                "owner": "LocalDeveloper",
                "runtime": "Python 3.14",
                "model": "LLM Orchestrator + Stockfish"
            }
            
            try:
                logger.info(f"Регистрация агента под именем '{current_name}' на https://arena.roomcomm.xyz/api/keys...")
                response = await self.client.post("/api/keys", json=payload, headers={"Content-Type": "application/json"})
                
                if response.status_code in (200, 201):
                    data = response.json()
                    token = data.get("key") or data.get("token")
                    
                    if token and str(token).startswith("ak_"):
                        self.token = token
                        self._save_token_to_file(token)
                        logger.info(f"Успешная регистрация под именем '{current_name}'! Получен ключ: {token[:10]}...")
                        return True
                elif response.status_code == 409:
                    logger.warning(f"Имя '{current_name}' уже занято (409 Conflict). Пробуем другое...")
                    continue
                else:
                    logger.warning(f"Ошибка регистрации. Статус: {response.status_code} - {response.text}")
                    break
            except Exception as e:
                logger.error(f"Ошибка сети при попытке регистрации агента: {e}")
                break
                
        return False

    async def get_current_seated_table(self) -> Optional[str]:
        """Проверяет через /api/keys/me, не сидит ли бот уже за активным столом"""
        try:
            headers = self._get_auth_headers()
            response = await self.client.get("/api/keys/me", headers=headers)
            if response.status_code == 200:
                data = response.json()
                seated = data.get("seated_at") or data.get("match") or data.get("table_id") or data.get("table")
                if seated:
                    logger.info(f"Обнаружен активный стол из /api/keys/me: {seated}")
                    return seated
        except Exception:
            pass
        return None

    async def get_open_tables(self) -> List[Dict[str, Any]]:
        """Получает список открытых столов ожидания"""
        try:
            headers = self._get_auth_headers()
            response = await self.client.get("/", headers=headers)
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

    async def create_table(self, game_type: str = "chess") -> Optional[str]:
        """Создает новый открытый стол или возвращает существующий активный"""
        try:
            headers = self._get_auth_headers()
            
            # 1. Проверяем, не сидим ли мы уже за столом
            seated = await self.get_current_seated_table()
            if seated:
                return seated

            # 2. Запрашиваем поддерживаемые игры
            games_resp = await self.client.get("/api/games", headers=headers)
            if games_resp.status_code == 200:
                games_data = games_resp.json()
                if isinstance(games_data, list) and games_data:
                    game_type = games_data[0].get("name", game_type).lower()
                elif isinstance(games_data, dict) and "games" in games_data:
                    available = games_data["games"]
                    if available:
                        game_type = available[0].lower() if isinstance(available[0], str) else available[0].get("name", "chess").lower()
            
            payload = {"game": game_type.lower()}
            logger.info(f"Попытка создания стола для игры: '{payload['game']}'...")
            
            response = await self.client.post("/api/tables", json=payload, headers=headers)
            if response.status_code in (200, 201):
                data = response.json()
                # Универсально ищем ID в любых возможных полях ответа
                table_id = (
                    data.get("id") or 
                    data.get("table_id") or 
                    data.get("match") or 
                    data.get("table") or 
                    data.get("match_id")
                )
                logger.info(f"Успешно создан новый стол с ID: {table_id}")
                return table_id
            elif response.status_code == 409:
                # Если ключ уже привязан к матчу, вытаскиваем ID из текста ошибки сервера
                error_text = response.text
                match = re.search(r'match\s+([A-Z0-9]+)', error_text)
                if match:
                    table_id = match.group(1)
                    logger.info(f"Обнаружен существующий активный стол из ошибки 409: {table_id}")
                    return table_id
                logger.warning(f"Конфликт создания стола: {error_text}")
            else:
                logger.warning(f"Не удалось создать стол. Статус: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Ошибка при создании стола: {e}")
        return None

    async def sit_at_table(self, table_id: str) -> bool:
        """Подключается к столу"""
        try:
            url = f"/api/tables/{table_id}/join"
            headers = self._get_auth_headers()
            response = await self.client.post(url, headers=headers)
            if response.status_code in (200, 201):
                logger.info(f"Успешное подключение к столу {table_id}!")
                return True
            else:
                logger.warning(f"Сервер отклонил подключение к столу {table_id}. Статус: {response.status_code}")
                return False
        except httpx.RequestError as e:
            logger.error(f"Ошибка сети при попытке сесть за стол {table_id}: {e}")
            return False
            
    async def get_match_state(self, table_id: str) -> Optional[Dict[str, Any]]:
        try:
            headers = self._get_auth_headers()
            response = await self.client.get(f"/api/tables/{table_id}", headers=headers)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    async def send_move(self, table_id: str, move: str) -> bool:
        try:
            payload = {"move": move}
            headers = self._get_auth_headers()
            response = await self.client.post(f"/api/tables/{table_id}/move", json=payload, headers=headers)
            return response.status_code in (200, 201)
        except Exception:
            return False

    async def leave_table(self, table_id: str) -> bool:
        """Покидает стол, если партия зависла или противник сбежал"""
        try:
            headers = self._get_auth_headers()
            response = await self.client.post(f"/api/matches/{table_id}/leave", headers=headers)
            if response.status_code in (200, 201):
                logger.info(f"Успешно покинули зависший стол {table_id}.")
                return True
            else:
                logger.warning(f"Не удалось покинуть стол {table_id}. Статус: {response.status_code}")
        except Exception as e:
            logger.error(f"Ошибка при выходе из-за стола: {e}")
        return False
        
    async def close(self) -> None:
        await self.client.aclose()