import asyncio
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Frank_by_DVB")

from core.client import ArenaClient
from core.orchestrator import LLMOrchestrator
from memory.db import LocalMemoryDB
from parsers.translator import GameStateTranslator
from engines.manager import EngineManager

BASE_URL = "https://arena.roomcomm.xyz"
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "")

async def main():
    logger.info("Запуск Arena Champion Bot (Финальная Архитектура)...")
    
    db = LocalMemoryDB()
    await db.connect()

    engines = EngineManager()
    if not engines.initialize():
        logger.error("Критическая ошибка: Не удалось инициализировать игровые движки.")
        return

    translator = GameStateTranslator()
    client = ArenaClient(base_url=BASE_URL, agent_token=AGENT_TOKEN)
    
    await client.register_agent("Frank_by_DVB")
    
    orchestrator = LLMOrchestrator(client=client, db=db, engines=engines, translator=translator)

    try:
        while True:
            # 1. Проверяем, не сидим ли мы УЖЕ за столом (вытаскиваем зависшие сессии)
            active_table = await client.get_current_seated_table()
            if active_table:
                logger.info(f"Возврат в активный матч на столе {active_table}...")
                await orchestrator.play_match(active_table)
                await asyncio.sleep(5)
                continue

            logger.info("Поиск открытых столов...")
            open_tables = await client.get_open_tables()
            target_table_id = None
            
            for table in open_tables:
                if table.get("id"):
                    target_table_id = table.get("id")
                    break
                    
            if not target_table_id:
                logger.info("Свободных столов нет. Создаем собственный...")
                target_table_id = await client.create_table("")
                
            if target_table_id:
                # 2. Проверяем, не посадил ли нас сервер автоматически при создании стола
                current_seat = await client.get_current_seated_table()
                if current_seat == target_table_id:
                    logger.info(f"Мы уже посажены за созданный стол {target_table_id}.")
                    await orchestrator.play_match(target_table_id)
                else:
                    logger.info(f"Попытка сесть за стол ID: {target_table_id}...")
                    joined = await client.sit_at_table(target_table_id)
                    if joined:
                        logger.info("Успешная посадка! Запуск матча.")
                        await orchestrator.play_match(target_table_id)
                    else:
                        logger.warning("Не удалось сесть за стол.")
            
            await asyncio.sleep(10)
                
    except asyncio.CancelledError:
        logger.info("Игровой процесс прерван.")
    finally:
        engines.shutdown()
        await db.disconnect()
        await client.close()
        logger.info("Бот остановлен.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nОстановка...")