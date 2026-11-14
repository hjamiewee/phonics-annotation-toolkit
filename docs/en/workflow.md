# Pipeline (workflow)

**English** | [한국어](../ko/workflow.md)

## Common principles

- **Preview by default.** Commands print a summary; add `--write` to write files.
- **Humans decide in decision files; code only applies them.** The code never guesses a sense or a phrase. Anything unknown is reported as unresolved.
- **Input in `data/`, output in `out/`.** `out/` is not committed and can always be rebuilt from the input.
- **Reproduction check.** Results are compared with the baseline in `tests/snapshots/`, so any change in a judgment shows up as a diff.

## Input files

| File | Contents | Edited by |
|---|---|---|
| `data/lessons.tsv` | Lessons and targets (4 main axes, 4 additional axes) | human |
| `data/lines.tsv` | Passage lines. `Line_ID` is filled by step 1 | human (+ step 1) |
| `data/decisions/phrases.tsv` | Phrases and compounds merged into one token | human |
| `data/decisions/defaults.tsv` | Default sense for each spelling | human |
| `data/decisions/context.tsv` | Judgments per context key `(Line_ID, Seq)`, with reasons | human |
| `data/lexicon/senses.tsv` | Sense dictionary: `p.Lemma-s`, Korean and English glosses | human |

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

```bash
python -m phonics_toolkit.words                    # summary and unresolved list
python -m phonics_toolkit.words --write            # out/words.tsv, out/word_sense.tsv
python -m phonics_toolkit.words --update-snapshot  # accept the new baseline
```

### Safety checks

- **Stale decisions**: each context decision also stores the token it was written for. If the line is edited and a different word now sits in that position, the run stops, so a judgment never lands on the wrong word.
- **Orphaned decisions**: if a context decision matches no token (the line was deleted or its `Seq` moved), the run stops.
- **Unknown senses**: if a default or context decision points to a sense key missing from `senses.tsv`, the run stops before it starts.

### Outputs

| File | One row per | Key columns |
|---|---|---|
| `out/words.tsv` | word occurrence | `line_id`, `seq`, `token`, `p.Token`, `p.Lemma-s`, glosses, `source` |
| `out/word_sense.tsv` | sense in use | `p.Lemma-s`, surface forms using it (`cat, cats`), glosses, count |

`source` records where a judgment came from (`context` or `default`), so a reviewer can focus on the positions that carry context decisions.

## Step 4 onward (planned)

| Step | What it does |
|---|---|
| 4 | GPC decomposition (sound axis) |
| 4-b | Sound numbers `a#`, frozen registry, Aud_ID |
| 5 | Lesson target judgment |
| 6–8 | Word_ID, high-frequency words, inflections |
| 9 | Image and audio asset lists |
