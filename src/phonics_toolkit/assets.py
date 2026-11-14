"""Step 9: image and audio asset lists.

* Image assets follow the **meaning axis**: one image per sense, split further
  by forms that change the picture (``n.cat-1.pl`` for several cats).
* Audio assets follow the **sound axis**: one recording per pronunciation, shared
  by every spelling that sounds the same (``to``, ``too``, ``two``).
"""

from __future__ import annotations

from collections import defaultdict

from .inflection import COMPARATIVE, PLURAL, SUPERLATIVE

# 그림으로 그리기 어려운 기능어 품사 — 이미지 목록에서 뺀다
FUNCTION_POS = {"det", "aux", "conj", "part"}
# 그림이 달라지는 형태의 꼬리표
FORM_SUFFIX = {PLURAL: ".pl", COMPARATIVE: ".cmp", SUPERLATIVE: ".sup"}

IMAGE_COLUMNS = ["image_key", "p.Lemma-s", "meaning_ko", "meaning_en", "tokens", "count", "target_count", "lessons"]
AUDIO_COLUMNS = ["aud_id", "pronunciation", "syl_cnt", "Token-a", "p.Token", "count"]


def image_key(row: dict[str, str]) -> str:
    """Image unit key: the sense key plus a form suffix when the form changes the picture."""
    # 복수형·비교급·최상급만 꼬리표를 붙인다 (과거형은 그림이 같다고 본다)
    return row["p.Lemma-s"] + FORM_SUFFIX.get(row["inflection"], "")


def image_assets(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """One row per image unit, with usage counts and the lessons that use it."""
    groups = defaultdict(list)
    for r in rows:
        if r["pos"] in FUNCTION_POS:
            continue
        groups[image_key(r)].append(r)
    out = []
    for key in sorted(groups):
        rs = groups[key]
        out.append({
            "image_key": key,
            "p.Lemma-s": rs[0]["p.Lemma-s"],
            "meaning_ko": rs[0]["meaning_ko"],
            "meaning_en": rs[0]["meaning_en"],
            # 이 그림을 쓰는 표면형
            "tokens": ", ".join(sorted({r["token"].lower() for r in rs})),
            "count": str(len(rs)),
            # 레슨 타깃(메인 또는 추가)으로 쓰인 횟수 — 우선순위를 정할 때 본다
            "target_count": str(sum(r["target"] == "Y" or r["add_target"] == "Y" for r in rs)),
            "lessons": ", ".join(sorted({r["lesson_id"] for r in rs})),
        })
    return out


def audio_assets(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """One row per recording (pronunciation), listing every sound key and spelling that uses it."""
    groups = defaultdict(list)
    for r in rows:
        if r["aud_id"]:
            groups[r["aud_id"]].append(r)
    return [
        {
            "aud_id": aud_id,
            "pronunciation": rs[0]["pronunciation"],
            "syl_cnt": rs[0]["syl_cnt"],
            # 같은 발음을 쓰는 소리 키와 품사+표면형 — 녹음 하나를 함께 쓴다
            "Token-a": ", ".join(sorted({r["Token-a"] for r in rs})),
            "p.Token": ", ".join(sorted({r["p.Token"] for r in rs})),
            "count": str(len(rs)),
        }
        for aud_id, rs in sorted(groups.items())
    ]
