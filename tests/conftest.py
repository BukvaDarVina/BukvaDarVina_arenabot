# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from core.client import ArenaClient
from core.orchestrator import LLMOrchestrator
from parsers.translator import GameStateTranslator

@pytest.fixture
def mock_client():
    client = ArenaClient(base_url="https://fake-arena.test", agent_token="ak_fake_token")
    client.client = AsyncMock()
    # Задаем дефолтное поведение для методов
    client.get_current_seated_table = AsyncMock(return_value=None)
    client.get_open_tables = AsyncMock(return_value=[])
    client.create_table = AsyncMock(return_value="FAKE_TABLE_1")
    client.sit_at_table = AsyncMock(return_value=True)
    client.send_move = AsyncMock(return_value=True)
    client.leave_table = AsyncMock(return_value=True)
    client.get_match_state = AsyncMock()
    return client

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.save_match = AsyncMock()
    return db

@pytest.fixture
def mock_engines():
    engines = MagicMock()
    engines.get_chess_move.return_value = "e2e4"
    return engines

@pytest.fixture
def translator():
    return GameStateTranslator()