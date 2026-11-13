"""나를 사랑한 스파이 — Streamlit 화면 (HITL 포함). 디자인: 기밀 문서 테마 (src/styles/).

실행:  streamlit run src/app.py
흐름:  ① 공통 설문 → ② 추가 심문(⏸ interrupt) → ③ 판결 진행 엿보기 + 열람 승인(⏸ interrupt) → ④ 기밀 파일
"""

from __future__ import annotations

import sys
import uuid
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # `streamlit run src/app.py` 에서도 src 패키지 import

import streamlit as st  # noqa: E402
from langgraph.types import Command  # noqa: E402

from src.agent import EXPERT_NODES, GRAPH, final_profile  # noqa: E402
from src.avatar import avatar_data_uri  # noqa: E402
from src.card import FONTS, STYLES, render_card, standalone_html  # noqa: E402
from src.card_view import card_view  # noqa: E402
from src.debate_view import debate_view  # noqa: E402
from src.intro_view import intro_view  # noqa: E402

st.set_page_config(page_title="나를 사랑한 스파이", page_icon=":material/fingerprint:", layout="centered")

# 기밀 문서 테마: 토큰 → 기본 규칙 → 화면 규칙 순서로 한 번에 주입
_STYLE = FONTS + "".join((STYLES / f).read_text(encoding="utf-8") for f in ("tokens.css", "base.css", "app.css"))
st.html(f"<style>{_STYLE}</style>")

PROGRESS = {
    "load_questions": "공통 질문을 불러왔어요 (MCP)",
    "guard_input": "입력 검사를 마쳤어요 (개인정보, 인젝션)",
    "parse_survey": "당신의 파일을 정리했어요",
    "gen_questions": "심문관이 추가 질문을 준비했어요",
    "ask_questions": "당신 주변의 수상한 인물 정보를 수집했어요",
    "profiler": "범죄 프로파일러가 출몰 기록을 풀었어요",
    "stylist": "패션 스타일리스트가 복장 단서를 보탰어요",
    "situational_expert": "상황별 전문가가 마음의 단서를 보탰어요",
    "guard_output": "출력 검사를 마쳤어요",
    "approve": "열람 처리를 마쳤어요",
}
# 위 메시지는 단계가 '끝난 뒤' 찍히므로, 스피너 옆 제목줄에는 바로 다음에 '돌고 있는' 단계를 보여 줌
RUNNING_NEXT = {
    "load_questions": "입력을 검사하는 중이에요…",
    "guard_input": "당신의 파일을 정리하는 중이에요…",
    "parse_survey": "심문관이 추가 질문을 준비하는 중이에요…",
    "ask_questions": "색출 팀장이 출몰 DB와 패션 DB를 조사하는 중이에요… (1분쯤 걸려요)",
}

# 설문은 한 화면에 한 문항씩. 순서만 여기서 정하고 질문 목록 자체는 MCP 서버가 정함
SURVEY_ORDER = ("gender", "mbti", "mood", "fashion", "heart", "weekend", "contact", "pet", "place", "taste")
NICKNAME_STEP = {"key": "nickname", "question": "당신을 뭐라고 부를까요?", "type": "text",
                 "hint": "예: 민지 (비워 둬도 돼요)", "max": 20}

ss = st.session_state
ss.setdefault("phase", "intro")  # 처음엔 시작 화면 → '내 주변 스파이 찾기'를 누르면 설문
ss.setdefault("thread", str(uuid.uuid4()))
ss.setdefault("pending", None)  # 현재 interrupt 값
ss.setdefault("card", None)
ss.setdefault("nickname", "")
ss.setdefault("step", 0)             # 설문 몇 번째 문항인지
ss.setdefault("step_dir", "fwd")     # 넘어온 방향 (애니메이션 방향)
ss.setdefault("ans", {})             # 설문 응답 (문항을 넘겨도 유지)


def cfg() -> dict:
    return {"configurable": {"thread_id": ss.thread}}


def run(payload, label: str) -> None:
    """그래프를 실행하면서 노드 진행 상황을 보여주고, interrupt 를 만나면 멈춥니다."""
    ss.pending = None
    answered = 0  # 이번 실행에서 답한 전문가 수
    with st.status(label, expanded=True) as status:
        for chunk in GRAPH.stream(payload, cfg(), stream_mode="updates"):
            for node, update in chunk.items():
                if node == "__interrupt__":
                    ss.pending = update[0].value
                elif node == "moderator" and update:  # 사회자(LLM Supervisor)가 누구를 불렀는지, 판결문을 썼는지
                    who = update.get("next_expert")
                    st.write(f"색출 팀장이 {who}을(를) 불렀어요" if who else "색출 팀장이 세 전문가의 단서로 판결문을 썼어요")
                    status.update(label=f"{who}이(가) 답하는 중이에요…" if who else "판결문을 검사하는 중이에요…")
                    answered = 0 if who else answered
                elif node in PROGRESS and update is not None:
                    st.write(PROGRESS[node])
                    if node in EXPERT_NODES:  # 세 번째 답이 끝나면 사회자는 판결문을 씀
                        answered += 1
                        status.update(label="색출 팀장이 당신의 스파이에 대한 보고서를 작성 중이에요…" if answered >= 3
                                      else "색출 팀장이 다음 전문가를 고르는 중이에요…")
                    elif node in RUNNING_NEXT:
                        status.update(label=RUNNING_NEXT[node])
        status.update(label="완료", state="complete", expanded=False)
    values = GRAPH.get_state(cfg()).values
    if values.get("refusal"):
        ss.phase = "refused"
    elif ss.pending and ss.pending["type"] == "questions":
        ss.phase = "questions"
    elif ss.pending and ss.pending["type"] == "approve":
        ss.phase = "approve"
    elif values.get("approved"):
        ss.phase = "card"
    else:
        ss.phase = "covered"


def make_card() -> str:
    values = GRAPH.get_state(cfg()).values
    p = final_profile(values)
    return render_card(p, avatar_data_uri(p), ss.nickname)


def reset() -> None:
    for k in ("phase", "thread", "pending", "card", "step", "step_dir", "ans"):
        ss.pop(k, None)
    ss.phase = "form"  # 다시 할 때는 시작 화면 없이 바로 설문으로


@st.cache_resource(show_spinner="공통 질문을 불러오는 중 (MCP)…")
def questions() -> list[dict]:
    try:
        from src.questions import load_questions
        return list(load_questions())
    except Exception:
        import json
        return json.loads((Path(__file__).resolve().parents[1] / "data" / "questions.json").read_text(encoding="utf-8"))


def survey_steps() -> list[dict]:
    """닉네임 + MCP 공통 질문을 정해 둔 순서로 (모르는 새 질문은 뒤에 붙임)."""
    by_key = {q["key"]: q for q in questions()}
    ordered = [by_key[k] for k in SURVEY_ORDER if k in by_key]
    return [NICKNAME_STEP, *ordered, *(q for k, q in by_key.items() if k not in SURVEY_ORDER)]


def _sync_answers() -> None:
    """화면에서 사라질 위젯 값(w_*)을 ss.ans 에 옮겨 둔다. 문항을 넘겨도 답이 남도록."""
    for k in list(ss.keys()):
        if isinstance(k, str) and k.startswith("w_"):
            ss.ans[k[2:]] = ss[k]


def go(delta: int) -> None:
    _sync_answers()
    ss.step = max(0, ss.step + delta)
    ss.step_dir = "fwd" if delta > 0 else "back"


def _pick(label: str, opts: list[str], key: str, captions: list[str] | None = None) -> str | None:
    cur = ss.ans.get(key)
    # 설명이 붙은 보기는 한 줄에 하나씩 세로로 (가로로 두면 설명이 좁게 접힘)
    v = st.radio(label, opts, index=opts.index(cur) if cur in opts else None, key=f"w_{key}",
                 horizontal=not captions, captions=captions, label_visibility="collapsed")
    ss.ans[key] = v
    return v


def _captions(q: dict) -> list[str] | None:
    """보기별 설명. 공통(captions) 또는 성별별(details: 스파이 성별 = 사용자와 반대 성별 기준)."""
    by_opt = q.get("captions")
    if q.get("details"):
        spy = {"여성": "남성", "남성": "여성"}.get(ss.ans.get("gender") or "")
        by_opt = q["details"].get(spy) or by_opt
    return [by_opt.get(o, "") for o in q["options"]] if by_opt else None


def ask_step(q: dict) -> bool:
    """문항 하나를 위젯으로 그리고, 답이 '다음'으로 넘어가도 될 만큼 채워졌는지 돌려줌."""
    k = q["key"]
    if q["type"] == "choice":
        return _pick(q["question"], q["options"], k, _captions(q)) is not None
    if q["type"] == "mbti":
        cols = st.columns(4)
        letters = []
        for i, (c, pair) in enumerate(zip(cols, q["options"])):
            with c:
                opts, cur = pair.split("/"), ss.ans.get(f"mbti_{i}")
                letters.append(st.radio(pair, opts, index=opts.index(cur) if cur in opts else None,
                                        key=f"w_mbti_{i}", horizontal=True))
                ss.ans[f"mbti_{i}"] = letters[-1]
        unknown = st.checkbox("MBTI를 잘 모르겠어요", value=bool(ss.ans.get("mbti_unknown")), key="w_mbti_unknown")
        ss.ans["mbti_unknown"] = unknown
        ss.ans["mbti"] = "" if unknown or not all(letters) else "".join(letters)
        return unknown or all(letters)
    ss.ans[k] = st.text_input(q["question"], value=ss.ans.get(k, ""), max_chars=q.get("max", 60),
                              placeholder=q.get("hint", ""), key=f"w_{k}", label_visibility="collapsed")
    return True


def track_html(i: int, n: int) -> str:
    segs = "".join(f'<i class="{"on" if j < i else "now" if j == i else ""}"></i>' for j in range(n))
    return f'<div class="survey-top"><div class="survey-track" aria-hidden="true">{segs}</div><p class="survey-count">{i + 1} / {n}</p></div>'


# ── ⓪ 시작 화면 (로고 애니메이션) ───────────────────────────────────────────
if ss.phase == "intro":
    if intro_view() == "start":
        ss.phase = "form"
        st.rerun()
    st.stop()

with st.container(key="masthead"):
    st.title("나를 사랑한 스파이")
    st.caption("당신의 취향을 완벽하게 저격한 그 사람, 사실 스파이라면 누구일까요?")

# ── ① 공통 설문 ─────────────────────────────────────────────────────────────
if ss.phase == "form":
    steps = survey_steps()
    ss.step = min(ss.step, len(steps) - 1)
    q = steps[ss.step]
    last = ss.step == len(steps) - 1
    st.html(track_html(ss.step, len(steps)))
    # 문항마다 새 컨테이너 key → 넘길 때마다 들어오는 애니메이션이 다시 재생됨 (방향은 step_dir)
    with st.container(key=f"step-{ss.step}-{ss.step_dir}"):
        st.html(f'<div class="step-no">{ss.step + 1:02d}</div><h2 class="step-q">{escape(q["question"])}</h2>')
        answered = ask_step(q)
    c1, c2 = st.columns(2)
    c1.button("이전", use_container_width=True, disabled=ss.step == 0, on_click=go, args=(-1,))
    if not last:
        c2.button("다음", type="primary", use_container_width=True, disabled=not answered, on_click=go, args=(1,))
    elif c2.button("심문 시작하기", type="primary", use_container_width=True, disabled=not answered):
        _sync_answers()
        ss.nickname = str(ss.ans.get("nickname", "")).strip()
        answers = {s["key"]: ss.ans.get(s["key"]) or "" for s in steps if s["key"] != "nickname"}
        run({"mode": "ui", "answers": answers, "nickname": ss.nickname, "trace": [], "contexts": []},
            "심문관이 당신의 파일을 검토하는 중…")
        st.rerun()

# ── ② 추가 심문 (interrupt) ─────────────────────────────────────────────────
elif ss.phase == "questions":
    st.subheader("추가 심문")
    st.caption("입력 검사를 통과했어요. 심문관이 두 가지를 더 묻습니다. 솔직할수록 정확한 요원이 나와요.")
    qs = ss.pending["questions"]
    with st.form("custom", border=False):
        replies = {}
        for i, q in enumerate(qs):
            with st.container(key=f"interro-{i}"):
                st.html(f'<div class="interro-no">{i + 1:02d}</div><p class="interro-q">{escape(q["question"])}</p>')
                pick = st.radio("선택", [*q["options"], "직접 입력"], key=f"c_{i}", horizontal=True,
                                label_visibility="collapsed")
                free = st.text_input("직접 입력", key=f"cf_{i}", max_chars=60,
                                     placeholder="'직접 입력'을 골랐다면 여기에 적어 주세요")
            replies[q["question"]] = free.strip() if pick == "직접 입력" else pick
        go = st.form_submit_button("색출 회의 소집하기", type="primary", use_container_width=True)
    if go:
        run(Command(resume=replies), "색출 회의 진행 중… 전문가 세 명이 토론하고 있어요 (30~60초)")
        st.rerun()

# ── ③ 판결 진행 엿보기 + 열람 승인 (interrupt) ─────────────────────────────────
elif ss.phase in ("approve", "covered"):
    values = GRAPH.get_state(cfg()).values
    prof = values.get("profile", {})
    # 전문가가 한 사람씩 말하는 대화 화면. 판결 장면의 판결 이유 바로 아래에 열람 결정 패널이 붙어 있음
    action = debate_view(values.get("minutes", []), prof.get("verdict_reason", ""),
                         key=ss.thread, phase=ss.phase, start_at_end=ss.phase == "covered")
    if action == "open":
        run(Command(resume="open"), "기밀 파일 여는 중…")
        st.rerun()
    elif action == "cover":
        run(Command(resume="cover"), "파일을 덮는 중…")
        st.rerun()
    elif action == "reopen":
        ss.phase = "card"
        st.rerun()
    elif action == "restart":
        reset()
        st.rerun()

# ── ④ 기밀 파일 ─────────────────────────────────────────────────────────────
elif ss.phase == "card":
    if ss.card is None:
        with st.spinner("요원 사진을 현상하는 중…"):
            ss.card = make_card()
    p = final_profile(GRAPH.get_state(cfg()).values)
    card_view(ss.card, key=ss.thread)  # 신상부터 보여 주고 '다음'으로 한 장씩 펼침
    st.write("")
    c1, c2 = st.columns(2)
    c1.download_button("기밀 문서 저장 (HTML)", standalone_html(ss.card, f"CODENAME {p.codename}"),
                       file_name=f"spy_{p.codename.replace(' ', '_')}.html", mime="text/html",
                       use_container_width=True)
    if c2.button("다른 스파이 찾기", type="primary", use_container_width=True):
        reset()
        st.rerun()

# ── 거절 ───────────────────────────────────────────────────────────────────
elif ss.phase == "refused":
    st.error(GRAPH.get_state(cfg()).values.get("refusal", ""))
    if st.button("처음부터", type="primary"):
        reset()
        st.rerun()

# ── 데모용: 그래프 trace ─────────────────────────────────────────────────────
if ss.phase != "form":
    with st.expander("그래프 trace 보기 (발표·디버깅용)"):
        vals = GRAPH.get_state(cfg()).values
        st.json({"contexts": vals.get("contexts", []), "trace": vals.get("trace", [])}, expanded=False)
