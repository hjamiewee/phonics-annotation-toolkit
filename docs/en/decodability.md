# Decodability analysis

**English** | [한국어](../ko/decodability.md)

## 1. Question

A phonics passage works when it can be read with the patterns taught so far.
When many untaught spelling–sound correspondences slip in, learners fall back on guessing instead of decoding.

This analysis asks:

- In each lesson, what share of the passage words can be read **with only the GPCs taught so far**?
- Which **GPCs block** the words that cannot be read, and where do those GPCs appear in the lesson sequence?

## 2. Definitions

| Term | Definition |
|---|---|
| Lesson order | Row order of `data/lessons.tsv` |
| `taught(k)` | Baseline GPCs + every main and additional GPC of lessons 1..k |
| Decodable | A word occurrence whose sounded GPCs are all in `taught(k)` |
| Sight | Not decodable, but on the high-frequency word list |
| Blocked | Every other word. Its untaught GPCs are its **blockers** |
| Decodable % | decodable ÷ tokens in the lesson |
| Readable % | (decodable + sight) ÷ tokens in the lesson |

The analysis reuses the pipeline's sound axis, so the pronunciation chosen for each occurrence counts.
For example, past `read` (/rɛd/) needs `ea:ɛ`, while present `read` (/rid/) needs `ea:i`.

## 3. Assumptions

- **Baseline GPCs**: single consonants (`b:b`, `c:k`, `d:d`, …) are known before the first lesson. The list lives in `analysis/baseline_gpc.tsv`; changing it changes the results.
- **Cumulative learning**: a GPC taught once is known in every later lesson.
- **High-frequency words**: words in `hfw.tsv` can be read as wholes.

## 4. Example results

```bash
python -m phonics_toolkit.decodability
```

| Lesson | New GPCs | Tokens | Decodable % | Readable % | Top blockers |
|---|---|---|---|---|---|
| DEMO.A.U1L1 | a:æ | 14 | 57 | 79 | o:ɑ (1), s:z (1), e:ɛ (1) |
| DEMO.A.U1L2 | o:ɑ, o:ɔ | 18 | 67 | 94 | a:eɪ (1) |
| DEMO.A.U2L1 | sh:ʃ | 15 | 13 | 53 | i:ɪ (6), s:z (1) |
| DEMO.A.U2L2 | s:z | 14 | 36 | 57 | i:ɪ (3), u:ʌ (2), wo:u (1) |
| DEMO.A.U3L1 | ea:i | 26 | 15 | 54 | oo:ʊ (3), e:ɛ (3), ay:eɪ (2) |
| DEMO.A.U3L2 | — | 13 | 15 | 69 | oo:u (2), wo:u (2) |

## 5. Reading the results

- **Sequencing gaps show up.** The sh lesson (U2L1) is only 13% decodable. Its top blocker is `i:ɪ` (short i), six times: `ship`, `fish`, and `dish` use short i, but the example curriculum never teaches it. Moving a short-i lesson before the sh lesson, or swapping in short a/o words (`shop`, `cash`), would fix it.
- **Well-built lessons show up too.** In the short-o lesson (U1L2), most words can be read with the short a taught earlier and the short o taught now. It is 94% readable, and the only blocked word is `ate` (long a).
- **The role of high-frequency words**: the gap between decodable % and readable % is what sight words fill in. The homophone lesson (U3L2) is 15% decodable but 69% readable, thanks to `to`, `go`, and `I`.

## 6. Limitations

- **Silent letters are ignored.** A silent letter that changes another sound, like the final e in `ate` (the VCe pattern), is a rule of its own, but this definition does not count it as a blocker.
- **Counts are by token.** A repeated word counts each time. Counting by word type could give different results.
- **High-frequency words are binary.** In practice the sight-word list also grows lesson by lesson.
- **The example data is small.** The point is what the metric reveals, not the numbers themselves.

## 7. Extensions

- **Curriculum comparison**: apply the metric to the lesson sequences of two textbook series and compare their decodability curves by level.
- **Lesson-order optimization**: treat blocker frequency as a cost and search for the order that maximizes total decodability.
- **Passage revision**: suggest decodable replacements for blocked words from the same meaning category.
- **Morphology**: add sounds taught in morphology lessons, such as /z/ in plural `-s`, as a separate axis.
