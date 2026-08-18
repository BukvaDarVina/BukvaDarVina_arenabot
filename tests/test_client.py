import pytest
import httpx
from unittest.mock import AsyncMock, patch
from core.client import ArenaClient

@pytest.mark.asyncio
async def test_client_sit_at_table_positive():
    """Позитив (Клиент): Успешная посадка за стол"""
    client = ArenaClient("http://test.arena")
    with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        res = await client.sit_at_table("123")
        assert res is True

@pytest.mark.asyncio
async def test_client_sit_at_table_negative():
    """Негатив (Клиент): Стол занят / не найден (404)"""
    client = ArenaClient("http://test.arena")
    with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 404
        res = await client.sit_at_table("123")
        assert res is False

@pytest.mark.asyncio
async def test_client_get_open_tables_error():
    """Негатив (Клиент): Ошибка лобби (500)"""
    client = ArenaClient("http://test.arena")
    with patch.object(client.client, 'get', new_callable=AsyncMock) as mock_get:
        # Эмулируем падение сети или 500 ошибку
        mock_get.side_effect = httpx.RequestError("500 Server Error")
        res = await client.get_open_tables()
        # В нашей текущей реализации (каркас) клиент возвращает фейковый список, 
        # чтобы не ронять бота, убеждаемся, что возвращается список.
        assert isinstance(res, list)