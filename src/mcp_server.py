"""(Day 4 · MCP 서버) 공통 설문 질문을 MCP 도구로 노출하는 로컬 서버.

단독 실행:  python src/mcp_server.py   (stdio 전송)
그래프에서는 src/questions.py 가 이 파일을 하위 프로세스로 띄워 get_questions 를 호출합니다.
"""

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DATA = Path(__file__).resolve().parents[1] / "data"

mcp = FastMCP("spy-questions")


@mcp.tool()
def get_questions() -> str:
    """'나를 사랑한 스파이' 공통 설문 질문 목록(JSON)을 돌려줍니다. MBTI 질문을 포함합니다."""
    return (DATA / "questions.json").read_text(encoding="utf-8")


@mcp.tool()
def get_question(key: str) -> str:
    """특정 key 의 질문 하나를 돌려줍니다 (예: fashion, place)."""
    for q in json.loads((DATA / "questions.json").read_text(encoding="utf-8")):
        if q["key"] == key:
            return json.dumps(q, ensure_ascii=False)
    return json.dumps({"error": f"unknown key: {key}"}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
