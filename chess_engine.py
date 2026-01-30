from __future__ import annotations
import os
import random
import chess
import chess.engine

PIECES = {
    "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
    "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}

def rc_to_square(rc: tuple[int,int]) -> chess.Square:
    r, c = rc
    return chess.square(c, 7 - r)

def square_to_rc(sq: chess.Square) -> tuple[int,int]:
    return (7 - chess.square_rank(sq), chess.square_file(sq))

_LEVELS = {
    "easy":  {"time": 0.05, "depth": 6},
    "medium":{"time": 0.15, "depth": 10},
    "hard":  {"time": 0.35, "depth": 14},
}

class ChessEngine:
    """Chess rules are fully validated by python-chess."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = chess.Board()
        self.history_san: list[str] = []
        self.undo_stack: list[tuple[str, list[str]]] = []  # (fen, history_copy)

    def _board_matrix(self):
        m = [[None for _ in range(8)] for _ in range(8)]
        for sq, piece in self.board.piece_map().items():
            r, c = square_to_rc(sq)
            m[r][c] = piece.symbol()
        return m

    def _status(self) -> str:
        if self.board.is_checkmate():
            return "checkmate"
        if self.board.is_stalemate():
            return "stalemate"
        if self.board.is_insufficient_material():
            return "draw-insufficient"
        if self.board.can_claim_threefold_repetition():
            return "draw-3fold-claimable"
        if self.board.can_claim_fifty_moves():
            return "draw-50move-claimable"
        if self.board.is_check():
            return "check"
        return "playing"

    def _last_move_rc(self):
        if not self.board.move_stack:
            return None
        mv = self.board.move_stack[-1]
        return {"from": list(square_to_rc(mv.from_square)), "to": list(square_to_rc(mv.to_square))}

    def get_state(self, minimal: bool=False):
        s = {
            "turn": "w" if self.board.turn == chess.WHITE else "b",
            "board": self._board_matrix(),
            "legend": PIECES,
            "status": self._status(),
            "lastMove": self._last_move_rc(),
        }
        if not minimal:
            s["fen"] = self.board.fen()
            s["history"] = self.history_san[-240:]
        return s

    def legal_moves_from(self, frm_rc: tuple[int,int]):
        frm = rc_to_square(frm_rc)
        out = []
        for mv in self.board.legal_moves:
            if mv.from_square != frm:
                continue
            tr, tc = square_to_rc(mv.to_square)
            payload = {"to": [tr, tc]}
            if mv.promotion:
                payload["promotion"] = chess.piece_symbol(mv.promotion)
            out.append(payload)
        return out

    def _push_undo(self):
        self.undo_stack.append((self.board.fen(), self.history_san.copy()))
        if len(self.undo_stack) > 300:
            self.undo_stack = self.undo_stack[-300:]

    def apply_move(self, frm_rc: tuple[int,int], to_rc: tuple[int,int], promotion: str|None=None):
        frm = rc_to_square(frm_rc)
        to = rc_to_square(to_rc)

        promo_piece = None
        if promotion:
            promotion = promotion.lower()
            promo_map = {"q": chess.QUEEN, "r": chess.ROOK, "b": chess.BISHOP, "n": chess.KNIGHT}
            promo_piece = promo_map.get(promotion)

        candidate = None
        for mv in self.board.legal_moves:
            if mv.from_square == frm and mv.to_square == to:
                if mv.promotion:
                    if promo_piece is None:
                        candidate = chess.Move(frm, to, promotion=chess.QUEEN)
                        break
                    if mv.promotion == promo_piece:
                        candidate = mv
                        break
                else:
                    candidate = mv
                    break

        if candidate is None or candidate not in self.board.legal_moves:
            return False, "Illegal move"

        self._push_undo()
        san = self.board.san(candidate)
        self.board.push(candidate)
        self.history_san.append(san)
        return True, san

    def undo(self, steps: int = 1):
        if steps < 1:
            return False, "Nothing to undo"
        ok_any = False
        for _ in range(steps):
            if not self.undo_stack:
                break
            fen, hist = self.undo_stack.pop()
            self.board = chess.Board(fen)
            self.history_san = hist
            ok_any = True
        return (ok_any, "Undone" if ok_any else "Nothing to undo")

    def ai_move(self, level: str="medium", kind: str="ai"):
        """kind='ai' => Stockfish. kind='bot' => random legal move."""
        if self._status() not in ("playing","check"):
            return False, "Game is over"

        legal = list(self.board.legal_moves)
        if not legal:
            return False, "No legal moves"

        if kind == "bot":
            mv = random.choice(legal)
            self._push_undo()
            san = self.board.san(mv)
            self.board.push(mv)
            self.history_san.append(f"BOT: {san}")
            return True, f"Bot played {san}"

        lvl = _LEVELS.get(level, _LEVELS["medium"])
        engine_path = os.environ.get("STOCKFISH_PATH") or "stockfish"
        try:
            with chess.engine.SimpleEngine.popen_uci(engine_path) as eng:
                limit = chess.engine.Limit(time=lvl["time"], depth=lvl["depth"])
                result = eng.play(self.board, limit)
                mv = result.move
        except FileNotFoundError:
            return False, "Stockfish not found. Install: brew install stockfish (or set STOCKFISH_PATH)"
        except Exception as e:
            return False, f"Engine error: {type(e).__name__}"

        if mv is None or mv not in self.board.legal_moves:
            return False, "Engine returned illegal move"

        self._push_undo()
        san = self.board.san(mv)
        self.board.push(mv)
        self.history_san.append(f"AI: {san}")
        return True, f"AI played {san}"
