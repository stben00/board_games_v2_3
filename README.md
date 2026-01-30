# Board Games v2.3 — Chess & Checkers (PvP / vs Bot / vs AI)

## Run (macOS)
```bash
cd /Users/air/Desktop
rm -rf board_games_v2_3
unzip -o board_games_v2_3.zip
cd board_games_v2_3

/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: http://127.0.0.1:5000

**Tip:** If UI looks outdated, hard refresh in browser: `Cmd + Shift + R`.

## Opponent modes
- **Human vs Human**: 2 players on one laptop
- **Human vs Bot**:
  - Chess: random legal moves
  - Checkers: random legal moves (still respects mandatory/max-capture rules)
- **Human vs AI**:
  - Chess: **Stockfish** via python-chess
  - Checkers: heuristic AI

## New features (v2.3)
- **Pawn promotion picker (Chess)**: choose Q/R/B/N in a modal
- **Last move highlight**: from/to squares highlighted
- **Undo** button:
  - PvP: undo one move
  - Vs computer: undo user + computer move (so it's your turn again)
