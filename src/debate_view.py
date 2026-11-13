"""판결 진행 엿보기 — 전문가 토론을 한 사람씩, 한두 문장씩 넘겨 보는 대화 화면.

st.components.v2 컴포넌트라 '다음'을 눌러도 Streamlit 이 다시 실행되지 않고 브라우저 안에서 넘어갑니다
(애니메이션이 끊기지 않음). 마지막 판결 도장 장면에 닿으면 state `done` 을 보내 열람 승인 단계를 엽니다.

보안: 발언은 LLM 출력이므로 JS 에서 textContent 로만 넣습니다 (innerHTML 금지).
"""

from __future__ import annotations

import base64
import math
import re
import urllib.parse
import urllib.request
from functools import lru_cache

import streamlit as st

from src.avatar import BEAUTY_MARK, DICEBEAR, SILHOUETTE, _bowtie, _fedora, _outer, _pocket_square, _tie

# ── 전문가 아바타 (DiceBear micah + 기존 소품 레이어) ─────────────────────────
EXPERTS: dict[str, dict] = {
    "범죄 프로파일러": {
        "params": {"seed": "profiler", "baseColor": "e0ac69", "hair": "fonze", "hairColor": "000000", "eyes": "eyes",
                   "eyebrows": "down", "mouth": "nervous", "shirt": "collared", "shirtColor": "ffffff",
                   "glasses": "square", "glassesColor": "000000", "glassesProbability": "100",
                   "facialHair": "scruff", "facialHairColor": "000000", "facialHairProbability": "100"},
        "layers": lambda: _outer("trench") + _tie("1f1f1f") + _fedora("5a4632"),
        "bg": "d6c7a4",
    },
    "패션 스타일리스트": {
        "params": {"seed": "stylist", "baseColor": "f9c9b6", "hair": "full", "hairColor": "77311d",
                   "eyes": "smilingShadow", "eyeShadowColor": "e0ddff", "eyebrows": "eyelashesUp", "mouth": "smirk",
                   "shirt": "open", "shirtColor": "fc909f", "earrings": "hoop", "earringColor": "f4d150",
                   "earringsProbability": "100"},
        "layers": lambda: _outer("burgundy_suit") + _pocket_square("ffffff") + BEAUTY_MARK,
        "bg": "e8d1ac",
    },
    "연애 심리학자": {
        "params": {"seed": "psychologist", "baseColor": "c68642", "hair": "pixie", "hairColor": "000000",
                   "eyes": "round", "eyebrows": "eyelashesDown", "mouth": "smile", "shirt": "crew",
                   "shirtColor": "9287ff", "glasses": "round", "glassesColor": "000000", "glassesProbability": "100",
                   "earrings": "stud", "earringColor": "ffffff", "earringsProbability": "100"},
        "layers": lambda: "",
        "bg": "e6dcc6",
    },
    "사회자": {
        "params": {"seed": "moderator", "baseColor": "ac6651", "hair": "mrClean", "hairColor": "e8e1e1",
                   "eyes": "eyes", "eyebrows": "up", "mouth": "smirk", "shirt": "collared", "shirtColor": "ffffff",
                   "glasses": "round", "glassesColor": "c9a66b", "glassesProbability": "100",
                   "facialHair": "beard", "facialHairColor": "e8e1e1", "facialHairProbability": "100"},
        "layers": lambda: _outer("black_suit") + _bowtie("b3261e"),
        "bg": "d9cdb2",
    },
    "반려동물 행동 전문가": {
        "params": {"seed": "petvet", "baseColor": "ffdbb4", "hair": "dannyPhantom", "hairColor": "ac6651",
                   "eyes": "smiling", "eyebrows": "up", "mouth": "laughing", "shirt": "collared",
                   "shirtColor": "6bd9e9", "facialHair": "beard", "facialHairColor": "ac6651",
                   "facialHairProbability": "100"},
        "layers": lambda: _bowtie("22325a"),
        "bg": "dfe3c8",
    },
}


@lru_cache(maxsize=8)
def _expert_svg(who: str) -> str:
    """성공한 결과만 캐시 (실패하면 예외 → 캐시되지 않아 다음 화면에서 다시 시도)."""
    e = EXPERTS[who]
    params = {"backgroundColor": e["bg"], "eyebrowsColor": "000000", "earringsProbability": "0",
              "glassesProbability": "0", "facialHairProbability": "0", **e["params"]}
    with urllib.request.urlopen(f"{DICEBEAR}?{urllib.parse.urlencode(params)}", timeout=10) as r:
        raw = r.read().decode("utf-8")
    i = raw.rfind("</svg>")
    return raw[:i] + e["layers"]() + raw[i:]


def expert_avatar(who: str) -> str:
    """전문가 아바타 data URI. 받아 오지 못하면 실루엣."""
    try:
        svg = _expert_svg(who) if who in EXPERTS else SILHOUETTE
    except Exception:
        svg = SILHOUETTE
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode()


# ── 발언을 카드로 나누기: 한 장에 2~3문장까지 ───────────────────────────────
_SENT = re.compile(r"(?<=[.!?…])[\"'”’)]*\s+")


def split_cards(text: str, max_sents: int = 3) -> list[str]:
    """발언을 문장 단위로 나눠 한 카드에 최대 3문장. 넘치면 고르게 나눔 (4문장 → 2+2, 5 → 3+2)."""
    sents = [x.strip() for x in _SENT.split(text.strip()) if x.strip()]
    if len(sents) <= max_sents:
        return [" ".join(sents) or text]
    n = math.ceil(len(sents) / max_sents)
    sizes = [len(sents) // n + (1 if i < len(sents) % n else 0) for i in range(n)]
    out, i = [], 0
    for k in sizes:
        out.append(" ".join(sents[i:i + k]))
        i += k
    return out


def build_scenes(minutes: list[dict], reason: str) -> list[dict]:
    """전문가끼리 단서를 이어 감. 사회자는 뒤에서 순서만 정하고 판결 장면에만 나옴. 한 장에 2~3문장까지, 마지막만 '결정적 단서'."""
    scenes: list[dict] = []
    minutes = [m for m in minutes if m.get("node") != "moderator" and m.get("who") != "사회자"]
    for n, m in enumerate(minutes):
        role = "결정적 단서" if n == len(minutes) - 1 else "단서"
        parts = split_cards(m.get("text", ""))  # 발언은 두 문장으로 받으므로 보통 한 장
        for i, part in enumerate(parts):
            scenes.append({"type": "line", "who": m.get("who", ""), "role": role, "avatar": expert_avatar(m.get("who", "")),
                           "text": part, "turn_start": i == 0, "part": i + 1, "parts": len(parts)})
    scenes.append({"type": "verdict", "reason": reason})
    return scenes


# ── 컴포넌트 ───────────────────────────────────────────────────────────────
HTML = """
<section class="stage" tabindex="-1" aria-label="판결 진행 엿보기">
  <header class="tease">
    <h2 class="q"><span class="q-text">스파이는 과연 누구</span><span class="q-mark">?</span></h2>
    <p class="sub">전문가 세 명이 단서를 맞춰 보고 있어요. 끝까지 들으면 색출 팀장의 판결이 나옵니다.</p>
  </header>
  <div class="top">
    <div class="track" aria-hidden="true"></div>
    <p class="count"></p>
  </div>
  <div class="scene" aria-live="polite"></div>
  <div class="controls">
    <button type="button" class="btn ghost back">이전</button>
    <button type="button" class="btn ghost skip">판결로 건너뛰기</button>
    <button type="button" class="btn stamp next">다음</button>
  </div>
</section>
"""

CSS = """
:host { display: block; width: 100%; min-width: 0; }
* { box-sizing: border-box; }
.stage { width: 100%; min-width: 0; font-family: var(--font-body); color: var(--color-ink); outline: none; padding-top: var(--space-xs);
  word-break: keep-all; overflow-wrap: break-word; }
.stage:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 4px; }

/* the teaser: the question the whole debate answers */
.tease { margin-bottom: var(--space-xl); text-align: center; }
.q { margin: 0; font: var(--display-weight) var(--text-3xl)/1.15 var(--font-display); color: var(--color-ink); text-wrap: balance;
  overflow-wrap: break-word; min-width: 0; animation: fade 520ms var(--ease-out) both; }
.q-mark { display: inline-block; margin-left: 0.08em; transform-origin: 50% 85%; animation: wobble 1100ms var(--ease-in-out) 500ms 2 both; }
.tease .sub { margin: var(--space-xs) auto 0; max-width: none; text-wrap: balance; color: var(--color-ink-2); animation: fade 520ms var(--ease-out) 160ms both; }
.tease.solved .q { animation: fade 420ms var(--ease-out) both; }
.tease.solved .q-mark { display: none; }

.top { display: flex; align-items: center; gap: var(--space-md); }
.track { flex: 1; display: flex; gap: var(--space-2xs); min-width: 0; }
.track i { flex: 1; height: 4px; background: var(--color-rule); transform-origin: left center; }
.track i.on { background: var(--color-ink); }
.track i.now { background: var(--color-accent); animation: grow var(--dur-long) var(--ease-out) both; }
.count { margin: 0; font-size: var(--text-sm); color: var(--color-muted); font-variant-numeric: tabular-nums; white-space: nowrap; }

.scene { position: relative; min-height: 15rem; margin-top: var(--space-lg); display: grid; grid-template-columns: minmax(0, 1fr); align-items: start; }

/* one speaker: the face on the left, the bubble beside it */
.line { display: grid; grid-template-columns: 8rem minmax(0, 1fr); gap: var(--space-lg); align-items: start; }
.face { position: relative; display: grid; justify-items: center; gap: var(--space-xs); }
.face img { display: block; width: 8rem; height: 8rem; border-radius: 50%; background: var(--color-paper-2);
  box-shadow: 0 0 0 2px var(--color-ink), 0 10px 18px -12px var(--color-ink); }
.face .name { font-weight: 700; font-size: var(--text-sm); text-align: center; line-height: 1.3; }
.face .role { font-size: var(--text-sm); color: var(--color-muted); }
.face.enter { animation: slide-in 560ms var(--ease-out) both; }
.face.nod img { animation: nod 420ms var(--ease-out) both; }
.face.talking img { animation: talk 900ms var(--ease-in-out) infinite; }

.bubble { position: relative; margin-top: var(--space-sm); padding: var(--space-lg) var(--space-lg) var(--space-md);
  background: var(--color-paper); border-radius: 22px; box-shadow: inset 0 0 0 2px var(--color-ink), 6px 6px 0 var(--color-paper-2);
  font-size: var(--text-lg); line-height: 1.7; min-height: 8.5rem; animation: pop 380ms var(--ease-out) both; }
.bubble::before { content: ""; position: absolute; left: -11px; top: 2.6rem; width: 20px; height: 20px; background: var(--color-paper);
  box-shadow: inset 2px -2px 0 var(--color-ink); transform: rotate(45deg); border-radius: 0 0 0 4px; }
.bubble .typed { white-space: pre-wrap; }
.bubble .caret { display: inline-block; width: 0.55em; height: 1.1em; margin-left: 2px; vertical-align: -0.15em; background: var(--color-ink);
  animation: blink 900ms steps(1) infinite; }
.bubble .more { display: block; margin-top: var(--space-sm); font-size: var(--text-sm); color: var(--color-muted); text-align: right; opacity: 0; transition: opacity var(--dur-short) var(--ease-out); }
.bubble.done .more { opacity: 1; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }

/* the round change: a stamp struck across the sheet */
.round { display: grid; justify-items: center; align-content: center; gap: var(--space-sm); min-height: 15rem; text-align: center; }
.round .mark { font: var(--display-weight) 3rem/1.1 var(--font-display); color: var(--color-accent); padding: var(--space-xs) var(--space-lg);
  box-shadow: inset 0 0 0 3px var(--color-accent), inset 0 0 0 6px var(--color-paper), inset 0 0 0 7px var(--color-accent);
  animation: strike 520ms var(--ease-out) both; }
.round p { margin: 0; color: var(--color-ink-2); animation: fade 420ms var(--ease-out) 360ms both; }

/* the verdict: the chair's stamp slams, the sheet shakes, the reason is typed under it */
.verdict { display: grid; justify-items: center; gap: var(--space-md); text-align: center; padding-block: var(--space-md); }
.verdict.shake { animation: shake 360ms var(--ease-out) 420ms both; }
.verdict .label { margin: 0; font-weight: 700; font-size: var(--text-sm); color: var(--color-ink-2); animation: fade 300ms var(--ease-out) both; }
.verdict .call { display: inline-block; padding: var(--space-xs) var(--space-lg); font: var(--display-weight) 3.2rem/1.1 var(--font-display);
  color: var(--color-accent); box-shadow: inset 0 0 0 3px var(--color-accent), inset 0 0 0 6px var(--color-paper), inset 0 0 0 7px var(--color-accent);
  transform: rotate(-4deg); animation: slam 620ms cubic-bezier(0.2, 1.4, 0.4, 1) 120ms both; }
.verdict .reason { margin: var(--space-xs) 0 0; max-width: 46ch; font-size: var(--text-lg); line-height: 1.6; min-height: 3.2em; }
/* the decision, right under the reason: the folder's dark sleeve slides up */
.gate { justify-self: stretch; margin-top: var(--space-md); padding: var(--space-lg); background: var(--color-ink); color: var(--color-paper);
  border-radius: 2px; text-align: left; animation: rise 460ms var(--ease-out) both; }
.gate-title { margin: 0; font: var(--display-weight) var(--text-xl)/1.25 var(--font-display); color: var(--color-paper); }
.gate-sub { margin: var(--space-xs) 0 0; color: var(--color-paper-2); }
.gate-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: var(--space-md); margin-top: var(--space-lg); }
.gate .btn { width: 100%; min-height: 48px; }
.gate .btn:focus-visible { outline-color: var(--color-paper); }
.btn.gate-ghost { color: var(--color-paper); box-shadow: inset 0 0 0 1.5px var(--color-paper); }
.btn.gate-ghost:hover:not(:disabled) { background: var(--color-ink-2); }
.btn.gate-ghost:active:not(:disabled) { background: var(--color-ink-2); transform: translateY(1px); }
.btn.gate-go { background: var(--color-accent); color: var(--color-accent-ink); font: var(--display-weight) var(--text-lg)/1 var(--font-display); }
.btn.gate-go:hover:not(:disabled) { background: var(--color-accent-deep); }
.btn.gate-go:active:not(:disabled) { background: var(--color-accent-deep); transform: translateY(1px); }

/* controls: the plain key and the stamp */
.controls { display: flex; gap: var(--space-sm); justify-content: flex-end; align-items: center; margin-top: var(--space-xl); flex-wrap: wrap; }
.btn { font: 700 var(--text-md)/1 var(--font-body); min-height: 44px; padding: var(--space-sm) var(--space-lg); border: 0; border-radius: 2px;
  cursor: pointer; background: transparent; color: var(--color-ink);
  transition: background-color var(--dur-micro) var(--ease-out), color var(--dur-micro) var(--ease-out), transform var(--dur-micro) var(--ease-out); }
.btn:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn.ghost { box-shadow: inset 0 0 0 1.5px var(--color-ink); }
.btn.ghost:hover:not(:disabled) { background: var(--color-paper-2); }
.btn.ghost:active:not(:disabled) { background: var(--color-paper-3); transform: translateY(1px); }
.btn.skip { margin-right: auto; box-shadow: none; color: var(--color-muted); padding-inline: var(--space-xs); text-decoration: underline; text-underline-offset: 0.2em; }
.btn.skip:hover:not(:disabled) { background: transparent; color: var(--color-ink); }
.btn.stamp { min-width: 9rem; color: var(--color-accent); font: var(--display-weight) var(--text-lg)/1 var(--font-display);
  box-shadow: inset 0 0 0 2px var(--color-accent), inset 0 0 0 4px var(--color-paper), inset 0 0 0 5px var(--color-accent); }
.btn.stamp:hover:not(:disabled) { background: var(--color-accent); color: var(--color-accent-ink); }
.btn.stamp:active:not(:disabled) { background: var(--color-accent-deep); color: var(--color-accent-ink); transform: translateY(1px) rotate(-1deg); }
[hidden] { display: none !important; }

@keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes slide-in { from { opacity: 0; transform: translateX(-48px) rotate(-6deg); } 70% { transform: translateX(6px) rotate(1deg); } to { opacity: 1; transform: none; } }
@keyframes nod { 0% { transform: none; } 40% { transform: translateY(5px) rotate(-3deg); } to { transform: none; } }
@keyframes talk { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-3px); } }
@keyframes pop { from { opacity: 0; transform: translateY(10px) scale(0.96); } to { opacity: 1; transform: none; } }
@keyframes blink { 50% { opacity: 0; } }
@keyframes fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@keyframes strike { from { opacity: 0; transform: scale(2.2) rotate(-14deg); } 70% { opacity: 1; transform: scale(0.95) rotate(-5deg); } to { opacity: 1; transform: scale(1) rotate(-6deg); } }
@keyframes slam { from { opacity: 0; transform: scale(3) rotate(-16deg); } 60% { opacity: 1; transform: scale(0.92) rotate(-3deg); } to { opacity: 1; transform: scale(1) rotate(-4deg); } }
@keyframes rise { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: none; } }
@keyframes wobble { 0%, 100% { transform: rotate(0); } 20% { transform: rotate(-14deg); } 45% { transform: rotate(10deg); } 70% { transform: rotate(-5deg); } }
@keyframes shake { 0%, 100% { transform: none; } 25% { transform: translate(-4px, 2px); } 50% { transform: translate(3px, -2px); } 75% { transform: translate(-2px, 1px); } }

@media (max-width: 40rem) {
  .line { grid-template-columns: 5rem minmax(0, 1fr); gap: var(--space-md); }
  .face img { width: 5rem; height: 5rem; }
  .bubble { font-size: var(--text-md); padding: var(--space-md); }
  .bubble::before { top: 1.6rem; }
  .verdict .call, .round .mark { font-size: 2.2rem; }
  .btn.skip { width: 100%; order: 3; margin-right: 0; }
  .gate-row { grid-template-columns: minmax(0, 1fr); }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
"""

JS = r"""
export default function (component) {
  const { data, parentElement } = component;
  const stage = parentElement.querySelector('.stage');
  if (!stage || !data) return;
  stage._cmp = component;  // 버튼을 누를 때 가장 최근 컴포넌트 함수로 신호를 보낸다
  // Streamlit 이 다시 실행돼도 같은 토론이면 진행 상태를 그대로 두고, 결정 패널만 새 단계로 바꾼다
  if (stage.dataset.key === data.key) { stage._setPhase && stage._setPhase(data.phase); return; }
  stage.dataset.key = data.key;

  const scenes = data.scenes || [];
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = (s) => stage.querySelector(s);
  const track = $('.track'), count = $('.count'), sceneBox = $('.scene');
  const back = $('.back'), next = $('.next'), skip = $('.skip');
  const tease = $('.tease'), qText = $('.q-text'), teaseSub = $('.tease .sub');
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };

  track.replaceChildren(...scenes.map(() => el('i')));
  let idx = -1, timer = null, typing = null, phase = data.phase || 'approve';

  // 열람 결정 패널: 판결 이유 바로 아래. approve(열람 승인) / covered(덮어 둔 뒤)
  const GATE = {
    approve: { title: '열람 승인이 필요해요', sub: '이 파일을 열면 요원의 정체가 드러나고 되돌릴 수 없어요.',
               ghost: ['덮어 둔다', 'cover', '덮는 중…'], go: ['열람한다', 'open', '여는 중…'] },
    covered: { title: '파일을 덮었어요', sub: '그 사람은 내일도 그 자리에 있을 거예요.',
               ghost: ['처음부터', 'restart', '정리하는 중…'], go: ['마음이 바뀌었어요, 열람할래요', 'reopen', '여는 중…'] },
  };
  function gate() {
    const g = GATE[phase] || GATE.approve;
    const box = el('div', 'gate'); box.setAttribute('role', 'group'); box.setAttribute('aria-label', g.title);
    const row = el('div', 'gate-row');
    const mk = ([label, action, busy], cls) => {
      const b = el('button', 'btn ' + cls, label); b.type = 'button';
      b.onclick = () => {
        row.querySelectorAll('button').forEach((x) => { x.disabled = true; });
        b.textContent = busy;
        stage._cmp.setTriggerValue('action', action);
      };
      return b;
    };
    row.append(mk(g.ghost, 'gate-ghost'), mk(g.go, 'gate-go'));
    box.append(el('p', 'gate-title', g.title), el('p', 'gate-sub', g.sub), row);
    return box;
  }
  stage._setPhase = (p) => {
    if (!p || p === phase) return;
    phase = p;
    const old = stage.querySelector('.gate');
    if (old) old.replaceWith(gate());
  };

  function typeInto(node, text, onDone) {
    clearInterval(timer);
    if (reduce) { node.textContent = text; typing = null; onDone && onDone(); return; }
    let i = 0; node.textContent = '';
    typing = () => { clearInterval(timer); node.textContent = text; typing = null; onDone && onDone(); };
    timer = setInterval(() => {
      i += 1; node.textContent = text.slice(0, i);
      if (i >= text.length) { clearInterval(timer); typing = null; onDone && onDone(); }
    }, 24);
  }

  function lineScene(s, prev) {
    const sameSpeaker = prev && prev.type === 'line' && prev.who === s.who;
    const wrap = el('div', 'line');
    const face = el('figure', 'face' + (sameSpeaker ? ' nod' : ' enter'));
    face.style.margin = '0';
    const img = el('img'); img.src = s.avatar; img.alt = s.who; img.width = 128; img.height = 128;
    face.append(img, el('figcaption', 'name', s.who), el('span', 'role', s.role));
    const bubble = el('div', 'bubble');
    const sr = el('span', 'sr', s.who + ': ' + s.text);
    const typed = el('span', 'typed'); typed.setAttribute('aria-hidden', 'true');
    const caret = el('span', 'caret'); caret.setAttribute('aria-hidden', 'true');
    const more = el('span', 'more', s.part < s.parts ? '이어서 말합니다' : '발언 끝'); more.setAttribute('aria-hidden', 'true');
    bubble.append(sr, typed, caret, more);
    wrap.append(face, bubble);
    sceneBox.replaceChildren(wrap);
    face.classList.add('talking');
    const delay = sameSpeaker || reduce ? 0 : 320;
    setTimeout(() => typeInto(typed, s.text, () => { caret.remove(); bubble.classList.add('done'); face.classList.remove('talking'); }), delay);
  }

  function roundScene(s) {
    const box = el('div', 'round');
    box.append(el('div', 'mark', s.title), el('p', null, s.sub));
    sceneBox.replaceChildren(box);
  }

  function verdictScene(s) {
    const box = el('div', 'verdict shake');
    const reason = el('p', 'reason');
    box.append(el('p', 'label', '색출 팀장 판결'), el('div', 'call', '스파이 검거'), reason);
    sceneBox.replaceChildren(box);
    setTimeout(() => typeInto(reason, s.reason, () => {
      if (idx === scenes.length - 1 && !box.querySelector('.gate')) box.append(gate());
    }), reduce ? 0 : 900);
  }

  function show(i) {
    clearInterval(timer); typing = null;
    const prev = scenes[idx];
    idx = Math.max(0, Math.min(scenes.length - 1, i));
    const s = scenes[idx];
    [...track.children].forEach((t, k) => { t.className = k < idx ? 'on' : (k === idx ? 'now' : ''); });
    const lines = scenes.filter((x) => x.type === 'line').length;
    const seen = scenes.slice(0, idx + 1).filter((x) => x.type === 'line').length;
    count.textContent = s.type === 'verdict' ? '판결' : `${seen} / ${lines}`;
    // 판결 장면에서는 상단 질문이 답으로 바뀐다 (이전으로 돌아가면 다시 질문)
    const solved = s.type === 'verdict';
    if (tease.classList.contains('solved') !== solved) {
      tease.classList.toggle('solved', solved);
      qText.textContent = solved ? '스파이를 검거했습니다' : '스파이는 과연 누구';
      teaseSub.textContent = solved ? '정체는 기밀 파일 속에 있어요. 열람 승인을 받아야 볼 수 있어요.'
                                    : '전문가 세 명이 단서를 맞춰 보고 있어요. 끝까지 들으면 판결이 나옵니다.';
    }
    if (s.type === 'line') lineScene(s, prev);
    else if (s.type === 'round') roundScene(s);
    else verdictScene(s);
    back.disabled = idx === 0;
    const last = idx === scenes.length - 1;
    // 판결 장면에서는 결정 패널이 주인공이라 '다음'과 '건너뛰기'를 숨긴다 ('이전'으로 토론을 다시 볼 수 있음)
    if (!last) next.textContent = scenes[idx + 1].type === 'verdict' ? '판결 듣기' : '다음';
    next.hidden = last;
    skip.hidden = last;
  }

  function forward() {
    if (typing) { typing(); return; }            // 타자 중이면 먼저 문장을 다 보여 준다
    if (idx < scenes.length - 1) show(idx + 1);
  }

  next.onclick = forward;
  back.onclick = () => show(idx - 1);
  skip.onclick = () => show(scenes.length - 1);
  stage.onkeydown = (e) => {
    if (e.target.closest('button') && (e.key === 'Enter' || e.key === ' ')) return;
    if (e.key === 'ArrowRight' || e.key === 'Enter' || e.key === ' ') { e.preventDefault(); forward(); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); show(idx - 1); }
  };

  show(data.start_at_end ? scenes.length - 1 : 0);
  return () => clearInterval(timer);
}
"""

_component = st.components.v2.component("spy_debate", html=HTML, css=CSS, js=JS)


def debate_view(minutes: list[dict], reason: str, key: str, phase: str = "approve",
                start_at_end: bool = False) -> str | None:
    """토론 화면을 그리고, 판결 장면의 결정 패널에서 누른 버튼을 돌려줌.

    phase="approve": 'open' | 'cover'   ·   phase="covered": 'reopen' | 'restart'   ·   안 눌렀으면 None
    """
    scenes = build_scenes(minutes, reason)
    result = _component(data={"key": key, "scenes": scenes, "phase": phase, "start_at_end": start_at_end},
                        key=f"debate-{key}", on_action_change=lambda: None)
    return getattr(result, "action", None)
