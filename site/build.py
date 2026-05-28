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
INSIGHTS_PATH = ROOT / "_分析" / "彙整" / "跨視角洞察.md"
OUT = Path(__file__).resolve().parent / "data.json"

PERSPECTIVE_LABEL_TO_KEY = {"老師": "teacher", "學生": "student"}

HEADING_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
LIST_ITEM_RE = re.compile(r"^[-*]\s+(.+)$")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
# 明確語法：[X.Y|師] / [X.Y|生] 強制標註視角，最高優先級
# 否則用 PERSPECTIVE_MARKER_RE 推論。更具體的 marker 寫在前面。
EXPLICIT_REF_RE = re.compile(r"\[([A-Z]\.\d+)\|([師生])\]")
REF_RE = re.compile(r"([A-Z])\.(\d+)")
COMBINED_REF_RE = re.compile(
    r"\[([A-Z]\.\d+)\|([師生])\]|([A-Z])\.(\d+)"
)
PERSPECTIVE_MARKER_RE = re.compile(
    r"(老師端|學生端|老師（|學生（|老師視角|學生視角|老師詞彙|學生詞彙|"
    r"老師講什麼|學生講什麼|老師完全沒寫|學生不會講|"
    r"老師對 AI|學生對 AI|老師對|學生對|老師清單|學生清單|老師只|學生只)"
)
SECTION_MARKER_RE = re.compile(r"^\*\*只有(學生|老師)端")

CATEGORY_RE = re.compile(r"^##\s+([A-Z])\.\s+(.+?)\s*$")
ITEM_RE = re.compile(r"^###\s+([A-Z]\.\d+)\s+(.+?)\s*$")
PROBLEM_RE = re.compile(r"^-\s+\*\*問題\*\*[：:]\s*(.*)$")
OBSERVATION_RE = re.compile(r"^>\s*\*\*觀察\*\*[：:]\s*(.*)$")
RELATION_RE = re.compile(
    r"^-\s+\*\*關聯（(學生|老師)視角(?:・(衝突))?）\*\*[：:]\s*(.*)$"
)
TRACE_RE = re.compile(r"^<!--\s*追溯[：:]\s*\[(.+?)\]\((.+?)\)\s*-->\s*$")
REL_ITEM_RE = re.compile(r"([A-Z]\.\d+)\s+(.+?)(?=\s*[；;]\s*[A-Z]\.\d+|$)")


def _escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _detect_perspective_for_ref(text_before: str, default: str = None) -> str:
    """For an X.N ref appearing after `text_before` in the same inline run,
    determine the perspective by finding the nearest 老師端／學生端／等強訊號 marker
    before the ref. Falls back to `default` if none found."""
    matches = list(PERSPECTIVE_MARKER_RE.finditer(text_before))
    if not matches:
        return default
    marker = matches[-1].group(1)
    return "teacher" if marker.startswith("老師") else "student"


def _block_default_perspective(text: str, fallback: str = None) -> str:
    """Determine the default perspective for an entire block (paragraph/list item)
    based on the first perspective marker found in its text."""
    m = PERSPECTIVE_MARKER_RE.search(text)
    if not m:
        return fallback
    return "teacher" if m.group(1).startswith("老師") else "student"


def _item_start_perspective(item_text: str) -> str | None:
    """Only return a perspective if the item TEXT starts with a perspective marker
    (after stripping leading `**`). This is used so list items don't override
    list_default unless the item begins with an explicit subject indicator."""
    stripped = item_text.lstrip("*").lstrip()
    m = PERSPECTIVE_MARKER_RE.match(stripped)
    if not m:
        return None
    return "teacher" if m.group(1).startswith("老師") else "student"


def _emit_text_with_refs(
    s: str,
    default_perspective: str = None,
    force_perspective: str = None,
) -> str:
    """Convert a plain (no bold) text run to HTML with `<button class="ref-tag">`
    wrapping every X.N or `[X.Y|師生]` reference.

    - `force_perspective`: if set, every plain ref uses this perspective
      (explicit `[X.Y|師生]` syntax always wins). Useful for table cells.
    - `default_perspective`: fallback when neither explicit syntax nor
      nearest-marker-before-ref provides a perspective.
    """
    parts = []
    last = 0
    for m in COMBINED_REF_RE.finditer(s):
        parts.append(_escape_html(s[last:m.start()]))
        if m.group(1):
            # 明確語法 [X.Y|師生] 永遠最優先
            code = m.group(1)
            persp = "teacher" if m.group(2) == "師" else "student"
        else:
            code = f"{m.group(3)}.{m.group(4)}"
            if force_perspective:
                persp = force_perspective
            elif m.group(3) == "J":
                # J 類別僅存在於老師清單
                persp = "teacher"
            else:
                persp = _detect_perspective_for_ref(s[:m.start()], default_perspective)
        if persp:
            parts.append(
                f'<button type="button" class="ref-tag ref-tag-{persp}" '
                f'data-perspective="{persp}" data-code="{code}">'
                f'{_escape_html(code)}</button>'
            )
        else:
            parts.append(_escape_html(code))
        last = m.end()
    parts.append(_escape_html(s[last:]))
    return "".join(parts)


def _inline(
    s: str,
    default_perspective: str = None,
    force_perspective: str = None,
) -> str:
    parts = []
    cursor = 0
    for bm in BOLD_RE.finditer(s):
        parts.append(
            _emit_text_with_refs(s[cursor:bm.start()], default_perspective, force_perspective)
        )
        # 粗體內不再處理 ref tag（粗體通常是強調語、不會放程式碼）
        parts.append(f"<strong>{_escape_html(bm.group(1))}</strong>")
        cursor = bm.end()
    parts.append(_emit_text_with_refs(s[cursor:], default_perspective, force_perspective))
    return "".join(parts)


def md_to_html(md: str) -> str:
    """Minimal Markdown → HTML for the insights file.

    Supports: # / ## / ### headings, paragraphs, **bold**, bullet lists,
    pipe tables, horizontal rules. Detects `**啟示**:` paragraphs and wraps
    them with `class="insight-callout"`. Tags X.N references with
    `<button class="ref-tag">` so the frontend can open the matching card.
    """
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    in_list = False
    section_perspective: str | None = None  # 由 **只有X端...** 設定，由 ## 或 --- 重置
    pending_list_default: str | None = None  # 來自前一個段落的視角；下一個清單繼承
    list_default: str | None = None          # 當前清單繼承來的視角

    def close_list():
        nonlocal in_list, list_default
        if in_list:
            out.append("</ul>")
            in_list = False
            list_default = None

    def _column_perspective(cell: str) -> str | None:
        """Determine perspective from a table header cell."""
        # 學生 prefix / 學生視角 / 學生（要即時）等
        if "學生" in cell:
            return "student"
        if "老師" in cell:
            return "teacher"
        return None

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped == "---":
            close_list()
            section_perspective = None
            pending_list_default = None
            out.append("<hr>")
            i += 1
            continue

        m = HEADING_RE.match(line)
        if m:
            close_list()
            section_perspective = None
            pending_list_default = None
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue

        if (
            stripped.startswith("|")
            and i + 1 < n
            and TABLE_SEP_RE.match(lines[i + 1].strip())
        ):
            close_list()
            pending_list_default = None
            header_cells = [c.strip() for c in stripped.strip("|").split("|")]
            col_persp = [_column_perspective(c) for c in header_cells]
            out.append("<table><thead><tr>")
            for c in header_cells:
                out.append(f"<th>{_inline(c)}</th>")
            out.append("</tr></thead><tbody>")
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                row = lines[i].strip()
                cells = [c.strip() for c in row.strip("|").split("|")]
                out.append("<tr>")
                for idx, c in enumerate(cells):
                    persp = col_persp[idx] if idx < len(col_persp) else None
                    # 表格 cell 一律用欄位視角強制標註；明確 [X.Y|師生] 仍會 override
                    out.append(f"<td>{_inline(c, force_perspective=persp)}</td>")
                out.append("</tr>")
                i += 1
            out.append("</tbody></table>")
            continue

        m = LIST_ITEM_RE.match(stripped)
        if m:
            if not in_list:
                out.append("<ul>")
                in_list = True
                # 清單開頭：繼承上一段段落的視角，否則用 section_perspective
                list_default = pending_list_default or section_perspective
                pending_list_default = None
            item_text = m.group(1).strip()
            # 優先序：item 開頭明確 marker（如「老師端要...」）> list_default > section
            # 不掃整個 item，避免「C.5 希望保留學生對話...」誤判為 student
            item_default = (
                _item_start_perspective(item_text)
                or list_default
                or section_perspective
            )
            out.append(f"<li>{_inline(item_text, default_perspective=item_default)}</li>")
            i += 1
            continue

        if not stripped:
            close_list()
            i += 1
            continue

        close_list()

        # 偵測「**只有(學生|老師)端...」這種 section marker，設定後續清單的預設視角
        sm = SECTION_MARKER_RE.match(stripped)
        if sm:
            section_perspective = "student" if sm.group(1) == "學生" else "teacher"

        if stripped.startswith("**啟示**"):
            after = stripped.replace("**啟示**", "", 1).lstrip("：:").strip()
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            next_is_list = j < n and LIST_ITEM_RE.match(lines[j].strip())
            if not after and next_is_list:
                # 「**啟示**：」獨立成段、後面緊接著條列：合併成一個整框
                callout_default = section_perspective
                out.append('<div class="insight-callout"><p><strong>啟示</strong></p><ul>')
                i = j
                while i < n and LIST_ITEM_RE.match(lines[i].strip()):
                    item = LIST_ITEM_RE.match(lines[i].strip()).group(1).strip()
                    item_default = _item_start_perspective(item) or callout_default
                    out.append(f"<li>{_inline(item, default_perspective=item_default)}</li>")
                    i += 1
                out.append("</ul></div>")
                pending_list_default = None
                continue
            para_default = _block_default_perspective(stripped, section_perspective)
            out.append(
                f'<p class="insight-callout">'
                f'{_inline(stripped, default_perspective=para_default)}</p>'
            )
            pending_list_default = para_default
            i += 1
            continue

        para_default = _block_default_perspective(stripped, section_perspective)
        out.append(f"<p>{_inline(stripped, default_perspective=para_default)}</p>")
        # 段落結束後，記住此段視角，給下一個（緊鄰的）清單繼承
        pending_list_default = para_default
        i += 1

    close_list()
    return "\n".join(out)


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

    insights_html = ""
    if INSIGHTS_PATH.exists():
        insights_html = md_to_html(INSIGHTS_PATH.read_text(encoding="utf-8"))

    output = {
        "generatedAt": date.today().isoformat(),
        "counts": {
            "student": sum(1 for c in all_cards if c["perspective"] == "student"),
            "teacher": sum(1 for c in all_cards if c["perspective"] == "teacher"),
            "total": len(all_cards),
        },
        "categories": all_categories,
        "cards": all_cards,
        "insightsHtml": insights_html,
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
