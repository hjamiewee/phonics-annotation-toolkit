"""Build the Word table (steps 2–3) and the sense dictionary view.

Reads passage lines, tokenizes them, attaches a sense to every token, and
produces two tables:

* ``words.tsv``      one row per word occurrence, keyed by ``(Line_ID, Seq)``
* ``word_sense.tsv`` one row per sense actually used, with the tokens that use it

Usage:
    python -m phonics_toolkit.words                    # preview a summary
    python -m phonics_toolkit.words --write            # write out/words.tsv, out/word_sense.tsv
    python -m phonics_toolkit.words --update-snapshot  # accept the current result as the new snapshot
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .sense import SOURCE_CONTEXT, UnknownSenseError, load_context, load_defaults, load_senses, resolve
from .store import DATA_DIR, REPO_ROOT, read_table, write_table
from .tokens import load_phrases, tokenize_line

# 결정 파일·사전 위치
DECISIONS_DIR = DATA_DIR / "decisions"
LEXICON_DIR = DATA_DIR / "lexicon"
# 산출물 위치 (git 에 올리지 않는다)
OUT_DIR = REPO_ROOT / "out"
# 재현 검사용 기준 결과 (git 에 올려 판정 변화를 diff 로 본다)
SNAPSHOT = REPO_ROOT / "tests" / "snapshots" / "words.tsv"

# Word 표의 열 순서
WORD_COLUMNS = [
    "line_id", "seq", "token", "p.Token", "p.Lemma-s",
    "pos", "lemma", "s#", "meaning_ko", "meaning_en", "source",
]
# 뜻 사전 보기의 열 순서
SENSE_COLUMNS = ["p.Lemma-s", "tokens", "meaning_ko", "meaning_en", "count"]


@dataclass
class WordBuild:
    """Result of one build: resolved rows plus anything a human still has to decide."""

    rows: list[dict[str, str]] = field(default_factory=list)
    unresolved: list[dict[str, str]] = field(default_factory=list)


def p_token(pos: str, token: str, lemma: str) -> str:
    """Bridge key between the two axes: part of speech + token, e.g. ``v.read``.

    The token is lowercased unless its lemma is capitalized (``pron.I``, ``propn.Pam``),
    so sentence-initial capitals do not split one word into two keys.
    """
    # 원형이 대문자로 시작하는 낱말(고유명사 · I)만 표기를 살린다
    surface = token if lemma[:1].isupper() else token.lower()
    return f"{pos}.{surface}"


def build_words(data_dir: Path = DATA_DIR) -> WordBuild:
    """Tokenize every line and attach a sense to every token."""
    decisions, lexicon = data_dir / "decisions", data_dir / "lexicon"
    # 사람이 관리하는 입력 네 가지: 구 목록 · 뜻 사전 · 대표값 · 문맥 판정
    phrases = load_phrases(decisions / "phrases.tsv")
    senses = load_senses(lexicon / "senses.tsv")
    defaults = load_defaults(decisions / "defaults.tsv")
    context = load_context(decisions / "context.tsv")

    # 판정 파일이 사전에 없는 뜻을 가리키면 시작 전에 멈춘다
    referenced = set(defaults.values()) | {d["sense"] for d in context.values()}
    missing = sorted(referenced - senses.keys())
    if missing:
        raise UnknownSenseError(f"senses not in senses.tsv: {missing}")

    build = WordBuild()
    # 문맥 판정이 실제로 쓰였는지 표시 — 안 쓰인 판정은 가리키는 자리가 사라진 것
    used_context = set()
    for line in read_table(data_dir / "lines.tsv", required=["line_id", "text"]):
        for seq, token in enumerate(tokenize_line(line["text"], phrases), start=1):
            found = resolve(line["line_id"], seq, token, context, defaults)
            if found is None:
                # 미해결 — 사람이 대표값이나 문맥 판정을 적어야 한다
                build.unresolved.append({"line_id": line["line_id"], "seq": str(seq), "token": token})
                continue
            key, source = found
            if source == SOURCE_CONTEXT:
                used_context.add((line["line_id"], seq))
            s = senses[key]
            build.rows.append({
                "line_id": line["line_id"],
                "seq": str(seq),
                "token": token,
                "p.Token": p_token(s.pos, token, s.lemma),
                "p.Lemma-s": key,
                "pos": s.pos,
                "lemma": s.lemma,
                "s#": str(s.s),
                "meaning_ko": s.meaning_ko,
                "meaning_en": s.meaning_en,
                "source": source,
            })

    # 어느 낱말에도 닿지 않은 문맥 판정이 있으면 줄이 지워졌거나 Seq 가 밀린 것
    orphaned = sorted(set(context) - used_context)
    if orphaned:
        raise ValueError(f"context decisions that match no token: {orphaned}")
    return build


def sense_view(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Aggregate the Word rows into one row per sense, with the tokens that use it."""
    tokens, count, first = defaultdict(set), Counter(), {}
    for r in rows:
        key = r["p.Lemma-s"]
        # 같은 뜻을 쓰는 표면형을 모은다 (n.cat-1 ← cat, cats)
        tokens[key].add(r["p.Token"].split(".", 1)[1])
        count[key] += 1
        first.setdefault(key, r)
    return [
        {
            "p.Lemma-s": key,
            "tokens": ", ".join(sorted(tokens[key])),
            "meaning_ko": first[key]["meaning_ko"],
            "meaning_en": first[key]["meaning_en"],
            "count": str(count[key]),
        }
        for key in sorted(tokens)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Word table and sense view.")
    parser.add_argument("--write", action="store_true", help="write out/words.tsv and out/word_sense.tsv")
    parser.add_argument("--update-snapshot", action="store_true", help="overwrite tests/snapshots/words.tsv")
    args = parser.parse_args()

    build = build_words()
    by_source = Counter(r["source"] for r in build.rows)
    # 요약: 토큰 수 · 출처별 수 · 미해결
    print(f"tokens: {len(build.rows) + len(build.unresolved)}  "
          f"context: {by_source['context']}  default: {by_source['default']}  "
          f"unresolved: {len(build.unresolved)}")
    for u in build.unresolved:
        print(f"  unresolved  {u['line_id']} seq {u['seq']}  {u['token']!r}")

    if args.write:
        write_table(OUT_DIR / "words.tsv", build.rows, WORD_COLUMNS)
        write_table(OUT_DIR / "word_sense.tsv", sense_view(build.rows), SENSE_COLUMNS)
        print("written: out/words.tsv, out/word_sense.tsv")
    if args.update_snapshot:
        # 판정을 바꾼 뒤 결과를 확인했을 때만 기준을 새로 찍는다
        write_table(SNAPSHOT, build.rows, WORD_COLUMNS)
        print(f"snapshot updated: {SNAPSHOT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
