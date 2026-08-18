import pytest
import sqlite3
from memory.db import LocalMemoryDB

@pytest.mark.asyncio
async def test_db_positive_save():
    """Позитив (БД): Сохранение матча и профиля оппонента"""
    # Используем БД в оперативной памяти, чтобы не засорять диск при тестах
    db = LocalMemoryDB(db_path=":memory:")
    await db.connect()
    
    try:
        await db.save_match("test_robik", "Chess", "win", [{"move": "e4"}])
        profile = await db.get_opponent_profile("test_robik", "Chess")
        assert len(profile) == 1
        assert profile[0]["result"] == "win"
        assert profile[0]["moves"] == [{"move": "e4"}]
    finally:
        await db.disconnect()

@pytest.mark.asyncio
async def test_db_negative_closed():
    """Негатив (БД): Ошибка записи в закрытую БД"""
    db = LocalMemoryDB(db_path=":memory:")
    await db.connect()
    await db.disconnect()  # Явно закрываем соединение
    
    # Пытаемся записать в закрытую БД — ожидаем выброса исключения (sqlite3.ProgrammingError)
    with pytest.raises(sqlite3.Error):
        await db.save_match("test_robik", "Chess", "win", [{"move": "e4"}])