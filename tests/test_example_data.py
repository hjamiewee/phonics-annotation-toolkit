"""Sanity checks on the example input data."""

from phonics_toolkit.store import DATA_DIR, read_table

# Lesson 탭에 꼭 있어야 하는 열 — 메인 타깃 4축 + 추가 타깃 4축
LESSON_COLUMNS = [
    "lesson_id", "level", "unit", "lesson", "title",
    "gpc", "environment", "morph", "lexical",
    "gpc_add", "environment_add", "morph_add", "lexical_add",
]
# Line 탭에 꼭 있어야 하는 열
LINE_COLUMNS = ["line_id", "lesson_id", "activity", "line_num", "line_type", "text"]
# 지문 한 줄의 종류
LINE_TYPES = {"word", "phrase", "sentence"}


def test_every_row_has_as_many_cells_as_the_header():
    """Raw TSV rows must have exactly one cell per header, even when trailing cells are empty."""
    for name in ("lessons.tsv", "lines.tsv"):
        # 읽기 함수는 모자란 칸을 빈칸으로 채워 주므로, 원본 줄을 직접 세어 확인한다
        rows = (DATA_DIR / name).read_text(encoding="utf-8").splitlines()
        width = len(rows[0].split("\t"))
        # 헤더와 칸 수가 다른 줄 번호 (1부터)
        bad = [i for i, r in enumerate(rows, 1) if len(r.split("\t")) != width]
        assert not bad, f"{name}: rows {bad} do not have {width} cells"


def test_lessons_have_required_columns_and_unique_ids():
    """Every lesson row has the required columns and a unique lesson_id."""
    # 필요한 열이 없으면 read_table 이 오류를 낸다
    lessons = read_table(DATA_DIR / "lessons.tsv", required=LESSON_COLUMNS)
    ids = [r["lesson_id"] for r in lessons]
    # 레슨 ID 는 겹치면 안 된다
    assert len(ids) == len(set(ids))


def test_lines_reference_existing_lessons():
    """Every line has a unique literal Line_ID and belongs to a known lesson."""
    lessons = {r["lesson_id"] for r in read_table(DATA_DIR / "lessons.tsv")}
    lines = read_table(DATA_DIR / "lines.tsv", required=LINE_COLUMNS)
    ids = [r["line_id"] for r in lines]
    # Line_ID 는 값으로 고정된 번호라 겹치거나 비면 안 된다
    assert all(ids) and len(ids) == len(set(ids))
    # 모든 줄이 실제로 있는 레슨에 속해야 한다
    assert {r["lesson_id"] for r in lines} <= lessons
    # 줄 종류는 정해진 세 가지 중 하나
    assert {r["line_type"] for r in lines} <= LINE_TYPES
