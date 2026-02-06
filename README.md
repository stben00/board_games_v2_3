# Board Games v2.3 — Chess & Checkers (PvP / vs Bot / vs AI)

Chess + Checkers in one web app (Flask + JS).
Supports PvP, random Bot, and AI (Stockfish for chess).

---

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