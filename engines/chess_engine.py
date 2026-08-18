import subprocess
import logging
from typing import Optional

logger = logging.getLogger("ChessEngine")

class ChessEngine:
    """
    Обертка для консольного движка Stockfish.
    Общается с процессом через стандартный ввод/вывод по протоколу UCI.
    """
    def __init__(self, executable_path: str = "stockfish"):
        self.executable_path = executable_path
        self.process = None

    def initialize(self) -> bool:
        try:
            self.process = subprocess.Popen(
                [self.executable_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            self._send_command("uci")
            # Ждем ответа 'uciok'
            while True:
                line = self.process.stdout.readline().strip()
                if line == "uciok":
                    break
            self._send_command("isready")
            while True:
                line = self.process.stdout.readline().strip()
                if line == "readyok":
                    break
            return True
        except FileNotFoundError:
            logger.error(f"Исполняемый файл '{self.executable_path}' не найден.")
            return False
        except Exception as e:
            logger.error(f"Ошибка при запуске Stockfish: {e}")
            return False

    def _send_command(self, command: str):
        if self.process and self.process.stdin:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()

    def get_best_move(self, fen: str, depth: int = 15) -> Optional[str]:
        logger.info(f"Запрос хода Stockfish для FEN: {fen} на глубину {depth}")
        self._send_command(f"position fen {fen}")
        self._send_command(f"go depth {depth}")
        
        while True:
            line = self.process.stdout.readline().strip()
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
        return None

    def shutdown(self):
        if self.process:
            self._send_command("quit")
            self.process.terminate()