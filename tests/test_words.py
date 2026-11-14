"""Steps 2–3 end to end on the example data, plus the reproduction check."""

import shutil

import pytest

from phonics_toolkit.store import DATA_DIR, read_table
from phonics_toolkit.words import SNAPSHOT, WORD_COLUMNS, build_words, sense_view


@pytest.fixture(scope="module")
def build():
    """Build the Word table once for all tests in this module."""
    return build_words()


def by_position(build, line_id, seq):
    """Return the Word row at ``(line_id, seq)``."""
    # 문맥 키로 Word 행 하나를 찾는다
    return next(r for r in build.rows if r["line_id"] == line_id and r["seq"] == str(seq))


def test_every_example_token_is_resolved(build):
    """The example data has a decision or default for every token."""
    assert build.unresolved == []


def test_result_matches_the_snapshot(build):
    """Reproduction check: any change in a judgment shows up as a snapshot diff.

    After an intended change, review the diff and run
    ``python -m phonics_toolkit.words --update-snapshot``.
    """
    # 기준 결과와 한 칸이라도 다르면 실패 — 의도한 변경이면 스냅샷을 새로 찍는다
    expected = read_table(SNAPSHOT, required=WORD_COLUMNS)
    assert build.rows == expected


def test_read_has_one_sense_in_present_and_past(build):
    """``read`` keeps the same sense whether present or past (it differs only on the sound axis)."""
    # 현재형(L00019)과 과거형(L00020) 모두 v.read-1
    assert by_position(build, "L00019", 2)["p.Lemma-s"] == "v.read-1"
    assert by_position(build, "L00020", 3)["p.Lemma-s"] == "v.read-1"


def test_bow_splits_by_context(build):
    """``bow`` is a ribbon by default and a greeting where a context decision says so."""
    assert by_position(build, "L00022", 5)["p.Lemma-s"] == "n.bow-1"
    assert by_position(build, "L00023", 5)["p.Lemma-s"] == "n.bow-2"


def test_sense_view_groups_surface_forms(build):
    """The sense view lists every surface form that uses a sense."""
    view = {r["p.Lemma-s"]: r for r in sense_view(build.rows)}
    # cat 과 cats 는 같은 뜻 키 n.cat-1 에 모인다
    assert view["n.cat-1"]["tokens"] == "cat, cats"


def test_context_decision_with_no_matching_token_is_an_error(tmp_path):
    """A decision whose line was deleted (or whose Seq moved past the end) stops the build."""
    # 예시 데이터를 임시 폴더에 복사해 고장 난 상황을 만든다
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR, data)
    with open(data / "decisions" / "context.tsv", "a", encoding="utf-8") as f:
        # 9번 자리는 L00023 에 없다
        f.write("L00023\t9\tbow\tn\tbow\t2\tpoints past the end of the line\n")
    with pytest.raises(ValueError, match="match no token"):
        build_words(data)
