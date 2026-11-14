"""Storage layer: read and write tab-separated tables, finding columns by header name.

The pipeline never refers to a column by its position. Every table is read into
rows of ``{header: value}``, so reordering or inserting columns never breaks a step.
Swapping this module for a spreadsheet or database backend leaves the rest of the
pipeline unchanged.
"""

from __future__ import annotations

import csv
from pathlib import Path

# 저장소 맨 위 폴더 (이 파일 위치에서 세 단계 위)
REPO_ROOT = Path(__file__).resolve().parents[2]
# 예시 입력 데이터 폴더
DATA_DIR = REPO_ROOT / "data"


class MissingColumnError(KeyError):
    """Raised when a required header is not present in a table."""


def read_table(path: Path, required: list[str] | None = None) -> list[dict[str, str]]:
    """Read a TSV file into a list of ``{header: value}`` rows.

    Args:
        path: TSV file to read. The first line is the header.
        required: Headers that must exist. Raises ``MissingColumnError`` if any is absent.

    Returns:
        One dict per data row. Missing trailing cells become empty strings.
    """
    # 탭으로 나뉜 파일을 UTF-8 로 연다 (IPA 기호가 있어서 인코딩 고정)
    with open(path, encoding="utf-8", newline="") as f:
        # 첫 줄을 헤더로 읽어 행마다 {헤더: 값} 사전으로 만든다
        reader = csv.DictReader(f, delimiter="\t")
        # 헤더 목록 (파일이 비어 있으면 빈 목록)
        headers = reader.fieldnames or []
        # 꼭 있어야 하는 열이 빠졌는지 확인 — 열은 위치가 아니라 이름으로 찾는다
        missing = [h for h in (required or []) if h not in headers]
        if missing:
            raise MissingColumnError(f"{path.name}: missing columns {missing}")
        # 줄 끝 빈칸이 생략된 행은 None 대신 빈 문자열로 채운다
        return [{h: (row.get(h) or "") for h in headers} for row in reader]


def write_table(path: Path, rows: list[dict[str, str]], headers: list[str]) -> None:
    """Write rows to a TSV file with the given header order."""
    # 결과 폴더가 없으면 만든다
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        # 지정한 헤더 순서로 쓴다 — 사전에 없는 열은 빈칸
        writer = csv.DictWriter(f, fieldnames=headers, delimiter="\t", restval="", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
