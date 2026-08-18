# tests/test_client.py
import pytest
from core.client import ArenaClient
import httpx

@pytest.mark.asyncio
async def test_get_open_tables_parsing(httpx_mock):
    # Подгоняем фейковый HTML-ответ платформы
    fake_html = """
    <html>
      <body>
        <div>Open tables — sit down, an agent is waiting</div>
        <a href="/m/FAKEID01">Join match 1</a>
        <a href="/table/FAKEID02">Join match 2</a>
        <div>Playing now</div>
        <a href="/m/BUSYID03">Busy match</a>
      </body>
    </html>
    """
    httpx_mock.add_response(url="https://test.arena/", text=fake_html)
    
    client = ArenaClient(base_url="https://test.arena/", agent_token="ak_test")
    tables = await client.get_open_tables()
    
    assert len(tables) == 2
    ids = [t["id"] for t in tables]
    assert "FAKEID01" in ids
    assert "FAKEID02" in ids
    assert "BUSYID03" not in ids # Убеждаемся, что парсер не берет занятые столы