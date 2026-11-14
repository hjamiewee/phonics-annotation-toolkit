"""Check that the English and Korean docs stay structurally in sync.

Both language versions must exist for every document and must have the same
heading structure (same number of headings at each level, in the same order).
"""

import re
from pathlib import Path

import pytest

# 저장소 맨 위 폴더
ROOT = Path(__file__).resolve().parents[1]
# 마크다운 제목 줄 (# ~ ######) — 코드 블록 안의 # 은 따로 걸러낸다
HEADING = re.compile(r"^(#{1,6})\s")

# 짝을 이루는 문서 목록: (영어, 한국어)
PAIRS = [(ROOT / "README.md", ROOT / "README.ko.md")] + [
    (p, ROOT / "docs" / "ko" / p.name) for p in sorted((ROOT / "docs" / "en").glob("*.md"))
]


def heading_levels(path: Path) -> list[int]:
    """Return the level of every Markdown heading in order, skipping fenced code blocks."""
    levels = []
    # 코드 블록(```) 안에 있는지 표시
    in_code = False
    for line in path.read_text(encoding="utf-8").splitlines():
        # ``` 를 만나면 코드 블록 안/밖을 뒤집는다
        if line.startswith("```"):
            in_code = not in_code
            continue
        # 코드 블록 밖의 제목 줄만 센다
        m = None if in_code else HEADING.match(line)
        if m:
            # 제목 수준 = # 의 개수
            levels.append(len(m.group(1)))
    return levels


def test_every_english_doc_has_a_korean_version():
    """Each docs/en file must have a docs/ko file with the same name, and vice versa."""
    # 두 폴더의 파일 이름 집합이 같아야 한다
    en = {p.name for p in (ROOT / "docs" / "en").glob("*.md")}
    ko = {p.name for p in (ROOT / "docs" / "ko").glob("*.md")}
    assert en == ko, f"only in en: {en - ko}, only in ko: {ko - en}"


@pytest.mark.parametrize("en_path, ko_path", PAIRS, ids=lambda p: p.name)
def test_heading_structure_matches(en_path: Path, ko_path: Path):
    """Both versions of a document must have the same heading levels in the same order."""
    # 한쪽에만 절을 추가하면 여기서 실패한다
    assert heading_levels(en_path) == heading_levels(ko_path)
