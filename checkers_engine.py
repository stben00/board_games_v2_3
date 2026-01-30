from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Tuple
import random
import copy

def opponent(color: str) -> str:
    return "b" if color == "w" else "w"

def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < 8 and 0 <= c < 8

def is_dark(r: int, c: int) -> bool:
    return (r + c) % 2 == 1

def piece_color(p: str) -> str:
    return "w" if p in ("w","W") else "b"

def is_king(p: str) -> bool:
    return p in ("W","B")

DIAGS = [(-1,-1), (-1,1), (1,-1), (1,1)]

@dataclass
class CheckersState:
    board: List[List[Optional[str]]]
    turn: str
    forced: Optional[Tuple[int,int]] = None
    history: List[str] = None
    status: str = "playing"
    lastMove: Optional[dict] = None

class CheckersEngine:
    def __init__(self):
        self.reset()

    def reset(self):
        self.state = CheckersState(
            board=self._initial_board(),
            turn="w",
            forced=None,
            history=[],
            status="playing",
            lastMove=None,
        )
        self.undo_stack: List[CheckersState] = []

    def _initial_board(self):
        b = [[None for _ in range(8)] for _ in range(8)]
        for r in range(3):
            for c in range(8):
                if is_dark(r,c):
                    b[r][c] = "b"
        for r in range(5,8):
            for c in range(8):
                if is_dark(r,c):
                    b[r][c] = "w"
        return b

    def _snapshot(self):
        return copy.deepcopy(self.state)

    def _push_undo(self):
        self.undo_stack.append(self._snapshot())
        if len(self.undo_stack) > 300:
            self.undo_stack = self.undo_stack[-300:]

    def undo(self, steps: int = 1):
        if steps < 1:
            return False, "Nothing to undo"
        ok_any = False
        for _ in range(steps):
            if not self.undo_stack:
                break
            self.state = self.undo_stack.pop()
            ok_any = True
        return (ok_any, "Undone" if ok_any else "Nothing to undo")

    def get_state(self, minimal: bool=False):
        s = {
            "turn": self.state.turn,
            "board": self.state.board,
            "forced": list(self.state.forced) if self.state.forced else None,
            "status": self.state.status,
            "rules": "max-capture,flying-kings",
            "lastMove": self.state.lastMove,
        }
        if not minimal:
            s["history"] = self.state.history[-240:]
        return s

    def _clone_board(self, board):
        return [row[:] for row in board]

    def _promote_if_needed(self, board, r, c):
        p = board[r][c]
        if p == "w" and r == 0:
            board[r][c] = "W"
        elif p == "b" and r == 7:
            board[r][c] = "B"

    def _simple_moves_from(self, board, r, c):
        p = board[r][c]
        if not p:
            return []
        color = piece_color(p)
        moves = []
        if is_king(p):
            for dr, dc in DIAGS:
                rr, cc = r+dr, c+dc
                while in_bounds(rr,cc) and board[rr][cc] is None:
                    moves.append({"from":[r,c], "to":[rr,cc], "capture": False})
                    rr += dr; cc += dc
        else:
            forward = -1 if color == "w" else 1
            for dc in (-1, 1):
                rr, cc = r+forward, c+dc
                if in_bounds(rr,cc) and board[rr][cc] is None:
                    moves.append({"from":[r,c], "to":[rr,cc], "capture": False})
        return moves

    def _capture_sequences_from(self, board, r, c):
        p = board[r][c]
        if not p:
            return []
        color = piece_color(p)
        sequences = []

        if is_king(p):
            for dr, dc in DIAGS:
                rr, cc = r+dr, c+dc
                while in_bounds(rr,cc) and board[rr][cc] is None:
                    rr += dr; cc += dc
                if not in_bounds(rr,cc):
                    continue
                if board[rr][cc] is None:
                    continue
                if piece_color(board[rr][cc]) == color:
                    continue
                victim_r, victim_c = rr, cc
                lr, lc = victim_r + dr, victim_c + dc
                while in_bounds(lr,lc) and board[lr][lc] is None:
                    nb = self._clone_board(board)
                    nb[victim_r][victim_c] = None
                    nb[r][c] = None
                    nb[lr][lc] = p
                    cont = self._capture_sequences_from(nb, lr, lc)
                    if cont:
                        for seq in cont:
                            sequences.append({"from":[r,c], "path":[[lr,lc]] + seq["path"], "captures":[[victim_r,victim_c]] + seq["captures"]})
                    else:
                        sequences.append({"from":[r,c], "path":[[lr,lc]], "captures":[[victim_r,victim_c]]})
                    lr += dr; lc += dc
        else:
            for dr, dc in DIAGS:
                mr, mc = r+dr, c+dc
                lr, lc = r+2*dr, c+2*dc
                if not (in_bounds(mr,mc) and in_bounds(lr,lc)):
                    continue
                mid = board[mr][mc]
                if mid and piece_color(mid) != color and board[lr][lc] is None:
                    nb = self._clone_board(board)
                    nb[mr][mc] = None
                    nb[r][c] = None
                    nb[lr][lc] = p
                    cont = self._capture_sequences_from(nb, lr, lc)
                    if cont:
                        for seq in cont:
                            sequences.append({"from":[r,c], "path":[[lr,lc]] + seq["path"], "captures":[[mr,mc]] + seq["captures"]})
                    else:
                        sequences.append({"from":[r,c], "path":[[lr,lc]], "captures":[[mr,mc]]})

        return sequences

    def _all_capture_sequences_for_turn(self, board, color, forced):
        if forced:
            r,c = forced
            p = board[r][c]
            if p and piece_color(p) == color:
                return self._capture_sequences_from(board, r, c)
            return []
        seqs = []
        for r in range(8):
            for c in range(8):
                p = board[r][c]
                if p and piece_color(p) == color:
                    seqs.extend(self._capture_sequences_from(board, r, c))
        return seqs

    def _max_capture_targets(self, seqs):
        if not seqs:
            return []
        mx = max(len(s["captures"]) for s in seqs)
        return [s for s in seqs if len(s["captures"]) == mx]

    def _legal_first_steps(self):
        b = self.state.board
        color = self.state.turn
        forced = self.state.forced

        seqs = self._all_capture_sequences_for_turn(b, color, forced)
        if seqs:
            best = self._max_capture_targets(seqs)
            out = []
            for s in best:
                out.append({"from": s["from"], "to": s["path"][0], "capture": True})
            uniq = {}
            for m in out:
                key = (m["from"][0],m["from"][1],m["to"][0],m["to"][1])
                uniq[key] = m
            return list(uniq.values()), True

        if forced:
            return [], False

        out = []
        for r in range(8):
            for c in range(8):
                p = b[r][c]
                if p and piece_color(p) == color:
                    out.extend(self._simple_moves_from(b, r, c))
        return out, False

    def legal_moves_from(self, frm_rc: Tuple[int,int]):
        r, c = frm_rc
        p = self.state.board[r][c]
        if not p or piece_color(p) != self.state.turn:
            return []
        moves, _ = self._legal_first_steps()
        return [m for m in moves if m["from"] == [r,c]]

    def apply_move(self, frm_rc: Tuple[int,int], to_rc: Tuple[int,int]):
        if self.state.status != "playing":
            return False, "Game is over"

        r1,c1 = frm_rc
        r2,c2 = to_rc
        if not (in_bounds(r1,c1) and in_bounds(r2,c2)):
            return False, "Out of bounds"
        if not is_dark(r2,c2):
            return False, "Only dark squares are playable"

        p = self.state.board[r1][c1]
        if not p:
            return False, "No piece"
        if piece_color(p) != self.state.turn:
            return False, "Not your turn"
        if self.state.board[r2][c2] is not None:
            return False, "Target occupied"

        legal, is_capture_phase = self._legal_first_steps()
        chosen = next((m for m in legal if m["from"]==[r1,c1] and m["to"]==[r2,c2]), None)
        if chosen is None:
            if is_capture_phase:
                return False, "Capture is mandatory (max-capture rule)"
            if self.state.forced:
                return False, "You must continue capturing with the same piece"
            return False, "Illegal move"

        self._push_undo()

        b = self.state.board
        b[r1][c1] = None
        b[r2][c2] = p
        self.state.lastMove = {"from":[r1,c1], "to":[r2,c2]}

        move_text = f"{'W' if self.state.turn=='w' else 'B'}: ({r1},{c1})->({r2},{c2})"

        did_capture = bool(chosen.get("capture"))
        if did_capture:
            cap_r, cap_c = self._find_captured_piece((r1,c1), (r2,c2), p)
            if cap_r is None:
                return False, "Internal: capture not found"
            b[cap_r][cap_c] = None
            move_text += f" x ({cap_r},{cap_c})"

            cont_seqs = self._capture_sequences_from(b, r2, c2)
            if cont_seqs:
                self.state.forced = (r2,c2)
                self.state.history.append(move_text)
                self._update_status()
                return True, "Capture! Continue (multi-jump, max-capture)"

        self._promote_if_needed(b, r2, c2)
        self.state.forced = None
        self.state.history.append(move_text)
        self.state.turn = opponent(self.state.turn)
        self._update_status()
        return True, "Move applied"

    def _find_captured_piece(self, frm, to, p):
        r1,c1 = frm; r2,c2 = to
        dr = 1 if r2>r1 else -1
        dc = 1 if c2>c1 else -1
        r, c = r1+dr, c1+dc
        color = piece_color(p)
        while in_bounds(r,c):
            if self.state.board[r][c] is None:
                r += dr; c += dc
                continue
            if piece_color(self.state.board[r][c]) == color:
                return (None, None)
            return (r,c)
        return (None, None)

    def _update_status(self):
        w=b=0
        for r in range(8):
            for c in range(8):
                p = self.state.board[r][c]
                if p:
                    if piece_color(p)=="w": w += 1
                    else: b += 1
        if w==0:
            self.state.status = "win-b"; return
        if b==0:
            self.state.status = "win-w"; return

        moves,_ = self._legal_first_steps()
        if not moves:
            self.state.status = "win-b" if self.state.turn=="w" else "win-w"
            return
        self.state.status = "playing"

    def ai_move(self, level: str="medium", kind: str="ai"):
        if self.state.status != "playing":
            return False, "Game is over"
        moves, _ = self._legal_first_steps()
        if not moves:
            return False, "No moves"

        def score(m):
            r2,c2 = m["to"]
            r1,c1 = m["from"]
            p = self.state.board[r1][c1]
            s = 0
            if m.get("capture"): s += 100
            if p == "w" and r2 == 0: s += 80
            if p == "b" and r2 == 7: s += 80
            s += (3.5 - abs(3.5 - c2)) * 2
            if p in ("W","B"): s += 10
            return s

        if kind == "bot" or level == "easy":
            choice = random.choice(moves)
        else:
            scored = [(score(m), m) for m in moves]
            scored.sort(key=lambda x: x[0], reverse=True)
            topk = 3 if level == "medium" else 1
            choice = random.choice(scored[:topk])[1]

        ok, msg = self.apply_move(tuple(choice["from"]), tuple(choice["to"]))
        if ok:
            tag = "AI" if kind == "ai" else "BOT"
            return True, f"{tag}: {msg}"
        return False, "AI failed"
