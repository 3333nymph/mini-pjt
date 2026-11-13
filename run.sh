#!/usr/bin/env bash
# 사용: ./run.sh ui   → Streamlit 화면 (http://localhost:8501)
#       ./run.sh api  → POST /query API (http://localhost:8000)
#       ./run.sh eval → 인-아웃 세트 실행 (LLM-as-Judge 포함)
#       ./run.sh test → 단위 테스트 (LLM 없이)
set -e
cd "$(dirname "$0")"
case "${1:-ui}" in
  ui)   python -m streamlit run src/app.py ;;
  api)  python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 ;;
  eval) python evaluation/run_eval.py --judge "${@:2}" ;;
  test) python -m pytest -q tests ;;
  *)    echo "usage: ./run.sh [ui|api|eval|test]"; exit 1 ;;
esac
