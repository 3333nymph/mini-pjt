"""POST /query — 과제 필수 API 스펙.

실행:  uvicorn src.api:app --port 8000
요청:  {"question": "여성, INFP, 클래식 수트 좋아함, 회사 근처 카페 자주 감"}
응답:  {"answer": "...", "contexts": [{"doc_id", "text"}], "trace": [{"step", "input", "output"}]}
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from src.agent import run_query

app = FastAPI(title="나를 사랑한 스파이 API")


class QueryIn(BaseModel):
    question: str


class Context(BaseModel):
    doc_id: str
    text: str


class Step(BaseModel):
    step: str
    input: str
    output: str


class QueryOut(BaseModel):
    answer: str
    contexts: list[Context]
    trace: list[Step]


@app.post("/query", response_model=QueryOut)
def query(body: QueryIn) -> QueryOut:
    # 동기 함수라 FastAPI 스레드풀에서 실행 (그래프 내부 MCP 호출이 asyncio.run 을 쓰기 때문)
    try:
        return QueryOut(**run_query(body.question))
    except Exception as e:  # 실패해도 스펙 형식은 지킴
        return QueryOut(answer=f"요원 파일을 만들지 못했어요. 잠시 후 다시 시도해 주세요. ({type(e).__name__})",
                        contexts=[], trace=[Step(step="error", input=body.question[:300], output=str(e)[:900])])


@app.get("/health")
def health() -> dict:
    return {"ok": True}
