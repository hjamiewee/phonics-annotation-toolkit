"""Steps 4 and 4-b: GPC decomposition checks, pronunciation choice, frozen registries."""

import pytest

from phonics_toolkit.sound import (
    SOURCE_DEFAULT, SOURCE_POSITION, SOURCE_SENSE, AudRegistry, DecompositionError,
    Pronunciation, SoundRegistry, choose_pronunciation, parse_decomposition,
)


def test_decomposition_rows_carry_syllable_role_and_position():
    """Each GPC gets its syllable number, role, and position in the word."""
    gpcs = parse_decomposition("actor", "a:æ c:k | t:t or:ər")
    assert [(g.label, g.syl_no, g.role, g.position) for g in gpcs] == [
        ("a:æ", 1, "vowel", "initial"),
        ("c:k", 1, "consonant", "medial"),
        ("t:t", 2, "consonant", "medial"),
        ("or:ər", 2, "vowel", "final"),
    ]


def test_silent_letters_have_no_position():
    """A silent ``e`` is kept as a grapheme with an empty phoneme; ``t`` before it is final."""
    gpcs = parse_decomposition("ate", "a:eɪ t:t e:")
    # 묵음 e 는 위치가 없고, 소리 있는 마지막 GPC(t)가 어말
    assert [(g.label, g.role, g.position) for g in gpcs] == [
        ("a:eɪ", "vowel", "initial"), ("t:t", "consonant", "final"), ("e:", "silent", ""),
    ]


def test_graphemes_must_spell_the_token():
    """A decomposition whose letters do not spell the word is rejected."""
    # c·a·t 를 이으면 cat 이지 cut 이 아니다
    with pytest.raises(DecompositionError, match="spell"):
        parse_decomposition("cut", "c:k a:æ t:t")


def test_every_syllable_needs_exactly_one_vowel():
    """A syllable with no vowel (or two) means the syllable boundary is wrong."""
    # 가운데 음절 t:t 에 모음이 없다 — 음절 경계를 잘못 그은 경우
    with pytest.raises(DecompositionError, match="0 vowels"):
        parse_decomposition("actor", "a:æ c:k | t:t | or:ər")


PRONS = {
    "bow": [Pronunciation("bow", parse_decomposition("bow", "b:b ow:oʊ"), default=True),
            Pronunciation("bow", parse_decomposition("bow", "b:b ow:aʊ"))],
    "read": [Pronunciation("read", parse_decomposition("read", "r:r ea:i d:d"), default=True),
             Pronunciation("read", parse_decomposition("read", "r:r ea:ɛ d:d"))],
}


def row(line_id, seq, token, sense):
    """A minimal Word row for pronunciation choice."""
    return {"line_id": line_id, "seq": str(seq), "token": token, "p.Lemma-s": sense}


def test_pronunciation_choice_order():
    """Position rule, then sense rule, then the token's default."""
    by_position = {("L00020", 3): ("read", "rɛd")}
    by_sense = {"n.bow-2": "baʊ"}
    # 자리 규칙: 과거형 read
    pron, src = choose_pronunciation(row("L00020", 3, "read", "v.read-1"), PRONS, by_position, by_sense)
    assert (pron.phonemes, src) == ("rɛd", SOURCE_POSITION)
    # 뜻 규칙: 인사 bow 는 언제나 /baʊ/
    pron, src = choose_pronunciation(row("L00023", 5, "bow", "n.bow-2"), PRONS, by_position, by_sense)
    assert (pron.phonemes, src) == ("baʊ", SOURCE_SENSE)
    # 규칙이 없으면 기본 소리
    pron, src = choose_pronunciation(row("L00022", 5, "bow", "n.bow-1"), PRONS, by_position, by_sense)
    assert (pron.phonemes, src) == ("boʊ", SOURCE_DEFAULT)


def test_unknown_token_has_no_pronunciation():
    """A token without a decomposition is unresolved, not guessed."""
    assert choose_pronunciation(row("L1", 1, "zebra", "n.zebra-1"), PRONS, {}, {}) is None


def test_sound_numbers_are_frozen_and_never_reused():
    """Known sounds keep their number; a new sound gets max + 1 even if a lower number is unused."""
    # read-1 만 등록돼 있고 read-2 는 지워진(쓰이지 않는) 번호라고 가정
    reg = SoundRegistry(rows=[
        {"Token-a": "read-1", "token": "read", "pronunciation": "rid"},
        {"Token-a": "read-2", "token": "read", "pronunciation": "rɛd"},
    ])
    assert reg.number("read", "rid") == 1
    # 새 소리는 3번 — 2번이 쓰이지 않아도 다시 주지 않는다
    assert reg.number("read", "riːd") == 3
    assert reg.new == [{"Token-a": "read-3", "token": "read", "pronunciation": "riːd"}]


def test_one_recording_per_pronunciation():
    """Spellings that sound the same share one Aud_ID."""
    reg = AudRegistry()
    # to · too · two 는 같은 녹음
    assert reg.aud_id("tu") == reg.aud_id("tu") == "A00001"
    assert reg.aud_id("rid") == "A00002"
