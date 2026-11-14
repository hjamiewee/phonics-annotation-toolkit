# 처리 단계 (워크플로)

[English](../en/workflow.md) | **한국어**

## 공통 원칙

- **기본은 미리보기입니다.** 명령은 요약만 보여주고, `--write`를 붙여야 파일에 씁니다.
- **사람 판정은 결정 파일에, 코드는 적용만.** 코드가 뜻이나 구를 추측하지 않습니다. 모르는 것은 미해결로 남깁니다.
- **입력은 `data/`, 산출물은 `out/`.** `out/`은 git에 올리지 않고, 언제든 입력에서 다시 만들 수 있습니다.
- **재현 검사.** 결과를 `tests/snapshots/`의 기준과 비교해, 판정이 바뀌면 diff로 드러나게 합니다.

## 입력 파일

| 파일 | 내용 | 누가 고치나 |
|---|---|---|
| `data/lessons.tsv` | 레슨과 타깃 (메인 4축, 추가 4축) | 사람 |
| `data/lines.tsv` | 지문 줄. `Line_ID`는 1단계가 채웁니다 | 사람 (+1단계) |
| `data/decisions/phrases.tsv` | 하나의 토큰으로 묶을 구·합성어 목록 | 사람 |
| `data/decisions/defaults.tsv` | 낱말 표기별 대표 뜻 | 사람 |
| `data/decisions/context.tsv` | 문맥 키 `(Line_ID, Seq)`별 판정과 근거 | 사람 |
| `data/lexicon/senses.tsv` | 뜻 사전: `p.Lemma-s`, 한국어·영어 뜻 | 사람 |

## 1단계: Line_ID 부여

```bash
python -m phonics_toolkit.ids            # 미리보기
python -m phonics_toolkit.ids --write    # data/lines.tsv 에 반영
```

- `line_id`가 빈 줄에만 새 번호를 줍니다. 이미 있는 번호는 건드리지 않습니다.
- 새 번호 = 기존 최댓값 + 1. 두 번 돌려도 결과가 같습니다.
- 번호를 값으로 적기 때문에, 줄을 정렬하거나 끼워 넣어도 번호가 바뀌지 않습니다. 문맥 판정이 `Line_ID`를 키로 쓰기 때문에 이 성질이 중요합니다.

## 2단계: 토큰화와 구 병합

- 낱말만 토큰이 됩니다. 마침표, 쉼표, 낱말 목록의 가운뎃점(`·`)은 버립니다.
- 낱말 안쪽의 아포스트로피와 하이픈은 낱말에 붙여 둡니다 (`Pam's`, `good-bye`).
- `phrases.tsv`에 있는 구만 하나로 묶습니다. 겹치면 가장 긴 구를 고릅니다.
  - `hot dog`(핫도그)는 목록에 있어 한 토큰이 됩니다.
  - `hot pot`(뜨거운 냄비)은 목록에 없어 두 토큰으로 남습니다. 형태가 같아도 하나로 묶을지는 사람이 정합니다.
- `Seq`는 병합한 **뒤에** 셉니다. `I read a book every day.`에서 `every day`는 5번 한 자리입니다.

## 3단계: 품사·원형·뜻

토큰 하나의 뜻은 아래 순서로 정합니다.

| 순서 | 찾는 곳 | 예 |
|---|---|---|
| 1 | 문맥 판정 `(Line_ID, Seq)` | `The actor took a bow.`의 `bow` → `n.bow-2` 인사 |
| 2 | 대표값, 대소문자 그대로 | `I` → `pron.I-1`, `Pam` → `propn.Pam-1` |
| 3 | 대표값, 소문자로 | 문장 첫머리 `The` → `det.the-1` |
| 4 | 없음 → **미해결** | 추측하지 않고 목록으로 보여줍니다 |

```bash
python -m phonics_toolkit.words                    # 요약과 미해결 목록
python -m phonics_toolkit.words --write            # out/words.tsv, out/word_sense.tsv
python -m phonics_toolkit.words --update-snapshot  # 기준 결과 갱신
```

### 안전장치

- **오래된 판정 감지**: 문맥 판정에는 판정할 때의 낱말(`token`)을 함께 적습니다. 줄이 고쳐져 그 자리에 다른 낱말이 오면 실행을 멈춥니다. 엉뚱한 낱말에 판정이 붙는 것을 막기 위해서입니다.
- **갈 곳 없는 판정 감지**: 어떤 토큰에도 닿지 않는 문맥 판정(줄이 지워졌거나 `Seq`가 밀린 경우)이 있으면 멈춥니다.
- **사전에 없는 뜻 감지**: 대표값이나 문맥 판정이 `senses.tsv`에 없는 뜻 키를 가리키면 시작 전에 멈춥니다.

### 산출물

| 파일 | 행 단위 | 주요 열 |
|---|---|---|
| `out/words.tsv` | 낱말 출현 하나 | `line_id`, `seq`, `token`, `p.Token`, `p.Lemma-s`, 뜻, `source` |
| `out/word_sense.tsv` | 쓰인 뜻 하나 | `p.Lemma-s`, 그 뜻을 쓰는 표면형(`cat, cats`), 뜻, 횟수 |

`source`는 판정의 출처(`context` 또는 `default`)입니다. 사람이 검토할 때 문맥 판정이 붙은 자리만 골라 볼 수 있습니다.

## 4단계 이후 (예정)

| 단계 | 하는 일 |
|---|---|
| 4 | GPC 분해 (소리 축) |
| 4-b | 소리 번호 `a#`, 번호 고정 대장, Aud_ID |
| 5 | 레슨 타깃 판정 |
| 6~8 | Word_ID, 고빈도어, 굴절형 |
| 9 | 이미지·음성 에셋 목록 |
