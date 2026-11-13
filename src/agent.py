"""메인 에이전트 그래프 — 나를 사랑한 스파이.

Supervisor(코드 분기)가 상태를 보고 다음 노드를 정하고, 각 노드는 일을 마치면 Supervisor 로 돌아옵니다.

  load_questions(MCP) → guard_input → parse_survey → gen_questions → ask_questions(⏸)
  → debate(프로파일러 ReAct · 스타일리스트 · 상황별 전문가) → verdict → guard_output → approve(⏸) → END

- mode="ui"  : Streamlit 화면. ⏸ 지점에서 interrupt() 로 사용자 답변·열람 승인을 받습니다.
- mode="api" : POST /query. 한 번에 끝나야 하므로 interrupt 를 건너뜁니다 (맞춤 질문 답 없음 · 열람 자동 승인).
"""

from __future__ import annotations

import json
import operator
import random
import uuid
from typing import Annotated, Any, Literal, TypedDict

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import Field, create_model

from src.guardrails import (REFUSALS, OutfitHallucinationGuard, check_input, check_output, forbidden_mentions,
                            mask_pii, strip_injection)
from src.llm import DATA, get_llm
from src.prompts import (FALLBACK_QUESTIONS, GEN_Q_SYSTEM, MODERATOR_SYSTEM, MODERATOR_TOOLS, PARSE_SYSTEM,
                         PROFILER_SYSTEM, SITUATIONAL, SOFTEN_SYSTEM, VERDICT_SYSTEM, stylist_system)
from src.schema import CustomQuestions, ExpertRemark, ModeratorTurn, SoftenedRemarks, SpyProfile, SpyStory, Survey
from src.tools import TOOLS, build_avatar, find_look, look_items

import os  # noqa: E402

# 반려동물을 키우는 사용자에게 '반려동물 요원'이 나올 확률. 데모용으로 SPY_PET_CHANCE=1 로 띄우면 항상 반려동물 요원
PET_SPY_CHANCE = float(os.getenv("SPY_PET_CHANCE", "0.3"))


# ── 상태 ──────────────────────────────────────────────────────────────────
class SpyState(TypedDict, total=False):
    mode: Literal["api", "ui"]
    question: str                 # API 원문 질의
    answers: dict                 # UI 설문 응답 (key → 값)
    nickname: str
    questions: list               # MCP 에서 받은 공통 질문
    intent: str
    refusal: str
    clean_text: str               # PII 마스킹 · 인젝션 제거 후 텍스트
    survey: dict
    spy_gender: str
    spy_species: str
    custom_questions: list
    custom_answers: dict
    spot: dict
    look: dict
    avatar: dict
    minutes: list                 # 색출 회의 기록 (사회자 물음 + 전문가 답)
    next_question: str            # 사회자가 다음 전문가에게 던진 물음
    next_expert: str              # 사회자가 고른 전문가 이름 (화면 진행 문구용)
    debate_done: bool             # 세 전문가가 모두 답했는지
    gender_random: bool           # 사용자가 성별을 말하지 않아 스파이 성별을 무작위로 정했는지
    mod_notes: list               # 사회자가 전문가를 부른 이유 (판결문에 씀)
    profile: dict
    output_checked: bool
    approved: bool
    trace: Annotated[list, operator.add]
    contexts: Annotated[list, operator.add]


def _t(step: str, inp: Any, out: Any) -> dict:
    s = lambda v: v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)  # noqa: E731
    return {"step": step, "input": s(inp)[:600], "output": s(out)[:900]}


LABELS = {"gender": "성별", "mbti": "MBTI", "mood": "끌리는 분위기", "weekend": "이상적인 주말", "contact": "연락 스타일",
          "fashion": "끌리는 패션", "heart": "심쿵 포인트", "pet": "반려동물", "place": "자주 가는 곳", "taste": "취향 한 줄"}


def _survey_text(state: SpyState) -> str:
    sv = state.get("survey", {})
    lines = [f"- {LABELS[k]}: {v}" for k, v in sv.items() if v and k in LABELS]
    for q, a in (state.get("custom_answers") or {}).items():
        if a:
            lines.append(f"- (추가 심문) {q}: {a}")
    return "\n".join(lines) or "- (응답 거의 없음)"


def _spy_brief(state: SpyState) -> str:
    sp = state["spy_species"]
    if sp == "사람":
        return f"스파이: 사람, {state['spy_gender']}"
    kind = "반려견" if sp == "강아지" else "반려묘"
    sex = "여아" if state["spy_gender"] == "여성" else "남아"
    return f"스파이: 사용자의 {kind}로 위장한 {sp} 요원 ({sex})"


# ── Supervisor ────────────────────────────────────────────────────────────
WORKERS = ("load_questions", "guard_input", "parse_survey", "gen_questions", "ask_questions",
           "moderator", "guard_output", "approve")


def supervisor(state: SpyState) -> Command:
    """(Day 6 · Supervisor) 상태를 보고 다음 담당 노드를 고릅니다. 고정 순서라 LLM 대신 코드로 분기."""
    if not state.get("questions"):
        nxt = "load_questions"
    elif not state.get("intent"):
        nxt = "guard_input"
    elif state.get("refusal") or state.get("approved") is not None:
        nxt = END
    elif not state.get("survey"):
        nxt = "parse_survey"
    elif state.get("custom_questions") is None:
        nxt = "gen_questions"
    elif state.get("custom_answers") is None:
        nxt = "ask_questions"
    elif not state.get("debate_done"):
        nxt = "moderator"   # 색출 회의와 판결문은 사회자(LLM Supervisor)에게 맡김
    elif not state.get("output_checked"):
        nxt = "guard_output"
    else:
        nxt = "approve"
    return Command(goto=nxt)


# ── ① 질문 불러오기 (MCP) ───────────────────────────────────────────────────
def load_questions(state: SpyState) -> dict:
    try:
        from src.questions import load_questions as mcp_load
        qs, src = list(mcp_load()), "mcp:spy-questions/get_questions"
    except Exception as e:  # MCP 서버 실패 시 같은 파일을 직접 읽어 서비스는 계속
        qs, src = json.loads((DATA / "questions.json").read_text(encoding="utf-8")), f"local fallback ({e})"
    return {"questions": qs, "trace": [_t("load_questions", src, [q["question"] for q in qs])]}


# ── 입력 가드레일 ───────────────────────────────────────────────────────────
def guard_input(state: SpyState) -> dict:
    if state.get("mode") == "ui":
        free = " / ".join(str(state.get("answers", {}).get(k, "")) for k in ("place", "taste"))
        text = f"{state.get('nickname', '')} / {free}"
    else:
        text = state.get("question", "")
    masked, pii = mask_pii(text)
    cleaned, inj_regex = strip_injection(masked)
    if state.get("mode") == "ui":  # 폼 응답은 설문이 확실하므로 의도 분류 LLM 은 생략
        intent, inj, reason = "survey", inj_regex, "설문 폼 입력"
    else:
        chk = check_input(masked)
        intent, inj, reason = chk.intent, chk.has_injection or inj_regex, chk.reason
        if intent == "survey" and not cleaned.strip():
            intent = "off_topic"
    out = {"intent": intent, "clean_text": cleaned}
    if intent != "survey":
        out["refusal"] = REFUSALS[intent]
    if state.get("mode") == "ui":  # 폼 자유 입력 칸도 마스킹 · 인젝션 제거
        answers = dict(state.get("answers", {}))
        for k in ("place", "taste"):
            answers[k] = strip_injection(mask_pii(str(answers.get(k, "")))[0])[0]
        out["answers"] = answers
    out["trace"] = [_t("guard_input", text, {"intent": intent, "pii_masked": pii, "injection": inj, "reason": reason})]
    return out


# ── 설문 해석 · 스파이 성별/종 결정 ──────────────────────────────────────────
def _spy_gender(user_gender: str) -> str:
    if user_gender in ("여성", "남성"):
        return "남성" if user_gender == "여성" else "여성"
    return random.choice(["여성", "남성"])


def _spy_species(pet: str) -> str:
    if pet not in ("강아지", "고양이", "둘 다") or random.random() >= PET_SPY_CHANCE:
        return "사람"
    return random.choice(["강아지", "고양이"]) if pet == "둘 다" else pet


def parse_survey(state: SpyState) -> dict:
    if state.get("mode") == "ui":
        a = state.get("answers", {})
        survey = Survey(**{k: a.get(k, "") for k in Survey.model_fields})
        how = "폼 응답 그대로"
    else:
        llm = get_llm("fast", 0.0, 600).with_structured_output(Survey).with_retry(stop_after_attempt=3)
        survey = llm.invoke([("system", PARSE_SYSTEM), ("human", state["clean_text"])])
        how = "LLM 추출 (Haiku)"
    gender, species = _spy_gender(survey.gender), _spy_species(survey.pet)
    return {"survey": survey.model_dump(), "spy_gender": gender, "spy_species": species,
            "gender_random": survey.gender not in ("여성", "남성"),
            "trace": [_t("parse_survey", how, {**survey.model_dump(), "spy_gender": gender, "spy_species": species})]}


# ── ② 맞춤 질문 ────────────────────────────────────────────────────────────


def gen_questions(state: SpyState) -> dict:
    llm = get_llm("talk", 1.0, 800).with_structured_output(CustomQuestions).with_retry(stop_after_attempt=3)
    trace = []
    for attempt in range(3):  # 출력 가드레일에 걸리면 사용자 모르게 다시 생성 (최대 2번)
        qs = [q.model_dump() for q in llm.invoke([("system", GEN_Q_SYSTEM), ("human", _survey_text(state))]).questions]
        verdict = check_output(json.dumps(qs, ensure_ascii=False))
        trace.append(_t("gen_questions", f"attempt {attempt + 1}", qs))
        trace.append(_t("guard_output_questions", "맞춤 질문 검사", verdict.model_dump()))
        if verdict.safe:
            break
    else:
        qs = FALLBACK_QUESTIONS
    return {"custom_questions": qs, "trace": trace}


def ask_questions(state: SpyState) -> dict:
    if state.get("mode") != "ui":
        return {"custom_answers": {}, "trace": [_t("ask_questions", "API 모드", "interrupt 생략 · 맞춤 질문 답 없음")]}
    raw = interrupt({"type": "questions", "questions": state["custom_questions"]})  # (Day 5 · HITL)
    answers = {q: strip_injection(mask_pii(str(a))[0])[0] for q, a in (raw or {}).items()}
    return {"custom_answers": answers, "trace": [_t("ask_questions", "interrupt → 사용자 답변", answers)]}


# ── ③ 색출 회의: 사회자(LLM Supervisor)가 전문가를 한 명씩 불러 답을 모음 ──────────
PROFILER, STYLIST, MODERATOR = "범죄 프로파일러", "패션 스타일리스트", "사회자"
EXPERT_NODES = ("profiler", "stylist", "situational_expert")


def _situ(state: SpyState) -> tuple[str, str, str]:
    """스파이 종에 따라 상황별 전문가 (이름, 아이콘, 시스템 프롬프트)."""
    return SITUATIONAL["사람" if state.get("spy_species", "사람") == "사람" else "반려동물"]


def _expert_names(state: SpyState) -> dict[str, str]:
    return {"profiler": PROFILER, "stylist": STYLIST, "situational_expert": _situ(state)[0]}


def _evidence(state: SpyState) -> str:
    """사회자가 두 DB 에서 조사한 근거 (전문가 모두에게 보여 줌)."""
    spot, look = state.get("spot") or {}, state.get("look") or {}
    lines = []
    if spot:
        lines.append(f"출몰 DB: {spot.get('place')} · 위장 신분 후보 {', '.join(spot.get('covers', []))} · "
                     f"출몰 {spot.get('time')} · {spot.get('behavior')}")
    else:
        lines.append("출몰 DB: 조회 안 함 (자주 가는 곳 미응답)")
    if look:
        present = look_items(state.get("avatar") or look.get("avatar", {}), state.get("spy_species", "사람"))
        lines.append(f"패션 DB: {look.get('note')} · 실제 소품 {', '.join(present)}")
    return "\n".join(lines)


def _transcript(state: SpyState) -> str:
    log = "\n".join(f"{m['icon']} {m['who']}: {m['text']}" for m in state.get("minutes", []) if m.get("node") != "moderator")
    return (f"{_spy_brief(state)}\n사용자 응답:\n{_survey_text(state)}\n\n[사회자 조사]\n{_evidence(state)}\n\n"
            f"[색출 회의 기록]\n{log or '(아직 없음)'}")


def _ask(state: SpyState) -> str:
    return (f"{_transcript(state)}\n\n사회자의 비공개 메모 (이 점을 짚어 주세요): {state.get('next_question', '')}\n"
            "이제 당신 차례입니다. 앞 전문가의 단서를 이어받아 말하세요.")


def _minute(state: SpyState, who: str, icon: str, text: str, node: str) -> list:
    return [*state.get("minutes", []), {"who": who, "icon": icon, "text": text, "node": node}]


_SLUG = {"profiler": "profiler", "stylist": "stylist", "situational": "situational_expert"}


def moderator(state: SpyState) -> Command:
    """(Day 6 · Supervisor) 사회자 LLM 이 다음에 부를 전문가와 물음을 정함. 세 명이 다 답하면 판결로.
    첫 차례에는 도구로 출몰 DB · 패션 DB 를 먼저 읽고(ReAct) 아바타를 정한 뒤 고른다. 부르는 순서는 정해져 있지 않다."""
    names = _expert_names(state)
    spoken = [m.get("node") for m in state.get("minutes", [])]
    left = [n for n in EXPERT_NODES if n not in spoken]
    if not left:  # 세 명이 다 답함 → 사회자가 모은 단서와 자기 메모로 판결문을 직접 씀
        story = _make_story(state)
        return Command(goto="supervisor", update={
            "debate_done": True, "next_expert": "", "profile": story.model_dump(),
            "trace": [_t("moderator", "세 전문가 답변 완료", "→ 사회자가 판결문 작성"),
                      _t("verdict", "사회자 판결 · 요원 파일 작성", story.model_dump())]})
    labels = {"profiler": "profiler", "stylist": "stylist", "situational_expert": "situational"}
    shown = random.sample(left, len(left))  # 목록 순서를 매번 섞음: 늘 앞에 있는 사람을 고르는 위치 편향 완화
    prompt = (f"{_transcript(state)}\n\n허용 목록(next 로 고를 수 있는 값, 순서 무관): {', '.join(labels[n] for n in shown)}\n"
              f"상황별 전문가는 이번 회의에서 '{names['situational_expert']}'입니다.")
    update: dict = {}
    try:
        if not state.get("look"):  # 첫 차례: 현장 조사 + 첫 전문가 선택
            turn, spot, look, trace, contexts = _investigate(state, prompt)
            avatar = build_avatar(look["avatar"], state["spy_gender"], state["spy_species"]).model_dump()
            update = {"spot": spot or {}, "look": look, "avatar": avatar, "contexts": contexts}
            tool_trace = trace
        else:
            turn = get_llm("main", 0.8, 400).with_structured_output(ModeratorTurn).with_retry(stop_after_attempt=3).invoke(
                [("system", MODERATOR_SYSTEM), ("human", prompt)])
            tool_trace = []
        pick, question, reason = _SLUG.get(turn.next, ""), turn.question.strip(), turn.reason
    except Exception as e:  # 사회자가 실패해도 회의는 이어지게 (조사는 코드가, 사람은 남은 순서대로)
        pick, question, reason, tool_trace = "", "", f"사회자 호출 실패: {type(e).__name__}", []
        if not state.get("look"):
            args = {"taste": state["survey"].get("fashion") or "미니멀", "gender": state["spy_gender"],
                    "species": state["spy_species"]}
            look = json.loads(find_look.invoke(args))
            update = {"spot": {}, "look": look, "contexts": [{"doc_id": look["doc_id"], "text": look["note"]}],
                      "avatar": build_avatar(look["avatar"], state["spy_gender"], state["spy_species"]).model_dump()}
            tool_trace = [_t("find_look", args, {"fallback": "사회자 실패로 코드가 호출", **look})]
    if pick not in left:  # 허용 목록 밖이면 코드가 보정 (같은 사람을 두 번 부르지 않게)
        reason = f"{reason} (허용 목록 밖 '{pick or '없음'}' → 보정)".strip()
        pick = left[0]
    question = question or f"{names[pick]}님, 지금까지 단서를 보면 어떤 생각이 드세요?"
    return Command(goto=pick, update={
        **update,
        "next_question": question, "next_expert": names[pick],
        "mod_notes": [*state.get("mod_notes", []), f"{names[pick]}에게 물은 이유: {reason}"],
        "minutes": _minute(state, MODERATOR, "🎙", question, "moderator"),
        "trace": [*tool_trace, _t("moderator", {"남은 전문가": [names[n] for n in left]},
                                  {"next": names[pick], "question": question, "reason": reason})],
    })


def _investigate(state: SpyState, prompt: str) -> tuple[ModeratorTurn, dict | None, dict, list, list]:
    """(Day 3 · ReAct · Day 4 다중 도구) 사회자가 도구를 스스로 골라 두 DB 를 조사한 뒤 첫 전문가를 고릅니다."""
    agent = create_agent(get_llm("main", 0.7, 1200), tools=TOOLS, system_prompt=MODERATOR_TOOLS + MODERATOR_SYSTEM,
                         response_format=ToolStrategy(ModeratorTurn), name="moderator")
    sv = state["survey"]
    msg = (f"{prompt}\n(find_spot/find_look 의 species={state['spy_species']}, find_look 의 gender={state['spy_gender']})")
    result = agent.invoke({"messages": [("human", msg)]})
    spot = look = None
    trace, contexts = [], []
    calls = {tc["id"]: tc for m in result["messages"] for tc in (getattr(m, "tool_calls", None) or [])}
    for m in result["messages"]:
        if isinstance(m, ToolMessage) and m.name in ("find_spot", "find_look"):
            data = json.loads(m.content)
            if m.name == "find_spot":
                spot = data
                text = f"{data['place']}: 위장 신분 {', '.join(data['covers'])} · 출몰 {data['time']} · {data['behavior']}"
            else:
                look = data
                text = f"{data['note']} (소품: {', '.join(data['items'])})"
            contexts.append({"doc_id": data["doc_id"], "text": text})
            trace.append(_t(m.name, calls.get(m.tool_call_id, {}).get("args", {}), data))
    if look is None:  # 모델이 find_look 을 빠뜨리면 코드가 대신 호출 (아바타는 반드시 필요)
        args = {"taste": sv.get("fashion") or "미니멀", "gender": state["spy_gender"], "species": state["spy_species"]}
        look = json.loads(find_look.invoke(args))
        contexts.append({"doc_id": look["doc_id"], "text": f"{look['note']} (소품: {', '.join(look['items'])})"})
        trace.append(_t("find_look", args, {"fallback": "사회자가 호출하지 않아 코드가 호출", **look}))
    return result["structured_response"], spot, look, trace, contexts


def _run_stylist(present: list[str], prompt: str) -> tuple[str, list[str], list]:
    """(Day 5 · 미들웨어) 1겹: items 를 실제 소품 Literal 로 제한 · 2겹: 응답 문장 검사 훅."""
    FashionRemark = create_model(
        "FashionRemark",
        items=(list[Literal[tuple(present)]], Field(min_length=1, max_length=3, description="언급한 소품")),  # type: ignore[valid-type]
        remark=(str, Field(description="토론 발언 딱 두 문장, 120자 안팎")),
    )
    guard = OutfitHallucinationGuard(present)
    agent = create_agent(get_llm("debate", 0.9, 800), tools=[], system_prompt=stylist_system(present),
                         response_format=ToolStrategy(FashionRemark), middleware=[guard], name="stylist")
    out = agent.invoke({"messages": [("human", prompt)]})["structured_response"]
    return out.remark, list(out.items), guard.log


def _remark(system: str, state: SpyState) -> str:
    return get_llm("debate", 0.9, 600).with_structured_output(ExpertRemark).with_retry(stop_after_attempt=3).invoke(
        [("system", system), ("human", _ask(state))]).remark


def profiler(state: SpyState) -> dict:
    """🔍 범죄 프로파일러 노드: 사회자가 조사한 출몰 기록을 해석해 답."""
    remark = _remark(PROFILER_SYSTEM, state)
    return {"minutes": _minute(state, PROFILER, "🔍", remark, "profiler"),
            "trace": [_t("profiler", {"question": state.get("next_question", "")}, remark)]}


def stylist(state: SpyState) -> dict:
    """👗 패션 스타일리스트 노드: 아바타에 실제로 있는 소품만으로 답 (환각 차단 미들웨어)."""
    present = look_items(state["avatar"], state["spy_species"]) or ["셔츠"]
    remark, items, log = _run_stylist(present, _ask(state))
    return {"minutes": _minute(state, STYLIST, "👗", remark, "stylist"),
            "trace": [_t("stylist", {"question": state.get("next_question", ""), "present_items": present},
                         {"remark": remark, "items": items, "hook": log})]}


def situational_expert(state: SpyState) -> dict:
    """💘 연애 심리학자 / 🐾 반려동물 행동 전문가 노드 (스파이 종에 따라)."""
    name, icon, system = _situ(state)
    remark = _remark(system, state)
    return {"minutes": _minute(state, name, icon, remark, "situational_expert"),
            "trace": [_t("situational_expert", {"expert": name, "question": state.get("next_question", "")}, remark)]}


# ── 판결 (사회자) ────────────────────────────────────────────────────────────


def _make_story(state: SpyState, extra: str = "") -> SpyStory:
    minutes = "\n".join(f"{m['icon']} {m['who']}: {m['text']}" for m in state["minutes"])
    spot = state.get("spot") or {}
    present = look_items(state["avatar"], state["spy_species"])
    brief = (f"{_spy_brief(state)}\n\n사용자 응답:\n{_survey_text(state)}\n\n"
             f"출몰 DB 조사: {json.dumps(spot, ensure_ascii=False) if spot else '없음 (자주 가는 곳 미응답)'}\n"
             f"아바타 소품: {', '.join(present)}\n\n판결 진행 엿보기 (당신이 진행한 회의):\n{minutes}\n\n"
             f"당신의 메모:\n{chr(10).join(state.get('mod_notes', [])) or '(없음)'}{extra}")
    llm = get_llm("main", 1.0, 3000).with_structured_output(SpyStory).with_retry(stop_after_attempt=3)
    return llm.invoke([("system", VERDICT_SYSTEM), ("human", brief)])


def _profile_text(p: dict, minutes: list) -> str:
    keys = ("verdict_reason", "alias", "agency", "cover_identity", "where_near_you", "original_mission",
            "first_contact", "signature", "twist", "secret_note")
    return "\n".join([*(str(p.get(k, "")) for k in keys), *p.get("clues", []), *(m["text"] for m in minutes)])


def _soften_minutes(minutes: list, reason: str) -> list:
    """출력 가드레일에 걸리면 전문가 발언(회의 기록)도 다듬음. 판결문만 다시 쓰면 같은 이유로 또 막히기 때문."""
    idx = [i for i, m in enumerate(minutes) if m.get("node") != "moderator"]
    texts = [f"{minutes[i]['who']}: {minutes[i]['text']}" for i in idx]
    out = get_llm("debate", 0.7, 1500).with_structured_output(SoftenedRemarks).with_retry(stop_after_attempt=3).invoke(
        [("system", SOFTEN_SYSTEM), ("human", f"지적 사유: {reason or '정책 위반'}\n\n" + "\n".join(texts))]).remarks
    if len(out) != len(idx):  # 개수가 어긋나면 손대지 않음
        return minutes
    new = [dict(m) for m in minutes]
    for i, text in zip(idx, out):
        new[i]["text"] = text.split(": ", 1)[1] if text.startswith(f"{new[i]['who']}: ") else text
    return new


def guard_output(state: SpyState) -> dict:
    chk = check_output(_profile_text(state["profile"], state["minutes"]))
    trace = [_t("guard_output", "요원 파일 · 회의록 검사", chk.model_dump())]
    if chk.safe:
        return {"output_checked": True, "trace": trace}
    # 판결문과 회의 기록을 함께 다듬어 다시 검사 (문제 문장이 전문가 발언에 있을 수도 있음)
    minutes = _soften_minutes(state["minutes"], chk.reason)
    story = _make_story({**state, "minutes": minutes},
                        f"\n\n(주의: 이전 초안이 정책 위반이었습니다: {chk.reason}. 수위를 낮춰 다시 쓰세요.)")
    chk2 = check_output(_profile_text(story.model_dump(), minutes))
    trace.append(_t("guard_output_retry", chk.reason or "정책 위반", {**chk2.model_dump(), "minutes_softened": True}))
    if chk2.safe:
        return {"profile": story.model_dump(), "minutes": minutes, "output_checked": True, "trace": trace}
    return {"refusal": REFUSALS["output_blocked"], "output_checked": True, "trace": trace}


# ── 열람 승인 (HITL) ────────────────────────────────────────────────────────
def approve(state: SpyState) -> dict:
    if state.get("mode") != "ui":
        return {"approved": True, "trace": [_t("approve", "API 모드", "열람 자동 승인")]}
    decision = interrupt({"type": "approve", "verdict": "스파이 검거"})  # (Day 5 · HITL 승인)
    ok = decision == "open"
    return {"approved": ok, "trace": [_t("approve", "interrupt → 열람 승인", "열람" if ok else "덮어 둠")]}


# ── 그래프 ──────────────────────────────────────────────────────────────────
def build_graph(checkpointer=None):
    """큰 단계는 코드 supervisor 가 순서대로, 색출 회의는 사회자(LLM Supervisor) ↔ 전문가 3명 고리."""
    g = StateGraph(SpyState)
    g.add_node("supervisor", supervisor, destinations=(*WORKERS, END))
    g.add_node("moderator", moderator, destinations=(*EXPERT_NODES, "supervisor"))
    for name in WORKERS:
        if name != "moderator":
            g.add_node(name, globals()[name])
            g.add_edge(name, "supervisor")
    for name in EXPERT_NODES:  # 전문가는 답한 뒤 사회자에게 돌아감
        g.add_node(name, globals()[name])
        g.add_edge(name, "moderator")
    g.add_edge(START, "supervisor")
    return g.compile(checkpointer=checkpointer or InMemorySaver())


GRAPH = build_graph()


def final_profile(state: dict) -> SpyProfile:
    return SpyProfile(**state["profile"], species=state["spy_species"], gender=state["spy_gender"],
                      avatar=state["avatar"], minutes=state["minutes"])


def build_answer(state: dict) -> str:
    """API 응답의 answer 텍스트."""
    if state.get("refusal"):
        return state["refusal"]
    p = final_profile(state)
    who = f"{p.gender}, {p.age}세" if p.species == "사람" else f"{p.species} 요원, 사람 나이로 {p.age}세"
    spot = state.get("spot") or {}
    lines = [
        f"⚖️ 판결: 스파이 검거 — {p.verdict_reason}",
        "",
        f"[요원 파일] CODENAME {p.codename} · 가명 {p.alias} ({who}) · 소속 {p.agency}",
        *(["  (성별을 알려 주지 않아 스파이 성별은 무작위로 정했어요)"] if state.get("gender_random") else []),
        f"- 위장 신분: {p.cover_identity}",
        f"- 현재 위치: {p.where_near_you}",
    ]
    if spot:
        lines.append(f"- 출몰 기록: {spot.get('time', '')} · {spot.get('behavior', '')}")
    lines += [f"- 복장: {', '.join(look_items(p.avatar.model_dump(), p.species))}",
              f"- 궁합 {p.compatibility}% · 설렘 위험도 {'♥' * p.danger_level}{'♡' * (5 - p.danger_level)}",
              "", "[판결 진행 엿보기]"]
    lines += [f"{m['icon']} {m['who']}: {m['text']}" for m in p.minutes if m.get("node") != "moderator"]  # 사회자 물음은 비공개
    lines += ["", "[최초 접촉 기록]", p.first_contact,
              "", "[수상했던 단서]", *p.clues,
              "", "[작전 이탈 보고]", p.twist,
              "", f"💌 쪽지: \"{p.secret_note}\""]
    return "\n".join(lines)


def run_query(question: str) -> dict:
    """POST /query 용: 한 번에 끝까지 실행하고 {answer, contexts, trace} 를 돌려줍니다."""
    config = {"configurable": {"thread_id": f"api-{uuid.uuid4()}"}, "run_name": "spy_query"}
    state = GRAPH.invoke({"mode": "api", "question": question, "trace": [], "contexts": []}, config)
    return {"answer": build_answer(state), "contexts": state.get("contexts", []), "trace": state.get("trace", [])}
