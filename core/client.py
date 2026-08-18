import logging
import httpx
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ArenaClient")

class ArenaClient:
    """Реальный HTTP/MCP Клиент для взаимодействия с платформой arena.roomcomm.xyz"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        # Асинхронный клиент с таймаутом
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=15.0)
        
    async def fetch_documents(self, docs: List[str]) -> None:
        """Читает документацию платформы (/start.md, /agents.md, llms.txt)"""
        for doc in docs:
            try:
                # Убедимся, что путь начинается с косой черты
                path = doc if doc.startswith("/") else f"/{doc}"
                response = await self.client.get(path)
                if response.status_code == 200:
                    logger.info(f"Документ {path} успешно прочитан (длина: {len(response.text)} байт).")
                else:
                    logger.warning(f"Не удалось прочитать {path}. Статус: {response.status_code}")
            except httpx.RequestError as e:
                logger.error(f"Ошибка сети при запросе документа {doc}: {e}")

    async def get_open_tables(self) -> List[Dict[str, Any]]:
        """Получает актуальный список открытых столов с главной страницы Арены (HTML парсинг)"""
        try:
            response = await self.client.get("/")
            if response.status_code == 200:
                html_content = response.text
                tables = []
                
                # Пробуем сначала на случай, если это все-таки JSON API
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        return data.get("tables", data.get("open_tables", []))
                except Exception:
                    pass
                    
                # Если это HTML, ищем ссылки на матчи или столы с помощью Regex
                # Например, ссылки вида /m/XXXXX или столы из секции "Open tables"
                # Шаг 1: Ищем все упоминания столов или ID матчей на странице
                match_links = re.findall(r'href=["\'](?:/m/|/api/tables/)([\w\-_]+)["\']', html_content)
                
                # Также поищем имена противников или названия игр рядом со ссылками
                for table_id in set(match_links):
                    tables.append({
                        "id": table_id,
                        "opponent_name": "Robik", # По умолчанию считаем противником бота станции
                        "is_rated": False
                    })
                    
                # Если регулярное выражение ничего не нашло в HTML, вернем тестовый дефолтный стол для отладки
                if not tables and "Open tables" in html_content:
                    logger.info("Обнаружена секция открытых столов в HTML, но ID не извлечены. Проверьте разметку.")
                    
                return tables
            else:
                logger.warning(f"Не удалось получить список столов. Статус: {response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Ошибка сети при запросе лобби: {e}")
        
        return []
        
    async def sit_at_table(self, table_id: str) -> bool:
        """Отправляет команду на посадку за конкретный игровой стол"""
        try:
            url = f"/api/tables/{table_id}/join"
            logger.info(f"Отправка POST-запроса на подключение к столу: {url}")
            response = await self.client.post(url)
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
        """Получает текущее состояние/логи конкретного матча или стола"""
        try:
            response = await self.client.get(f"/api/tables/{table_id}")
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Ошибка сети при получении состояния стола {table_id}: {e}")
        return None

    async def send_move(self, table_id: str, move: str) -> bool:
        """Отправляет сделанный ботом ход на Арену"""
        try:
            payload = {"move": move}
            response = await self.client.post(f"/api/tables/{table_id}/move", json=payload)
            return response.status_code in (200, 201)
        except httpx.RequestError as e:
            logger.error(f"Ошибка при отправке хода '{move}' на стол {table_id}: {e}")
            return False
        
    async def close(self) -> None:
        """Закрывает сетевые соединения клиента"""
        await self.client.aclose()
        logger.info("Соединения ArenaClient закрыты.")