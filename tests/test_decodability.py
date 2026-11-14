"""Decodability analysis."""

from phonics_toolkit.decodability import BLOCKED, DECODABLE, SIGHT, analyze, classify
from phonics_toolkit.sound import parse_decomposition


def test_classify_uses_only_taught_gpcs():
    """A word is decodable only when every sounded GPC has been taught."""
    cat = parse_decomposition("cat", "c:k a:æ t:t")
    assert classify(cat, False, {"c:k", "a:æ", "t:t"}) == (DECODABLE, [])
    # a:æ 를 아직 안 배웠으면 막힌다 — 막은 GPC 를 함께 돌려준다
    assert classify(cat, False, {"c:k", "t:t"}) == (BLOCKED, ["a:æ"])


def test_high_frequency_words_are_readable_by_sight():
    """An undecodable high-frequency word counts as sight, not blocked."""
    the = parse_decomposition("the", "th:ð e:ə")
    assert classify(the, True, set())[0] == SIGHT


def test_silent_letters_do_not_block():
    """Silent graphemes are ignored (a documented limitation)."""
    ate = parse_decomposition("ate", "a:eɪ t:t e:")
    assert classify(ate, False, {"a:eɪ", "t:t"})[0] == DECODABLE


def test_report_finds_the_sequencing_gap():
    """In the example curriculum, short i is never taught, so it blocks the sh lesson most."""
    reports = {r.lesson_id: r for r in analyze()}
    sh = reports["DEMO.A.U2L1"]
    # ship · fish · dish 의 짧은 i 가 가장 많이 막는다
    assert sh.blockers.most_common(1)[0][0] == "i:ɪ"
    # 짧은 o 레슨은 대부분 읽을 수 있다
    assert reports["DEMO.A.U1L2"].pct(DECODABLE, SIGHT) > 90
