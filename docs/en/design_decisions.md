# Judgment criteria and boundary cases

**English** | [한국어](../ko/design_decisions.md)

## 1. Purpose

The hardest part of annotation is not writing rules; it is **judging the cases on a rule's boundary consistently**.
This document records the judgment principles and how each boundary case was decided, with the reasoning.

Each case follows the same structure:

- **Situation**: what is ambiguous
- **Options**: the possible judgments
- **Decision**: the judgment used in this repository
- **Reasoning**: why
- **Where**: the files that hold the judgment

## 2. Principles

### 2.1 Split senses by what learners must tell apart, not by translation

A sense number (`s#`) is not split every time the Korean translation changes.
It is split only **when a learner needs a different gloss or a different picture**.

- The ribbon `bow` and the greeting `bow` need completely different pictures, so they are `n.bow-1` and `n.bow-2`.
- `have` can translate as "가지다" (own) or "있다" (there is), but one gloss explains both, so it stays `v.have-1`.

Splitting too finely multiplies images and context decisions; lumping too broadly makes pictures that do not fit the sentence.

### 2.2 A default for the common case, context decisions for exceptions

Each word gets one basic sense as its default. Only positions that differ from the default get a context decision `(Line_ID, Seq)`.

- Human effort scales with the number of exceptions, not the size of the corpus.
- The context file itself becomes a reviewable list of "places that depart from the basic sense."

### 2.3 Never guess

A word with no evidence is left **unresolved** rather than filled with a plausible value.
A wrong value hides; a blank is always seen by the next person.

### 2.4 "Not judged" is not "no"

Words in a lesson without targets get an empty value, not `N`.
`N` means "judged, and not a target"; empty means "there is nothing to judge against." Mixing them distorts every statistic.

## 3. Meaning-axis boundary cases

### 3.1 The preposition `in`: "inside" vs. "in (an open space)"

- **Situation**: is `in` the same sense in `a fish in a dish` and `cats nap in the sun`?
- **Options**: (a) both `in-1` "~안에" (inside) (b) `in-1` for a bounded container, `in-2` "~에" for open space or nature
- **Decision**: (b). `in a dish` is `in-1`; `in the sun` and `in the mud` are `in-2`.
- **Reasoning**: glossing `in the sun` as "inside the sun" gives a Korean learner the wrong picture. The test question is **"can it be rephrased with *inside*?"** `inside a dish` works; `inside the sun` changes the meaning.
- **Where**: `data/decisions/context.tsv` (L00017, L00018), `data/lexicon/senses.tsv`

### 3.2 `be`: "is (something)" vs. "is (somewhere)"

- **Situation**: is `is` in `The fox is on the log.` the linking "~이다"?
- **Options**: (a) every `be` is `v.be-1` "~이다" (b) `v.be-2` "(어디에) 있다" when the complement is a place
- **Decision**: (b). With a place complement (`on the log`, `at the shop`) it is `v.be-2`.
- **Reasoning**: Korean uses different verbs for "is (something)" and "is (somewhere)." The gloss changes, so by principle 2.1 the sense splits. The test is whether **what follows is a prepositional phrase of place**.
- **Where**: `data/decisions/context.tsv` (L00009, L00014)

### 3.3 `take a bow`: merge as a phrase, or split senses?

- **Situation**: should `The actor took a bow.` merge `take a bow` into one phrase?
- **Options**: (a) merge into the phrase `take a bow` "to bow" (b) do not merge: `took` → `v.take-2` "to perform (an action)", `bow` → `n.bow-2` "greeting"
- **Decision**: (b)
- **Reasoning**: merging would remove `bow` as a token. Then the word the learner actually reads in a phonics passage, `bow`, could no longer carry its own sound (/baʊ/) and picture (a greeting). Phrases are merged only **when the parts lose their meaning** (3.4). In `take a bow` the parts keep theirs: "perform a greeting."
- **Where**: `data/decisions/context.tsv` (L00023)

### 3.4 Compounds and phrases: `hot dog` vs. `hot pot`

- **Situation**: both are adjective + noun. Should either be one token?
- **Options**: (a) treat them alike because they look alike (b) merge only what is listed
- **Decision**: (b). `hot dog` is merged; `hot pot` stays two tokens.
- **Reasoning**: a `hot dog` is not a hot canine but one food; the parts lose their meaning and there is one picture. A `hot pot` (a hot cooking pot) is the sum of its words. Form alone cannot tell them apart, so **a human lists them and the code never guesses**. `every day` (adverbial phrase, "daily") is merged the same way and is a different entry from `everyday` (adjective, "ordinary").
- **Where**: `data/decisions/phrases.tsv`

### 3.5 Capitalization: `I`, names, `Rose` vs. `rose`

- **Situation**: should default lookup be case-sensitive?
- **Options**: (a) always look up lowercase (b) exact case first, then lowercase
- **Decision**: (b)
- **Reasoning**: lowercase-only lookup turns the name `Rose` into the flower `rose`. Strictly case-sensitive lookup makes sentence-initial `The` a different word from `the`. Two-step lookup solves both. `p.Token` likewise keeps the original case only for words whose lemma is capitalized (`I`, names).
- **Where**: `src/phonics_toolkit/sense.py`, `src/phonics_toolkit/words.py`

## 4. Sound-axis boundary cases

### 4.1 Same sense, different sound: `read`

- **Situation**: `read` in `I read a book every day.` and in `Yesterday I read a book.`
- **Options**: (a) split the sense to separate the sounds (b) one sense `v.read-1`, two sounds `read-1` and `read-2`
- **Decision**: (b)
- **Reasoning**: the meaning (to read) and the picture are the same; only the sound and tense differ. Splitting the sense would create the same image twice. So the split happens on the sound axis only, with a position rule (`L00020:3` → /rɛd/) and an inflection decision (`past`) on the past-tense occurrence. This is the clearest case for separating the two axes.
- **Where**: `data/decisions/sound_rules.tsv`, `data/decisions/inflection_context.tsv`

### 4.2 When the sense decides the sound: `bow`

- **Situation**: does every occurrence of the greeting `bow` (/baʊ/) need its own position rule?
- **Options**: (a) a position rule per occurrence (b) one sense rule: `n.bow-2` → /baʊ/
- **Decision**: (b)
- **Reasoning**: the greeting `bow` is always /baʊ/. When the sense determines the sound, one sense rule covers every occurrence. Position rules are kept for cases like `read`, **where the sound varies within one sense**. The number of rules does not grow with the size of the corpus.
- **Where**: `data/decisions/sound_rules.tsv`

### 4.3 Silent e: `ate`

- **Situation**: how should the final e of `ate` be written?
- **Options**: (a) a split digraph `a_e:eɪ` (b) a grapheme with an empty phoneme `e:`
- **Decision**: (b) `a:eɪ t:t e:`
- **Reasoning**: keeping the simple property that graphemes read left to right spell the word lets the code check automatically that every decomposition matches its spelling. The cost is that the VCe pattern is not visible as one unit; that limitation is recorded in the decodability docs.
- **Where**: `data/lexicon/gpc.tsv`, `docs/en/decodability.md` §6

### 4.4 Two sounds of short o: `pot` and `log`

- **Situation**: the pronunciation dictionary gives `pot` /ɑ/ and `log` /ɔ/. What does a short-o lesson target?
- **Options**: (a) `o:ɑ` only (b) both `o:ɑ, o:ɔ`
- **Decision**: (b)
- **Reasoning**: for many American English speakers the two vowels have merged (the cot–caught merger), and phonics materials teach both as "short o." The decomposition keeps the dictionary distinction, and **the lesson lists both sounds as targets**. Because the decomposition is unchanged, other analyses can still tell the two apart.
- **Where**: `data/lessons.tsv` (DEMO.A.U1L2)

### 4.5 Recording units and weak forms: `to`, `too`, `two`

- **Situation**: is there one recording per spelling or per pronunciation? And `to` is often reduced to /tə/ in a sentence.
- **Options**: (a) one recording per spelling (b) one recording per pronunciation, using the citation form
- **Decision**: (b). `to`, `too`, and `two` share one /tu/ recording.
- **Reasoning**: recording the same sound several times is wasteful, and slight differences between takes risk sounding like "different sounds" to a learner. Weak forms in connected speech belong to sentence recordings, not word-level audio assets. For the same reason, past `read` and `red` share one /rɛd/ recording.
- **Where**: `registry/aud_id.tsv`, `src/phonics_toolkit/sound.py`

## 5. Target-judgment boundary cases

### 5.1 Environment: `on` in a medial lesson

- **Situation**: in a short-o (medial) lesson, `on` has /ɑ/. Is it a target?
- **Decision**: `N`
- **Reasoning**: the lesson teaches "short o between consonants" (`pot`, `fox`). In `on` the o is the first sound, a different position. This is why GPC and position are checked **together**.

### 5.2 Morph is ANDed: `has` in a plural lesson

- **Situation**: in a plural `-s` lesson (`s:s, s:z`, final), `has` also ends in /z/. Is it a target?
- **Decision**: `N`
- **Reasoning**: the lesson teaches not just a sound but "the -s that marks a plural." ANDing the sound and form conditions excludes `has` (a third-person verb). Conversely, `Two` in `Two cats` is plural in meaning but has no `-s`, so it is `N`. (The example plural lesson does not contain `has`, so the `has` case is checked by a unit test.)

### 5.3 Targets follow the sound: past `read` in an `ea:i` lesson

- **Situation**: in an `ea` lesson, is every word spelled with `ea` a target?
- **Decision**: present `read` (/rid/) is `Y`; past `read` (/rɛd/) is `N`.
- **Reasoning**: the target is not a spelling but the **spelling–sound correspondence** `ea:i`. The past form uses the same spelling with a different sound (`ea:ɛ`), which is not what this lesson teaches. The sound axis's position rule carries straight into target judgment.

### 5.4 Lexical path: homophones only within the lesson

- **Situation**: in a homophone lesson, `sea` is a homophone of `see`. Is it a target?
- **Decision**: `N`
- **Reasoning**: a homophone lesson aims to tell apart **pairs presented together**. If `see` does not appear in that lesson, `sea` has no partner. The scope of the judgment is limited to **words presented in the same lesson**.

## 6. Procedure for changing a judgment

Every case in this document is checked by `tests/test_design_decisions.py`. If a judgment change makes a test fail, update the matching section of both language versions in the same commit.

1. Edit the decision file and write the reasoning in the `reason` column.
2. Run `python -m phonics_toolkit` to preview, and check unresolved items and new registry rows.
3. Run `python -m pytest` to compare with the snapshot. Confirm from the diff that **only the intended cells** changed.
4. Once confirmed, refresh the baseline with `--update-snapshot` and say what changed and why in the commit message.
5. If the change **reverses** an earlier judgment, do not finalize it at once; put it on a review list and check again. Most inconsistencies come from changes like these.
