#!/usr/bin/env python3
"""Parse the two requirement Markdown files into site/data.json.

Run from anywhere:
    python3 site/build.py
"""
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = {
    "student": ROOT / "_分析" / "彙整" / "產品需求清單-學生視角.md",
    "teacher": ROOT / "_分析" / "彙整" / "產品需求清單-老師視角.md",
}
OUT = Path(__file__).resolve().parent / "data.json"

PERSPECTIVE_LABEL_TO_KEY = {"老師": "teacher", "學生": "student"}

CATEGORY_RE = re.compile(r"^##\s+([A-Z])\.\s+(.+?)\s*$")
ITEM_RE = re.compile(r"^###\s+([A-Z]\.\d+)\s+(.+?)\s*$")
PROBLEM_RE = re.compile(r"^-\s+\*\*問題\*\*[：:]\s*(.*)$")
OBSERVATION_RE = re.compile(r"^>\s*\*\*觀察\*\*[：:]\s*(.*)$")
RELATION_RE = re.compile(
    r"^-\s+\*\*關聯（(學生|老師)視角(?:・(衝突))?）\*\*[：:]\s*(.*)$"
)
TRACE_RE = re.compile(r"^<!--\s*追溯[：:]\s*\[(.+?)\]\((.+?)\)\s*-->\s*$")
REL_ITEM_RE = re.compile(r"([A-Z]\.\d+)\s+(.+?)(?=\s*[；;]\s*[A-Z]\.\d+|$)")


def parse_file(path: Path, perspective: str):
    lines = path.read_text(encoding="utf-8").splitlines()
    categories: list[dict] = []
    cards: list[dict] = []
    current_category = None
    current_card = None

    i = 0
    while i < len(lines):
        line = lines[i]

        m = CATEGORY_RE.match(line)
        if m:
            current_card = None
            current_category = {"code": m.group(1), "name": m.group(2), "count": 0}
            categories.append(current_category)
            i += 1
            continue

        m = ITEM_RE.match(line)
        if m:
            code = m.group(1)
            title = m.group(2)
            cat_code = code.split(".")[0]
            cat_name = current_category["name"] if current_category else ""
            current_card = {
                "id": f"{perspective}-{code}",
                "perspective": perspective,
                "category": cat_code,
                "categoryName": cat_name,
                "code": code,
                "title": title,
                "problem": "",
                "observation": None,
                "relations": [],
                "sourceLink": None,
                "sourceLabel": None,
            }
            cards.append(current_card)
            if current_category:
                current_category["count"] += 1
            i += 1
            continue

        if current_card is None:
            i += 1
            continue

        m = PROBLEM_RE.match(line)
        if m:
            current_card["problem"] = m.group(1).strip()
            i += 1
            continue

        m = OBSERVATION_RE.match(line)
        if m:
            parts = [m.group(1).strip()]
            j = i + 1
            while j < len(lines) and lines[j].startswith(">"):
                cont = lines[j].lstrip("> ").strip()
                if cont:
                    parts.append(cont)
                j += 1
            current_card["observation"] = " ".join(p for p in parts if p)
            i = j
            continue

        m = RELATION_RE.match(line)
        if m:
            other_label = m.group(1)
            other_key = PERSPECTIVE_LABEL_TO_KEY[other_label]
            conflict = m.group(2) == "衝突"
            value = m.group(3).strip()
            for rel_match in REL_ITEM_RE.finditer(value):
                rel_code = rel_match.group(1)
                fallback_title = rel_match.group(2).strip().rstrip("；;").strip()
                current_card["relations"].append(
                    {
                        "perspective": other_key,
                        "code": rel_code,
                        "title": fallback_title,
                        "conflict": conflict,
                    }
                )
            i += 1
            continue

        m = TRACE_RE.match(line)
        if m:
            current_card["sourceLabel"] = m.group(1)
            current_card["sourceLink"] = m.group(2)
            i += 1
            continue

        i += 1

    return categories, cards


def main():
    all_cards: list[dict] = []
    all_categories: dict[str, list[dict]] = {}
    for perspective, path in SOURCES.items():
        if not path.exists():
            raise SystemExit(f"Source not found: {path}")
        categories, cards = parse_file(path, perspective)
        all_categories[perspective] = categories
        all_cards.extend(cards)

    # Second pass: resolve relation titles to canonical titles when available.
    title_lookup = {(c["perspective"], c["code"]): c["title"] for c in all_cards}
    unresolved: list[str] = []
    for card in all_cards:
        for rel in card["relations"]:
            canonical = title_lookup.get((rel["perspective"], rel["code"]))
            if canonical:
                rel["title"] = canonical
            else:
                unresolved.append(f"{card['id']} -> {rel['perspective']}-{rel['code']}")

    output = {
        "generatedAt": date.today().isoformat(),
        "counts": {
            "student": sum(1 for c in all_cards if c["perspective"] == "student"),
            "teacher": sum(1 for c in all_cards if c["perspective"] == "teacher"),
            "total": len(all_cards),
        },
        "categories": all_categories,
        "cards": all_cards,
    }

    OUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",  # 固定用 LF，避免在 Windows 產生 CRLF 造成整檔 diff
    )
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(f"  student: {output['counts']['student']} cards")
    print(f"  teacher: {output['counts']['teacher']} cards")
    print(f"  total:   {output['counts']['total']} cards")
    if unresolved:
        print(f"  ⚠ {len(unresolved)} unresolved relation references (using fallback titles):")
        for u in unresolved[:10]:
            print(f"    - {u}")
        if len(unresolved) > 10:
            print(f"    ... and {len(unresolved) - 10} more")


if __name__ == "__main__":
    main()
