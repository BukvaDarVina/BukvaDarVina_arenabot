import asyncio
import logging
import sys

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
    client = ArenaClient(base_url=BASE_URL)
    orchestrator = LLMOrchestrator(client=client, db=db, engines=engines, translator=translator)

    # 2. Разведка: чтение документации платформы
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
                opponent = table.get("opponent_name", "Unknown")
                is_rated = table.get("is_rated", True)
                table_id = table.get("id")
                
                logger.info(f"Найден стол {table_id}: противник [{opponent}], рейтинговый: {is_rated}")
                
                # Ищем подходящий стол (например, с Robik или любой свободный)
                if table_id:
                    target_table_id = table_id
                    break
                    
            if target_table_id:
                logger.info(f"Попытка занять стол {target_table_id}...")
                joined = await client.sit_at_table(target_table_id)
                
                if joined:
                    logger.info("Успешная посадка за стол! Передача управления оркестратору матча.")
                    await orchestrator.play_match(target_table_id)
                else:
                    logger.warning("Не удалось сесть за стол (возможно, его занял другой агент).")
            else:
                logger.info("Свободных столов нет. Повторный поиск через 10 секунд...")
                
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