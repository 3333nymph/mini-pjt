"""(Day 3·4) 도메인 도구 — 🔍 범죄 프로파일러가 ReAct 로 골라 쓰는 두 개의 DB 조회 도구.

- find_spot : 스파이 출몰 DB  (장소 → 위장 신분 후보 · 출몰 시간대 · 수상한 행동)
- find_look : 패션 DB        (패션 취향 · 성별 · 종 → 아바타 코디)

데이터는 data/*.json 에 직접 작성한 가상 데이터입니다.
"""

from __future__ import annotations

import json
import random
from functools import lru_cache

from langchain_core.tools import tool

from src.llm import DATA
from src.schema import FEMALE_HAIR, FUR_COLORS, HAIR_COLORS, MALE_HAIR, SKIN_COLORS, Avatar, tidy_details


@lru_cache(maxsize=4)
def _db(name: str) -> tuple[dict, ...]:
    return tuple(json.loads((DATA / name).read_text(encoding="utf-8")))


def _group(species: str) -> str:
    return "사람" if species in ("", "사람") else "반려동물"


@tool
def find_spot(place: str, species: str = "사람") -> str:
    """스파이 출몰 DB를 조회합니다. 사용자가 자주 가는 장소(place)를 넣으면 그 장소에 잠입한 스파이의
    위장 신분 후보, 출몰 시간대, 수상한 행동을 돌려줍니다. species 는 스파이의 종(사람/강아지/고양이)입니다.
    사용자가 자주 가는 곳을 말하지 않았다면 이 도구는 쓸 필요가 없습니다."""
    group = _group(species)
    rows = [r for r in _db("spot_db.json") if r["species"] == group]
    text = (place or "").lower()
    # 가장 길게 맞는 키워드의 행을 고름 ('스터디카페'가 '카페' 행보다, '산책로'가 짧은 말보다 우선)
    score = lambda r: max((len(k) for k in r["keywords"] if k.lower() in text), default=0)  # noqa: E731
    best = max(rows, key=score, default=None)
    hit = best if best is not None and score(best) > 0 else None
    if hit is None:
        hit = rows[0] if group == "반려동물" else next(r for r in rows if r["doc_id"].endswith("default-01"))
    return json.dumps({k: hit[k] for k in ("doc_id", "place", "covers", "time", "behavior")}, ensure_ascii=False)


@tool
def find_look(taste: str, gender: str, species: str = "사람", cover: str = "") -> str:
    """패션 DB를 조회합니다. 사용자가 끌리는 패션 취향(taste: 미니멀/스트릿/클래식 수트/꾸안꾸 캐주얼/빈티지),
    스파이 성별(gender: 여성/남성), 스파이의 종(species), 위장 신분(cover, 선택)에 맞는 스파이 복장을 돌려줍니다.
    결과의 items 가 스파이가 실제로 착용한 소품입니다."""
    group = _group(species)
    rows = [r for r in _db("look_db.json") if r["species"] == group]
    if group == "사람":
        cand = [r for r in rows if r["taste"] == taste and r["gender"] in (gender, "공통")]
        cand = cand or [r for r in rows if r["gender"] in (gender, "공통")]
    else:
        cand = rows
    row = random.choice(cand)
    return json.dumps({"doc_id": row["doc_id"], "taste": row["taste"], "note": row["note"],
                       "items": look_items(row["avatar"], species), "avatar": row["avatar"]}, ensure_ascii=False)


TOOLS = [find_spot, find_look]

# ── 아바타 조립 (LLM 이 아닌 코드가 정함 · 피부색은 취향과 무관하게 무작위) ────────────

OUTER_KO = {"trench": "트렌치코트", "black_suit": "블랙 수트", "navy_suit": "네이비 수트",
            "burgundy_suit": "버건디 수트", "white_suit": "화이트 수트", "leather_jacket": "가죽 재킷",
            "denim_jacket": "데님 재킷", "camel_coat": "카멜 코트", "cardigan": "카디건"}
NECK_KO = {"tie": "넥타이", "bowtie": "나비넥타이", "scarf": "스카프", "pearl_necklace": "진주 목걸이"}
DETAIL_KO = {"fedora": "페도라", "beret": "베레모", "cap": "볼캡", "earpiece": "이어피스", "headphones": "헤드폰",
             "beauty_mark": "얼굴의 점", "pocket_square": "행커치프", "lapel_pin": "라펠 핀", "boutonniere": "부토니에르"}

# 환각 차단 훅이 문장에서 찾는 소품 단어 (소품 이름 → 같은 뜻의 표현)
ITEM_WORDS: dict[str, tuple[str, ...]] = {
    "트렌치코트": ("트렌치",), "블랙 수트": ("블랙 수트", "검은 수트", "검은 정장"),
    "네이비 수트": ("네이비 수트", "남색 수트"), "버건디 수트": ("버건디 수트", "버건디 정장"),
    "화이트 수트": ("화이트 수트", "흰 수트", "흰 정장"),
    "넥타이": ("넥타이",), "나비넥타이": ("나비넥타이", "보타이"),
    "가죽 재킷": ("가죽 재킷", "라이더 재킷", "레더 재킷"), "데님 재킷": ("데님 재킷", "청재킷", "청 재킷"),
    "카멜 코트": ("카멜 코트", "카멜코트"), "카디건": ("카디건", "가디건"),
    "스카프": ("스카프", "머플러"), "진주 목걸이": ("진주 목걸이", "진주", "목걸이"),
    "페도라": ("페도라", "중절모"), "베레모": ("베레모", "베레"), "볼캡": ("볼캡", "야구 모자", "야구모자"),
    "이어피스": ("이어피스", "통신기", "인이어", "이어폰"), "헤드폰": ("헤드폰", "헤드셋"),
    "얼굴의 점": ("애교점", "얼굴의 점", "눈가의 점"), "행커치프": ("행커치프", "포켓 스퀘어", "포켓스퀘어"),
    "라펠 핀": ("라펠 핀", "라펠핀", "배지"), "부토니에르": ("부토니에르", "코사지", "꽃 장식", "장미"),
    "안경": ("안경",), "선글라스": ("선글라스",), "귀걸이": ("귀걸이", "이어링"), "수염": ("수염",),
    "목줄": ("목줄",), "이름표": ("이름표",),
}


def look_items(av: dict, species: str = "사람") -> list[str]:
    """아바타 부품 dict → 그림에 실제로 있는 소품의 한국어 이름 목록."""
    items = []
    if av.get("outer", "none") != "none":
        items.append(OUTER_KO[av["outer"]])
    if av.get("neckwear", "none") in NECK_KO:
        items.append(NECK_KO[av["neckwear"]])
    elif species not in ("", "사람"):
        items += ["목줄", "이름표"]
    if av.get("glasses", "none") != "none":
        items.append("안경" if species in ("", "사람") else "선글라스")
    human = species in ("", "사람")
    if human and av.get("earrings", "none") != "none":  # 반려동물 그림에는 귀걸이·수염이 없음
        items.append("귀걸이")
    if human and av.get("facial_hair", "none") != "none":
        items.append("수염")
    details = tidy_details(av)  # 그림에서 빠지는 소품은 목록에서도 뺌 (환각 차단과 맞추기)
    if species not in ("", "사람"):
        details = [d for d in details if d != "headphones"]
    items += [DETAIL_KO[d] for d in details if d in DETAIL_KO]
    return items


def build_avatar(look_avatar: dict, gender: str, species: str, rng: random.Random | None = None) -> Avatar:
    """패션 DB 코디 + 성별에 맞는 얼굴 부품(무작위)으로 아바타를 완성합니다."""
    rng = rng or random.Random()
    female = gender == "여성"
    a = {
        "hair": rng.choice(FEMALE_HAIR if female else MALE_HAIR),
        "hair_color": rng.choice(HAIR_COLORS),
        "skin_color": rng.choice(SKIN_COLORS),
        "eyes": rng.choice(["eyes", "round", "smiling"] + (["eyesShadow", "smilingShadow"] if female else [])),
        "eye_shadow_color": rng.choice(["d2eff3", "e0ddff", "ffeba4", "ffedef"]),
        "eyebrows": rng.choice(["eyelashesUp", "eyelashesDown"] if female else ["up", "down"]),
        "earrings": rng.choice(["hoop", "stud"]) if female else "none",
        "earring_color": rng.choice(["f4d150", "ffffff"]),
        "mouth": rng.choice(["smile", "laughing", "smirk", "pucker" if female else "nervous"]),
        "facial_hair": "none" if female else rng.choice(["none", "none", "scruff", "beard"]),
        "glasses_color": rng.choice(["000000", "000000", "77311d", "c93305"]),
        "nose": rng.choice(["curve", "pointed", "tound"]),
        "ears": rng.choice(["attached", "detached"]),
        "fur_color": rng.choice(FUR_COLORS),
    }
    a.update({k: v for k, v in look_avatar.items() if v is not None})
    if not female and a.get("earrings") == "hoop":
        a["earrings"] = "stud"
    if female:
        a["facial_hair"] = "none"
        if a.get("earrings", "none") == "none":
            a["earrings"] = "stud"
    return Avatar(**a)
