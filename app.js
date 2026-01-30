import { $, postJSON } from "./ui.js";

const boardEl = $("board");
const msgEl = $("msg");
const turnText = $("turnText");
const turnDot = $("turnDot");
const statusPill = $("statusPill");
const historyEl = $("history");

const tabChess = $("tabChess");
const tabCheckers = $("tabCheckers");
const btnNew = $("btnNew");
const btnUndo = $("btnUndo");

const filesTop = $("filesTop");
const filesBottom = $("filesBottom");
const ranksLeft = $("ranksLeft");
const ranksRight = $("ranksRight");

const opponentModeEl = $("opponentMode"); // pvp/bot/ai
const userSideEl = $("userSide");         // w/b
const aiLevelEl = $("aiLevel");           // easy/medium/hard

// Promotion modal
const promoModal = $("promoModal");
const promoCancel = $("promoCancel");
const promoBtns = Array.from(document.querySelectorAll(".promoBtn"));

let mode = "chess";
let state = null;

let selected = null;
let hints = [];

// pending promotion move
let pendingPromo = null; // {from:[r,c], to:[r,c]}

function opponentMode(){ return opponentModeEl?.value || "pvp"; }
function userSide(){ return userSideEl?.value || "w"; }
function aiLevel(){ return aiLevelEl?.value || "medium"; }

function isVsComputer(){ return opponentMode() !== "pvp"; }
function computerKind(){ return opponentMode(); } // "bot" or "ai"

function setMessage(text, type="info"){
  msgEl.textContent = text || "";
  msgEl.style.color =
    type==="bad" ? "rgba(255,77,109,.95)" :
    type==="good" ? "rgba(49,209,124,.95)" :
    "rgba(255,255,255,.70)";
}

function setTurnUI(){
  if(!state) return;
  const t = state.turn === "w" ? "White" : "Black";
  turnText.textContent = `Turn: ${t}`;
  turnDot.style.background = state.turn === "w"
    ? "rgba(255,209,102,.95)"
    : "rgba(124,92,255,.95)";
  statusPill.textContent = state.status || "playing";
}

function initCoords(){
  const files = ["a","b","c","d","e","f","g","h"];
  const ranks = ["8","7","6","5","4","3","2","1"];
  filesTop.innerHTML = files.map(x=>`<span>${x}</span>`).join("");
  filesBottom.innerHTML = files.map(x=>`<span>${x}</span>`).join("");
  ranksLeft.innerHTML = ranks.map(x=>`<span>${x}</span>`).join("");
  ranksRight.innerHTML = ranks.map(x=>`<span>${x}</span>`).join("");
}

function cellColor(r,c){ return (r+c)%2===0 ? "light" : "dark"; }
function clearSelection(){ selected = null; hints = []; }

function renderHistory(){
  const list = state?.history || [];
  historyEl.innerHTML = "";
  if(!list.length){
    historyEl.innerHTML = `<div class="histItem">No moves yet.</div>`;
    return;
  }
  for(const item of list.slice(-70).reverse()){
    const div = document.createElement("div");
    div.className = "histItem";
    div.textContent = item;
    historyEl.appendChild(div);
  }
}

function chessPiece(symbol){ return state?.legend?.[symbol] || symbol; }

function lastMoveTag(r,c){
  const lm = state?.lastMove;
  if(!lm) return null;
  if(lm.from && lm.from[0]===r && lm.from[1]===c) return "lastFrom";
  if(lm.to && lm.to[0]===r && lm.to[1]===c) return "lastTo";
  return null;
}

function render(){
  boardEl.innerHTML = "";
  if(!state) return;

  setTurnUI();
  renderHistory();

  let checkKingPos = null;
  if(mode === "chess" && state.status === "check"){
    const kingSym = state.turn === "w" ? "K" : "k";
    for(let r=0;r<8;r++){
      for(let c=0;c<8;c++){
        if(state.board[r][c] === kingSym) checkKingPos = [r,c];
      }
    }
  }

  for(let r=0; r<8; r++){
    for(let c=0; c<8; c++){
      const cell = document.createElement("div");
      cell.className = `cell ${cellColor(r,c)}`;
      cell.dataset.r = r;
      cell.dataset.c = c;

      if(mode === "checkers" && (r+c)%2===0) cell.classList.add("disabled");

      const lmTag = lastMoveTag(r,c);
      if(lmTag) cell.classList.add(lmTag);

      if(selected && selected[0]===r && selected[1]===c) cell.classList.add("selected");
      if(checkKingPos && checkKingPos[0]===r && checkKingPos[1]===c) cell.classList.add("check");

      const hint = hints.find(h => h.to[0]===r && h.to[1]===c);
      if(hint){
        if(hint.capture) cell.classList.add("capture");
        else cell.classList.add("hintMove");
      }

      const p = state.board[r][c];
      if(p){
        if(mode === "chess"){
          const el = document.createElement("div");
          el.className = "piece";
          el.textContent = chessPiece(p);
          cell.appendChild(el);
        } else {
          const el = document.createElement("div");
          const isW = (p==="w"||p==="W");
          el.className = "checker " + (isW ? "w" : "b") + ((p==="W"||p==="B") ? " king" : "");
          cell.appendChild(el);
        }
      }

      cell.addEventListener("click", onCellClick);
      boardEl.appendChild(cell);
    }
  }
}

async function fetchLegal(from){
  const res = await postJSON("/api/legal_moves", { mode, from });
  if(!res.ok || !res.payload.ok) return [];
  if(res.payload.state){
    state.turn = res.payload.state.turn;
    state.status = res.payload.state.status;
    state.forced = res.payload.state.forced;
  }
  return res.payload.moves || [];
}

function isUsersTurn(){
  if(!isVsComputer()) return true;
  return state.turn === userSide();
}

function canSelectPiece(r,c){
  const p = state.board[r][c];
  if(!p) return false;
  if(!isUsersTurn()) return false;

  if(mode === "checkers"){
    if(state.forced && (state.forced[0]!==r || state.forced[1]!==c)) return false;
    const isW = (p==="w"||p==="W");
    return (state.turn==="w" && isW) || (state.turn==="b" && !isW);
  } else {
    const isW = (p === p.toUpperCase());
    return (state.turn==="w" && isW) || (state.turn==="b" && !isW);
  }
}

async function startNew(){
  clearSelection();
  const res = await postJSON("/api/new", { mode });
  if(!res.ok || !res.payload.ok){
    setMessage("Failed to start new game", "bad");
    return;
  }
  state = res.payload.state;
  setMessage("New game started", "good");
  render();
  await maybeComputerMove();
}

async function maybeComputerMove(){
  if(!state) return;
  if(!isVsComputer()) return;
  if(state.status && state.status !== "playing" && state.status !== "check") return;
  if(isUsersTurn()) return;

  setMessage("Computer is thinking…", "info");
  const res = await postJSON("/api/ai_move", { mode, level: aiLevel(), kind: computerKind() });
  if(!res.ok || !res.payload.ok){
    setMessage(res.payload.message || res.payload.error || "Computer move failed", "bad");
    return;
  }
  state = res.payload.state;
  setMessage(res.payload.message || "Computer moved", "good");

  if(mode === "checkers"){
    let guard = 0;
    while(isVsComputer() && !isUsersTurn() && state.forced && guard < 16){
      guard += 1;
      const res2 = await postJSON("/api/ai_move", { mode, level: aiLevel(), kind: computerKind() });
      if(!res2.ok || !res2.payload.ok) break;
      state = res2.payload.state;
    }
  }

  clearSelection();
  render();
}

function openPromoModal(from, to){
  pendingPromo = { from, to };
  promoModal?.classList.remove("hidden");
}
function closePromoModal(){
  pendingPromo = null;
  promoModal?.classList.add("hidden");
}

promoCancel?.addEventListener("click", closePromoModal);
promoBtns.forEach(btn => {
  btn.addEventListener("click", async () => {
    if(!pendingPromo) return;
    const piece = btn.dataset.piece; // q/r/b/n
    const { from, to } = pendingPromo;
    closePromoModal();
    await doMove(from, to, piece);
  });
});

async function doMove(from, to, promotion=null){
  const res = await postJSON("/api/move", { mode, from, to, promotion });
  if(!res.ok || !res.payload.ok){
    setMessage(res.payload.error || res.payload.message || "Illegal move", "bad");
    return false;
  }
  state = res.payload.state;
  setMessage(res.payload.message || "OK", "good");

  if(mode === "checkers" && state.forced){
    selected = state.forced;
    hints = await fetchLegal(selected);
  } else {
    clearSelection();
  }

  render();
  await maybeComputerMove();
  return true;
}

async function onCellClick(e){
  if(!state) return;
  const r = Number(e.currentTarget.dataset.r);
  const c = Number(e.currentTarget.dataset.c);
  if(mode === "checkers" && (r+c)%2===0) return;

  if(state.status && state.status !== "playing" && state.status !== "check"){
    setMessage("Game is over. Press New Game.", "bad");
    return;
  }

  if(!selected){
    if(!canSelectPiece(r,c)){
      setMessage(isVsComputer() && !isUsersTurn() ? "Wait: computer turn." : (state.forced ? "Continue with forced piece." : "Select your piece."), "info");
      return;
    }
    selected = [r,c];
    hints = await fetchLegal(selected);
    if(!hints.length){
      setMessage("No legal moves for this piece.", "bad");
      clearSelection();
    } else {
      setMessage("Choose a highlighted destination.", "info");
    }
    render();
    return;
  }

  if(canSelectPiece(r,c)){
    selected = [r,c];
    hints = await fetchLegal(selected);
    render();
    return;
  }

  const hint = hints.find(h => h.to[0]===r && h.to[1]===c);
  if(!hint){
    setMessage("Choose a highlighted destination.", "bad");
    return;
  }

  if(mode === "chess" && hint.promotion){
    openPromoModal(selected, [r,c]);
    return;
  }

  await doMove(selected, [r,c]);
}

async function doUndo(){
  if(!state) return;
  const res = await postJSON("/api/undo", { mode, steps: 1 });
  if(!res.ok || !res.payload.ok){
    setMessage(res.payload.message || "Nothing to undo", "bad");
    return;
  }
  state = res.payload.state;

  if(isVsComputer() && state && state.turn !== userSide()){
    const res2 = await postJSON("/api/undo", { mode, steps: 1 });
    if(res2.ok && res2.payload.ok){
      state = res2.payload.state;
    }
  }

  clearSelection();
  setMessage("Undone", "good");
  render();
}

btnUndo?.addEventListener("click", doUndo);

function setMode(next){
  mode = next;
  tabChess.classList.toggle("active", mode==="chess");
  tabCheckers.classList.toggle("active", mode==="checkers");
  startNew();
}

tabChess.addEventListener("click", () => setMode("chess"));
tabCheckers.addEventListener("click", () => setMode("checkers"));
btnNew.addEventListener("click", startNew);

opponentModeEl?.addEventListener("change", startNew);
userSideEl?.addEventListener("change", startNew);
aiLevelEl?.addEventListener("change", startNew);

initCoords();
startNew();
