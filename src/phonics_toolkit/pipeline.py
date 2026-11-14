"""Run every step and produce the Word table, the GPC table, and the asset lists.

Usage:
    python -m phonics_toolkit                    # preview a summary
    python -m phonics_toolkit --write            # write out/*.tsv and append new registry rows
    python -m phonics_toolkit --update-snapshot  # accept the current Word table as the new baseline
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from . import assets
from .inflection import label, load_inflection_context, load_irregular
from .sound import AudRegistry, SoundRegistry, choose_pronunciation, load_pronunciations, load_sound_rules
from .store import DATA_DIR, REPO_ROOT, read_table, write_table
from .target import Targets, judge_lesson
from .words import SENSE_COLUMNS, build_words, sense_view

# 번호 고정 대장 위치 (git 에 올린다 — 번호가 바뀌면 diff 로 보인다)
REGISTRY_DIR = REPO_ROOT / "registry"
# 산출물 위치 (git 에 올리지 않는다)
OUT_DIR = REPO_ROOT / "out"
# 재현 검사용 기준 결과
SNAPSHOT = REPO_ROOT / "tests" / "snapshots" / "words.tsv"

# 최종 Word 표의 열 순서 — 문맥 · 소리 축 · 뜻 축 · 판정 · 출처
WORD_COLUMNS = [
    "word_id", "line_id", "lesson_id", "seq", "token",
    "Token-a", "a#", "pronunciation", "syl_cnt", "aud_id",
    "p.Token", "p.Lemma-s", "pos", "lemma", "s#", "meaning_ko", "meaning_en",
    "inflection", "hfw", "target", "add_target",
    "sense_source", "sound_source",
]
GPC_COLUMNS = ["Token-a", "seq", "gpc", "gr", "ph", "syl_no", "role", "position"]
WORD_ID_COLUMNS = ["word_id", "line_id", "seq", "token"]
SOUND_REGISTRY_COLUMNS = ["Token-a", "token", "pronunciation"]
AUD_REGISTRY_COLUMNS = ["aud_id", "pronunciation"]


@dataclass
class Result:
    """Everything one pipeline run produces."""

    words: list[dict[str, str]]
    word_gpc: list[dict[str, str]]
    word_sense: list[dict[str, str]]
    images: list[dict[str, str]]
    audio: list[dict[str, str]]
    unresolved: list[dict[str, str]] = field(default_factory=list)
    # 이번 실행에서 새로 생긴 대장 행 — 0 이 아니면 --write 로 대장에 반영해야 한다
    new_registry_rows: dict[str, int] = field(default_factory=dict)
    registries: dict[str, tuple[Path, list[dict[str, str]], list[str]]] = field(default_factory=dict)


def assign_word_ids(rows: list[dict[str, str]], path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Give each ``(Line_ID, Seq)`` a frozen Word_ID; returns ``(new rows, whole registry)``."""
    registry = read_table(path, required=WORD_ID_COLUMNS) if path.exists() else []
    by_key = {(r["line_id"], r["seq"]): r for r in registry}
    next_num = max((int(r["word_id"][1:]) for r in registry), default=0) + 1
    new = []
    for row in rows:
        entry = by_key.get((row["line_id"], row["seq"]))
        if entry is None:
            # 처음 보는 자리 — 최댓값 다음 번호를 값으로 고정
            entry = {"word_id": f"W{next_num:05d}", "line_id": row["line_id"], "seq": row["seq"], "token": row["token"]}
            registry.append(entry)
            new.append(entry)
            next_num += 1
        elif entry["token"] != row["token"]:
            # 대장의 낱말과 다르면 줄이 고쳐진 것 — 번호를 엉뚱한 낱말에 주지 않는다
            raise ValueError(f"{row['line_id']}:{row['seq']}: Word_ID {entry['word_id']} was issued for {entry['token']!r}")
        row["word_id"] = entry["word_id"]
    return new, registry


def build(data_dir: Path = DATA_DIR, registry_dir: Path = REGISTRY_DIR) -> Result:
    """Run steps 1–9 in memory. Nothing is written."""
    decisions, lexicon = data_dir / "decisions", data_dir / "lexicon"

    # --- 2~3단계: 토큰화 · 뜻 축 ---
    meaning = build_words(data_dir)
    rows = meaning.rows
    unresolved = [{**u, "axis": "sense"} for u in meaning.unresolved]

    # --- 4 · 4-b단계: 소리 축 ---
    prons = load_pronunciations(lexicon / "gpc.tsv")
    by_position, by_sense = load_sound_rules(decisions / "sound_rules.tsv")
    sound_reg = SoundRegistry.load(registry_dir / "sound_registry.tsv")
    aud_reg = AudRegistry.load(registry_dir / "aud_id.tsv")
    gpcs_of = {}
    for r in rows:
        found = choose_pronunciation(r, prons, by_position, by_sense)
        if found is None:
            # 분해가 없는 낱말 — 소리 칸을 비우고 미해결로 보고
            unresolved.append({"line_id": r["line_id"], "seq": r["seq"], "token": r["token"], "axis": "sound"})
            r.update({"Token-a": "", "a#": "", "pronunciation": "", "syl_cnt": "", "aud_id": "", "sound_source": ""})
            continue
        pron, source = found
        token = pron.token
        n = sound_reg.number(token, pron.phonemes)
        r.update({
            "Token-a": f"{token}-{n}",
            "a#": str(n),
            "pronunciation": pron.phonemes,
            "syl_cnt": str(pron.syllables),
            "aud_id": aud_reg.aud_id(pron.phonemes),
            "sound_source": source,
        })
        gpcs_of[r["Token-a"]] = pron.gpcs

    # --- 8단계: 굴절형 (타깃 판정의 형태 축이 쓰므로 먼저 계산) ---
    irregular = load_irregular(lexicon / "irregular.tsv")
    infl_context = load_inflection_context(decisions / "inflection_context.tsv")
    for r in rows:
        r["inflection"] = label(r, irregular, infl_context)

    # --- 7단계: 고빈도어 (표기 일치 · 대소문자 무시) ---
    hfw = {r["token"].lower() for r in read_table(lexicon / "hfw.tsv", required=["token"])}
    for r in rows:
        r["hfw"] = "Y" if r["token"].lower() in hfw else "N"

    # --- 6단계: Word_ID ---
    new_ids, id_registry = assign_word_ids(rows, registry_dir / "word_id.tsv")

    # --- 5단계: 레슨 타깃 (메인 · 추가) ---
    lessons = {l["lesson_id"]: l for l in read_table(data_dir / "lessons.tsv")}
    by_lesson = defaultdict(list)
    for r in rows:
        by_lesson[r["lesson_id"]].append(r)
    for lesson_id, lesson_rows in by_lesson.items():
        lesson = lessons[lesson_id]
        for column, suffix in (("target", ""), ("add_target", "_add")):
            verdicts = judge_lesson(lesson_rows, gpcs_of, Targets.from_lesson(lesson, suffix))
            for r, v in zip(lesson_rows, verdicts):
                r[column] = v

    # --- GPC 표: 쓰인 소리 키마다 분해 행 ---
    word_gpc = [
        {"Token-a": key, "seq": str(g.seq), "gpc": g.label, "gr": g.gr, "ph": g.ph,
         "syl_no": str(g.syl_no), "role": g.role, "position": g.position}
        for key in sorted(gpcs_of) for g in gpcs_of[key]
    ]

    # --- 9단계: 뜻 사전 · 에셋 목록 ---
    return Result(
        words=rows,
        word_gpc=word_gpc,
        word_sense=sense_view(rows),
        images=assets.image_assets(rows),
        audio=assets.audio_assets(rows),
        unresolved=unresolved,
        new_registry_rows={"sound_registry": len(sound_reg.new), "aud_id": len(aud_reg.new), "word_id": len(new_ids)},
        registries={
            "sound_registry": (registry_dir / "sound_registry.tsv", sound_reg.rows, SOUND_REGISTRY_COLUMNS),
            "aud_id": (registry_dir / "aud_id.tsv", aud_reg.rows, AUD_REGISTRY_COLUMNS),
            "word_id": (registry_dir / "word_id.tsv", id_registry, WORD_ID_COLUMNS),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the whole annotation pipeline.")
    parser.add_argument("--write", action="store_true", help="write out/*.tsv and append new registry rows")
    parser.add_argument("--update-snapshot", action="store_true", help="overwrite tests/snapshots/words.tsv")
    args = parser.parse_args()

    result = build()
    words = result.words
    # 요약: 토큰 수 · 판정 출처 · 타깃 수 · 에셋 수 · 미해결 · 새 대장 행
    print(f"tokens: {len(words)}  senses: {len(result.word_sense)}  sound keys: {len({w['Token-a'] for w in words})}")
    print(f"sense source: {dict(Counter(w['sense_source'] for w in words))}  "
          f"sound source: {dict(Counter(w['sound_source'] for w in words))}")
    print(f"target Y: {sum(w['target'] == 'Y' for w in words)}  add_target Y: {sum(w['add_target'] == 'Y' for w in words)}")
    print(f"image assets: {len(result.images)}  audio assets: {len(result.audio)}")
    print(f"unresolved: {len(result.unresolved)}  new registry rows: {result.new_registry_rows}")
    for u in result.unresolved:
        print(f"  unresolved {u['axis']:<5} {u['line_id']}:{u['seq']} {u['token']!r}")

    if args.write:
        for name, rows, columns in (
            ("words", words, WORD_COLUMNS),
            ("word_gpc", result.word_gpc, GPC_COLUMNS),
            ("word_sense", result.word_sense, SENSE_COLUMNS),
            ("img_assets", result.images, assets.IMAGE_COLUMNS),
            ("aud_assets", result.audio, assets.AUDIO_COLUMNS),
        ):
            write_table(OUT_DIR / f"{name}.tsv", rows, columns)
        # 대장은 새 행이 있을 때만 다시 쓴다 (기존 행은 그대로 · 뒤에 붙기만 한다)
        for name, (path, rows, columns) in result.registries.items():
            if result.new_registry_rows[name]:
                write_table(path, rows, columns)
        print("written: out/*.tsv" + ("  + registry" if any(result.new_registry_rows.values()) else ""))
    if args.update_snapshot:
        # 판정을 바꾼 뒤 결과를 확인했을 때만 기준을 새로 찍는다
        write_table(SNAPSHOT, words, WORD_COLUMNS)
        print(f"snapshot updated: {SNAPSHOT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
