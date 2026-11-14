"""Step 8: inflection labels (plural, third person, past, ...).

Order of evidence:
    1. A context decision for this occurrence (``Yesterday I read`` -> past),
       needed when the form looks exactly like the lemma.
    2. The irregular-form list (``sat`` -> past of ``sit``).
    3. Regular endings checked against the lemma (``cats`` = ``cat`` + s -> plural).

A word whose token equals its lemma and has no context decision gets no label.
"""

from __future__ import annotations

from pathlib import Path

from .store import read_table

# 라벨 이름 (레슨의 morph 열도 이 이름을 쓴다)
PLURAL = "plural"
THIRD_PERSON = "third_person"
PAST = "past"
PROGRESSIVE = "progressive"
COMPARATIVE = "comparative"
SUPERLATIVE = "superlative"


def load_irregular(path: Path) -> dict[tuple[str, str], str]:
    """Irregular forms keyed by ``(form, lemma)``, e.g. ``("sat", "sit") -> "past"``."""
    rows = read_table(path, required=["form", "lemma", "label"])
    # 원형까지 키에 넣는다 — 같은 철자가 다른 원형의 굴절형일 수 있어서
    return {(r["form"], r["lemma"]): r["label"] for r in rows}


def load_inflection_context(path: Path) -> dict[tuple[str, int], tuple[str, str]]:
    """Context decisions keyed by ``(Line_ID, Seq)`` -> ``(token, label)``."""
    rows = read_table(path, required=["line_id", "seq", "token", "label"])
    return {(r["line_id"], int(r["seq"])): (r["token"], r["label"]) for r in rows}


def regular_label(pos: str, token: str, lemma: str) -> str:
    """Label a regular inflection by comparing the token with its lemma."""
    t, l = token.lower(), lemma.lower()
    # 원형과 같으면 굴절 없음
    if t == l:
        return ""
    # 명사: cat → cats · box → boxes · baby → babies
    if pos == "n" and t in {l + "s", l + "es", l[:-1] + "ies"}:
        return PLURAL
    if pos == "v":
        # 동사 -s: nap → naps · fix → fixes
        if t in {l + "s", l + "es", l[:-1] + "ies"}:
            return THIRD_PERSON
        # 동사 -ing: nap → napping (자음 중복) · bake → baking (e 탈락)
        if t.endswith("ing") and t in {l + "ing", l + l[-1] + "ing", l[:-1] + "ing"}:
            return PROGRESSIVE
        # 동사 -ed: jump → jumped · nap → napped · bake → baked
        if t in {l + "ed", l + l[-1] + "ed", l + "d", l[:-1] + "ied"}:
            return PAST
    if pos in {"adj", "adv"}:
        # 비교급·최상급: big → bigger · biggest
        if t in {l + "er", l + l[-1] + "er", l + "r", l[:-1] + "ier"}:
            return COMPARATIVE
        if t in {l + "est", l + l[-1] + "est", l + "st", l[:-1] + "iest"}:
            return SUPERLATIVE
    # 규칙으로 설명이 안 되면 비워 둔다 (불규칙형은 목록에 적는다)
    return ""


def label(
    row: dict[str, str],
    irregular: dict[tuple[str, str], str],
    context: dict[tuple[str, int], tuple[str, str]],
) -> str:
    """Return the inflection label of one Word row."""
    # 1) 문맥 판정 — read(현재) / read(과거) 처럼 철자로는 알 수 없는 경우
    decision = context.get((row["line_id"], int(row["seq"])))
    if decision is not None:
        token, decided = decision
        if token != row["token"]:
            raise ValueError(f"{row['line_id']}:{row['seq']}: inflection decision written for {token!r}")
        return decided
    # 2) 불규칙형 목록
    key = (row["token"].lower(), row["lemma"].lower())
    if key in irregular:
        return irregular[key]
    # 3) 규칙 어미
    return regular_label(row["pos"], row["token"], row["lemma"])
