# phonics-annotation-toolkit

**English** | [한국어](README.ko.md)

An annotation pipeline for phonics textbook passages. It shows two things:

- **An automated workflow from data to assets.** One command takes passage lines and human decision files and produces the full annotated word table, lesson-target flags, and audio and image asset lists, with every judgment traceable and reproducible.
- **A two-axis data model.** Each word is split into a **Token axis** (how it sounds) that drives **audio assets**, and a **Lemma axis** (what it means) that drives **image assets**.

> This repository is a demo **written from scratch**, based on my experience designing and running
> a corpus-building project at work. It contains no real textbook text, company code, or company data.
> Every example sentence was written for this repository.

## Background

Phonics textbooks are organized around "the spelling–sound pattern taught in this lesson."
To digitize that content, every word in every passage needs answers to three questions:

- **How does the word sound?** Grapheme–phoneme correspondences (GPCs), syllables, audio recording
- **What does the word mean?** Part of speech, lemma, sense number, illustration
- **Is the word a target of this lesson?** Does it match the GPCs, word forms, or word relations the lesson teaches?

At work, this design handled **about 52,000 word occurrences** across two textbook series and three levels over four months.
About **33,000 context-level sense judgments** were kept in decision files and applied reproducibly,
and lesson-target flags, frozen sound numbers (**about 5,400 sound keys**), and asset lists were generated automatically for every row.
This repository reproduces that data model and workflow on a small example dataset.

## How it works

```
data/lines.tsv             passage lines
data/lessons.tsv           lesson targets
data/decisions/, lexicon/  human judgments: defaults, context decisions, GPC decompositions
        │
        ▼
python -m phonics_toolkit          (one command, preview by default)
        │
        ├── out/words.tsv          every word occurrence, both axes, every judgment
        ├── out/word_gpc.tsv       GPC decomposition of every sound key
        ├── out/word_sense.tsv     sense dictionary in use
        ├── out/aud_assets.tsv     audio assets   ← Token axis
        └── out/img_assets.tsv     image assets   ← Lemma axis
```

- **Humans decide; the pipeline applies.** People write judgments into decision files, keyed by context `(Line_ID, Seq)` when a word needs a context-specific reading. The code never guesses: anything without a decision is reported as unresolved.
- **Every judgment records its source.** Each row says whether its sense and sound came from a default, a context decision, or a rule (`sense_source`, `sound_source`), so automatic and human judgments are always distinguishable.
- **Everything downstream is automatic.** Sound numbers, recording IDs, inflection labels, lesson-target flags, and both asset lists are computed for every row.
- **Changes are checked, not trusted.** A snapshot test fails on any changed cell, and append-only registries keep IDs from changing between runs.

Inputs, rules, and commands for each step are in the [pipeline docs](docs/en/workflow.md).

## Two axes: Token → audio, Lemma → images

A word's sounds and meanings do not map one-to-one.

| Example | Spellings | Sounds | Senses |
|---|---|---|---|
| `read` (present / past) | 1 | 2 (/rid/, /rɛd/) | 1 |
| `bow` (ribbon / greeting / to bend) | 1 | 2 (/boʊ/, /baʊ/) | 3 |
| `to` · `too` · `two` | 3 | 1 (/tu/) | 3 |

So each word occurrence gets one key per axis.

```
                  Word (one word occurrence in a passage)
                 /                          \
   Token axis — Token-a                     Lemma axis — p.Lemma-s
   (sound)  read-1, read-2, bow-1 ...       (meaning)  v.read-1, n.bow-2 ...
        │                                        │
   GPC decomposition (letters, sounds,      Sense dictionary
   syllables, position)                          │
        │                                        │
   Audio asset: one pronunciation           Image asset: one sense (+ form)
   = one recording (Aud_ID)                 = one image
```

See the [data model](docs/en/data_model.md) for details and the [glossary](docs/glossary.md) for terms.

## What comes out

Results from the example data. The two axes split the same words differently.

**Audio assets (Token axis)**: one recording per pronunciation, shared across spellings.

| aud_id | pronunciation | sound keys (Token-a) | words |
|---|---|---|---|
| A00028 | tu | to-1, too-1, two-1 | prep.to, adv.too, num.two |
| A00011 | rɛd | read-2, red-1 | v.read (past), adj.red |
| A00034 | rid | read-1 | v.read (present) |
| A00044 | boʊ | bow-1 | n.bow (ribbon) |
| A00047 | baʊ | bow-2 | n.bow (greeting) |

**Image assets (Lemma axis)**: one image per sense, split again when the form changes the picture.

| image_key | meaning | surface forms |
|---|---|---|
| v.read-1 | to read | read (present and past) |
| n.bow-1 | ribbon, looped knot | bow |
| n.bow-2 | a bending greeting | bow |
| n.cat-1 | cat | cat |
| n.cat-1.pl | cat (several) | cats |

`read` needs **two recordings but one image**; `to`, `too`, and `two` need **three images but one recording**.
A single key for both would either duplicate or lose assets.

## Further reading

- [Judgment criteria and boundary cases](docs/en/design_decisions.md): how ambiguous cases were decided, with the reasoning. For example, why `in` differs in `in a dish` and `in the sun`, and why `take a bow` is not merged as a phrase.
- [Decodability analysis](docs/en/decodability.md): for each lesson, the share of passage words readable with only the GPCs taught so far, and the GPCs that block the rest. In the example curriculum it finds a sequencing gap: the sh lesson is only 13% decodable because short i has not been taught yet.

## Repository layout

```
├── README.md / README.ko.md
├── docs/
│   ├── glossary.md        # Korean–English glossary
│   ├── en/                # English docs
│   └── ko/                # Korean docs
├── data/
│   ├── lessons.tsv, lines.tsv   # Example input (lessons, passage lines)
│   ├── decisions/         # Human judgments: phrases, defaults, context decisions, sound rules
│   └── lexicon/           # Sense dictionary, GPC decompositions, word lists
├── registry/              # Append-only registries (sound numbers, recording IDs, Word_IDs)
├── src/phonics_toolkit/   # Pipeline code
├── tests/                 # Unit tests and reproduction check (snapshots/)
└── analysis/              # Analysis assumptions (baseline GPC list)
```

## Running

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
python -m pytest

# Whole pipeline: preview the summary, then write the outputs (out/)
python -m phonics_toolkit
python -m phonics_toolkit --write

# Decodability analysis
python -m phonics_toolkit.decodability
```
