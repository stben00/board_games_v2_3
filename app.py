from flask import Flask, render_template, request, jsonify
from game_engine.chess_engine import ChessEngine
from game_engine.checkers_engine import CheckersEngine


def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    chess = ChessEngine()
    checkers = CheckersEngine()

    def get_mode(data: dict) -> str:
        m = (data.get("mode") or "chess").strip().lower()
        return "checkers" if m == "checkers" else "chess"

    def is_pos(x) -> bool:
        return isinstance(x, list) and len(x) == 2 and all(isinstance(i, int) for i in x)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/new")
    def new_game():
        data = request.get_json(silent=True) or {}
        mode = get_mode(data)

        if mode == "chess":
            chess.reset()
            return jsonify({"ok": True, "mode": "chess", "state": chess.get_state()})

        checkers.reset()
        return jsonify({"ok": True, "mode": "checkers", "state": checkers.get_state()})

    @app.post("/api/legal_moves")
    def legal_moves():
        data = request.get_json(silent=True) or {}
        mode = get_mode(data)
        frm = data.get("from")

        if not is_pos(frm):
            return jsonify({"ok": False, "error": "Bad format: 'from' must be [r,c]"}), 400

        if mode == "chess":
            moves = chess.legal_moves_from(tuple(frm))
            st = chess.get_state(minimal=True)
        else:
            moves = checkers.legal_moves_from(tuple(frm))
            st = checkers.get_state(minimal=True)

        return jsonify({"ok": True, "moves": moves, "state": st})

    @app.post("/api/move")
    def make_move():
        data = request.get_json(silent=True) or {}
        mode = get_mode(data)

        frm = data.get("from")
        to = data.get("to")
        promo = data.get("promotion")

        if not (is_pos(frm) and is_pos(to)):
            return jsonify({"ok": False, "error": "Bad move format: use {from:[r,c], to:[r,c]}"}), 400

        if mode == "chess":
            ok, msg = chess.apply_move(tuple(frm), tuple(to), promo)
            return jsonify({"ok": ok, "message": msg, "state": chess.get_state()})

        ok, msg = checkers.apply_move(tuple(frm), tuple(to))
        return jsonify({"ok": ok, "message": msg, "state": checkers.get_state()})

    @app.post("/api/undo")
    def undo():
        data = request.get_json(silent=True) or {}
        mode = get_mode(data)
        steps = data.get("steps", 1)

        try:
            steps = int(steps)
        except Exception:
            steps = 1

        steps = max(1, min(10, steps))  # защита от "undo 99999"

        if mode == "chess":
            ok, msg = chess.undo(steps=steps)
            return jsonify({"ok": ok, "message": msg, "state": chess.get_state()})

        ok, msg = checkers.undo(steps=steps)
        return jsonify({"ok": ok, "message": msg, "state": checkers.get_state()})

    @app.post("/api/ai_move")
    def ai_move():
        data = request.get_json(silent=True) or {}
        mode = get_mode(data)

        level = (data.get("level") or "medium").strip().lower()
        kind = (data.get("kind") or "ai").strip().lower()  # ai / bot

        if level not in ("easy", "medium", "hard"):
            level = "medium"
        if kind not in ("ai", "bot"):
            kind = "ai"

        if mode == "chess":
            ok, msg = chess.ai_move(level=level, kind=kind)
            return jsonify({"ok": ok, "message": msg, "state": chess.get_state()})

        ok, msg = checkers.ai_move(level=level, kind=kind)
        return jsonify({"ok": ok, "message": msg, "state": checkers.get_state()})

    # Красивый JSON + нормальная ошибка 404 (чтобы понимать, что сломалось)
    app.config["JSON_SORT_KEYS"] = False

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"ok": False, "error": "Not found"}), 404

    return app


app = create_app()

import os
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
    