import logging
import sqlite3
import json
import asyncio
from typing import Dict, Any, List

logger = logging.getLogger("LocalMemoryDB")

class LocalMemoryDB:
    """
    Слой памяти бота (Обучение / Opponent Profiling).
    Отвечает за работу с локальной БД (сохранение ходов, id оппонентов).
    Используется для хранения логов завершенных матчей и адаптации вероятностей под конкретных противников.
    """
    
    def __init__(self, db_path: str = "data/arena_memory.db"):
        # Обновленный путь по умолчанию для работы с Docker Volume
        # Для простоты запуска без внешних зависимостей, используем встроенный SQLite.
        self.db_path = db_path
        self.conn = None
        
    async def connect(self) -> None:
        """Устанавливает соединение с БД и создает таблицы, если их нет."""
        logger.info(f"Подключение к локальной базе данных: {self.db_path}")
        
        # Для неблокирующей работы с синхронным драйвером sqlite3 в async-окружении
        # оборачиваем инициализацию в отдельный поток. 
        # (В production-версии можно будет заменить на aiosqlite).
        await asyncio.to_thread(self._init_db)
        logger.info("База данных успешно инициализирована.")
        
    def _init_db(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self.conn.cursor()
        
        # Таблица для Opponent Profiling
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opponent_id TEXT NOT NULL,
                game_type TEXT NOT NULL,
                result TEXT,
                moves_log TEXT
            )
        ''')
        
        # Таблица для механизма рефлексии и динамического обновления промптов (RAG)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_type TEXT,
                error_type TEXT,
                correction_rule TEXT
            )
        ''')
        self.conn.commit()

    async def disconnect(self) -> None:
        """Закрывает сетевые/файловые соединения с БД."""
        if self.conn:
            logger.info("Закрытие соединения с базой данных...")
            self.conn.close()
            self.conn = None

    async def save_match(self, opponent_id: str, game_type: str, result: str, moves_log: List[Dict[str, Any]]) -> None:
        """
        Сохраняет историю завершенного матча для Opponent Profiling.
        """
        logger.info(f"Сохранение результатов матча против {opponent_id} ({game_type})...")
        
        def _save():
            if not self.conn:
                raise sqlite3.ProgrammingError("Cannot operate on a closed database.")
                
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT INTO matches (opponent_id, game_type, result, moves_log) VALUES (?, ?, ?, ?)',
                (opponent_id, game_type, result, json.dumps(moves_log))
            )
            self.conn.commit()
            
        await asyncio.to_thread(_save)

    async def get_opponent_profile(self, opponent_id: str, game_type: str) -> List[Dict[str, Any]]:
        """
        Извлекает историю игр против конкретного оппонента.
        """
        logger.info(f"Запрос профиля оппонента {opponent_id} для игры {game_type}...")
        
        def _get():
            if not self.conn:
                raise sqlite3.ProgrammingError("Cannot operate on a closed database.")
                
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT result, moves_log FROM matches WHERE opponent_id = ? AND game_type = ?',
                (opponent_id, game_type)
            )
            rows = cursor.fetchall()
            
            profile = []
            for row in rows:
                result, moves_json = row
                profile.append({
                    "result": result,
                    "moves": json.loads(moves_json)
                })
            return profile
            
        return await asyncio.to_thread(_get)
        
    async def save_reflection_rule(self, game_type: str, error_type: str, rule: str) -> None:
        """
        Сохраняет правило рефлексии после ошибки парсинга для LLM-Оркестратора.
        """
        logger.info(f"Сохранение нового правила парсинга (RAG) для {game_type}: {rule}")
        
        def _save():
            if not self.conn:
                raise sqlite3.ProgrammingError("Cannot operate on a closed database.")
                
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT INTO reflections (game_type, error_type, correction_rule) VALUES (?, ?, ?)',
                (game_type, error_type, rule)
            )
            self.conn.commit()
            
        await asyncio.to_thread(_save)