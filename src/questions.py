"""MCP 클라이언트 — 공통 질문 서버(src/mcp_server.py)에서 질문 목록을 받아옵니다."""

from __future__ import annotations

import asyncio
import json
import sys
from functools import lru_cache
from pathlib import Path

SERVER = Path(__file__).resolve().parent / "mcp_server.py"


async def _fetch() -> list[dict]:
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient({
        "spy-questions": {"command": sys.executable, "args": [str(SERVER)], "transport": "stdio"},
    })
    tools = {t.name: t for t in await client.get_tools()}
    raw = await tools["get_questions"].ainvoke({})
    # 어댑터 버전에 따라 문자열 또는 content 블록 목록으로 돌아옴
    if isinstance(raw, list):
        raw = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in raw)
    return json.loads(raw)


def _run(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # 이미 이벤트 루프가 도는 스레드라면 새 스레드에서 실행
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(1) as ex:
        return ex.submit(asyncio.run, coro).result()


@lru_cache(maxsize=1)
def load_questions() -> tuple[dict, ...]:
    """질문 목록은 바뀌지 않으므로 프로세스당 한 번만 MCP 서버를 띄웁니다."""
    return tuple(_run(_fetch()))
