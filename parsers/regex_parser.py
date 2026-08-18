import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("RegexParser")

class RegexParser:
    """
    Модуль парсинга на основе регулярных выражений.
    Безошибочно перехватывает текстовые ходы из трансляций Арены и переводит их в машинный формат[cite: 66, 87].
    """
    
    def __init__(self):
        # Шахматы. Пример: "White plays e4" или "Black plays Nf3" [cite: 66, 258]
        self.chess_pattern = re.compile(r"(?P<player>White|Black) plays (?P<move>[a-zA-Z0-9\-+]+)\.?")
        
        # Реверси. Пример: "FalsiFiable plays C2, flipping 1 (6–6)" [cite: 66, 273]
        self.reversi_pattern = re.compile(r"(?P<player>.+?) plays (?P<move>[A-H][1-8]), flipping \d+ \(\d+–\d+\)\.?")
        
        # Гомоку (Пять в ряд). Пример: "VBel plays H8" [cite: 251]
        self.gomoku_pattern = re.compile(r"(?P<player>.+?) plays (?P<move>[A-Z]\d+)\.?")
        
        # Быки и коровы. Пример: "KSN_CSM guesses 1234 → 0 bulls, 2 cows" [cite: 259]
        self.bulls_cows_pattern = re.compile(r"(?P<player>.+?) guesses (?P<guess>\d{4}) → (?P<bulls>\d+) bulls, (?P<cows>\d+) cows\.?")
        
        # Морской бой. Пример: "opencode-agent shoots D4 — misses" или "ALESHA_DVB shoots G8 — sinks a ship" [cite: 278, 295]
        self.sea_battle_pattern = re.compile(r"(?P<player>.+?) shoots (?P<move>[A-J](?:10|[1-9])) — (?P<result>misses|hits|sinks a ship)\.?")
        
        # Шашки. Пример: "Cow-SRB plays b8–a7 (12–12)" или "Cow-SRB plays b6–d4, taking 1 (11–12)" [cite: 21, 264]
        self.shashki_pattern = re.compile(r"(?P<player>.+?) plays (?P<move>[a-h][1-8]–[a-h][1-8])(?:, taking \d+)? \(\d+–\d+\)\.?")
        
        # Точки-тире. Пример: "MatrixZ from SRB draws h0,0" [cite: 253]
        self.dots_boxes_pattern = re.compile(r"(?P<player>.+?) draws (?P<move>[hv]\d+,\d+)\.?")

    def parse_chess(self, text: str) -> Optional[Dict[str, str]]:
        match = self.chess_pattern.search(text)
        return match.groupdict() if match else None

    def parse_reversi(self, text: str) -> Optional[Dict[str, str]]:
        match = self.reversi_pattern.search(text)
        return match.groupdict() if match else None

    def parse_gomoku(self, text: str) -> Optional[Dict[str, str]]:
        match = self.gomoku_pattern.search(text)
        return match.groupdict() if match else None

    def parse_bulls_cows(self, text: str) -> Optional[Dict[str, Any]]:
        match = self.bulls_cows_pattern.search(text)
        if match:
            data = match.groupdict()
            return {
                "player": data["player"],
                "guess": data["guess"],
                "bulls": int(data["bulls"]),
                "cows": int(data["cows"])
            }
        return None

    def parse_sea_battle(self, text: str) -> Optional[Dict[str, str]]:
        match = self.sea_battle_pattern.search(text)
        return match.groupdict() if match else None
        
    def parse_shashki(self, text: str) -> Optional[Dict[str, str]]:
        match = self.shashki_pattern.search(text)
        return match.groupdict() if match else None

    def parse_dots_boxes(self, text: str) -> Optional[Dict[str, str]]:
        match = self.dots_boxes_pattern.search(text)
        return match.groupdict() if match else None