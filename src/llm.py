"""Bedrock Claude 모델 생성. .env 를 읽고 LangSmith 트레이스(Day 7)도 환경 변수로 켜집니다."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
load_dotenv(ROOT / ".env")

REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
MAIN_MODEL = os.getenv("SPY_MAIN_MODEL", "us.anthropic.claude-sonnet-4-6")
# 가드레일 판정처럼 짧은 분류 작업용 (권한이 없으면 SPY_FAST_MODEL 로 메인 모델을 지정)
FAST_MODEL = os.getenv("SPY_FAST_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
# 맞춤 질문 · 전문가 토론처럼 호출이 많고 짧은 글 (속도 우선). 카드에 남는 판결문만 MAIN_MODEL
TALK_MODEL = os.getenv("SPY_TALK_MODEL", FAST_MODEL)
# 색출 회의(전문가 토론)는 사용자가 한 줄씩 읽는 글이라 Sonnet. 판결문(us. 4.6)과 한도를 나눠 쓰려고 global 프로필
DEBATE_MODEL = os.getenv("SPY_DEBATE_MODEL", "global.anthropic.claude-sonnet-4-6")
# MAIN_MODEL 이 하루 토큰 한도(ThrottlingException) 등으로 실패하면 차례로 대신 쓰는 모델.
# Bedrock 한도는 추론 프로필마다 따로라서 한 프로필이 막혀도 다른 프로필은 살아 있는 경우가 많다. 마지막은 Haiku.
def _models(env: str, default: str) -> list[str]:
    return [m.strip() for m in os.getenv(env, default).split(",") if m.strip()]


MAIN_FALLBACKS = _models("SPY_MAIN_FALLBACKS",
                         f"global.anthropic.claude-sonnet-4-6,us.anthropic.claude-sonnet-4-5-20250929-v1:0,{FAST_MODEL}")
# 질문·토론·판정(Haiku)도 하루 한도에 걸리면 다른 프로필의 Haiku → Sonnet 4.5 순으로 대신 쓴다
FAST_FALLBACKS = _models("SPY_FAST_FALLBACKS",
                         "global.anthropic.claude-haiku-4-5-20251001-v1:0,us.anthropic.claude-sonnet-4-5-20250929-v1:0,"
                         "global.anthropic.claude-sonnet-4-5-20250929-v1:0")
# 토론(Sonnet 4.6)이 막히면 Sonnet 4.5 → 마지막은 Haiku
DEBATE_FALLBACKS = _models("SPY_DEBATE_FALLBACKS",
                           "us.anthropic.claude-sonnet-4-5-20250929-v1:0,global.anthropic.claude-sonnet-4-5-20250929-v1:0,"
                           f"{FAST_MODEL}")


def _chat(model: str, temperature: float, max_tokens: int, attempts: int):
    from botocore.config import Config
    from langchain_aws import ChatBedrockConverse

    cfg = Config(retries={"max_attempts": attempts, "mode": "adaptive"}, read_timeout=120)
    return ChatBedrockConverse(model=model, region_name=REGION, temperature=temperature, max_tokens=max_tokens,
                               config=cfg)


@lru_cache(maxsize=8)
def get_llm(kind: str = "main", temperature: float = 0.9, max_tokens: int = 2000):
    """kind: main(판결문) · debate(색출 회의) · talk(맞춤 질문) · fast(판정).
    한도에 걸리면 *_FALLBACKS 의 다른 프로필로 자동 대체."""
    from botocore.exceptions import ClientError

    if kind == "main":
        # 하루 한도는 재시도해도 풀리지 않으므로 주 모델 재시도는 짧게 하고 바로 대체 모델로 넘긴다
        model, fallbacks, attempts = MAIN_MODEL, MAIN_FALLBACKS, 2
    elif kind == "debate":
        # 1·2라운드가 2개씩 병렬이라 순간 throttling 이 날 수 있어 주 모델도 몇 번 재시도
        model, fallbacks, attempts = DEBATE_MODEL, DEBATE_FALLBACKS, 4
    else:
        # 병렬 호출 시 순간 ThrottlingException 이 나므로 주 모델도 어느 정도 재시도한 뒤 넘긴다
        model, fallbacks, attempts = {"fast": FAST_MODEL, "talk": TALK_MODEL}.get(kind, FAST_MODEL), FAST_FALLBACKS, 4
    primary = _chat(model, temperature, max_tokens, attempts)
    backups = [_chat(m, temperature, max_tokens, 8) for m in fallbacks if m != model]
    return primary.with_fallbacks(backups, exceptions_to_handle=(ClientError,)) if backups else primary
