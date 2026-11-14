# Data model: a sound axis and a meaning axis

**English** | [한국어](../ko/data_model.md)

## 1. Why two axes

A phonics textbook needs two kinds of information about each word.

- **Sound**: how the spelling is pronounced. Used for reading instruction and audio recording.
- **Meaning**: what the word means in this context. Used for glosses and illustrations.

The problem is that the two do not map one-to-one.

| Word | Situation | Sounds | Senses |
|---|---|---|---|
| `read` | `I can read.` / `I read it yesterday.` | two: /rid/, /rɛd/ | one: "to read" |
| `bow` | ribbon / greeting / to bend | two: /boʊ/, /baʊ/ | three |
| `to` · `too` · `two` | three spellings | one: /tu/ | three |

If sound and meaning share a single key such as `part of speech + word`, things go wrong:

- Present and past `read` share a key, so they collapse into one recording.
- `to`, `too`, and `two` get recorded separately, even though they sound the same.
- The ribbon `bow` and the greeting `bow` end up with the same image.

So this model gives every Word row **a sound key (`Token-a`) and a meaning key (`p.Lemma-s`) separately**.

## 2. Hierarchy

```
Lesson
 └─ Activity
     └─ Line (one line of a passage: word, phrase, or sentence)
         └─ Word (one word occurrence within the line)
```

- **Lesson**: records what the lesson targets (GPCs, position, word forms, word relations).
- **Line**: one line of a passage, identified by `Line_ID`.
- **Word**: one occurrence, including its position in the line (`Seq`). `(Line_ID, Seq)` is the context key.

IDs are **stored as literal values**. They are not computed from row positions, so sorting or inserting rows
never renumbers them. A new ID is the current maximum + 1.

## 3. Sound axis (Token)

### 3.1 Token-a: the sound key

`Token-a` = lowercase Token + `-` + sound number (`a#`)

| Token | Pronunciation | Token-a |
|---|---|---|
| `read` | /rid/ | `read-1` |
| `read` | /rɛd/ | `read-2` |
| `bow` | /boʊ/ | `bow-1` |
| `bow` | /baʊ/ | `bow-2` |

- It carries no part of speech, because sound does not depend on it. `n.bow` (greeting) and `v.bow` (to bend) are both `bow-2`.
- Capitalization is folded. `Rose` and `rose` sound the same.

### 3.2 GPC decomposition

Each Token-a is split into grapheme–phoneme correspondence (GPC) rows.

| Token-a | seq | Gr (grapheme) | Ph (phoneme) | syl_no | position |
|---|---|---|---|---|---|
| `read-1` | 1 | r | r | 1 | initial |
| `read-1` | 2 | ea | i | 1 | medial |
| `read-1` | 3 | d | d | 1 | final |
| `read-2` | 1 | r | r | 1 | initial |
| `read-2` | 2 | ea | ɛ | 1 | medial |
| `read-2` | 3 | d | d | 1 | final |

Rule: **one Token with one sound has exactly one decomposition.** There are no per-part-of-speech decompositions.

### 3.3 Frozen sound-number registry

Once an `a#` is assigned, it never changes.

- A new sound gets the next number for that Token and is recorded in the registry (`registry/sound_registry.tsv`).
- Even when no word uses a sound anymore, its number stays in the registry, so the same number can never point to a different sound.

### 3.4 Aud_ID: recording IDs

The recording unit is the **pronunciation**, not the Token-a. Each pronunciation gets a fixed ID starting at `A00001`.

| Aud_ID | Pronunciation | Token-a |
|---|---|---|
| `A00001` | tu | `to-1`, `too-1`, `two-1` |
| `A00002` | rid | `read-1` |
| `A00003` | rɛd | `read-2` |

`to`, `too`, and `two` share one recording. Aud_IDs are never changed or deleted either.

## 4. Meaning axis (Lemma)

### 4.1 p.Lemma-s: the sense key

`p.Lemma-s` = part of speech + `.` + lemma + `-` + sense number (`s#`)

| Sentence | Token | p.Lemma-s | Sense |
|---|---|---|---|
| `She can tie a bow.` | bow | `n.bow-1` | ribbon |
| `The actor took a bow.` | bow | `n.bow-2` | a bending greeting |
| `I read a book every day.` | read | `v.read-1` | to read |
| `Yesterday I read a book.` | read | `v.read-1` | to read |

`read` has two sounds but only one sense, `v.read-1`. This is the clearest case of the two axes moving independently.

### 4.2 Context decisions: (Line_ID, Seq)

The same spelling can mean different things in different contexts. So human judgments are attached to the
**context key `(Line_ID, Seq)`** and kept in decision files.

- Positions listed in a decision file use that judgment.
- Positions not listed fall back to the word's **default sense**.
- Decision files live in git, so every change to a judgment has a record of when and why.

### 4.3 Image units

By default there is one image per sense. Forms that change the picture for the same sense get a suffix.

| Key | Meaning | Example |
|---|---|---|
| `n.cat-1` | base | one cat |
| `n.cat-1.pl` | plural | several cats |
| `adj.big-1.cmp` | comparative | the bigger one |
| `adj.big-1.sup` | superlative | the biggest one |

## 5. Anatomy of one Word row

`read` in `Yesterday I read a book.`:

| Column | Value | Axis |
|---|---|---|
| Line_ID, Seq | `L00020`, 3 | context |
| Token | `read` | — |
| Token-a | `read-2` | sound |
| a# | 2 | sound |
| p.Token | `v.read` | bridge |
| p.Lemma-s | `v.read-1` | meaning |
| Meaning | to read | meaning |
| Inflection | past | form |

`p.Token` (part of speech + Token) acts as the bridge between the two axes.

## 6. Design principles

1. **IDs are frozen.** Row IDs, `a#`, and Aud_IDs are never changed or deleted once assigned.
2. **One Token with one sound has one decomposition.** A conflict is an error, not a variant.
3. **Human judgments live in decision files.** They are keyed by context, and the code only reads them.
4. **Columns are found by name.** Reordering columns never breaks the code.
5. **Judgment changes are checked by reproduction tests.** After any structural change, a test confirms the judgments are unchanged before moving on.
