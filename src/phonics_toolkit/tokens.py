"""Step 2: split a passage line into word tokens and merge listed phrases.

Only words become tokens; punctuation and list separators are dropped.
Multi-word units (compounds such as ``hot dog``, phrases such as ``every day``)
are merged only when they appear in the phrase list. Merging is never guessed,
because ``hot dog`` is one word but ``hot pot`` is an adjective plus a noun.

``Seq`` (a token's position in its line) is counted *after* merging, so a
merged phrase occupies a single position.
"""

from __future__ import annotations

import re
from pathlib import Path

from .store import read_table

# 낱말 = 영문자 덩어리. 안쪽의 아포스트로피·하이픈은 낱말에 붙여 둔다 (Pam's · good-bye)
WORD = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")


def split_words(text: str) -> list[str]:
    """Return the words of ``text`` in order, keeping their original capitalization."""
    # 마침표·쉼표·가운뎃점(·) 같은 기호는 토큰이 되지 않는다
    return WORD.findall(text)


def load_phrases(path: Path) -> set[tuple[str, ...]]:
    """Load the phrase list as lowercase word tuples, e.g. ``("hot", "dog")``."""
    rows = read_table(path, required=["phrase"])
    # 비교는 소문자로 — 문장 첫머리의 대문자(Hot dog ...)도 같은 구로 잡는다
    return {tuple(r["phrase"].lower().split()) for r in rows if r["phrase"].strip()}


def merge_phrases(words: list[str], phrases: set[tuple[str, ...]]) -> list[str]:
    """Merge every listed phrase into one token, preferring the longest match.

    Example: ``["Tom", "ate", "a", "hot", "dog"]`` with ``{("hot", "dog")}``
    becomes ``["Tom", "ate", "a", "hot dog"]``.
    """
    # 목록에 있는 가장 긴 구의 낱말 수 — 그보다 길게는 볼 필요가 없다
    max_len = max((len(p) for p in phrases), default=1)
    lowered = [w.lower() for w in words]
    merged, i = [], 0
    while i < len(words):
        # 긴 구부터 맞춰 본다 (a lot of 가 a lot 보다 먼저)
        for n in range(min(max_len, len(words) - i), 1, -1):
            if tuple(lowered[i:i + n]) in phrases:
                # 원래 표기를 살려 공백으로 잇는다
                merged.append(" ".join(words[i:i + n]))
                i += n
                break
        else:
            # 맞는 구가 없으면 낱말 하나를 그대로 토큰으로
            merged.append(words[i])
            i += 1
    return merged


def tokenize_line(text: str, phrases: set[tuple[str, ...]]) -> list[str]:
    """Split a line into tokens and merge phrases. Index + 1 is the token's ``Seq``."""
    return merge_phrases(split_words(text), phrases)
