# Используем легковесный образ Python (версия 3.14, как в спецификации проекта)
FROM python:3.14-slim-bullseye

# Отключаем создание .pyc файлов и буферизацию вывода (полезно для логов)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем системные зависимости: Stockfish и утилиты
RUN apt-get update && apt-get install -y \
    stockfish \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл зависимостей и устанавливаем Python-пакеты
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь исходный код проекта в контейнер
COPY . .

# Указываем команду для запуска бота
CMD ["python", "main.py"]