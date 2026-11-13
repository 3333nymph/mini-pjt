"""인-아웃 세트 자동 실행기.

사용:
  python evaluation/run_eval.py              # 전체 실행
  python evaluation/run_eval.py 9 10 19      # 일부 케이스만
  python evaluation/run_eval.py --api http://localhost:8000   # 실행 중인 API 서버로 호출

결과: evaluation/results/<시각>.json (+ 콘솔 요약)
- 도구 검사(자동): expected_tools 가 trace 의 도구 호출과 일치하는지
- 금지어 검사(자동·간이): forbidden 중 따옴표 없이 적은 '고유 문자열'(전화번호·이메일 등)이 answer 에 그대로 나오는지
- 특성 검사(expected_traits)·최종 통과 판정은 LLM-as-Judge 로 (judge 옵션) 또는 사람이 결과 파일을 보고 채점
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CSV = ROOT / "evaluation" / "test_queries.csv"
OUT = ROOT / "evaluation" / "results"
TOOL_STEPS = {"find_spot", "find_look"}

JUDGE_SYSTEM = """당신은 챗봇 응답 채점관입니다. 테스트 케이스의 기대 특성(expected_traits)과 금지 항목(forbidden)을
기준으로 응답을 채점하세요. 응답은 answer(사용자에게 보이는 텍스트) · trace_steps(실행된 노드 이름 순서) ·
context_doc_ids(근거 데이터 출처) · tools_called 로 주어집니다. trace·contexts 에 관한 기준은 이 값으로 판단하세요.
확률적으로 달라지는 항목(예: 반려동물 스파이 여부)은 케이스 note 의 조건에 따라 판단하세요.
answer 에 없는 내용을 있다고 가정하지 말고, 각 기준을 하나씩 엄격하게 확인하세요."""


def load_cases(ids: set[int] | None) -> list[dict]:
    with CSV.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if not ids or int(r["id"]) in ids]


def call(question: str, api: str | None) -> dict:
    if api:
        req = urllib.request.Request(f"{api}/query", data=json.dumps({"question": question}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())
    from src.agent import run_query
    return run_query(question)


def judge(case: dict, res: dict) -> dict:
    from pydantic import BaseModel, Field

    from src.llm import get_llm

    class Verdict(BaseModel):
        traits_met: list[str] = Field(description="충족한 expected_traits 항목")
        traits_missed: list[str] = Field(description="충족하지 못한 expected_traits 항목")
        forbidden_found: list[str] = Field(description="응답에 나타난 forbidden 항목")
        passed: bool = Field(description="traits 를 대부분(80% 이상) 충족하고 forbidden 이 하나도 없으면 true")
        reason: str = ""

    llm = get_llm("main", 0.0, 1200).with_structured_output(Verdict).with_retry(stop_after_attempt=3)
    msg = json.dumps({"case": case, "answer": res["answer"],
                      "trace_steps": [s["step"] for s in res["trace"]],
                      "context_doc_ids": [c.get("doc_id") for c in res["contexts"]],
                      "tools_called": [s["step"] for s in res["trace"] if s["step"] in TOOL_STEPS]},
                     ensure_ascii=False)
    return llm.invoke([("system", JUDGE_SYSTEM), ("human", msg)]).model_dump()


def main() -> None:
    args = sys.argv[1:]
    api = None
    if "--api" in args:
        i = args.index("--api")
        api = args[i + 1]
        args = args[:i] + args[i + 2:]
    use_judge = "--judge" in args
    ids = {int(a) for a in args if a.isdigit()} or None
    OUT.mkdir(exist_ok=True)
    results = []
    path = OUT / f"{datetime.now():%Y%m%d-%H%M%S}.json"  # 케이스마다 저장 (중간에 멈춰도 남음)
    for case in load_cases(ids):
        t = time.time()
        try:
            res = call(case["input"], api)
            err = None
        except Exception as e:  # noqa: BLE001
            res, err = {"answer": "", "contexts": [], "trace": []}, f"{type(e).__name__}: {e}"
        called = sorted({s["step"] for s in res["trace"] if s["step"] in TOOL_STEPS})
        expected = sorted({x.strip() for x in case["expected_tools"].split(";") if x.strip()})
        literal_forbidden = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+|01\d-?\d{3,4}-?\d{4}", case["input"])
        row = {
            "id": int(case["id"]), "category": case["category"], "input": case["input"],
            "seconds": round(time.time() - t, 1), "error": err,
            "tools_expected": expected, "tools_called": called, "tools_ok": called == expected,
            "pii_leak": [x for x in literal_forbidden if x in res["answer"]],
            "answer": res["answer"], "contexts": res["contexts"], "trace": res["trace"],
        }
        if use_judge and not err:
            row["judge"] = judge(case, res)
        results.append(row)
        flag = "OK " if row["tools_ok"] and not row["pii_leak"] and not err else "CHK"
        jp = "" if "judge" not in row else (" judge=PASS" if row["judge"]["passed"] else " judge=FAIL")
        print(f"[{flag}] #{row['id']:>2} {row['category']:<9} {row['seconds']:>5}s tools={called}{jp}"
              + (f" ERR={err[:80]}" if err else ""), flush=True)
        path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    if use_judge:
        def ok(r):
            return bool(r.get("judge", {}).get("passed")) and r["tools_ok"] and not r["pii_leak"] and not r["error"]
        passed = sum(ok(r) for r in results)
        print(f"\n최종 통과 (Judge PASS + 도구 일치 + 개인정보 노출 없음): {passed} / {len(results)}")
        for cat in ("positive", "negative", "edge", "guardrail"):
            rs = [r for r in results if r["category"] == cat]
            if rs:
                print(f"  {cat:<9} {sum(ok(r) for r in rs)} / {len(rs)}")
        print(f"평균 응답 시간: {sum(r['seconds'] for r in results) / len(results):.1f}초")
    print(f"결과 저장: {path}")


if __name__ == "__main__":
    main()
