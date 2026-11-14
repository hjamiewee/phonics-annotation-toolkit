"""Steps 5 and 8: inflection labels and lesson target judgment."""

from phonics_toolkit.inflection import label, regular_label
from phonics_toolkit.sound import parse_decomposition
from phonics_toolkit.target import Targets, judge_lesson


def test_regular_inflections():
    """Regular endings are recognized against the lemma, including spelling changes."""
    assert regular_label("n", "cats", "cat") == "plural"
    assert regular_label("n", "babies", "baby") == "plural"
    assert regular_label("v", "napping", "nap") == "progressive"
    assert regular_label("v", "baked", "bake") == "past"
    assert regular_label("adj", "biggest", "big") == "superlative"
    # 원형과 같으면 라벨 없음
    assert regular_label("v", "read", "read") == ""


def test_context_beats_irregular_list_and_rules():
    """``read`` with no spelling change needs a context decision to be labeled past."""
    row = {"line_id": "L00020", "seq": "3", "token": "read", "lemma": "read", "pos": "v"}
    assert label(row, {}, {("L00020", 3): ("read", "past")}) == "past"
    # 문맥 판정이 없으면 라벨 없음
    assert label({**row, "line_id": "L00019", "seq": "2"}, {}, {}) == ""
    # 불규칙형 목록
    sat = {"line_id": "L1", "seq": "1", "token": "sat", "lemma": "sit", "pos": "v"}
    assert label(sat, {("sat", "sit"): "past"}, {}) == "past"


def word(token, gpc, inflection="", pronunciation=""):
    """A minimal Word row plus its decomposition, for target tests."""
    return {"token": token, "Token-a": f"{token}-1", "inflection": inflection,
            "pronunciation": pronunciation}, parse_decomposition(token, gpc)


def judge(lesson_axes, words):
    """Judge rows against a lesson built from ``lesson_axes``."""
    lesson = {f"{a}{s}": "" for a in ("gpc", "environment", "morph", "lexical") for s in ("", "_add")}
    lesson.update(lesson_axes)
    rows = [w for w, _ in words]
    gpcs_of = {w["Token-a"]: g for w, g in words}
    return judge_lesson(rows, gpcs_of, Targets.from_lesson(lesson))


def test_gpc_must_sit_in_the_named_environment():
    """In a medial short-o lesson, ``on`` (o at the start) is not a target but ``pot`` is."""
    words = [word("pot", "p:p o:ɑ t:t"), word("on", "o:ɑ n:n")]
    assert judge({"gpc": "o:ɑ", "environment": "medial"}, words) == ["Y", "N"]


def test_morph_is_anded_with_gpc():
    """In a plural -s lesson, ``has`` ends in /z/ but is not a plural, so it is not a target."""
    words = [word("dogs", "d:d o:ɔ g:g s:z", "plural"), word("has", "h:h a:æ s:z", "third_person")]
    assert judge({"gpc": "s:s, s:z", "environment": "final", "morph": "plural"}, words) == ["Y", "N"]


def test_sound_axis_decides_vowel_team_targets():
    """In an ``ea:i`` lesson, present ``read`` /rid/ is a target and past ``read`` /rɛd/ is not."""
    present = word("read", "r:r ea:i d:d")
    past = ({**present[0], "Token-a": "read-2"}, parse_decomposition("read", "r:r ea:ɛ d:d"))
    assert judge({"gpc": "ea:i"}, [present, past]) == ["Y", "N"]


def test_homophones_are_found_within_the_lesson():
    """``to`` and ``two`` share /tu/; ``sea`` has no partner in the lesson."""
    words = [word("to", "t:t o:u", pronunciation="tu"), word("two", "t:t wo:u", pronunciation="tu"),
             word("sea", "s:s ea:i", pronunciation="si")]
    assert judge({"lexical": "homophone"}, words) == ["Y", "Y", "N"]


def test_lesson_without_targets_is_not_judged():
    """No axis filled -> empty values, not N."""
    assert judge({}, [word("cat", "c:k a:æ t:t")]) == [""]
