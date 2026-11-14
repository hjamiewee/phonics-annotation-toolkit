# phonics-annotation-toolkit

**English** | [한국어](README.ko.md)

A pipeline that annotates phonics textbook passages word by word.
Each word carries its **sound (pronunciation and grapheme–phoneme correspondences)** and its
**meaning (part of speech and sense number)** on separate keys, and the pipeline uses both to
judge lesson targets and to build **audio and image asset lists**.

> This repository is a demo **written from scratch**, based on my experience designing and running
> a corpus-building project at work. It contains no real textbook text, company code, or company data.
> Every example sentence was written for this repository.

## Background

Phonics textbooks are organized around "the spelling–sound pattern taught in this lesson."
To digitize that content, every word in every passage needs answers to three questions:

- **How does the word sound?** Grapheme–phoneme correspondences (GPCs), syllables, audio recording
- **What does the word mean?** Part of speech, lemma, sense number, illustration
- **Is the word a target of this lesson?** Does it match the GPCs, word forms, or word relations the lesson teaches?

At work I annotated two textbook series across three levels — tens of thousands of word occurrences — this way.
This repository reproduces that data model and pipeline on a small example dataset.

## Core design: a sound axis and a meaning axis

A word's sounds and meanings do not map one-to-one.

| Example | Spellings | Sounds | Senses |
|---|---|---|---|
| `read` (present / past) | 1 | 2 (/rid/, /rɛd/) | 1 |
| `bow` (ribbon / greeting / to bend) | 1 | 2 (/boʊ/, /baʊ/) | 3 |
| `to` · `too` · `two` | 3 | 1 (/tu/) | 3 |

So each Word row is split into two keys, one per axis.

```
                  Word (one word occurrence in a passage)
                 /                          \
   Sound axis — Token-a                     Meaning axis — p.Lemma-s
   read-1, read-2, bow-1 ...                v.read-1, n.bow-2 ...
        │                                        │
   GPC decomposition (letters, sounds,      Sense dictionary
   syllables, position)                          │
        │                                   Image unit — one sense (+ form) = one image
   Aud_ID — one pronunciation = one recording
```

See the [data model](docs/en/data_model.md) for details and the [glossary](docs/glossary.md) for terms.

## Pipeline

| Step | What it does | Status |
|---|---|---|
| 1 | Assign Line_IDs | Planned |
| 2 | Tokenize, merge phrases | Planned |
| 3 | Part of speech, lemma, sense (context decision files + defaults) | Planned |
| 4 | GPC decomposition | Planned |
| 4-b | Sound numbers (`a#`) with a frozen registry | Planned |
| 5 | Lesson target judgment (main and additional) | Planned |
| 6–8 | Word_ID, high-frequency words, inflection labels | Planned |
| 9 | Sense dictionary, image and audio asset lists | Planned |

## Repository layout

```
├── README.md / README.ko.md
├── docs/
│   ├── glossary.md        # Korean–English glossary
│   ├── en/                # English docs
│   └── ko/                # Korean docs
├── data/                  # Example input (lessons, passage lines)
├── registry/              # Frozen ID registries (sound numbers, recording IDs)
├── src/phonics_toolkit/   # Pipeline code
├── tests/                 # Reproduction and regression tests
└── analysis/              # Analysis notebooks
```

## Progress

- [x] Data model docs, glossary, example data
- [ ] Tokenization and sense judgment (meaning axis)
- [ ] GPC decomposition, sound numbers, Aud_ID (sound axis)
- [ ] Lesson target judgment
- [ ] Asset list generation
- [ ] Decodability analysis

## Running

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
python -m pytest
```
