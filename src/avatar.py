"""스파이 아바타: DiceBear micah + 직접 그린 옷·디테일 레이어(SVG).

micah 좌표계(viewBox 0 0 360 360) 기준으로 덧그립니다. 얼굴 위치는 seed와 무관하게 고정입니다.
"""

from __future__ import annotations

import base64
import random
import urllib.parse
import urllib.request

from src.schema import FEMALE_HAIR, MALE_HAIR, SpyProfile, tidy_details

DICEBEAR = "https://api.dicebear.com/9.x/micah/svg"
BG = "cfc6b0"

SILHOUETTE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#cfc6b0"/>'
    '<circle cx="50" cy="38" r="18" fill="#3a3a3a"/><path d="M14 100c4-26 20-38 36-38s32 12 36 38z" fill="#3a3a3a"/>'
    '<text x="50" y="44" font-size="14" text-anchor="middle" fill="#cfc6b0">?</text></svg>'
)

OUTER_COLORS = {
    "trench": "#c9a66b",
    "black_suit": "#1f1f1f",
    "navy_suit": "#22325a",
    "burgundy_suit": "#6b1f2a",
    "white_suit": "#f2f2f2",
    "leather_jacket": "#2b2b2b",
    "denim_jacket": "#4a6fa5",
    "camel_coat": "#c19a6b",
    "cardigan": "#7d8a5a",
}

_K = 'stroke="#000" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"'


def _outer(kind: str) -> str:
    color = OUTER_COLORS[kind]
    base = (
        f'<path d="M40 360 L70 318 L128 298 L150 340 L160 360 Z" fill="{color}" {_K}/>'
        f'<path d="M320 360 L292 318 L236 298 L212 340 L200 360 Z" fill="{color}" {_K}/>'
    )
    lapels = (f'<path d="M128 298 L118 322 L150 340" fill="none" {_K}/>'
              f'<path d="M236 298 L246 322 L212 340" fill="none" {_K}/>')
    if kind == "leather_jacket":  # 뾰족한 칼라 + 비스듬한 지퍼
        return (base + f'<path d="M128 298 L104 318 L140 330" fill="#3a3a3a" {_K}/>'
                f'<path d="M236 298 L260 318 L224 330" fill="#3a3a3a" {_K}/>'
                '<path d="M86 340 L120 352" stroke="#c9c9c9" stroke-width="3" stroke-linecap="round"/>'
                '<circle cx="84" cy="339" r="3" fill="#c9c9c9"/>')
    if kind == "denim_jacket":  # 셔츠 칼라 + 박음질 + 가슴 주머니
        stitch = 'fill="none" stroke="#f4d150" stroke-width="2" stroke-dasharray="5 4"'
        return (base + f'<path d="M128 298 L112 316 L146 326" fill="#5b80b5" {_K}/>'
                f'<path d="M236 298 L252 316 L218 326" fill="#5b80b5" {_K}/>'
                f'<path d="M64 334 L140 334" {stitch}/><path d="M296 334 L222 334" {stitch}/>'
                f'<rect x="250" y="338" width="28" height="18" rx="2" fill="#5b80b5" {_K}/>')
    if kind == "cardigan":  # 라펠 없이 V넥 + 단추
        buttons = "".join(f'<circle cx="{x}" cy="{y}" r="4" fill="#e8d2a8" stroke="#000" stroke-width="2"/>'
                          for x, y in ((150, 346), (206, 346)))
        return base + buttons
    if kind == "camel_coat":  # 라펠 + 큼직한 단추
        return (base + lapels + '<circle cx="152" cy="352" r="5" fill="#5a4632" stroke="#000" stroke-width="2"/>'
                '<circle cx="208" cy="352" r="5" fill="#5a4632" stroke="#000" stroke-width="2"/>')
    return base + lapels


def _tie(c: str) -> str:
    return (f'<path d="M169 330 L187 330 L183 342 L173 342 Z" fill="#{c}" {_K}/>'
            f'<path d="M173 342 L183 342 L190 362 L166 362 Z" fill="#{c}" {_K}/>')


def _bowtie(c: str) -> str:
    return (f'<path d="M160 326 L178 335 L160 344 Z" fill="#{c}" {_K}/>'
            f'<path d="M196 326 L178 335 L196 344 Z" fill="#{c}" {_K}/>'
            f'<rect x="173" y="330" width="10" height="10" rx="2" fill="#{c}" {_K}/>')


def _scarf(c: str) -> str:
    """목에 두른 스카프 + 앞으로 늘어진 끝자락."""
    return (f'<path d="M126 296 Q180 330 238 296 L240 314 Q180 350 124 314 Z" fill="#{c}" {_K}/>'
            f'<path d="M196 322 L214 362 L190 362 L182 326 Z" fill="#{c}" {_K}/>')


def _pearls(_c: str = "") -> str:
    pts = [(140, 312), (152, 320), (165, 326), (178, 328), (191, 326), (204, 320), (216, 312)]
    return "".join(f'<circle cx="{x}" cy="{y}" r="5" fill="#fbf7ee" stroke="#000" stroke-width="2"/>' for x, y in pts)


def _headphones() -> str:
    """목에 건 헤드폰 (스트릿)."""
    return ('<path d="M122 300 Q180 352 238 300" fill="none" stroke="#1f1f1f" stroke-width="9" stroke-linecap="round"/>'
            f'<ellipse cx="120" cy="302" rx="15" ry="19" fill="#2b2b2b" {_K}/>'
            f'<ellipse cx="240" cy="302" rx="15" ry="19" fill="#2b2b2b" {_K}/>'
            '<ellipse cx="120" cy="302" rx="7" ry="10" fill="#b3261e"/><ellipse cx="240" cy="302" rx="7" ry="10" fill="#b3261e"/>')


LAPEL_PIN = f'<circle cx="104" cy="330" r="7" fill="#f4d150" {_K}/><circle cx="104" cy="330" r="2.5" fill="#b3261e"/>'
BOUTONNIERE = ('<path d="M112 336 L100 352" stroke="#3f6b3a" stroke-width="4" stroke-linecap="round"/>'
               '<path d="M104 346 Q94 342 96 334 Q104 338 104 346 Z" fill="#4f8a47" stroke="#000" stroke-width="2"/>'
               f'<circle cx="114" cy="330" r="9" fill="#b3261e" {_K}/>'
               '<path d="M110 328 Q114 323 118 329 Q114 334 110 331" fill="none" stroke="#6b1f2a" stroke-width="2"/>')


def _beret(c: str) -> str:
    return (f'<ellipse cx="204" cy="70" rx="108" ry="34" transform="rotate(-8 204 70)" fill="#{c}" {_K}/>'
            f'<path d="M206 38 L210 24" fill="none" {_K}/>'
            '<path d="M120 84 Q200 96 288 64" fill="none" stroke="#000" stroke-width="3" stroke-linecap="round" opacity="0.35"/>')


def _cap(c: str) -> str:
    return (f'<path d="M114 92 C112 34 152 16 198 16 C246 16 282 38 282 92 Z" fill="#{c}" {_K}/>'
            f'<path d="M114 90 C82 92 52 98 44 110 C84 114 150 106 206 94 Z" fill="#{c}" {_K}/>'
            '<path d="M198 18 L198 90 M150 26 Q160 60 160 90 M246 26 Q236 60 236 90" fill="none" stroke="#000" '
            'stroke-width="2" opacity="0.35"/>'
            f'<circle cx="198" cy="18" r="6" fill="#{c}" {_K}/>')


def _hat(details: list[str], c: str) -> str:
    if "fedora" in details:
        return _fedora(c)
    if "beret" in details:
        return _beret(c)
    if "cap" in details:
        return _cap(c)
    return ""


NECKWEAR = {"tie": lambda c: _tie(c), "bowtie": lambda c: _bowtie(c), "scarf": lambda c: _scarf(c),
            "pearl_necklace": lambda c: _pearls(c)}


def _neckwear(kind: str, c: str) -> str:
    return NECKWEAR[kind](c) if kind in NECKWEAR else ""


def _fedora(c: str) -> str:
    band = "#b3261e" if c != "b3261e" else "#1f1f1f"
    return (
        f'<path d="M108 78 C112 30 140 12 196 12 C252 12 278 30 282 78 Z" fill="#{c}" {_K}/>'
        f'<path d="M150 22 Q196 40 242 22" fill="none" {_K}/>'
        f'<path d="M110 66 L280 66 L282 80 L108 80 Z" fill="{band}" stroke="#000" stroke-width="4" stroke-linejoin="round"/>'
        f'<path d="M58 92 C80 70 310 70 334 92 C318 104 74 104 58 92 Z" fill="#{c}" {_K}/>'
    )


EARPIECE = (
    '<path d="M104 186 C96 210 112 222 102 246 C94 266 114 276 106 300" fill="none" '
    'stroke="#1f1f1f" stroke-width="3" stroke-linecap="round"/>'
    '<circle cx="106" cy="182" r="7" fill="#1f1f1f" stroke="#000" stroke-width="3"/>'
)
BEAUTY_MARK = '<circle cx="238" cy="196" r="5.5" fill="#2a1a12" stroke="#000" stroke-width="1"/>'


def _pocket_square(c: str) -> str:
    return f'<path d="M262 340 L290 340 L284 330 L276 338 L270 328 Z" fill="#{c}" {_K}/>'


def _fix_for_gender(p: SpyProfile) -> dict:
    """Claude가 성별과 안 맞는 값을 골라도 그림이 어긋나지 않게 보정."""
    a = p.avatar.model_dump()
    rnd = random.Random(p.codename)
    female = p.gender == "여성"
    if female:
        if a["hair"] not in FEMALE_HAIR:
            a["hair"] = rnd.choice(FEMALE_HAIR)
        if not a["eyebrows"].startswith("eyelashes"):
            a["eyebrows"] = "eyelashesUp" if a["eyebrows"] == "up" else "eyelashesDown"
        if a["earrings"] == "none":
            a["earrings"] = "hoop"
        a["facial_hair"] = "none"
    else:
        if a["hair"] not in MALE_HAIR:
            a["hair"] = rnd.choice(MALE_HAIR)
        if a["eyebrows"].startswith("eyelashes"):
            a["eyebrows"] = "up" if a["eyebrows"].endswith("Up") else "down"
        if a["earrings"] == "hoop":
            a["earrings"] = "stud"
    a["details"] = tidy_details(a)  # 모자 하나 · 라펠 없는 옷엔 핀·꽃 없음 · 목이 겹치면 헤드폰 뺌
    return a


def avatar_url(p: SpyProfile) -> str:
    a = _fix_for_gender(p)
    params = {
        "seed": p.codename,
        "backgroundColor": BG,
        "baseColor": a["skin_color"],
        "hair": a["hair"],
        "hairColor": a["hair_color"],
        "eyes": a["eyes"],
        "eyeShadowColor": a["eye_shadow_color"],
        "eyebrows": a["eyebrows"],
        "eyebrowsColor": "000000",
        "mouth": a["mouth"],
        "nose": a["nose"],
        "ears": a["ears"],
        "shirt": a["shirt"],
        "shirtColor": a["shirt_color"],
        "earringsProbability": "0" if a["earrings"] == "none" else "100",
        "glassesProbability": "0" if a["glasses"] == "none" else "100",
        "facialHairProbability": "0" if a["facial_hair"] == "none" else "100",
    }
    if a["earrings"] != "none":
        params |= {"earrings": a["earrings"], "earringColor": a["earring_color"]}
    if a["glasses"] != "none":
        params |= {"glasses": a["glasses"], "glassesColor": a["glasses_color"]}
    if a["facial_hair"] != "none":
        params |= {"facialHair": a["facial_hair"], "facialHairColor": a["hair_color"]}
    return f"{DICEBEAR}?{urllib.parse.urlencode(params)}"


def overlay(p: SpyProfile) -> str:
    a = _fix_for_gender(p)
    parts = []
    if "earpiece" in a["details"]:
        parts.append(EARPIECE)
    if a["outer"] != "none":
        parts.append(_outer(a["outer"]))
    parts.append(_neckwear(a["neckwear"], a["neckwear_color"]))
    if "headphones" in a["details"]:
        parts.append(_headphones())
    if "pocket_square" in a["details"]:
        parts.append(_pocket_square("ffffff" if a["outer"] != "white_suit" else "b3261e"))
    if "lapel_pin" in a["details"]:
        parts.append(LAPEL_PIN)
    if "boutonniere" in a["details"]:
        parts.append(BOUTONNIERE)
    if "beauty_mark" in a["details"]:
        parts.append(BEAUTY_MARK)
    parts.append(_hat(a["details"], a["hat_color"]))
    return "".join(parts)


# ── 동물 요원 (강아지/고양이): DiceBear 없이 직접 그림. 머리는 원점 기준으로 그린 뒤 확대 ──

def _cat_head(c: str, shades: bool) -> str:
    return (
        f'<path d="M-38 -14 L-34 -58 L-8 -34 Z" fill="#{c}" {_K}/><path d="M38 -14 L34 -58 L8 -34 Z" fill="#{c}" {_K}/>'
        '<path d="M-31 -22 L-30 -46 L-15 -32 Z" fill="#f7b7c3"/><path d="M31 -22 L30 -46 L15 -32 Z" fill="#f7b7c3"/>'
        f'<ellipse cx="0" cy="0" rx="44" ry="38" fill="#{c}" {_K}/>'
        '<ellipse cx="-15" cy="-4" rx="4.5" ry="7" fill="#000"/><ellipse cx="15" cy="-4" rx="4.5" ry="7" fill="#000"/>'
        '<path d="M-5 8 L5 8 L0 13 Z" fill="#f08aa0" stroke="#000" stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M0 13 Q-6 21 -12 17 M0 13 Q6 21 12 17" fill="none" stroke="#000" stroke-width="3" stroke-linecap="round"/>'
        '<path d="M-22 10 L-50 6 M-22 15 L-48 18 M22 10 L50 6 M22 15 L48 18" stroke="#000" stroke-width="2" stroke-linecap="round"/>'
        + (_shades(-4) if shades else "")
    )


def _dog_head(c: str, shades: bool) -> str:
    ear = "5a4632" if c not in ("5a4632", "2b2b2b") else "1f1f1f"
    return (
        f'<ellipse cx="0" cy="0" rx="42" ry="38" fill="#{c}" {_K}/>'
        f'<ellipse cx="-40" cy="-2" rx="13" ry="28" transform="rotate(18 -40 -2)" fill="#{ear}" {_K}/>'
        f'<ellipse cx="40" cy="-2" rx="13" ry="28" transform="rotate(-18 40 -2)" fill="#{ear}" {_K}/>'
        '<ellipse cx="-14" cy="-6" rx="5" ry="6" fill="#000"/><ellipse cx="14" cy="-6" rx="5" ry="6" fill="#000"/>'
        '<ellipse cx="0" cy="12" rx="16" ry="12" fill="#fff4e0" stroke="#000" stroke-width="3"/>'
        '<ellipse cx="0" cy="7" rx="7" ry="5" fill="#000"/>'
        '<path d="M-4 20 Q0 32 4 20 Z" fill="#f08aa0" stroke="#000" stroke-width="2.5" stroke-linejoin="round"/>'
        + (_shades(-6) if shades else "")
    )


def _shades(ey: int) -> str:
    return (f'<rect x="-27" y="{ey - 8}" width="22" height="15" rx="5" fill="#111" stroke="#000" stroke-width="3"/>'
            f'<rect x="5" y="{ey - 8}" width="22" height="15" rx="5" fill="#111" stroke="#000" stroke-width="3"/>'
            f'<path d="M-5 {ey - 3} L5 {ey - 3}" stroke="#000" stroke-width="3"/>'
            f'<path d="M-22 {ey - 4} L-15 {ey - 4} M10 {ey - 4} L17 {ey - 4}" stroke="#fff" stroke-width="2" stroke-linecap="round"/>')


def animal_svg(p: SpyProfile) -> str:
    a = p.avatar.model_copy(update={"details": [d for d in tidy_details(p.avatar.model_dump()) if d != "headphones"]})
    fur = a.fur_color
    head = _cat_head(fur, a.glasses != "none") if p.species == "고양이" else _dog_head(fur, a.glasses != "none")
    parts = [f'<rect width="360" height="360" fill="#{BG}"/>',
             f'<path d="M30 362 C40 290 110 268 180 268 C250 268 320 290 330 362 Z" fill="#{fur}" {_K}/>']
    if a.outer != "none":
        parts.append(_outer(a.outer))
    if a.neckwear != "none":
        parts.append(_neckwear(a.neckwear, a.neckwear_color))
    else:  # 넥웨어가 없으면 반려동물 목걸이 + 금색 이름표
        parts.append('<path d="M118 300 Q180 330 242 300" fill="none" stroke="#b3261e" stroke-width="12" stroke-linecap="round"/>'
                     f'<circle cx="180" cy="328" r="11" fill="#f4d150" {_K}/>')
    if "pocket_square" in a.details and a.outer != "none":
        parts.append(_pocket_square("ffffff" if a.outer != "white_suit" else "b3261e"))
    parts.append(f'<g transform="translate(180 182) scale(2.4)">{head}</g>')
    parts.append(_hat(a.details, a.hat_color))
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 360">' + "".join(parts) + "</svg>"


def avatar_svg(p: SpyProfile) -> str:
    if p.species != "사람":
        return animal_svg(p)
    try:
        with urllib.request.urlopen(avatar_url(p), timeout=10) as r:
            svg = r.read().decode("utf-8")
    except Exception:
        return SILHOUETTE
    i = svg.rfind("</svg>")
    return svg[:i] + overlay(p) + svg[i:]


def avatar_data_uri(p: SpyProfile) -> str:
    """다운로드한 HTML이 오프라인에서도 보이도록 data URI로 넣습니다."""
    return "data:image/svg+xml;base64," + base64.b64encode(avatar_svg(p).encode("utf-8")).decode()
