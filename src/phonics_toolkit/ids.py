"""Step 1: assign literal IDs to rows that do not have one yet.

IDs are stored as values, never computed from row positions, so sorting or
inserting rows can never renumber them. A new ID is the current maximum + 1.

Usage:
    python -m phonics_toolkit.ids            # preview
    python -m phonics_toolkit.ids --write    # fill blank Line_IDs in data/lines.tsv
"""

from __future__ import annotations

import argparse
import re

from .store import DATA_DIR, read_table, write_table

# Line_ID 형식: L + 다섯 자리 숫자 (L00001)
LINE_PREFIX = "L"
ID_DIGITS = 5


def fill_blank_ids(rows: list[dict[str, str]], column: str, prefix: str) -> list[str]:
    """Give every row with an empty ``column`` the next free ID, in row order.

    Existing IDs are never touched. Returns the list of newly assigned IDs.
    """
    # 이 접두어로 된 기존 ID 의 숫자 부분만 모은다 (L00026 → 26)
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    used = [int(m.group(1)) for r in rows if (m := pattern.match(r[column]))]
    # 다음 번호 = 기존 최댓값 + 1 (기존 ID 가 없으면 1부터)
    next_num = max(used, default=0) + 1
    assigned = []
    for row in rows:
        # 이미 ID 가 있는 행은 건드리지 않는다
        if row[column]:
            continue
        # 빈 행에만 새 번호를 값으로 적는다
        row[column] = f"{prefix}{next_num:0{ID_DIGITS}d}"
        assigned.append(row[column])
        next_num += 1
    return assigned


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill blank Line_IDs.")
    parser.add_argument("--write", action="store_true", help="write the result back to data/lines.tsv")
    args = parser.parse_args()

    path = DATA_DIR / "lines.tsv"
    rows = read_table(path, required=["line_id"])
    # 원래 열 순서를 그대로 지켜서 다시 쓴다
    headers = list(rows[0].keys()) if rows else ["line_id"]
    assigned = fill_blank_ids(rows, "line_id", LINE_PREFIX)

    # 기본은 미리보기 — --write 를 붙여야 파일에 반영한다
    print(f"new Line_IDs: {len(assigned)}" + (f" ({assigned[0]} ~ {assigned[-1]})" if assigned else ""))
    if args.write and assigned:
        write_table(path, rows, headers)
        print(f"written: {path.relative_to(DATA_DIR.parent)}")


if __name__ == "__main__":
    main()
