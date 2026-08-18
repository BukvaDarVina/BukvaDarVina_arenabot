import subprocess
import logging
import shutil
from typing import Optional

logger = logging.getLogger("ChessEngine")

class ChessEngine:
    """
    Обертка для консольного движка Stockfish.
    Общается с процессом через стандартный ввод/вывод по протоколу UCI.
    """
    def __init__(self, executable_path: Optional[str] = None):
        # Используем shutil.which для поиска stockfish в системе или проверяем стандартные пути
        self.executable_path = executable_path or shutil.which("stockfish") or self._find_stockfish()
        self.process: Optional[subprocess.Popen] = None

    def _find_stockfish(self) -> str:
        """Безопасный поиск бинарника Stockfish в системе"""
        possible_paths = [
            "/usr/games/stockfish",
            "/usr/bin/stockfish",
            "/usr/local/bin/stockfish",
            "stockfish"
        ]
        for path in possible_paths:
            if shutil.which(path):
                return path
        return "stockfish"

    def initialize(self) -> bool:
        try:
            logger.info(f"Инициализация Stockfish по пути: {self.executable_path}")
            self.process = subprocess.Popen(
                [self.executable_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Отправляем команду uci для проверки связи
            self._send_command("uci")
            
            # Читаем вывод с таймаутом / защитой от бесконечного цикла
            initialized = False
            lines_read = 0
            while lines_read < 50:  # Защита от зависания
                if not self.process.stdout:
                    break
                line = self.process.stdout.readline().strip()
                if not line:
                    continue
                if line == "uciok":
                    initialized = True
                    break
                lines_read += 1
                
            if not initialized:
                logger.warning("Stockfish запущен, но не ответил 'uciok вовремя. Пробуем продолжить.")
                
            self._send_command("isready")
            logger.info("Stockfish успешно инициализирован.")
            return True
            
        except FileNotFoundError:
            logger.error(f"Исполняемый файл Stockfish '{self.executable_path}' не найден в системе.")
            return False
        except Exception as e:
            logger.error(f"Ошибка при инициализации Stockfish: {e}")
            return False

    def _send_command(self, command: str):
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()
            except Exception as e:
                logger.error(f"Ошибка отправки команды в Stockfish: {e}")

    def get_best_move(self, fen: str, depth: int = 10) -> Optional[str]:
        if not self.process or self.process.poll() is not None:
            logger.error("Stockfish процесс не запущен или завершен.")
            return None
            
        logger.info(f"Запрос хода Stockfish для FEN: {fen} на глубину {depth}")
        try:
            self._send_command(f"position fen {fen}")
            self._send_command(f"go depth {depth}")
            
            # Ищем строку с лучший ходом
            while True:
                if not self.process.stdout:
                    break
                line = self.process.stdout.readline().strip()
                if not line:
                    continue
                if line.startswith("bestmove"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]
        except Exception as e:
            logger.error(f"Ошибка при получении хода от Stockfish: {e}")
            
        return None

    def shutdown(self):
        if self.process:
            try:
                self._send_command("quit")
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                if self.process:
                    self.process.kill()
            finally:
                self.process = None
            logger.info("Процесс Stockfish остановлен.")