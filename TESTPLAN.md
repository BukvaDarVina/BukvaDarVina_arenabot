# План тестирования (TESTPLAN) - Arena Champion Bot

| Сценарий | Предусловие | Шаг | Ожидаемый статус/тело |
| :--- | :--- | :--- | :--- |
| **Позитив (Парсер)**: Валидный ход шахматы | Текст хода: `"White plays e4"` | Вызов `RegexParser.parse_chess(text)` | `{"player": "White", "move": "e4"}` |
| **Позитив (Парсер)**: Валидный ход шашки с взятием | Текст хода: `"Cow-SRB plays b6–d4, taking 1 (11–12)"` | Вызов `RegexParser.parse_shashki(text)` | `{"player": "Cow-SRB", "move": "b6–d4"}` |
| **Негатив (Парсер)**: Некорректный текст хода | Текст хода: `"Garbage text 123"` | Вызов `GameStateTranslator.parse_move(...)` | `None` (без исключений) |
| **Позитив (Клиент)**: Успешная посадка за стол | Мок POST `/api/tables/123/join` отвечает `200 OK` | Вызов `ArenaClient.sit_at_table("123")` | `True` |
| **Негатив (Клиент)**: Стол занят / не найден | Мок POST `/api/tables/123/join` отвечает `404 Not Found` | Вызов `ArenaClient.sit_at_table("123")` | `False` (или `{"error": "404"}`) |
| **Негатив (Клиент)**: Ошибка лобби | Мок GET `/api/lobby/tables` отвечает `500 Server Error` | Вызов `ArenaClient.get_open_tables()` | `[]` (лог ошибки, `{"error": "500"}`) |
| **Позитив (Движок)**: Быки/Коровы первый ход | Пустая история ходов `history = []` | Вызов `BullsAndCowsEngine.get_next_guess([])` | `"0123"` |
| **Граница (Движок)**: Быки/Коровы остался 1 вариант | В `history` переданы ходы, отсекающие всё, кроме `1` кода | Вызов `BullsAndCowsEngine.get_next_guess(history)` | Строка с оставшимся кодом |
| **Негатив (Движок)**: Быки/Коровы ложная история | В `history` переданы взаимоисключающие подсказки | Вызов `BullsAndCowsEngine.get_next_guess(history)` | `"0000"` (обработка путаницы) |
| **Позитив (Движок)**: Морской бой начало | Пустые `hits` и `misses` в `board_state` | Вызов `SeaBattleEngine.get_best_shot(...)` | `"E5"` (или другая из `possible_center_shots`) |
| **Граница (Движок)**: Морской бой, центры заняты | В `hits` и `misses` переданы `["E5", "E6", "F5", "F6"]` | Вызов `SeaBattleEngine.get_best_shot(...)` | `"A1"` (срабатывание фолбэка) |
| **Негатив (Stockfish)**: Нет бинарника в ОС | `executable_path = "wrong_path"` | Вызов `ChessEngine.initialize()` | `False` (лог `FileNotFoundError`) |
| **Инвариант (Stockfish)**: Вызов до инициализации | `is_initialized = False` | Вызов `EngineManager.get_chess_move(...)` | `None` |
| **Позитив (БД)**: Сохранение матча | БД инициализирована, таблицы созданы | Вызов `LocalMemoryDB.save_match(...)` | Успешная запись (отсутствие Exception) |
| **Негатив (БД)**: Ошибка записи в закрытую БД | Вызван `disconnect()`, соединение `None` | Вызов `LocalMemoryDB.save_match(...)` | Исключение или `{"error": "db_closed"}` |
| **Инвариант (Оркестратор)**: Неизвестная игра | Игра `"Monopoly"`, `table_id = "1"` | Вызов `GameStateTranslator.parse_move(...)` | `None` (игнорируется корректно) |
