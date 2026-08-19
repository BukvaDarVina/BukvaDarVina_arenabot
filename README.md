--- a/original.md
+++ b/original.md
@@ -1,12 +1,12 @@
-🏆 Arena Champion Bot
+🏆 Arena Champion Bot

## 🎯 Цели проекта
-Создание сильнейшего бота для игровой платформы https://arena.roomcomm.xyz[cite: 2]. Бот использует гибридную архитектуру «Франкенштейн»: языковая модель (LLM) выступает в роли оркестратора для общения с лобби и парсинга, а для принятия решений по ходам используются классические математические движки[cite: 8, 59]. Это исключает галлюцинации LLM в долгих партиях[cite: 7]. Конечная цель — побеждать лидеров турнирной таблицы в рейтинговых играх, таких как `hermes-agent`, `SSE-SRB` и `MatrixZ from SRB`[cite: 27].
+Create a strong bot for the game platform https://arena.roomcomm.xyz. The bot uses a hybrid architecture called "Frankenstein": a language model (LLM) serves as an orchestrator for communication with the lobby and parsing, while classical mathematical engines are used to make decisions about moves. This eliminates hallucinations in long games.

-The ultimate goal is to defeat leaders on the tournament table in rating games such as `hermes-agent`, `SSE-SRB` and `MatrixZ from SRB`.
+

## 🛠 Стек технологий
-**Язык:** Python 3.14.6
-**Протоколы связи:** HTTP-запросы и MCP (Model Context Protocol)[cite: 11].
-**Мышцы (Игровые движки):**
-  - **Шахматы:** Консольный движок Stockfish через протокол UCI[cite: 14].
-  - **Быки и коровы:** Алгоритм Кнута (математическая гарантия победы максимум за 5 ходов)[cite: 17].
-  - **Морской бой:** Карта плотности вероятности (Probability Density Grid)[cite: 18].
-  - **Реверси и Гомоку:** Минимакс с альфа-бета отсечением[cite: 16].
-**Память (Обучение / Opponent Profiling):** Локальная БД (PostgreSQL или SQLite) для хранения логов завершенных матчей и даптации вероятностей под конкретных противников[cite: 43].
+**Language:** Python 3.14.6
+**Protocols:** HTTP requests and MCP (Model Context Protocol)
+**Engines:**
+	+ Chess: Stockfish console engine through UCI protocol
+	+ Goats and Cows: Knuth's algorithm (mathematical guarantee of victory within 5 moves)
+	+ Battleship: Probability Density Grid
+	+ Reversi and Gomoku: Minimax with alpha-beta pruning

## 📂 Структура каталогов

