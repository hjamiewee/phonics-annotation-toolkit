"""Step 2: tokenization and phrase merging."""

from phonics_toolkit.tokens import merge_phrases, split_words, tokenize_line

# 시험용 구 목록
PHRASES = {("hot", "dog"), ("every", "day"), ("a", "lot", "of"), ("a", "lot")}


def test_punctuation_and_separators_are_dropped():
    """Commas, periods, and list separators never become tokens."""
    assert split_words("I have two cats, too.") == ["I", "have", "two", "cats", "too"]
    # 낱말 목록 줄의 가운뎃점(·)도 토큰이 아니다
    assert split_words("to · too · two") == ["to", "too", "two"]


def test_inner_apostrophes_and_hyphens_stay_in_the_word():
    """``Pam's`` and ``good-bye`` are single tokens."""
    assert split_words("Pam's good-bye") == ["Pam's", "good-bye"]


def test_listed_phrases_merge_and_keep_their_spelling():
    """A listed phrase becomes one token; its original capitalization is kept."""
    # 문장 첫머리 대문자여도 구로 잡고, 표기는 원래대로 둔다
    assert tokenize_line("Hot dog for me.", PHRASES) == ["Hot dog", "for", "me"]


def test_unlisted_word_pairs_are_not_merged():
    """``hot pot`` is not in the list, so it stays two tokens."""
    # 구 병합은 목록에 있을 때만 — 추측하지 않는다
    assert tokenize_line("Tom got a hot pot.", PHRASES) == ["Tom", "got", "a", "hot", "pot"]


def test_longest_phrase_wins():
    """When phrases overlap, the longest listed match is merged."""
    # a lot of 와 a lot 이 둘 다 있으면 긴 쪽
    assert merge_phrases(["a", "lot", "of", "fun"], PHRASES) == ["a lot of", "fun"]


def test_seq_is_counted_after_merging():
    """A merged phrase occupies a single position, so later words shift forward."""
    tokens = tokenize_line("I read a book every day.", PHRASES)
    # every day 가 한 자리(5번)를 차지한다
    assert tokens.index("every day") + 1 == 5
    assert len(tokens) == 5
