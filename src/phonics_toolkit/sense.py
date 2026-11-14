"""Step 3: decide part of speech, lemma, and sense for each token (the meaning axis).

Every judgment comes from a human-maintained file; the code only applies them.

Lookup order for one token:
    1. Context decision for this exact occurrence, keyed by ``(Line_ID, Seq)``
    2. Default for the token with its exact capitalization (``I``, ``Pam``)
    3. Default for the lowercase token (sentence-initial ``The`` -> ``the``)
    4. Otherwise the token is reported as unresolved. Nothing is guessed.

A context decision also stores the token it was written for. If the line is
edited later and that position now holds a different word, the decision is
stale and the run stops instead of silently attaching it to the wrong word.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .store import read_table

# 판정의 출처 — 결과 표에 함께 적어 사람이 검토할 때 본다
SOURCE_CONTEXT = "context"
SOURCE_DEFAULT = "default"


class StaleDecisionError(ValueError):
    """A context decision points to a position that now holds a different token."""


class UnknownSenseError(KeyError):
    """A decision refers to a sense key that is not in the sense dictionary."""


@dataclass(frozen=True)
class Sense:
    """One entry of the sense dictionary."""

    pos: str
    lemma: str
    s: int
    meaning_ko: str
    meaning_en: str

    @property
    def key(self) -> str:
        """The sense key ``p.Lemma-s``, e.g. ``v.read-1`` or ``n.hot dog-1``."""
        return sense_key(self.pos, self.lemma, self.s)


def sense_key(pos: str, lemma: str, s: int | str) -> str:
    """Build a sense key: part of speech + ``.`` + lemma + ``-`` + sense number."""
    # 예: ("n", "bow", 2) → n.bow-2
    return f"{pos}.{lemma}-{int(s)}"


def load_senses(path: Path) -> dict[str, Sense]:
    """Load the sense dictionary, keyed by ``p.Lemma-s``."""
    cols = ["pos", "lemma", "s#", "meaning_ko", "meaning_en"]
    senses = {}
    for r in read_table(path, required=cols):
        sense = Sense(r["pos"], r["lemma"], int(r["s#"]), r["meaning_ko"], r["meaning_en"])
        # 같은 뜻 키가 두 번 나오면 사전이 잘못된 것
        if sense.key in senses:
            raise ValueError(f"duplicate sense key {sense.key}")
        senses[sense.key] = sense
    return senses


def load_defaults(path: Path) -> dict[str, str]:
    """Load default senses: token as written -> sense key."""
    rows = read_table(path, required=["token", "pos", "lemma", "s#"])
    # 키는 파일에 적힌 표기 그대로 (대소문자 구분 — I · Pam 은 대문자로 적는다)
    return {r["token"]: sense_key(r["pos"], r["lemma"], r["s#"]) for r in rows}


def load_context(path: Path) -> dict[tuple[str, int], dict[str, str]]:
    """Load context decisions keyed by ``(Line_ID, Seq)``."""
    rows = read_table(path, required=["line_id", "seq", "token", "pos", "lemma", "s#"])
    decisions = {}
    for r in rows:
        key = (r["line_id"], int(r["seq"]))
        # 한 자리에 판정이 둘이면 어느 것을 쓸지 알 수 없다
        if key in decisions:
            raise ValueError(f"duplicate context decision for {key}")
        decisions[key] = {**r, "sense": sense_key(r["pos"], r["lemma"], r["s#"])}
    return decisions


def resolve(
    line_id: str,
    seq: int,
    token: str,
    context: dict[tuple[str, int], dict[str, str]],
    defaults: dict[str, str],
) -> tuple[str, str] | None:
    """Return ``(sense_key, source)`` for one token, or ``None`` if unresolved."""
    # 1) 이 자리에 사람이 적은 문맥 판정이 있으면 그것을 쓴다
    decision = context.get((line_id, seq))
    if decision is not None:
        # 판정을 적을 때의 낱말과 지금 낱말이 다르면 줄이 고쳐진 것 — 멈춘다
        if decision["token"] != token:
            raise StaleDecisionError(
                f"{line_id} seq {seq}: decision was written for {decision['token']!r}, "
                f"but the token is now {token!r}"
            )
        return decision["sense"], SOURCE_CONTEXT
    # 2) 대소문자까지 같은 대표값 (I · Pam · Tom)
    if token in defaults:
        return defaults[token], SOURCE_DEFAULT
    # 3) 소문자로 바꾼 대표값 (문장 첫머리 The → the)
    if token.lower() in defaults:
        return defaults[token.lower()], SOURCE_DEFAULT
    # 4) 어디에도 없으면 추측하지 않고 미해결로 남긴다
    return None
