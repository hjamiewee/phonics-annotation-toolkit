"""Steps 4 and 4-b: GPC decomposition and frozen sound numbers (the sound axis).

Each lowercase token lists one decomposition per pronunciation in
``data/lexicon/gpc.tsv``, written as grapheme:phoneme pairs with ``|`` between
syllables::

    read    r:r ea:i d:d        (default)
    read    r:r ea:ɛ d:d
    ate     a:eɪ t:t e:         (silent e: empty phoneme)
    every day   e:ɛ v:v | e: r:r y:i | d:d ay:eɪ

Every decomposition is checked: its graphemes must spell the token, and each
syllable must contain exactly one vowel phoneme.

Which pronunciation an occurrence uses is decided by, in order:
    1. a position rule ``Line_ID:Seq``      (``Yesterday I read`` -> /rɛd/)
    2. a sense rule ``p.Lemma-s``           (``n.bow-2`` greeting -> /baʊ/)
    3. the token's default pronunciation

Sound numbers (``a#``) and recording IDs (``Aud_ID``) come from registries that
are only ever appended to, so an assigned number never changes meaning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .store import read_table

# 모음 소리 목록 — 음절마다 이 중 정확히 하나가 있어야 한다 (이중모음·r 모음은 한 소리로 센다)
VOWELS = {"æ", "ɑ", "ɔ", "ɛ", "ɪ", "ʊ", "ʌ", "ə", "i", "u", "eɪ", "aɪ", "oʊ", "aʊ", "ɔɪ", "ər"}
# 소리 판정의 출처
SOURCE_POSITION = "position"
SOURCE_SENSE = "sense"
SOURCE_DEFAULT = "default"
# 판정 규칙 키가 Line_ID:Seq 모양인지 (L00020:3)
POSITION_KEY = re.compile(r"^(L\d+):(\d+)$")


class DecompositionError(ValueError):
    """A GPC decomposition does not spell its token or breaks the syllable rule."""


@dataclass(frozen=True)
class GPC:
    """One grapheme–phoneme correspondence inside a decomposition."""

    seq: int
    gr: str
    ph: str
    syl_no: int
    role: str
    position: str

    @property
    def label(self) -> str:
        """The ``Gr:Ph`` notation used by lesson targets, e.g. ``ea:i`` (silent: ``e:``)."""
        return f"{self.gr}:{self.ph}"


@dataclass
class Pronunciation:
    """One way a token is pronounced, with its decomposition."""

    token: str
    gpcs: list[GPC]
    default: bool = False

    @property
    def phonemes(self) -> str:
        """The pronunciation string: phonemes joined in order, e.g. ``rɛd``."""
        # 소리 기호를 순서대로 이어 붙인다 (묵음은 빈 문자열이라 자연히 빠진다)
        return "".join(g.ph for g in self.gpcs)

    @property
    def syllables(self) -> int:
        """Number of syllables."""
        return max(g.syl_no for g in self.gpcs)


def parse_decomposition(token: str, text: str) -> list[GPC]:
    """Parse ``"r:r ea:i d:d"`` into GPC rows and validate it against ``token``."""
    parsed = []
    for syl_no, syllable in enumerate(text.split("|"), start=1):
        pairs = syllable.split()
        # 음절마다 모음 소리가 정확히 하나 — 0개거나 2개면 음절 경계가 잘못된 것
        vowels = [p for p in pairs if p.split(":", 1)[1] in VOWELS]
        if len(vowels) != 1:
            raise DecompositionError(f"{token!r}: syllable {syl_no} ({syllable.strip()!r}) has {len(vowels)} vowels")
        for pair in pairs:
            if ":" not in pair:
                raise DecompositionError(f"{token!r}: {pair!r} is not grapheme:phoneme")
            gr, ph = pair.split(":", 1)
            parsed.append((gr, ph, syl_no))

    # 글자를 이어 붙이면 낱말 철자가 돼야 한다 (구는 공백을 빼고 비교)
    spelled = "".join(gr for gr, _, _ in parsed)
    if spelled != token.replace(" ", ""):
        raise DecompositionError(f"{token!r}: graphemes spell {spelled!r}")

    # 위치는 소리가 있는 GPC 만으로 정한다 — 묵음 e 뒤에 있어도 t 가 어말
    voiced = [i for i, (_, ph, _) in enumerate(parsed) if ph]
    gpcs = []
    for i, (gr, ph, syl_no) in enumerate(parsed):
        # 역할: 모음 · 자음 · 묵음
        role = "silent" if not ph else ("vowel" if ph in VOWELS else "consonant")
        # 위치: 첫 소리 initial · 마지막 소리 final · 그 사이 medial (소리 하나뿐이면 initial)
        if not ph:
            position = ""
        elif i == voiced[0]:
            position = "initial"
        elif i == voiced[-1]:
            position = "final"
        else:
            position = "medial"
        gpcs.append(GPC(i + 1, gr, ph, syl_no, role, position))
    return gpcs


def load_pronunciations(path: Path) -> dict[str, list[Pronunciation]]:
    """Load every token's pronunciations; a token with several must mark exactly one default."""
    prons: dict[str, list[Pronunciation]] = {}
    for r in read_table(path, required=["token", "gpc", "default"]):
        token = r["token"]
        pron = Pronunciation(token, parse_decomposition(token, r["gpc"]), r["default"] == "Y")
        # 같은 낱말에 같은 소리가 두 번 — 같은 Token·같은 소리면 분해는 하나여야 한다
        if any(p.phonemes == pron.phonemes for p in prons.get(token, [])):
            raise DecompositionError(f"{token!r}: pronunciation {pron.phonemes!r} is decomposed twice")
        prons.setdefault(token, []).append(pron)
    for token, options in prons.items():
        # 소리가 하나면 그것이 기본, 여럿이면 기본 표시가 정확히 하나
        if len(options) == 1:
            options[0].default = True
        elif sum(p.default for p in options) != 1:
            raise DecompositionError(f"{token!r}: {len(options)} pronunciations need exactly one default")
    return prons


def load_sound_rules(path: Path) -> tuple[dict[tuple[str, int], tuple[str, str]], dict[str, str]]:
    """Load sound rules, split into position rules and sense rules.

    Returns ``(by_position, by_sense)`` where ``by_position[(line_id, seq)] = (token, phonemes)``
    and ``by_sense[p_lemma_s] = phonemes``.
    """
    by_position, by_sense = {}, {}
    for r in read_table(path, required=["key", "token", "pronunciation"]):
        m = POSITION_KEY.match(r["key"])
        if m:
            # 자리 규칙 — 판정할 때의 낱말도 함께 둬서 줄이 고쳐지면 잡는다
            by_position[(m.group(1), int(m.group(2)))] = (r["token"], r["pronunciation"])
        else:
            # 뜻 규칙 — 그 뜻이면 언제나 이 소리 (n.bow-2 → baʊ)
            by_sense[r["key"]] = r["pronunciation"]
    return by_position, by_sense


def choose_pronunciation(
    row: dict[str, str],
    prons: dict[str, list[Pronunciation]],
    by_position: dict[tuple[str, int], tuple[str, str]],
    by_sense: dict[str, str],
) -> tuple[Pronunciation, str] | None:
    """Pick the pronunciation of one Word row, or ``None`` if the token has no decomposition."""
    options = prons.get(row["token"].lower())
    if not options:
        # 분해가 없는 낱말 — 추측하지 않고 미해결
        return None
    by_phonemes = {p.phonemes: p for p in options}

    def pick(phonemes: str, where: str) -> Pronunciation:
        # 규칙이 가리키는 소리가 이 낱말의 분해에 없으면 규칙이 잘못된 것
        if phonemes not in by_phonemes:
            raise DecompositionError(f"{where}: {row['token']!r} has no pronunciation {phonemes!r}")
        return by_phonemes[phonemes]

    # 1) 자리 규칙
    rule = by_position.get((row["line_id"], int(row["seq"])))
    if rule is not None:
        token, phonemes = rule
        if token != row["token"]:
            raise DecompositionError(f"{row['line_id']}:{row['seq']}: rule written for {token!r}, token is {row['token']!r}")
        return pick(phonemes, f"{row['line_id']}:{row['seq']}"), SOURCE_POSITION
    # 2) 뜻 규칙
    if row["p.Lemma-s"] in by_sense:
        return pick(by_sense[row["p.Lemma-s"]], row["p.Lemma-s"]), SOURCE_SENSE
    # 3) 기본 소리
    return next(p for p in options if p.default), SOURCE_DEFAULT


@dataclass
class SoundRegistry:
    """Frozen ``a#`` numbers: one row per (token, pronunciation), numbered per token.

    Numbers are never reused. A pronunciation no longer used anywhere keeps its row.
    """

    rows: list[dict[str, str]] = field(default_factory=list)
    new: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "SoundRegistry":
        # 대장이 아직 없으면 빈 대장에서 시작
        return cls(read_table(path, required=["Token-a", "token", "pronunciation"]) if path.exists() else [])

    def number(self, token: str, phonemes: str) -> int:
        """Return the frozen ``a#`` for this sound, registering the next number if it is new."""
        mine = [r for r in self.rows if r["token"] == token]
        for r in mine:
            if r["pronunciation"] == phonemes:
                # 이미 등록된 소리 — 그 번호를 그대로 쓴다
                return int(r["Token-a"].rsplit("-", 1)[1])
        # 새 소리 — 이 낱말의 다음 번호 (지운 번호도 다시 쓰지 않는다)
        n = max((int(r["Token-a"].rsplit("-", 1)[1]) for r in mine), default=0) + 1
        row = {"Token-a": f"{token}-{n}", "token": token, "pronunciation": phonemes}
        self.rows.append(row)
        self.new.append(row)
        return n


@dataclass
class AudRegistry:
    """Frozen recording IDs: one ``A00001``-style ID per pronunciation string."""

    rows: list[dict[str, str]] = field(default_factory=list)
    new: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "AudRegistry":
        return cls(read_table(path, required=["aud_id", "pronunciation"]) if path.exists() else [])

    def aud_id(self, phonemes: str) -> str:
        """Return the recording ID for a pronunciation, registering a new one if needed."""
        for r in self.rows:
            if r["pronunciation"] == phonemes:
                # 같은 발음은 같은 녹음 (to · too · two)
                return r["aud_id"]
        # 새 발음 — 최댓값 + 1
        n = max((int(r["aud_id"][1:]) for r in self.rows), default=0) + 1
        row = {"aud_id": f"A{n:05d}", "pronunciation": phonemes}
        self.rows.append(row)
        self.new.append(row)
        return row["aud_id"]
