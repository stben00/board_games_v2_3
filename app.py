from flask import Flask, render_template, request, jsonify
from game_engine.chess_engine import ChessEngine
from game_engine.checkers_engine import CheckersEngine


def create_app():
    app = Flask(__name__)

    chess = ChessEngine()
    checkers = CheckersEngine()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/new")
    def new_game():
        data = request.get_json(force=True)
        mode = data.get("mode", "chess")

        if mode == "chess":
            chess.reset()
            return jsonify({"ok": True, "mode": "chess", "state": chess.get_state()})

        checkers.reset()
        return jsonify({"ok": True, "mode": "checkers", "state": checkers.get_state()})

    @app.post("/api/legal_moves")
    def legal_moves():
        data = request.get_json(force=True)
        mode = data.get("mode", "chess")
        frm = data.get("from")

        if not (isinstance(frm, list) and len(frm) == 2):
            return jsonify({"ok": False, "error": "Bad format"}), 400

        if mode == "chess":
            moves = chess.legal_moves_from(tuple(frm))
            return jsonify({"ok": True, "moves": moves, "state": chess.get_state(minimal=True)})

        moves = checkers.legal_moves_from(tuple(frm))
        return jsonify({"ok": True, "moves": moves, "state": checkers.get_state(minimal=True)})

    @app.post("/api/move")
    def make_move():
        data = request.get_json(force=True)
        mode = data.get("mode", "chess")
        frm = data.get("from")
        to = data.get("to")
        promo = data.get("promotion")

        if not (isinstance(frm, list) and isinstance(to, list) and len(frm) == 2 and len(to) == 2):
            return jsonify({"ok": False, "error": "Bad move format"}), 400

        if mode == "chess":
            ok, msg = chess.apply_move(tuple(frm), tuple(to), promo)
            return jsonify({"ok": ok, "message": msg, "state": chess.get_state()})

        ok, msg = checkers.apply_move(tuple(frm), tuple(to))
        return jsonify({"ok": ok, "message": msg, "state": checkers.get_state()})

    @app.post("/api/undo")
    def undo():
        data = request.get_json(force=True)
        mode = data.get("mode", "chess")
        steps = int(data.get("steps", 1))

        if mode == "chess":
            ok, msg = chess.undo(steps=steps)
            return jsonify({"ok": ok, "message": msg, "state": chess.get_state()})

        ok, msg = checkers.undo(steps=steps)
        return jsonify({"ok": ok, "message": msg, "state": checkers.get_state()})

    @app.post("/api/ai_move")
    def ai_move():
        data = request.get_json(force=True)
        mode = data.get("mode", "chess")
        level = data.get("level", "medium")
        kind = data.get("kind", "ai")  # "ai" or "bot"

        if mode == "chess":
            ok, msg = chess.ai_move(level=level, kind=kind)
            return jsonify({"ok": ok, "message": msg, "state": chess.get_state()})

        ok, msg = checkers.ai_move(level=level, kind=kind)
        return jsonify({"ok": ok, "message": msg, "state": checkers.get_state()})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)