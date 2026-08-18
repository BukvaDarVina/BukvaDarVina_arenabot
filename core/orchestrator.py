import asyncio
import logging
from typing import Any
import ollama # Добавлен импорт Ollama

logger = logging.getLogger("LLMOrchestrator")

class LLMOrchestrator:
    """
    Мозг системы (Голова Франкенштейна). 
    Связывает клиент, память, транслятор состояний и математические движки.
    Использует локальную модель через Ollama.
    """
    
    def __init__(self, client: Any, db: Any, engines: Any, translator: Any, model_name: str = "llama3"):
        self.client = client
        self.db = db
        self.engines = engines
        self.translator = translator
        self.model_name = model_name # Имя локальной модели
        logger.info(f"LLM-Оркестратор инициализирован с локальной моделью: {self.model_name}")

    async def _ask_ollama(self, prompt: str) -> str:
        """Асинхронный вызов локальной модели Ollama"""
        try:
            # Вызов локального API Ollama (по умолчанию http://localhost:11434)
            response = await asyncio.to_thread(
                ollama.chat, 
                model=self.model_name, 
                messages=[{'role': 'user', 'content': prompt}]
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Ошибка при обращении к Ollama: {e}")
            return "ERROR"
            
    async def play_match(self, table_id: str) -> None:
        """
        Основной игровой цикл:
        1. Получить состояние Арены.
        2. Распарсить текстовый ход через транслятор (Regex/LLM).
        3. Передать ход в нужный движок (Stockfish, Кнут, Минимакс).
        4. Отправить ответный ход на Арену.
        """
        logger.info(f"Начало партии за столом {table_id}. Переход в цикл ожидания...")
        
        try:
            # TODO: Реализовать подписку на Server-Sent Events (SSE) или WebSockets платформы
            while True:
                # Пример того, как Оркестратор может использовать Ollama, если Regex не справился
                # Например, если translator.parse_move вернул None:
                # llm_response = await self._ask_ollama(f"Extract move from this text: {unparsed_text}")
                
                # Временная заглушка, чтобы цикл не был бесконечным при запуске каркаса
                await asyncio.sleep(1)
                logger.info("Ожидание хода оппонента...")
                break 
        except asyncio.CancelledError:
            logger.info("Игровой цикл прерван.")
        finally:
            logger.info(f"Завершение работы с игровым столом {table_id}.")