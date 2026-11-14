"""Decodability: how much of each lesson's text a learner can read with what has been taught so far.

Definitions
-----------
* Lessons are taught in the order of ``data/lessons.tsv``.
* ``taught(k)`` = baseline GPCs (assumed known before the first lesson)
  plus every main and additional GPC of lessons 1..k.
* A word occurrence in lesson k is

  - **decodable** if every GPC with a sound is in ``taught(k)``
    (silent letters are ignored; see the docs for this limitation),
  - **sight** if it is not decodable but is a high-frequency word,
  - **blocked** otherwise. The GPCs it is missing are its *blockers*.

* Per lesson: ``decodable %`` and ``readable %`` (decodable + sight).

Usage:
    python -m phonics_toolkit.decodability          # print the report
    python -m phonics_toolkit.decodability --write  # also write out/decodability.tsv
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .pipeline import OUT_DIR, build
from .sound import GPC
from .store import DATA_DIR, REPO_ROOT, read_table, write_table
from .target import split_list

# 첫 레슨 전에 안다고 가정하는 GPC (단자음) — 분석의 가정이라 analysis/ 에 둔다
BASELINE = REPO_ROOT / "analysis" / "baseline_gpc.tsv"
# 단어 분류
DECODABLE, SIGHT, BLOCKED = "decodable", "sight", "blocked"
REPORT_COLUMNS = ["lesson_id", "title", "new_gpc", "tokens", "decodable", "sight", "blocked",
                  "decodable_pct", "readable_pct", "top_blockers"]


@dataclass
class LessonReport:
    """Decodability of one lesson's text."""

    lesson_id: str
    title: str
    new_gpc: list[str]
    counts: Counter = field(default_factory=Counter)
    blockers: Counter = field(default_factory=Counter)

    @property
    def tokens(self) -> int:
        return sum(self.counts.values())

    def pct(self, *kinds: str) -> float:
        """Share of tokens in the given categories, in percent."""
        # 토큰이 없는 레슨은 0 으로 둔다
        return 100 * sum(self.counts[k] for k in kinds) / self.tokens if self.tokens else 0.0


def classify(gpcs: list[GPC], is_hfw: bool, taught: set[str]) -> tuple[str, list[str]]:
    """Classify one word occurrence; returns ``(category, missing GPC labels)``."""
    # 소리가 있는 GPC 중 아직 안 배운 것 (묵음 글자는 보지 않는다)
    missing = [g.label for g in gpcs if g.ph and g.label not in taught]
    if not missing:
        return DECODABLE, []
    # 해독은 못 하지만 고빈도어라 통째로 읽을 수 있는 경우
    return (SIGHT if is_hfw else BLOCKED), missing


def analyze(data_dir: Path = DATA_DIR, baseline_path: Path = BASELINE) -> list[LessonReport]:
    """Compute a decodability report per lesson, in teaching order."""
    result = build(data_dir)
    # 소리 키 → 분해 (word_gpc 표에서 다시 묶는다)
    gpcs_of: dict[str, list[GPC]] = {}
    for g in result.word_gpc:
        gpcs_of.setdefault(g["Token-a"], []).append(
            GPC(int(g["seq"]), g["gr"], g["ph"], int(g["syl_no"]), g["role"], g["position"]))

    taught = {r["gpc"] for r in read_table(baseline_path, required=["gpc"])}
    reports = []
    for lesson in read_table(data_dir / "lessons.tsv"):
        # 이 레슨이 새로 가르치는 GPC 를 누적 집합에 더한다 (메인 + 추가)
        new = sorted((split_list(lesson["gpc"]) | split_list(lesson["gpc_add"])) - taught)
        taught |= set(new)
        report = LessonReport(lesson["lesson_id"], lesson["title"], new)
        for w in result.words:
            if w["lesson_id"] != lesson["lesson_id"] or not w["Token-a"]:
                continue
            kind, missing = classify(gpcs_of[w["Token-a"]], w["hfw"] == "Y", taught)
            report.counts[kind] += 1
            if kind == BLOCKED:
                report.blockers.update(missing)
        reports.append(report)
    return reports


def to_rows(reports: list[LessonReport]) -> list[dict[str, str]]:
    """Flatten reports into table rows."""
    return [
        {
            "lesson_id": r.lesson_id,
            "title": r.title,
            "new_gpc": ", ".join(r.new_gpc),
            "tokens": str(r.tokens),
            "decodable": str(r.counts[DECODABLE]),
            "sight": str(r.counts[SIGHT]),
            "blocked": str(r.counts[BLOCKED]),
            "decodable_pct": f"{r.pct(DECODABLE):.0f}",
            "readable_pct": f"{r.pct(DECODABLE, SIGHT):.0f}",
            # 막힌 낱말을 가장 많이 만든 미학습 GPC 세 개
            "top_blockers": ", ".join(f"{g} ({n})" for g, n in r.blockers.most_common(3)),
        }
        for r in reports
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-lesson decodability report.")
    parser.add_argument("--write", action="store_true", help="write out/decodability.tsv")
    args = parser.parse_args()

    rows = to_rows(analyze())
    # 마크다운 표로 출력 — 문서에 그대로 붙일 수 있다
    head = ["lesson", "new GPCs", "tokens", "decodable %", "readable %", "top blockers"]
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for r in rows:
        print(f"| {r['lesson_id']} | {r['new_gpc'] or '—'} | {r['tokens']} | "
              f"{r['decodable_pct']} | {r['readable_pct']} | {r['top_blockers'] or '—'} |")
    if args.write:
        write_table(OUT_DIR / "decodability.tsv", rows, REPORT_COLUMNS)
        print("written: out/decodability.tsv")


if __name__ == "__main__":
    main()
