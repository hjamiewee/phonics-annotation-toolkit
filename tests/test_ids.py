"""Step 1: literal ID assignment."""

from phonics_toolkit.ids import fill_blank_ids


def test_new_ids_continue_from_the_current_maximum():
    """Blank rows get max + 1, max + 2, ... and existing IDs are left alone."""
    # 중간에 빈 행이 있어도 기존 번호는 그대로, 새 번호는 최댓값 다음부터
    rows = [{"line_id": "L00003"}, {"line_id": ""}, {"line_id": "L00001"}, {"line_id": ""}]
    assigned = fill_blank_ids(rows, "line_id", "L")
    assert assigned == ["L00004", "L00005"]
    assert [r["line_id"] for r in rows] == ["L00003", "L00004", "L00001", "L00005"]


def test_ids_start_at_one_when_none_exist():
    """With no existing IDs, numbering starts at 1."""
    rows = [{"line_id": ""}, {"line_id": ""}]
    assert fill_blank_ids(rows, "line_id", "L") == ["L00001", "L00002"]


def test_running_twice_assigns_nothing_new():
    """Assignment is idempotent: a second run finds no blank rows."""
    # 두 번 돌려도 번호가 바뀌거나 늘지 않는다
    rows = [{"line_id": ""}]
    fill_blank_ids(rows, "line_id", "L")
    assert fill_blank_ids(rows, "line_id", "L") == []
