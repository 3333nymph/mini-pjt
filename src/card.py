"""'기밀 문서' 결과 카드(HTML) — 기밀 문서 테마 (마닐라 서류철 위 타자 친 서류, 빨간 도장, 손글씨 쪽지).

카드 CSS 는 tokens.css 를 함께 싣기 때문에 Streamlit 안(st.html)과 저장한 HTML 파일 모두 같은 모양으로 보입니다.
"""

from __future__ import annotations

import random
from datetime import date
from html import escape
from pathlib import Path

from src.schema import SpyProfile

STYLES = Path(__file__).resolve().parent / "styles"
FONTS = ("@import url('https://fonts.googleapis.com/css2?family=Special+Elite"
         "&family=Courier+Prime:wght@400;700&family=Nanum+Gothic+Coding:wght@400;700"
         "&family=Nanum+Myeongjo:wght@800&family=Nanum+Pen+Script&display=swap');")

# Hallmark 스탬프는 CSS 첫 줄이어야 해서 FONTS(@import) 앞에 붙입니다 (주석은 @import 앞에 와도 됩니다)
CARD_STAMP = ("/* Hallmark · component: the dossier card · theme: custom (by request: manila paper, a red TOP SECRET stamp) · "
              "signature: the TOP SECRET stamp, the taped-in photo and the spy's handwritten note · v2.0.0 */\n")

CARD_CSS = """
.dossier {
  position: relative; isolation: isolate; max-width: 46rem; margin: 0 auto; padding: var(--space-xl) var(--space-xl) var(--space-2xl);
  background: var(--color-paper); color: var(--color-ink); font: 400 var(--text-md)/1.6 var(--font-body);
  box-shadow: var(--shadow-sheet); border-radius: var(--radius-card); box-sizing: border-box; font-synthesis: none;
}
.dossier *, .dossier *::before, .dossier *::after { box-sizing: border-box; }
.dossier::after { content: ""; position: absolute; inset: 0; z-index: -1; pointer-events: none; opacity: var(--texture-opacity);
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='g'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 9 -4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23g)'/%3E%3C/svg%3E") 0 0 / 200px; }

.dossier .head { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: var(--space-md); align-items: start;
  padding-bottom: var(--space-md); border-bottom: var(--rule-bar) double var(--color-ink); }
.dossier .codename { margin: 0; font: 400 var(--text-3xl)/1.1 var(--font-display); letter-spacing: var(--tracking-display);
  overflow-wrap: break-word; min-width: 0; color: var(--color-ink); text-wrap: balance; }
.dossier .agency { margin: var(--space-2xs) 0 0; color: var(--color-ink-2); }
.dossier .stamps { display: grid; justify-items: end; gap: var(--space-sm); padding-top: var(--space-2xs); }
.dossier .stamp { padding: var(--space-2xs) var(--space-sm); font: 400 var(--text-lg)/1.1 var(--font-display); white-space: nowrap; }
.dossier .stamp.p2 { color: var(--color-accent); transform: rotate(-8deg); text-transform: uppercase;
  box-shadow: inset 0 0 0 2px var(--color-accent), inset 0 0 0 4px var(--color-paper), inset 0 0 0 5px var(--color-accent); }
.dossier .stamp.p1 { color: var(--color-accent-2); transform: rotate(5deg); box-shadow: inset 0 0 0 2px var(--color-accent-2); }

.dossier .meta { display: flex; flex-wrap: wrap; gap: var(--space-2xs) var(--space-lg); margin: var(--space-sm) 0 0; padding: var(--space-xs) 0;
  border-bottom: var(--rule-hair) dotted var(--color-rule); font-size: var(--text-sm); }
.dossier .meta div { display: flex; gap: var(--space-xs); }
.dossier .meta dt { font-weight: 700; }
.dossier .meta dd { margin: 0; font-variant-numeric: tabular-nums; }

.dossier .profile { display: grid; grid-template-columns: minmax(0, 11rem) minmax(0, 1fr); gap: var(--space-xl); margin-top: var(--space-xl); }
.dossier .photo { position: relative; aspect-ratio: 1; max-width: 100%; padding: var(--space-xs); background: var(--color-paper);
  box-shadow: var(--shadow-photo), inset 0 0 0 1px var(--color-rule); transform: rotate(-2.5deg); align-self: start; }
.dossier .photo::before { content: ""; position: absolute; top: calc(var(--space-sm) * -1); left: 50%; width: 5.5rem; height: 1.6rem;
  background: var(--color-tape); transform: translateX(-50%) rotate(3deg); pointer-events: none; }
.dossier .photo img { display: block; width: 100%; height: 100%; background: var(--color-paper-2); }
.dossier .facts { margin: 0; }
.dossier .facts div { display: grid; grid-template-columns: minmax(0, 6rem) minmax(0, 1fr); gap: var(--space-sm); padding-block: var(--space-xs); border-bottom: var(--rule-hair) dotted var(--color-rule); }
.dossier .facts dt { font: 700 var(--text-sm)/1.6 var(--font-body); }
.dossier .facts dd { margin: 0; }
.dossier .redact { background: var(--color-ink); color: transparent; cursor: help; transition: color var(--dur-short) var(--ease-out), background-color var(--dur-short) var(--ease-out); }
.dossier .redact:hover, .dossier .redact:focus-visible { background: transparent; color: var(--color-ink); }
.dossier .redact:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }

/* the two typed boxes: compatibility, and the flutter risk inked red */
.dossier .bill { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: var(--space-md); margin-top: var(--space-xl); }
.dossier .bill .pass { padding: var(--space-md) var(--space-lg); box-shadow: inset 0 0 0 1.5px var(--color-ink); min-width: 0; }
.dossier .bill .lbl { font: 700 var(--text-sm) var(--font-body); }
.dossier .bill .fig { font: 400 3rem/1 var(--font-display); font-variant-numeric: tabular-nums; margin-top: var(--space-xs); white-space: nowrap; color: var(--color-ink); }
.dossier .bill .pass.p2 .fig { color: var(--color-accent); }
.dossier .bill .fig small { font-size: var(--text-xl); }

.dossier h2 { margin: var(--space-xl) 0 var(--space-sm); padding-bottom: var(--space-2xs); border-bottom: var(--rule-hair) solid var(--color-ink);
  font: var(--display-weight) var(--text-xl)/1.25 var(--font-display); color: var(--color-ink); text-wrap: balance; }
.dossier p { margin: 0; max-width: 62ch; }
.dossier ol { margin: 0; padding-left: var(--space-lg); max-width: 62ch; }
.dossier ol li { padding-block: var(--space-2xs); }
.dossier ol li::marker { font-weight: 700; }

.dossier details { margin-top: var(--space-xl); border-block: var(--rule-hair) solid var(--color-ink); }
.dossier summary { display: flex; flex-wrap: wrap; align-items: baseline; gap: var(--space-xs) var(--space-md); padding-block: var(--space-sm); cursor: pointer; list-style: none; }
.dossier summary::-webkit-details-marker { display: none; }
.dossier summary:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.dossier summary:hover .t { text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 0.2em; }
.dossier summary:active { background: color-mix(in oklab, var(--color-paper-2) 40%, transparent); }
.dossier summary .t { font: var(--display-weight) var(--text-xl)/1.25 var(--font-display); }
.dossier summary .t::before { content: "+ "; }
.dossier details[open] summary .t::before { content: "– "; }
.dossier summary .v { font: 700 var(--text-sm) var(--font-body); color: var(--color-accent); }
.dossier summary .open-hint { font-size: var(--text-sm); color: var(--color-muted); }
.dossier details[open] .open-hint { display: none; }
.dossier .transcript { margin: 0 0 var(--space-sm); }
.dossier .transcript div { display: grid; grid-template-columns: minmax(0, 8rem) minmax(0, 1fr); gap: var(--space-md); padding-block: var(--space-xs); border-bottom: var(--rule-hair) dotted var(--color-rule); }
.dossier .transcript dt { font: 700 var(--text-sm)/1.6 var(--font-body); }
.dossier .transcript dd { margin: 0; }
.dossier .transcript .final { border-bottom: 0; }
.dossier .transcript .final dd { font-weight: 700; }

.dossier .tags { display: flex; flex-wrap: wrap; gap: var(--space-xs); margin: 0; padding: 0; list-style: none; }
.dossier .tags li { padding: var(--space-2xs) var(--space-sm); outline: 1.5px dashed var(--color-ink); outline-offset: -1.5px; font-size: var(--text-sm); }
/* the spy's note: a sticky note in biro, the only handwriting on the page */
.dossier .note { margin: var(--space-2xl) auto 0; max-width: 30rem; padding: var(--space-lg) var(--space-lg) var(--space-md);
  background: var(--color-note); color: var(--color-accent-2); box-shadow: var(--shadow-photo); transform: rotate(-1.5deg);
  font: 400 1.9rem/1.3 var(--font-outlier); }
.dossier .note .from { display: block; margin-top: var(--space-xs); font: 400 var(--text-sm)/1.4 var(--font-body); color: var(--color-accent-2); }
/* the last line, struck as a warning stamp at the foot of the file */
.dossier .foot { display: table; max-width: 100%; margin: var(--space-2xl) auto var(--space-sm); padding: var(--space-sm) var(--space-lg);
  font: var(--display-weight) var(--text-xl)/1.35 var(--font-display); color: var(--color-accent); text-align: center; text-wrap: balance; word-break: keep-all;
  box-shadow: inset 0 0 0 3px var(--color-accent), inset 0 0 0 6px var(--color-paper), inset 0 0 0 7px var(--color-accent);
  transform: rotate(-2deg); }
.dossier .foot-sub { margin: var(--space-md) auto 0; text-align: center; font-size: var(--text-sm); color: var(--color-muted); }

@media (max-width: 40rem) {
  .dossier { padding: var(--space-lg) var(--space-md) var(--space-xl); }
  .dossier .head { grid-template-columns: minmax(0, 1fr); }
  .dossier .stamps { justify-items: start; grid-auto-flow: column; justify-content: start; }
  .dossier .profile { grid-template-columns: minmax(0, 1fr); gap: var(--space-lg); }
  .dossier .photo { width: 11rem; }
  .dossier .bill { grid-template-columns: minmax(0, 1fr); }
}
@media (prefers-reduced-motion: reduce) { .dossier .redact { transition: none; } }
"""

CSS = CARD_STAMP + FONTS + "\n" + (STYLES / "tokens.css").read_text(encoding="utf-8") + CARD_CSS


def _who(p: SpyProfile) -> str:
    if p.species == "사람":
        return f"{escape(p.gender)}, {p.age}세"
    kind = "반려견" if p.species == "강아지" else "반려묘"
    sex = "여아" if p.gender == "여성" else "남아"
    return f"{kind} 요원, {sex}, 사람 나이로 {p.age}세"


def render_card(p: SpyProfile, avatar_src: str, for_user: str = "") -> str:
    e = escape
    file_no = f"{random.randint(100, 999)}-{random.randint(1000, 9999)}"
    clue = e(p.clues[0]) if p.clues else ""
    tags = "".join(f"<li>#{e(t)}</li>" for t in p.taste_keywords)
    target = e(for_user) if for_user else "당신"
    minutes = "".join(f"<div><dt>{e(m.get('who', ''))}</dt><dd>{e(m.get('text', ''))}</dd></div>"
                      for m in p.minutes if m.get("node") != "moderator")  # 사회자 물음은 비공개
    return f"""
<article class="dossier" aria-label="요원 신상 파일">
  <header class="head">
    <div>
      <h1 class="codename">{e(p.codename)}</h1>
      <p class="agency">{e(p.agency)}의 요원 신상 파일</p>
    </div>
    <div class="stamps"><span class="stamp p2">Top secret</span><span class="stamp p1">임무 이탈</span></div>
  </header>
  <dl class="meta">
    <div><dt>파일 번호</dt><dd>{file_no}</dd></div>
    <div><dt>작성일</dt><dd>{date.today():%Y.%m.%d}</dd></div>
    <div><dt>열람 대상</dt><dd>{target}</dd></div>
  </dl>
  <section class="profile">
    <div class="photo"><img src="{avatar_src}" alt="요원 {e(p.alias)}의 사진" width="176" height="176"></div>
    <dl class="facts">
      <div><dt>가명</dt><dd><b>{e(p.alias)}</b> ({_who(p)})</dd></div>
      <div><dt>위장 신분</dt><dd>{e(p.cover_identity)}</dd></div>
      <div><dt>현재 위치</dt><dd>{e(p.where_near_you)}</dd></div>
      <div><dt>원래 임무</dt><dd><span class="redact" tabindex="0" title="마우스를 올리면 보여요">{e(p.original_mission)}</span></dd></div>
      <div><dt>시그니처</dt><dd>{e(p.signature)}</dd></div>
    </dl>
  </section>
  <section class="bill" aria-label="궁합과 설렘 위험도">
    <div class="pass p1"><div class="lbl">{target}와의 궁합</div><div class="fig">{p.compatibility}<small>%</small></div></div>
    <div class="pass p2"><div class="lbl">설렘 위험도</div><div class="fig">{p.danger_level}<small>/5</small></div></div>
  </section>
  <!-- data-reveal: 화면(card_view)에서는 '다음'을 누를 때마다 하나씩 펼침. 저장한 HTML 은 스크립트가 없어 전부 보임 -->
  <section class="part" data-reveal="최초 접촉 기록">
    <h2>최초 접촉 기록</h2>
    <p>{e(p.first_contact)}</p>
  </section>
  <section class="part" data-reveal="수상했던 단서">
    <h2>수상했던 단서</h2>
    <p>{clue}</p>
  </section>
  <section class="part" data-reveal="작전 이탈 보고">
    <h2>작전 이탈 보고</h2>
    <p>{e(p.twist)}</p>
  </section>
  <section class="part last" data-reveal="요원이 남긴 쪽지">
    <blockquote class="note">{e(p.secret_note)}<span class="from">요원이 몰래 남긴 쪽지</span></blockquote>
    <details>
      <summary><span class="t">판결 진행 엿보기</span><span class="v">판결: 스파이 검거</span><span class="open-hint">눌러서 펼치기</span></summary>
      <dl class="transcript">{minutes}<div class="final"><dt>색출 팀장 판결</dt><dd>스파이 검거. {e(p.verdict_reason)}</dd></div></dl>
    </details>
    <h2>분석된 취향</h2>
    <ul class="tags">{tags}</ul>
  </section>
  <section class="part finale" data-reveal="열람 완료">
    <p class="foot">이 문서는 열람 후 자동으로 설렘이 발생합니다.</p>
    <p class="foot-sub">열람 확인 · 설렘 자동 실행 완료</p>
  </section>
</article>
"""


def standalone_html(card: str, title: str) -> str:
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title>
<meta name="description" content="나를 사랑한 스파이가 남긴 요원 신상 파일">
<style>{CSS}
html, body {{ overflow-x: clip; }}
body {{ margin: 0; padding: var(--space-xl) var(--space-md); background: var(--color-paper-2); }}</style></head>
<body>{card}</body></html>"""
