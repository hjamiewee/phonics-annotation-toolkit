"""Step 3: sense lookup order and safety checks."""

import pytest

from phonics_toolkit.sense import SOURCE_CONTEXT, SOURCE_DEFAULT, StaleDecisionError, resolve, sense_key

# 시험용 대표값 — 대소문자 구분 키
DEFAULTS = {"bow": "n.bow-1", "I": "pron.I-1", "the": "det.the-1", "rose": "n.rose-1", "Rose": "propn.Rose-1"}
# 시험용 문맥 판정 — (Line_ID, Seq) 키
CONTEXT = {("L00023", 5): {"token": "bow", "sense": "n.bow-2"}}


def test_sense_key_format():
    """Sense keys are POS + '.' + lemma + '-' + sense number, spaces allowed in the lemma."""
    assert sense_key("v", "read", 1) == "v.read-1"
    assert sense_key("n", "hot dog", "1") == "n.hot dog-1"


def test_context_decision_beats_the_default():
    """The same token gets the context sense at its decided position and the default elsewhere."""
    # 문맥 판정이 있는 자리: 인사
    assert resolve("L00023", 5, "bow", CONTEXT, DEFAULTS) == ("n.bow-2", SOURCE_CONTEXT)
    # 판정이 없는 자리: 대표값 리본
    assert resolve("L00022", 5, "bow", CONTEXT, DEFAULTS) == ("n.bow-1", SOURCE_DEFAULT)


def test_exact_case_default_comes_before_lowercase():
    """``Rose`` (a name) and ``rose`` (a flower) are different defaults."""
    assert resolve("L1", 1, "Rose", {}, DEFAULTS)[0] == "propn.Rose-1"
    assert resolve("L1", 3, "rose", {}, DEFAULTS)[0] == "n.rose-1"
    # 대문자 표기가 대표값에 없으면 소문자로 찾는다 (문장 첫머리 The)
    assert resolve("L1", 1, "The", {}, DEFAULTS)[0] == "det.the-1"


def test_unknown_tokens_are_unresolved_not_guessed():
    """A token with no decision and no default returns None."""
    assert resolve("L1", 1, "zebra", {}, DEFAULTS) is None


def test_stale_context_decision_stops_the_run():
    """If the decided position now holds a different word, raise instead of mislabeling it."""
    # 줄이 고쳐져 5번 자리가 bow 가 아니게 된 경우
    with pytest.raises(StaleDecisionError):
        resolve("L00023", 5, "hat", CONTEXT, DEFAULTS)
