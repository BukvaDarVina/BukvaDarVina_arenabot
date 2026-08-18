# tests/test_orchestrator.py
import pytest
from core.orchestrator import LLMOrchestrator
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_orchestrator_full_match_cycle(mock_client, mock_db, mock_engines, translator):
    # Настраиваем фейковые состояния матча
    # 1 такт: Мы ходим первыми (нет ходов, is_my_turn=True)
    # 2 такт: Ожидание хода противника (is_my_turn=False)
    # 3 такт: Противник походил, наша очередь (появился ход)
    # 4 такт: Матч завершен
    
    states = [
        {"game_type": "chess", "moves": [], "is_my_turn": True, "is_finished": False},
        {"game_type": "chess", "moves": ["e2e4"], "is_my_turn": False, "is_finished": False},
        {"game_type": "chess", "moves": ["e2e4", "e7e5"], "is_my_turn": True, "is_finished": False},
        {"game_type": "chess", "moves": ["e2e4", "e7e5", "g1f3"], "is_my_turn": False, "is_finished": True, "winner": "ArenaChampionBot"}
    ]
    
    # side_effect позволяет возвращать разные значения при каждом вызове
    mock_client.get_match_state.side_effect = states
    
    orchestrator = LLMOrchestrator(client=mock_client, db=mock_db, engines=mock_engines, translator=translator)
    
    # Запускаем матч. Он должен завершиться сам, когда дойдет до 4-го состояния.
    await orchestrator.play_match("TEST_TABLE_ID")
    
    # Проверяем, что бот сделал 2 хода (на 1-м и 3-м такте)
    assert mock_client.send_move.call_count == 2
    
    # Проверяем, что движок вызывался 2 раза
    assert mock_engines.get_chess_move.call_count == 2
    
    # Проверяем, что результаты матча сохранены в БД
    mock_db.save_match.assert_called_once()
    
    # Проверяем, что мы покинули стол в конце
    mock_client.leave_table.assert_called_once_with("TEST_TABLE_ID")