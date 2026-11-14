# Pipeline (workflow)

**English** | [한국어](../ko/workflow.md)

## Common principles

- **Preview by default.** Commands print a summary; add `--write` to write files.
- **Humans decide in decision files; code only applies them.** The code never guesses a sense or a phrase. Anything unknown is reported as unresolved.
- **Input in `data/`, output in `out/`.** `out/` is not committed and can always be rebuilt from the input.
- **Reproduction check.** Results are compared with the baseline in `tests/snapshots/`, so any change in a judgment shows up as a diff.

## Running

```bash
python -m phonics_toolkit                    # run every step, print the summary and unresolved list
python -m phonics_toolkit --write            # write out/*.tsv and append new registry numbers
python -m phonics_toolkit --update-snapshot  # accept the new baseline after reviewing a change
```

## Input files

| File | Contents | Edited by |
|---|---|---|
| `data/lessons.tsv` | Lessons and targets (4 main axes, 4 additional axes) | human |
| `data/lines.tsv` | Passage lines. `Line_ID` is filled by step 1 | human (+ step 1) |
| `data/decisions/phrases.tsv` | Phrases and compounds merged into one token | human |
| `data/decisions/defaults.tsv` | Default sense for each spelling | human |
| `data/decisions/context.tsv` | Judgments per context key `(Line_ID, Seq)`, with reasons | human |
| `data/lexicon/senses.tsv` | Sense dictionary: `p.Lemma-s`, Korean and English glosses | human |
| `data/lexicon/gpc.tsv` | GPC decomposition per token and pronunciation, with the default marked | human |
| `data/decisions/sound_rules.tsv` | Pronunciation picked by position (`Line_ID:Seq`) or by sense (`p.Lemma-s`) | human |
| `data/lexicon/irregular.tsv`, `data/decisions/inflection_context.tsv` | Irregular forms, context inflection decisions | human |
| `data/lexicon/hfw.tsv` | High-frequency word list | human |
| `registry/*.tsv` | Frozen registries: sound numbers, recording IDs, Word_IDs | pipeline (append only) |

## Step 1: assign Line_IDs

```bash
python -m phonics_toolkit.ids            # preview
python -m phonics_toolkit.ids --write    # write to data/lines.tsv
```

- Only lines with an empty `line_id` get a new number. Existing numbers are never touched.
- New number = current maximum + 1. Running it twice gives the same result.
- Because numbers are stored as values, sorting or inserting lines never renumbers them. This matters because context decisions use `Line_ID` as their key.

## Step 2: tokenize and merge phrases

- Only words become tokens. Periods, commas, and the list separator `·` are dropped.
- Apostrophes and hyphens inside a word stay attached (`Pam's`, `good-bye`).
- Only phrases listed in `phrases.tsv` are merged. When phrases overlap, the longest wins.
  - `hot dog` is listed, so it becomes one token.
  - `hot pot` (a hot cooking pot) is not listed, so it stays two tokens. Whether two words form one unit is a human decision, even when they look alike.
- `Seq` is counted **after** merging. In `I read a book every day.`, `every day` takes the single position 5.

## Step 3: part of speech, lemma, sense

A token's sense is decided in this order:

| Order | Where it looks | Example |
|---|---|---|
| 1 | Context decision `(Line_ID, Seq)` | `bow` in `The actor took a bow.` → `n.bow-2` greeting |
| 2 | Default, exact capitalization | `I` → `pron.I-1`, `Pam` → `propn.Pam-1` |
| 3 | Default, lowercased | sentence-initial `The` → `det.the-1` |
| 4 | Nothing → **unresolved** | Listed for a human, never guessed |

### Safety checks

- **Stale decisions**: each context decision also stores the token it was written for. If the line is edited and a different word now sits in that position, the run stops, so a judgment never lands on the wrong word.
- **Orphaned decisions**: if a context decision matches no token (the line was deleted or its `Seq` moved), the run stops.
- **Unknown senses**: if a default or context decision points to a sense key missing from `senses.tsv`, the run stops before it starts.

### Outputs

| File | One row per | Key columns |
|---|---|---|
| `out/words.tsv` | word occurrence | `line_id`, `seq`, `token`, `p.Token`, `p.Lemma-s`, glosses, `sense_source` |
| `out/word_sense.tsv` | sense in use | `p.Lemma-s`, surface forms using it (`cat, cats`), glosses, count |

`sense_source` records where a sense judgment came from (`context` or `default`), so a reviewer can focus on the positions that carry context decisions.

## Step 4: GPC decomposition

- `gpc.tsv` lists one decomposition per pronunciation for each lowercase token: `grapheme:phoneme` pairs separated by spaces, syllables separated by `|`.
  - `read` → `r:r ea:i d:d` (default), `r:r ea:ɛ d:d`
  - `ate` → `a:eɪ t:t e:` (a silent e has an empty phoneme)
  - A phrase is one token, so it is decomposed too: `hot dog` → `h:h o:ɑ t:t | d:d o:ɔ g:g`
- Every decomposition is checked on load:
  - Its graphemes must spell the token (`c:k a:æ t:t` can never be a decomposition of `cut`).
  - Each syllable must contain exactly one vowel phoneme.
  - A token cannot decompose the same pronunciation twice, and a token with several pronunciations must mark exactly one default.
- Each GPC gets a syllable number, a role (vowel, consonant, silent), and a position (initial, medial, final). Position counts only GPCs with a sound, so the `t` in `ate` is final.

## Step 4-b: sound numbers and recording IDs

The pronunciation of each occurrence is chosen in this order:

| Order | Rule | Example |
|---|---|---|
| 1 | Position rule `Line_ID:Seq` | `read` in `Yesterday I read` → /rɛd/ |
| 2 | Sense rule `p.Lemma-s` | `n.bow-2` (greeting) → /baʊ/ |
| 3 | The token's default | `bow` → /boʊ/ |

- **`a#` (sound number)**: looked up for (token, pronunciation) in `registry/sound_registry.tsv`. A new pronunciation gets that token's maximum + 1 and is appended. Numbers that fall out of use are never deleted or reused. `Token-a` = `token-a#`.
- **Aud_ID (recording ID)**: looked up by pronunciation string in `registry/aud_id.tsv`. Different spellings with the same pronunciation share one recording (`to`·`too`·`two` → one; past `read` and `red` → one).

## Step 5: lesson target judgment

Each word in a lesson gets Y or N from the lesson's four axes (`gpc`, `environment`, `morph`, `lexical`). The main axes fill `target`; the `_add` axes fill `add_target`.

- **Phonics path**: every filled axis must match. The GPC must sit in the named position (`on` has o at the start, so it is N in a medial lesson), and morph is ANDed (in a plural lesson, `has` ends in /z/ but is not a plural, so it is N).
- **Lexical path**: with `homophone`, a word is Y when the same lesson presents a differently spelled word with the same pronunciation.
- Y if either path holds. A lesson with every axis empty is not judged and stays empty.
- Sound-axis decisions carry straight into targets: in an `ea:i` lesson, present `read` is Y and past `read` (/rɛd/) is N.

## Steps 6–8: Word_ID, high-frequency words, inflections

- **Inflection (8)**: context decision → irregular-form list → regular endings compared with the lemma. The morph axis of step 5 needs it, so it is actually computed before step 5.
- **High-frequency words (7)**: Y when the token matches `hfw.tsv`, ignoring case.
- **Word_ID (6)**: looked up for `(Line_ID, Seq)` in `registry/word_id.tsv`; a new position gets maximum + 1. If the registry's token differs from the current token, the run stops.

## Step 9: outputs

| File | One row per | Axis |
|---|---|---|
| `out/words.tsv` | word occurrence, with every judgment | both |
| `out/word_gpc.tsv` | GPC of a sound key in use | sound |
| `out/word_sense.tsv` | sense in use | meaning |
| `out/img_assets.tsv` | image: sense + form suffix (`.pl`·`.cmp`·`.sup`), function words excluded | meaning |
| `out/aud_assets.tsv` | recording: pronunciation, syllable count, sound keys and surface forms using it | sound |

## Working with registries

- After adding data, if the preview shows non-zero `new registry rows`, run `--write` to append the numbers and commit the registry files.
- The test `test_registries_are_up_to_date` checks that the committed registries already hold every number the data needs. It guarantees that numbers never change from run to run.
