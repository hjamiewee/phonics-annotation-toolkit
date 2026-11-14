"""Step 5: lesson target judgment (``target`` for main targets, ``add_target`` for additional).

A lesson describes its targets on four axes:

* ``gpc``          GPCs taught, e.g. ``a:æ`` or ``s:s, s:z``
* ``environment``  where the GPC must occur: ``initial``, ``medial``, ``final``
* ``morph``        word-internal pieces, e.g. ``plural``
* ``lexical``      whole-word relations, e.g. ``homophone``

A word in the lesson is a target (``Y``) when either path holds:

* **Phonics path**: every axis that is filled among gpc/environment/morph matches.
  GPC and environment are checked together (the taught GPC must sit in that
  position), and morph is ANDed with them: in a plural lesson ``has`` ends in
  /z/ but is not a plural, so it is ``N``.
* **Lexical path**: the word stands in the named relation with another word
  presented in the same lesson.

A lesson with no axis filled is not judged and gets an empty value.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .sound import GPC

# 어휘 관계 이름
HOMOPHONE = "homophone"


def split_list(text: str) -> set[str]:
    """``"s:s, s:z"`` -> ``{"s:s", "s:z"}``; an empty cell gives an empty set."""
    return {part.strip() for part in text.split(",") if part.strip()}


@dataclass(frozen=True)
class Targets:
    """The four target axes of one lesson (main or additional)."""

    gpc: frozenset[str]
    environment: frozenset[str]
    morph: frozenset[str]
    lexical: frozenset[str]

    @classmethod
    def from_lesson(cls, lesson: dict[str, str], suffix: str = "") -> "Targets":
        """Read the main axes (``suffix=""``) or the additional axes (``suffix="_add"``)."""
        return cls(*(frozenset(split_list(lesson[f"{axis}{suffix}"]))
                     for axis in ("gpc", "environment", "morph", "lexical")))

    @property
    def is_empty(self) -> bool:
        """True when the lesson names no target on any axis."""
        return not (self.gpc or self.environment or self.morph or self.lexical)


def phonics_match(gpcs: list[GPC], inflection: str, t: Targets) -> bool:
    """Phonics path: GPC (in its environment) AND morph, for whichever axes are filled."""
    if not (t.gpc or t.environment or t.morph):
        return False
    if t.gpc or t.environment:
        # 가르친 GPC 가 정해진 위치에 있는가 (위치가 비면 어디든 된다)
        hit = any(
            (not t.gpc or g.label in t.gpc) and (not t.environment or g.position in t.environment)
            for g in gpcs
        )
        if not hit:
            return False
    # 형태 축이 있으면 굴절 라벨도 맞아야 한다 (AND)
    return not t.morph or inflection in t.morph


def homophones(rows: list[dict[str, str]]) -> set[int]:
    """Indexes of rows whose pronunciation is shared by a differently spelled word in ``rows``."""
    spellings = defaultdict(set)
    for r in rows:
        if r["pronunciation"]:
            # 발음별로 철자를 모은다
            spellings[r["pronunciation"]].add(r["token"].lower())
    # 같은 발음에 철자가 둘 이상이면 동음어 (to · too · two)
    return {i for i, r in enumerate(rows) if len(spellings.get(r["pronunciation"], ())) > 1}


def judge_lesson(rows: list[dict[str, str]], gpcs_of: dict[str, list[GPC]], t: Targets) -> list[str]:
    """Judge every Word row of one lesson; returns ``Y``/``N`` per row, or ``""`` if nothing to judge."""
    if t.is_empty:
        # 타깃이 없는 레슨은 판정하지 않는다
        return [""] * len(rows)
    lexical_hits = homophones(rows) if HOMOPHONE in t.lexical else set()
    result = []
    for i, r in enumerate(rows):
        gpcs = gpcs_of.get(r["Token-a"], [])
        # 두 경로 중 하나라도 맞으면 타깃
        ok = phonics_match(gpcs, r["inflection"], t) or i in lexical_hits
        result.append("Y" if ok else "N")
    return result
