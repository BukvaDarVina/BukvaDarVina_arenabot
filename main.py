import asyncio
import logging
import sys
import os

AGENT_TOKEN = os.getenv("AGENT_TOKEN", "default_arena_token")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ArenaChampionBot")

# Прямые импорты модулей бота
from core.client import ArenaClient
from core.orchestrator import LLMOrchestrator
from memory.db import LocalMemoryDB
from parsers.translator import GameStateTranslator
from engines.manager import EngineManager

BASE_URL = "https://arena.roomcomm.xyz"

async def main():
    logger.info("Запуск Arena Champion Bot (Архитектура «Франкенштейн»)...")
    logger.info(f"Целевая платформа: {BASE_URL}")
    
    # 1. Инициализация слоев
    logger.info("Инициализация слоя памяти (SQLite)...")
    db = LocalMemoryDB()
    await db.connect()

    logger.info("Инициализация мышц (Stockfish, Алгоритм Кнута, Probability Grid, Минимакс)...")
    engines = EngineManager()
    if not engines.initialize():
        logger.error("Критическая ошибка: Не удалось инициализировать игровые движки (проверьте Stockfish).")
        return

    logger.info("Инициализация нервной системы (Транслятор состояний и Regex-парсеры)...")
    translator = GameStateTranslator()

    logger.info("Инициализация API клиента и головы (LLM-Оркестратор)...")
    client = ArenaClient(base_url=BASE_URL, agent_token=AGENT_TOKEN)
    await client.register_agent("ArenaChampionBot")
    
    orchestrator = LLMOrchestrator(client=client, db=db, engines=engines, translator=translator)

    # Выполнение разведки
    logger.info("Выполнение разведки: чтение точек входа платформы...")
    docs_to_read = ['/start.md', '/agents.md', '/llms.txt']
    await client.fetch_documents(docs_to_read)

    # 3. Боевой цикл: непрерывный поиск столов и участие в матчах
    try:
        while True:
            logger.info("Запрос состояния лобби и поиск открытых столов...")
            open_tables = await client.get_open_tables()
            
            target_table_id = None
            for table in open_tables:
                table_id = table.get("id")
                if table_id:
                    target_table_id = table_id
                    break
                    
            if not target_table_id:
                logger.info("Свободных столов для подключения нет. Создаем собственный стол...")
                target_table_id = await client.create_table("Chess")
                
            if target_table_id:
                logger.info(f"Работа со столом ID: {target_table_id}...")
                joined = await client.sit_at_table(target_table_id)
                
                if joined:
                    logger.info("Успешное подключение! Запуск игрового цикла.")
                    await orchestrator.play_match(target_table_id)
                else:
                    logger.warning("Не удалось сесть за стол. Пауза 10 секунд...")
            
            await asyncio.sleep(10)
                
    except asyncio.CancelledError:
        logger.info("Игровой процесс прерван.")
    finally:
        # Корректное завершение работы всех систем
        engines.shutdown()
        await db.disconnect()
        await client.close()
        logger.info("Бот успешно остановлен.")

if __name__ == "__main__":
    if sys.version_info < (3, 10):
        logger.error("Требуется Python 3.10 или выше.")
        sys.exit(1)
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nОстановка бота по запросу пользователя (Ctrl+C)...")