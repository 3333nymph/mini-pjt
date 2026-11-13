"""기밀 파일 화면 — 신상(사진·가명·궁합) 아래에서 기록을 카드 한 장씩 넘겨 보는 컴포넌트.

설문 화면처럼 진행 막대와 'N / 5'를 두고, 첫 장(최초 접촉 기록)을 바로 크게 보여 준다.
'다음'을 누를 때마다 수상했던 단서 → 작전 이탈 보고 → 요원이 남긴 쪽지 → 열람 완료
("이 문서는 열람 후 자동으로 설렘이 발생합니다." 도장)로 넘어간다.
저장용 HTML(standalone_html)에는 스크립트가 없으므로 전부 펼쳐진 채로 보인다.

보안: 카드 HTML 은 render_card 가 모든 LLM 값을 html.escape 한 결과라 innerHTML 로 넣어도 안전하다.
"""

from __future__ import annotations

import streamlit as st

from src.card import CARD_CSS

HTML = '<div class="card-host"></div>'

DECK_CSS = """
:host { display: block; width: 100%; min-width: 0; }
.card-host { width: 100%; min-width: 0; }

/* the deck: one record card at a time, under the profile */
.deck { margin-top: var(--space-xl); }
.deck-top { display: flex; align-items: center; gap: var(--space-md); margin-bottom: var(--space-sm); }
.deck-track { flex: 1; display: flex; gap: var(--space-2xs); }
.deck-track i { flex: 1; height: 4px; background: var(--color-rule); transform-origin: left; }
.deck-track i.seen { background: var(--color-ink-2); }
.deck-track i.now { background: var(--color-accent); animation: grow 420ms var(--ease-out) both; }
.deck-count { margin: 0; font: 700 var(--text-sm)/1 var(--font-body); color: var(--color-ink-2); }

.deck-stage { position: relative; min-height: 18rem; padding: var(--space-xl) var(--space-xl) var(--space-lg); border-radius: 2px;
  background: var(--color-paper); box-shadow: inset 0 0 0 1px var(--color-rule), var(--shadow-sheet); overflow: hidden; }
.deck .part { display: none; word-break: keep-all; overflow-wrap: break-word; }
.deck .part.on { display: block; }
.deck .part.on.fwd { animation: from-right 420ms var(--ease-out) both; }
.deck .part.on.back { animation: from-left 420ms var(--ease-out) both; }
.deck .part > h2:first-child { margin: 0 0 var(--space-md); font-size: var(--text-xl); }
.deck .part > p, .deck .part li { font-size: var(--text-lg); line-height: 1.75; }
.deck .part.on ol li { animation: rise 460ms var(--ease-out) both; }
.deck .part.on ol li:nth-child(1) { animation-delay: 220ms; }
.deck .part.on ol li:nth-child(2) { animation-delay: 440ms; }
.deck .part.on ol li:nth-child(3) { animation-delay: 660ms; }
/* the note card: the sticky note is slapped on first, the rest settles in under it */
.deck .part.last .note { margin-top: var(--space-sm); }
.deck .part.last.on .note { animation: stick 720ms cubic-bezier(0.2, 1.4, 0.4, 1) both; }
.deck .part.last.on > :not(.note) { animation: rise 520ms var(--ease-out) 650ms both; }
/* the finale: the warning stamp lands, the heart skips twice, then the receipt line */
.deck .finale { text-align: center; }
.deck .finale .foot { margin: var(--space-xl) auto var(--space-sm); font-size: var(--text-2xl); }
.deck .finale.on { animation: none; }
.deck .finale.on .foot { animation: slam 620ms cubic-bezier(0.2, 1.4, 0.4, 1) 200ms both, throb 760ms var(--ease-in-out) 1000ms 2; }
.deck .finale.on .foot-sub { animation: rise 420ms var(--ease-out) 1900ms both; }

.deck-nav { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 2fr); gap: var(--space-md); margin-top: var(--space-lg); }
.deck-nav button { min-height: 52px; padding: var(--space-sm) var(--space-md); border: 0; border-radius: 2px; cursor: pointer;
  transition: background-color var(--dur-micro) var(--ease-out), color var(--dur-micro) var(--ease-out), transform var(--dur-micro) var(--ease-out); }
.deck-prev { background: transparent; color: var(--color-ink); font: 700 var(--text-md)/1.1 var(--font-body); box-shadow: inset 0 0 0 1.5px var(--color-ink); }
.deck-prev:hover:not(:disabled) { background: var(--color-paper-2); }
.deck-prev:active:not(:disabled) { background: var(--color-paper-3); transform: translateY(1px); }
.deck-prev:disabled { opacity: 0.35; cursor: not-allowed; }
.deck-next { background: var(--color-accent); color: var(--color-accent-ink); font: var(--display-weight) var(--text-lg)/1.15 var(--font-display);
  box-shadow: 0 0 0 3px var(--color-paper), 0 0 0 5px var(--color-accent); }
.deck-next:hover { background: var(--color-accent-deep); }
.deck-next:active { background: var(--color-accent-deep); transform: translateY(1px) rotate(-0.5deg); }
.deck-nav .done { display: grid; place-items: center; margin: 0; font: 700 var(--text-md)/1.3 var(--font-body); color: var(--color-accent); text-align: center; }
.deck-all { display: block; margin: var(--space-sm) auto 0; min-height: 44px; padding: var(--space-xs); border: 0; background: transparent; cursor: pointer;
  font: 400 var(--text-sm)/1 var(--font-body); color: var(--color-muted); text-decoration: underline; text-underline-offset: 0.2em; }
.deck-all:hover { color: var(--color-ink); }
.deck-all:active { color: var(--color-ink-2); }
.deck button:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 3px; }
[hidden] { display: none !important; }

/* "show everything": the cards stack like the saved file */
.deck.all .deck-top, .deck.all .deck-nav, .deck.all .deck-all { display: none; }
.deck.all .deck-stage { min-height: 0; padding: 0; background: none; box-shadow: none; overflow: visible; }
.deck.all .part { display: block; animation: none; }
.deck.all .part > h2:first-child { margin-top: var(--space-xl); }

@media (max-width: 40rem) {
  .deck-stage { min-height: 15rem; padding: var(--space-lg) var(--space-md); }
  .deck .part > p, .deck .part li { font-size: var(--text-md); }
  .deck .finale .foot { font-size: var(--text-xl); }
  .deck-nav { grid-template-columns: minmax(0, 1fr) minmax(0, 1.6fr); gap: var(--space-sm); }
  .deck-next { font-size: var(--text-md); }
}

@keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes from-right { from { opacity: 0; transform: translateX(36px); } to { opacity: 1; transform: none; } }
@keyframes from-left { from { opacity: 0; transform: translateX(-36px); } to { opacity: 1; transform: none; } }
@keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
@keyframes stick { from { opacity: 0; transform: translateY(-46px) rotate(-9deg) scale(1.12); }
  65% { opacity: 1; transform: translateY(3px) rotate(0deg) scale(0.98); } to { opacity: 1; transform: rotate(-1.5deg); } }
@keyframes slam { from { opacity: 0; transform: scale(2.6) rotate(-12deg); } 60% { opacity: 1; transform: scale(0.94) rotate(-1deg); }
  to { opacity: 1; transform: rotate(-2deg); } }
@keyframes throb { 0%, 100% { transform: rotate(-2deg) scale(1); } 20% { transform: rotate(-2deg) scale(1.07); }
  40% { transform: rotate(-2deg) scale(1); } 60% { transform: rotate(-2deg) scale(1.04); } }
@media (prefers-reduced-motion: reduce) {
  .deck *, .deck *::before, .deck *::after { animation: none !important; transition: none !important; }
}
"""

JS = r"""
export default function (component) {
  const { data, parentElement } = component;
  const host = parentElement.querySelector('.card-host');
  if (!host || !data) return;
  if (host.dataset.key === data.key) return;   // 다시 실행돼도 보던 장 유지
  host.dataset.key = data.key;
  host.innerHTML = data.html;                  // render_card 가 escape 한 HTML

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const parts = [...host.querySelectorAll('[data-reveal]')];
  if (!parts.length) return;
  const n = parts.length;
  const el = (tag, cls, text) => { const x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; };

  // 신상 정보 바로 아래에 카드 묶음을 만들고 기록들을 그 안으로 옮긴다
  const deck = el('section', 'deck'); deck.setAttribute('aria-label', '요원 기록 카드');
  const top = el('div', 'deck-top'), track = el('div', 'deck-track'), count = el('p', 'deck-count');
  track.setAttribute('aria-hidden', 'true');
  const segs = parts.map(() => el('i'));
  track.append(...segs); top.append(track, count);
  const stage = el('div', 'deck-stage'); stage.setAttribute('aria-live', 'polite');
  parts[0].before(deck);
  parts.forEach((p) => stage.append(p));
  const nav = el('div', 'deck-nav');
  const prev = el('button', 'deck-prev', '이전'); prev.type = 'button';
  const next = el('button', 'deck-next'); next.type = 'button';
  const done = el('p', 'done', '파일 열람을 마쳤어요');
  nav.append(prev, next, done);
  const all = el('button', 'deck-all', '한 번에 모두 펼쳐 보기'); all.type = 'button';
  deck.append(top, stage, nav, all);

  let cur = 0;
  function show(i, dir) {
    cur = i;
    parts.forEach((p) => p.classList.remove('on', 'fwd', 'back'));
    const p = parts[i];
    void p.offsetWidth;                         // 같은 장을 다시 보여 줄 때도 애니메이션 재생
    p.classList.add('on', dir);
    segs.forEach((s, j) => { s.className = j < i ? 'seen' : j === i ? 'now' : ''; });
    count.textContent = `${i + 1} / ${n}`;
    prev.disabled = i === 0;
    const last = i === n - 1;
    next.hidden = last; done.hidden = !last;
    if (!last) next.textContent = '다음: ' + parts[i + 1].dataset.reveal;
  }
  function go(d) {
    const i = Math.max(0, Math.min(n - 1, cur + d));
    if (i === cur) return;
    show(i, d > 0 ? 'fwd' : 'back');
    if (deck.getBoundingClientRect().top < 0) deck.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
  }
  prev.onclick = () => go(-1);
  next.onclick = () => go(1);
  all.onclick = () => { deck.classList.add('all'); };
  show(0, 'fwd');
}
"""

_component = st.components.v2.component("spy_card", html=HTML, css=CARD_CSS + DECK_CSS, js=JS)


def card_view(card_html: str, key: str) -> None:
    """render_card 결과를 신상 + 기록 카드 한 장씩 넘기기로 보여 줌."""
    _component(data={"key": key, "html": card_html}, key=f"card-{key}")
