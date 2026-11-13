<!-- ooo:START -->
<!-- ooo:VERSION:0.59.9 -->
# Ouroboros — Specification-First AI Development

> Before telling AI what to build, define what should be built.
> As Socrates asked 2,500 years ago — "What do you truly know?"
> Ouroboros turns that question into an evolutionary AI workflow engine.

Most AI coding fails at the input, not the output. Ouroboros fixes this by
**exposing hidden assumptions before any code is written**.

1. **Socratic Clarity** — Question until ambiguity ≤ 0.2
2. **Ontological Precision** — Solve the root problem, not symptoms
3. **Evolutionary Loops** — Each evaluation cycle feeds back into better specs

```
Interview → Seed → Execute → Evaluate
    ↑                           ↓
    └──── Evolutionary Loop ────┘
```

## ooo Commands

Each command loads its agent/MCP on-demand. Details in each skill file.

| Command | Loads |
|---------|-------|
| `ooo` | — |
| `ooo interview` | `ouroboros:socratic-interviewer` |
| `ooo seed` | `ouroboros:seed-architect` |
| `ooo run` | MCP required |
| `ooo evolve` | MCP: `evolve_step` |
| `ooo evaluate` | `ouroboros:evaluator` |
| `ooo unstuck` | `ouroboros:{persona}` |
| `ooo status` | MCP: `session_status` |
| `ooo setup` | — |
| `ooo help` | — |

## Agents

Loaded on-demand — not preloaded.

**Core**: socratic-interviewer, ontologist, seed-architect, evaluator,
advocate, contrarian, judge
**Support**: hacker, simplifier, researcher, architect
<!-- ooo:END -->

# 프로젝트: 나를 사랑한 스파이 (미니 프로젝트 제출물)

- 사용자와는 **한국어**로 대화한다.
- 서비스 기획은 [SERVICE.md](SERVICE.md)에 있다. 설계를 바꾸면 SERVICE.md도 같이 맞춘다.
- [evaluation/test_queries.csv](evaluation/test_queries.csv)는 기능이 바뀌면 같이 갱신한다 (도구 이름, 전문가 구성, 정책 등). 7개 열 스키마와 카테고리 비율(positive 40 · negative 20 · edge 25 · guardrail 15%)을 유지하고, 필드 안에는 쉼표 대신 세미콜론을 쓴다. Excel용으로 UTF-8 BOM으로 저장한다.
- [history.md](history.md)는 채팅에서 진행한 작업 기록이다. 작업을 하나 마칠 때마다 맨 아래에 번호를 이어서 **요청 → 한 일 → 바뀐 파일**을 짧게 추가한다. 날짜가 바뀌면 `## 날짜 · 주제` 소제목을 새로 단다. 지난 항목은 고치지 않는다 (사실이 틀린 경우만 바로잡는다).
- [README.md](README.md)는 과제 §4-5 템플릿을 따르는 살아 있는 문서다. 구현, 평가 결과, 시행착오가 생길 때마다 갱신하고 `(예정)` 항목을 실제 값으로 채운다.

## 필수 폴더 구조

제출물은 반드시 아래 구조를 따른다. 새 파일을 만들 때도 이 위치에 둔다.

```
mini-pjt_{본인이름}/
├── src/                       # 소스코드
│   ├── agent.py               # 메인 에이전트 그래프
│   ├── tools.py               # 도메인 도구
│   ├── retriever.py           # RAG 파이프라인
│   └── ...
├── data/                      # 사용한 문서·데이터
├── evaluation/
│   ├── test_queries.csv       # 인-아웃 세트 (§4-4 스키마 필수 · 자체 평가·최종 채점의 기준)
│   ├── round1_report.md       # 1차 자체 평가 결과 (Day 9)
│   └── round2_report.md       # 2차 자체 평가 결과 (Day 10 · 개선 후)
├── SERVICE.md                 # 서비스 스펙 (§4-3 템플릿 필수)
├── Dockerfile                 # 클린 환경 재현 (선택사항)
├── requirements.txt
├── README.md                  # §4-5 템플릿 준수
└── run.sh                     # 실행 스크립트 (선택)
```

### 이 프로젝트에 적용할 때
- `src/agent.py`: LangGraph 그래프 (큰 단계는 코드 supervisor, 색출 회의는 사회자 LLM Supervisor ↔ 전문가 3명 노드 고리, 사회자가 ReAct로 두 DB 조사 · 판결문까지 작성, 가드레일, 열람 승인 interrupt)
- `src/tools.py`: `find_spot`(스파이 출몰 DB), `find_look`(패션 DB)
- `src/prompts.py`: LLM 지시문 모음 (agent.py 에서 분리). 프롬프트 문구는 여기서 고친다.
- `tests/test_core.py`: 단위 테스트 (LLM은 가짜 객체, `./run.sh test`). 분기·가드레일·도구·보정 로직을 바꾸면 같이 고친다.
- `src/` 기타: Streamlit 화면, 아바타(avatar), 카드(card), 토론 대화 화면(debate_view: 전문가가 한두 문장씩 말풍선으로 말하고 "다음"으로 넘김, st.components.v2 · 판결 장면의 판결 이유 바로 아래에 열람 결정 패널), 카드 넘기기 화면(card_view: 신상 아래에서 기록을 카드 한 장씩, 진행 막대·이전/다음, 마지막 장은 설렘 경고 도장), 시작 화면(intro_view: 봉인 로고·"기밀" 도장·타자 제목 애니메이션 후 "스파이 색출 시작" 버튼으로 설문 시작), MCP 질문 서버
- `src/retriever.py`: 현재 설계는 RAG를 쓰지 않는다. RAG를 추가할 때만 만든다.
- `data/`: 공통 질문, 출몰 DB, 패션 DB (모두 직접 작성한 가상 데이터)
- `evaluation/test_queries.csv`: 인-아웃 케이스와 `guardrail` 케이스. 스키마는 과제 §4-4를 따른다.
- 구현은 `src/`에 있다 (2026-11-11 1차 구현). 루트의 옛 PoC(`app.py`, `spy/`)는 2026-11-13 사용자 확인 후 삭제했다.
- 실행은 프로젝트 루트에서: `python -m streamlit run src/app.py`, `python -m uvicorn src.api:app --port 8000` (`run.sh` 참고). 모든 모듈은 `from src.x import ...` 형태로 import 한다.
- 화면 디자인은 Hallmark custom "기밀 문서" 테마다 (마닐라 서류철 위 타자 친 서류, 빨간 도장은 주요 버튼·도장에만, 파란 볼펜은 선택·포커스에만, 글꼴은 Special Elite·나눔명조 제목, Courier Prime·나눔고딕코딩 본문, 나눔손글씨 펜은 카드 쪽지에만. `src/styles/tokens.css`, `base.css`, `app.css`, 카드는 `src/card.py`의 `CARD_CSS`). 색·글꼴은 토큰(`var(--color-*)`, `var(--font-*)`)으로만 쓴다. Streamlit 1.67 위젯은 react-aria 구조라 `stRadioOption[data-selected]`, `stTextInputRootElement` 같은 data-testid로 스타일한다. 이모지를 아이콘으로 쓰지 않는다.
- 모델 배치: 사회자(회의 진행 · 조사 · 판결문)는 Sonnet 4.6(`main`, `us.` 프로필), 색출 회의 전문가 답은 Sonnet 4.6(`debate`, `global.` 프로필 · 막히면 Sonnet 4.5 → Haiku), 맞춤 질문은 Haiku(`talk`), 가드레일·설문 추출은 Haiku(`fast`). `src/llm.py`의 `get_llm(kind)`로 고른다.
- Bedrock 주의: 하루 토큰 한도(ThrottlingException "Too many tokens per day")는 추론 프로필마다 따로다. 판결문(`main`)은 `us.` Sonnet 4.6을 쓰고, 실패하면 `global.` Sonnet 4.6 → `us.` Sonnet 4.5 → Haiku 4.5 순으로 자동 대체한다 (`src/llm.py`의 `MAIN_FALLBACKS`, 환경 변수 `SPY_MAIN_FALLBACKS`). 질문·토론·가드레일(Haiku)도 `us.` Haiku 4.5 → `global.` Haiku 4.5 → `us.`/`global.` Sonnet 4.5 순으로 대체한다 (`FAST_FALLBACKS`, `SPY_FAST_FALLBACKS`). 이 계정은 Sonnet 4와 3.7 권한이 없다. 에이전트(`create_agent`) 구조화 출력은 `ToolStrategy`를 쓴다 (네이티브 방식은 배열 maxItems 미지원). `mcp` 패키지는 `<2`로 고정 (어댑터 호환).
- 제출 폴더 이름은 `mini-pjt_parkeunji`(2026-11-13 확정). GitHub 저장소는 `3333nymph/mini-pjt` (`main` 브랜치).

## 필수 API 스펙

평가와 채점은 아래 API로 이루어진다. 요청과 응답 형식을 바꾸지 않는다.

```
POST /query
Content-Type: application/json
Body: {"question": "사용자 질의"}

Response:
{
  "answer": "근거 기반 응답",
  "contexts": [{"doc_id": "...", "text": "..."}, ...],
  "trace": [{"step": "retrieve", "input": "...", "output": "..."}, ...]
}
```

### 이 프로젝트에 적용할 때 (설계안)
- 서버: FastAPI (`src/api.py`). 같은 그래프(`src/agent.py`)를 Streamlit 화면과 API가 함께 쓴다.
- `question`: 자연어 한 덩어리로 설문 응답을 받는다 (예: "여성, INFP, 클래식 수트 좋아함, 회사 근처 카페 자주 감"). 첫 노드가 구조화 출력으로 설문 응답을 뽑아낸다.
- API 한 번 호출로 끝나야 하므로 **API 모드에서는 interrupt를 건너뛴다**. 맞춤 질문은 생성만 하고 답은 비워 두며, 열람 승인은 자동 승인으로 처리한다. interrupt를 쓰는 HITL은 Streamlit 화면에서만 동작한다.
- `answer`: 스파이 판결과 요원 파일 요약 텍스트. 가드레일에 걸리면 거절 사유를 담는다.
- `contexts`: 근거로 쓴 데이터. `doc_id`는 출처를 붙여 적는다 (예: `spot_db:cafe-01`, `look_db:classic-m-03`, `mcp:questions`).
- `trace`: 노드 순서대로 `step` / `input` / `output`을 남긴다 (실제: `load_questions`, `guard_input`, `parse_survey`, `gen_questions`, `guard_output_questions`, `ask_questions`, `find_spot`, `find_look`, `moderator`(여러 번), `profiler`, `stylist`, `situational_expert`, `verdict`, `guard_output`, `approve`).
