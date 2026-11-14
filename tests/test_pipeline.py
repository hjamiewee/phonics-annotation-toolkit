"""The whole pipeline on the example data, plus the reproduction check."""

import pytest

from phonics_toolkit.pipeline import SNAPSHOT, WORD_COLUMNS, build
from phonics_toolkit.store import read_table


@pytest.fixture(scope="module")
def result():
    """Run the pipeline once for all tests in this module."""
    return build()


def at(result, line_id, seq):
    """Return the final Word row at ``(line_id, seq)``."""
    return next(r for r in result.words if r["line_id"] == line_id and r["seq"] == str(seq))


def test_nothing_is_unresolved(result):
    """Every example token has a sense and a pronunciation."""
    assert result.unresolved == []


def test_registries_are_up_to_date(result):
    """The committed registries already contain every number this data needs.

    If this fails, new words or sounds were added: run ``python -m phonics_toolkit --write``
    and commit the appended registry rows.
    """
    # 대장에 새로 붙여야 할 행이 0 이어야 한다 — 번호가 실행마다 달라지지 않는다는 뜻
    assert result.new_registry_rows == {"sound_registry": 0, "aud_id": 0, "word_id": 0}


def test_result_matches_the_snapshot(result):
    """Reproduction check: any change in any judgment shows up as a snapshot diff.

    After an intended change, review the diff and run
    ``python -m phonics_toolkit --update-snapshot``.
    """
    # 기준 결과와 한 칸이라도 다르면 실패 — 의도한 변경이면 스냅샷을 새로 찍는다
    assert result.words == read_table(SNAPSHOT, required=WORD_COLUMNS)


def test_read_same_sense_two_sounds(result):
    """The two axes move independently: one sense, two sound keys."""
    present, past = at(result, "L00019", 2), at(result, "L00020", 3)
    assert present["p.Lemma-s"] == past["p.Lemma-s"] == "v.read-1"
    assert (present["Token-a"], past["Token-a"]) == ("read-1", "read-2")
    assert past["inflection"] == "past"


def test_bow_two_senses_two_sounds(result):
    """The ribbon bow and the greeting bow differ on both axes."""
    ribbon, greeting = at(result, "L00022", 5), at(result, "L00023", 5)
    assert (ribbon["p.Lemma-s"], ribbon["Token-a"]) == ("n.bow-1", "bow-1")
    assert (greeting["p.Lemma-s"], greeting["Token-a"]) == ("n.bow-2", "bow-2")


def test_homophones_share_one_recording(result):
    """``to``, ``too``, and ``two`` are three sound keys but one recording."""
    tu = next(a for a in result.audio if a["pronunciation"] == "tu")
    assert tu["Token-a"] == "to-1, too-1, two-1"
    # 과거형 read 와 red 도 같은 녹음
    red = next(a for a in result.audio if a["pronunciation"] == "rɛd")
    assert red["Token-a"] == "read-2, red-1"


def test_plural_gets_its_own_image(result):
    """One cat and several cats are different images of the same sense."""
    keys = {a["image_key"] for a in result.images}
    assert {"n.cat-1", "n.cat-1.pl"} <= keys
    # 기능어(관사 등)는 이미지 목록에 없다
    assert not any(k.startswith("det.") for k in keys)


def test_word_ids_are_unique(result):
    """Every occurrence has a distinct frozen Word_ID."""
    ids = [r["word_id"] for r in result.words]
    assert len(ids) == len(set(ids))
