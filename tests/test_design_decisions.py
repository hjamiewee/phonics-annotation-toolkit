"""Every boundary case in docs/*/design_decisions.md, checked against the pipeline output.

If one of these fails after a judgment change, update the matching section of
both language versions of the document in the same commit.
"""

import pytest

from phonics_toolkit.pipeline import build


@pytest.fixture(scope="module")
def words():
    """Final Word rows keyed by ``(line_id, seq)``."""
    return {(r["line_id"], int(r["seq"])): r for r in build().words}


def test_3_1_in_inside_vs_open_space(words):
    """§3.1: ``in a dish`` is in-1; ``in the sun`` and ``in the mud`` are in-2."""
    assert words[("L00013", 5)]["p.Lemma-s"] == "prep.in-1"
    assert words[("L00017", 4)]["p.Lemma-s"] == "prep.in-2"
    assert words[("L00018", 4)]["p.Lemma-s"] == "prep.in-2"


def test_3_2_be_with_a_place_complement(words):
    """§3.2: ``is`` before a place phrase is v.be-2."""
    assert words[("L00009", 3)]["p.Lemma-s"] == "v.be-2"
    assert words[("L00014", 3)]["p.Lemma-s"] == "v.be-2"


def test_3_3_take_a_bow_is_not_merged(words):
    """§3.3: ``took`` and ``bow`` stay separate tokens with their own senses."""
    assert words[("L00023", 3)]["p.Lemma-s"] == "v.take-2"
    assert words[("L00023", 5)]["p.Lemma-s"] == "n.bow-2"


def test_3_4_hot_dog_merged_hot_pot_not(words):
    """§3.4: ``hot dog`` is one token; ``hot pot`` is two."""
    assert words[("L00027", 4)]["token"] == "hot dog"
    assert (words[("L00010", 4)]["token"], words[("L00010", 5)]["token"]) == ("hot", "pot")


def test_4_1_read_one_sense_two_sounds(words):
    """§4.1: same sense, different sound keys."""
    assert words[("L00019", 2)]["p.Lemma-s"] == words[("L00020", 3)]["p.Lemma-s"]
    assert (words[("L00019", 2)]["Token-a"], words[("L00020", 3)]["Token-a"]) == ("read-1", "read-2")


def test_4_2_bow_sound_follows_sense(words):
    """§4.2: the greeting bow gets /baʊ/ from a sense rule, not a position rule."""
    greeting = words[("L00023", 5)]
    assert (greeting["pronunciation"], greeting["sound_source"]) == ("baʊ", "sense")


def test_4_4_short_o_lesson_includes_log(words):
    """§4.4: with both o:ɑ and o:ɔ listed, ``log`` (/ɔ/) is a short-o target."""
    assert words[("L00008", 1)]["target"] == "Y"


def test_4_5_one_recording_per_pronunciation(words):
    """§4.5: to · too · two share one recording, as do past read and red."""
    aud = lambda key: words[key]["aud_id"]
    assert aud(("L00025", 3)) == aud(("L00026", 5)) == aud(("L00026", 3))  # to · too · two
    assert aud(("L00020", 3)) == aud(("L00005", 4))                         # read(past) · red


def test_5_1_environment(words):
    """§5.1: ``on`` is not a target in the medial short-o lesson."""
    assert words[("L00009", 4)]["target"] == "N"


def test_5_2_morph_is_anded(words):
    """§5.2: ``Two`` is plural in meaning but has no -s, so it is not a plural-lesson target."""
    assert words[("L00017", 1)]["target"] == "N"
    assert words[("L00017", 2)]["target"] == "Y"  # cats


def test_5_3_targets_follow_the_sound(words):
    """§5.3: in the ea:i lesson, present read is a target and past read is not."""
    assert (words[("L00019", 2)]["target"], words[("L00020", 3)]["target"]) == ("Y", "N")


def test_5_4_homophones_need_a_partner_in_the_lesson(words):
    """§5.4: ``sea`` has no partner in the homophone lesson; ``two`` does."""
    assert words[("L00025", 4)]["token"] == "the" and words[("L00025", 5)]["target"] == "N"  # sea
    assert words[("L00026", 3)]["target"] == "Y"  # two
