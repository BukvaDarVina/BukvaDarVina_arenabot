# Arena Champion Bot

Автоматический бот для игровой платформы [arena.roomcomm.xyz](https://arena.roomcomm.xyz), использующий гибридную архитектуру: LLM-оркестратор управляет лобби и парсингом состояний, а классические математические движки рассчитывают ходы. Это исключает галлюцинации LLM при игре.

## Архитектура

```
┌─────────────────────────────────────────────────┐
│  main.py  — точка входа, игровой цикл           │
├──────────┬──────────────┬───────────────────────┤
│  core/   │  engines/    │  parsers/             │
│  client  │  chess_engine│  translator           │
│  orchestr│  bulls_cows  │  regex_parser         │
├──────────┴──────────────┴───────────────────────┤
│  memory/ — SQLite для логов и профилей соперников│
└─────────────────────────────────────────────────┘
```

**Поток данных:** `Arena API` → `ArenaClient` → `GameStateTranslator` → `EngineManager` → ход отправляется обратно.

## Игровые движки

| Игра | Движок | Алгоритм |
|------|--------|----------|
| Шахматы | Stockfish | UCI-протокол |
| Быки и коровы | `BullsAndCowsEngine` | Алгоритм Кнута (гарантия победы ≤ 5 ходов) |
| Морской бой | `SeaBattleEngine` | Probability Density Grid |
| Реверси | `ReversiEngine` | Минимакс с альфа-бета отсечением |
| Гомоку | `GomokuEngine` | Минимакс с альфа-бета отсечением |
| Шашки | `CheckersEngine` | Случайный легальный ход |
| Гомино (Dots & Boxes) | `DotsBoxesEngine` | Случайный ход |
| Дурак | `DurakEngine` | Базовая логика атакующего/защитника |
| Камень-ножницы-бумага | `RockPaperScissorsEngine` | Случайный выбор |
| Пакт | `PactEngine` | Случайное сотрудничество/предательство |
| Правило, Танк, Каратель и др. | Базовые движки | Эвристики / случайные ходы |

## Стек технологий

- **Язык:** Python 3.14
- **HTTP-клиент:** httpx (async)
- **Движок шахмат:** Stockfish (UCI)
- **LLM для чата:** Ollama (опционально)
- **Валидация данных:** Pydantic v2
- **БД:** SQLite (local)
- **Тестирование:** pytest, pytest-asyncio, pytest-httpx, pytest-mock
- **Контейнеризация:** Docker

## Структура каталогов

```
.
├── core/
│   ├── client.py          # HTTP-клиент для API арены
│   └── orchestrator.py    # Оркестрация игрового процесса
├── engines/
│   ├── manager.py         # Фасад для всех игровых движков
│   ├── chess_engine.py    # Stockfish через UCI
│   ├── bulls_cows_engine.py
│   ├── sea_battle_engine.py
│   ├── reversi_engine.py
│   └── ...
├── parsers/
│   ├── translator.py      # Роутер текстовых состояний
│   └── regex_parser.py    # Regex-паттерны для 7 типов игр
├── memory/
│   └── db.py              # SQLite: логи матчей, профили соперников
├── tests/
│   ├── conftest.py
│   ├── test_client.py
│   ├── test_engines.py
│   ├── test_parsers.py
│   ├── test_orchestrator.py
│   └── test_memory.py
├── data/                  # SQLite-БД и токен агента
├── main.py                # Точка входа
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Быстрый старт

### Локально

```bash
# 1. Клонировать репозиторий
git clone https://github.com/user/BukvaDarVina_arenabot.git
cd BukvaDarVina_arenabot

# 2. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Запустить
python main.py
```

### Docker

```bash
docker-compose up --build
```

Контейнер автоматически перезапускается (`restart: always`). Данные сохраняются в `./data/`.

## Конфигурация

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `AGENT_TOKEN` | *(пусто)* | Токен API агента. Если не задан, берётся из `data/token.txt` |
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | URL сервиса Ollama для генерации чата |
| `TZ` | `UTC` | Часовой пояс |

## Тестирование

```bash
pip install -r tests/requirements-test.txt
pytest
```

Тесты покрывают: парсеры, клиент (HTTP-мокинг), все игровые движки, базу данных и интеграционный сценарий полного матча.

## Поддерживаемые игры

Бот автоматически определяет тип игры по текстовому состоянию и выбирает соответствующий движок. В настоящее время полностью реализованы **шахматы** (Stockfish) и **быки и коровы** (Кнут). Остальные движки находятся на стадии доработки.
