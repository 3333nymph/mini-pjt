"""시작 화면 — 봉인 로고가 그려지고 '기밀' 도장이 찍힌 뒤 제목이 타자로 쳐지는 온보딩.

'스파이 색출 시작'을 누르면 action='start' 를 돌려주고, 앱은 설문으로 넘어갑니다.
화면 아무 데나 누르거나 키를 누르면 애니메이션을 건너뛰고 버튼을 바로 보여 줍니다.
"""

from __future__ import annotations

import streamlit as st

from src.card import FONTS, STYLES

TITLE = "나를 사랑한 스파이"
TAGLINE = "당신의 취향을 완벽하게 저격한 그 사람, 사실 스파이라면 누구일까요?"
START = "스파이 색출 시작"

# 봉인 마크: 바깥 고리(문구가 도는 띠) + 점선 고리 + 하트 모양 안에 열쇠 구멍
LOGO = """
<svg class="seal" viewBox="0 0 240 240" role="img" aria-label="나를 사랑한 스파이 봉인 마크">
  <defs><path id="ring" d="M120 120 m-92 0 a92 92 0 1 1 184 0 a92 92 0 1 1 -184 0"/></defs>
  <circle class="ring-o" cx="120" cy="120" r="108"/>
  <circle class="ring-i" cx="120" cy="120" r="76"/>
  <g class="ring-text"><text><textPath href="#ring" startOffset="0">AGENT FILE · 요원 파일 · FOR YOUR EYES ONLY · 당신만 열람 ·</textPath></text></g>
  <path class="heart" pathLength="1"
        d="M120 168 C 84 144, 66 120, 76 98 C 85 79, 108 78, 120 96 C 132 78, 155 79, 164 98 C 174 120, 156 144, 120 168 Z"/>
  <circle class="keyhole" cx="120" cy="114" r="10"/>
  <path class="keyhole" d="M114 118 L110 142 H130 L126 118 Z"/>
</svg>
"""

HTML = f"""
<section class="intro" aria-labelledby="intro-title">
  <div class="sheet">
    <p class="file-no">FILE No. 0214 · 열람 등급: 당신만</p>
    <div class="logo">{LOGO}<span class="stamp" aria-hidden="true">기밀</span></div>
    <h1 id="intro-title" class="title"><span class="sr">{TITLE}</span><span class="typed" aria-hidden="true"></span><span class="caret" aria-hidden="true"></span></h1>
    <p class="tag">{TAGLINE}</p>
    <ol class="steps" aria-label="진행 순서">
      <li><b>01</b> 취향 심문</li><li><b>02</b> 전문가 색출 회의</li><li><b>03</b> 기밀 파일 열람</li>
    </ol>
    <button type="button" class="go">{START}</button>
    <p class="skip-hint" aria-hidden="true">화면을 누르면 바로 넘어가요</p>
  </div>
</section>
"""

CSS = FONTS + (STYLES / "tokens.css").read_text(encoding="utf-8").replace(":root", ":host") + """
:host { display: block; width: 100%; min-width: 0; }
.intro { display: grid; place-items: center; min-height: min(78vh, 46rem); padding: var(--space-lg) 0; color: var(--color-ink);
  font: 400 var(--text-md)/1.6 var(--font-body); }
.sheet { position: relative; display: grid; justify-items: center; gap: var(--space-md); width: 100%; max-width: 36rem; text-align: center;
  animation: drop 700ms var(--ease-out) both; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.file-no { margin: 0; font-size: var(--text-sm); color: var(--color-muted); animation: fade 400ms var(--ease-out) 300ms both; }

/* the seal: rings and heart are drawn in ink, then the stamp lands on it */
.logo { position: relative; width: min(15rem, 62vw); aspect-ratio: 1; }
.seal { width: 100%; height: 100%; overflow: visible; }
.ring-o, .ring-i { fill: none; stroke: var(--color-ink); }
.ring-o { stroke-width: 3; stroke-dasharray: 680; stroke-dashoffset: 680; animation: draw 900ms var(--ease-in-out) 350ms forwards; }
.ring-i { stroke-width: 1.5; stroke-dasharray: 3 5; opacity: 0; animation: fade 500ms var(--ease-out) 900ms both; }
.ring-text { transform-origin: 120px 120px; animation: fade 600ms var(--ease-out) 1100ms both, spin 60s linear 1700ms infinite; }
.ring-text text { font: 700 13px var(--font-body); fill: var(--color-ink-2); }
.heart { fill: none; stroke: var(--color-accent); stroke-width: 5; stroke-linejoin: round; stroke-linecap: round; stroke-dasharray: 1; stroke-dashoffset: 1;
  animation: draw 900ms var(--ease-in-out) 900ms forwards, fill-in 400ms var(--ease-out) 1750ms forwards; }
.keyhole { fill: var(--color-paper); opacity: 0; animation: fade 300ms var(--ease-out) 1900ms both; }
.stamp { position: absolute; right: -6%; bottom: 8%; padding: var(--space-2xs) var(--space-md);
  font: var(--display-weight) var(--text-2xl)/1.1 var(--font-display); color: var(--color-accent);
  background: color-mix(in oklch, var(--color-paper) 60%, transparent);
  box-shadow: inset 0 0 0 3px var(--color-accent), inset 0 0 0 6px var(--color-paper), inset 0 0 0 7px var(--color-accent);
  transform: rotate(-14deg); animation: slam 560ms cubic-bezier(0.2, 1.4, 0.4, 1) 2150ms both; }
.logo { animation: thump 320ms var(--ease-out) 2400ms both; }

.title { margin: var(--space-xs) 0 0; min-height: 1.25em; font: var(--display-weight) clamp(2rem, 7vw, 3.2rem)/1.2 var(--font-display);
  color: var(--color-ink); text-wrap: balance; }
.caret { display: inline-block; width: 0.08em; height: 0.9em; margin-left: 0.06em; vertical-align: -0.08em; background: var(--color-ink);
  opacity: 0; }
.typing .caret { opacity: 1; animation: blink 900ms steps(1) infinite; }
.tag { margin: 0; max-width: 30ch; color: var(--color-ink-2); text-wrap: balance; word-break: keep-all; }
.steps { display: flex; flex-wrap: wrap; justify-content: center; gap: var(--space-xs) var(--space-lg); margin: var(--space-xs) 0 0; padding: 0;
  list-style: none; font-size: var(--text-sm); color: var(--color-ink-2); }
.steps b { color: var(--color-accent); margin-right: var(--space-2xs); }
.go { margin-top: var(--space-sm); min-height: 56px; min-width: min(18rem, 100%); padding: var(--space-sm) var(--space-xl); border: 0; border-radius: 2px;
  cursor: pointer; background: var(--color-accent); color: var(--color-accent-ink); font: var(--display-weight) var(--text-xl)/1.1 var(--font-display);
  box-shadow: 0 0 0 3px var(--color-paper), 0 0 0 5px var(--color-accent);
  transition: background-color var(--dur-micro) var(--ease-out), transform var(--dur-micro) var(--ease-out); }
.go:hover:not(:disabled) { background: var(--color-accent-deep); }
.go:active:not(:disabled) { background: var(--color-accent-deep); transform: translateY(1px) rotate(-1deg); }
.go:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 6px; }
.go:disabled { cursor: progress; opacity: 0.7; }
.skip-hint { margin: 0; font-size: var(--text-sm); color: var(--color-muted); }

/* staged reveal: hidden until the intro reaches them (or the viewer skips) */
.tag, .steps, .go { opacity: 0; transform: translateY(10px); transition: opacity 420ms var(--ease-out), transform 420ms var(--ease-out); }
.ready .tag, .ready .steps, .ready .go { opacity: 1; transform: none; }
.ready .steps { transition-delay: 160ms; }
.ready .go { transition-delay: 320ms; animation: nudge 2.4s var(--ease-in-out) 1.6s infinite; }
.ready .skip-hint { visibility: hidden; }
.skipped * { animation-delay: 0ms !important; animation-duration: 1ms !important; }
.skipped .ring-text { animation: none; opacity: 1; }

@keyframes drop { from { opacity: 0; transform: translateY(-24px) rotate(-1.5deg); } to { opacity: 1; transform: none; } }
@keyframes fade { from { opacity: 0; } to { opacity: 1; } }
@keyframes draw { to { stroke-dashoffset: 0; } }
@keyframes fill-in { to { fill: var(--color-accent); } }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes slam { from { opacity: 0; transform: scale(3) rotate(-30deg); } 60% { opacity: 1; transform: scale(0.92) rotate(-12deg); }
  to { opacity: 1; transform: rotate(-14deg); } }
@keyframes thump { 0%, 100% { transform: none; } 35% { transform: translateY(4px) scale(0.985); } 70% { transform: translate(-2px, -1px); } }
@keyframes blink { 50% { opacity: 0; } }
@keyframes nudge { 0%, 88%, 100% { transform: none; } 92% { transform: rotate(-2deg); } 96% { transform: rotate(1.5deg); } }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
  .ring-o, .heart { stroke-dashoffset: 0; } .heart { fill: var(--color-accent); }
  .ring-i, .keyhole, .ring-text, .stamp { opacity: 1; }
}
"""

JS = r"""
export default function (component) {
  const { data, parentElement } = component;
  const root = parentElement.querySelector('.intro');
  if (!root) return;
  root._cmp = component;
  if (root.dataset.on) return;          // 다시 실행돼도 애니메이션을 처음부터 돌리지 않음
  root.dataset.on = '1';

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const title = (data && data.title) || '';
  const typed = root.querySelector('.typed'), h1 = root.querySelector('.title'), go = root.querySelector('.go');
  let timer = null, i = 0, done = false;

  function ready() {
    if (done) return; done = true;
    clearInterval(timer); typed.textContent = title; h1.classList.remove('typing');
    root.classList.add('ready');
  }
  function type() {
    h1.classList.add('typing');
    timer = setInterval(() => { i += 1; typed.textContent = title.slice(0, i); if (i >= title.length) { setTimeout(ready, 250); clearInterval(timer); } }, 90);
  }
  if (reduce) ready(); else setTimeout(() => { if (!done) type(); }, 2700);

  // 화면을 누르거나 키를 누르면 바로 끝 장면으로
  const skip = (e) => { if (done || (e && e.target === go)) return; root.classList.add('skipped'); ready(); };
  root.addEventListener('pointerdown', skip);
  root.addEventListener('keydown', skip);

  go.onclick = () => {
    if (!done) { root.classList.add('skipped'); ready(); }
    go.disabled = true; go.textContent = '수사 파일 여는 중…';
    root._cmp.setTriggerValue('action', 'start');
  };
}
"""

_component = st.components.v2.component("spy_intro", html=HTML, css=CSS, js=JS)


def intro_view() -> str | None:
    """시작 화면. '스파이 색출 시작'을 누르면 'start'."""
    result = _component(data={"title": TITLE}, key="intro", on_action_change=lambda: None)
    return getattr(result, "action", None)
