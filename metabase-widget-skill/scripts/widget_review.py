#!/usr/bin/env python3
"""Parse and update widget-review.md for the metabase-widget skill.

Stdlib-only.

Subcommands:
    parse           Parse widget-review.md → JSON to stdout
    update-results  Write Stage 2 API results back into widget-review.md

The parser is intentionally strict: it reports the exact line number of any
problem rather than silently skipping malformed content.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SummaryRow:
    number: int
    requirement: str
    widget_title: str
    recommended_approach: str
    tier: str
    visualization: str
    alternative_approach: str
    alt_tier: str
    alt_visualization: str
    status: str
    result: str
    line: int = 0


@dataclass
class DetailedSection:
    number: int
    title: str
    question: str = ""
    payload_context: str = ""
    recommended_approach_md: str = ""
    sql: str = ""
    assumptions: str = ""
    save_title: str = ""
    save_description: str = ""
    display: str = ""
    visualization_settings: dict | None = None
    line: int = 0


@dataclass
class Widget:
    number: int
    title: str
    requirement: str
    status: str
    tier: str
    display: str
    sql: str
    description: str
    visualization_settings: dict = field(default_factory=dict)
    is_ready: bool = False


# ---------------------------------------------------------------------------
# Parse summary table
# ---------------------------------------------------------------------------

EXPECTED_HEADERS = [
    "#",
    "Requirement",
    "Widget Title",
    "Recommended Approach",
    "Tier",
    "Visualization",
    "Alternative Approach",
    "Alt Tier",
    "Alt Visualization",
    "Status",
    "Result",
]


def _split_row(line: str) -> list[str]:
    parts = line.split("|")
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    return [p.strip() for p in parts]


def parse_summary(lines: list[str]) -> list[SummaryRow]:
    in_summary = False
    header_idx: int | None = None
    headers: list[str] = []
    rows: list[SummaryRow] = []

    for idx, raw in enumerate(lines, start=1):
        if raw.strip().startswith("## Summary"):
            in_summary = True
            continue
        if not in_summary:
            continue
        if raw.strip().startswith("## ") and not raw.strip().startswith("## Summary"):
            break
        if "|" not in raw:
            continue
        cells = _split_row(raw)
        if not cells:
            continue
        if header_idx is None:
            headers = cells
            missing = [h for h in EXPECTED_HEADERS if h not in headers]
            if missing:
                raise ValueError(
                    f"Summary table on line {idx} is missing required column(s): {missing}"
                )
            header_idx = idx
            continue
        if set(cells) <= {"", "---", "----", "-----", "------", ":-", "-:", ":-:"} or all(re.fullmatch(r":?-+:?", c or "-") for c in cells):
            continue
        if len(cells) != len(headers):
            raise ValueError(
                f"Summary row on line {idx} has {len(cells)} cells but the header has {len(headers)}."
            )
        row_map = dict(zip(headers, cells))
        num_str = row_map["#"].strip()
        if not num_str.isdigit():
            raise ValueError(f"Summary row on line {idx} has non-numeric # column: '{num_str}'")
        rows.append(
            SummaryRow(
                number=int(num_str),
                requirement=row_map["Requirement"],
                widget_title=row_map["Widget Title"],
                recommended_approach=row_map["Recommended Approach"],
                tier=row_map["Tier"],
                visualization=row_map["Visualization"],
                alternative_approach=row_map["Alternative Approach"],
                alt_tier=row_map["Alt Tier"],
                alt_visualization=row_map["Alt Visualization"],
                status=row_map["Status"],
                result=row_map["Result"],
                line=idx,
            )
        )

    if header_idx is None:
        raise ValueError("Could not find the Summary table — expected '## Summary' followed by a markdown table.")
    return rows


# ---------------------------------------------------------------------------
# Parse detailed sections
# ---------------------------------------------------------------------------

SECTION_RE = re.compile(r"^###\s+(\d+)\.\s+(.+?)\s*$")
SUBHEADING_RE = re.compile(r"^####\s+(.+?)\s*$")


def parse_detailed_sections(lines: list[str]) -> dict[int, DetailedSection]:
    in_details = False
    sections: dict[int, DetailedSection] = {}
    current: DetailedSection | None = None
    current_sub: str | None = None
    sub_buffers: dict[str, list[str]] = {}

    def finalize(section: DetailedSection, subs: dict[str, list[str]]) -> None:
        section.question = "\n".join(subs.get("Question", [])).strip()
        section.payload_context = "\n".join(subs.get("Payload Context", [])).strip()
        section.recommended_approach_md = "\n".join(subs.get("Recommended Approach", [])).strip()
        section.assumptions = "\n".join(subs.get("Assumptions & Caveats", [])).strip()

        save_block = "\n".join(subs.get("Metabase Save Details", [])).strip()
        section.save_title = _extract_field(save_block, r"\*\*Title:\*\*\s*(.+?)(?:\n|$)")
        section.save_description = _extract_description(save_block)
        section.display = _extract_field(save_block, r"\*\*Display:\*\*\s*([^\s`]+)")
        viz = _extract_json_block(save_block, "Visualization settings")
        section.visualization_settings = viz

        rec = section.recommended_approach_md
        sql = _extract_sql_from_block(rec, label_hint="SQL equivalent")
        if not sql:
            sql = _extract_sql_from_block(rec, label_hint=None)
        section.sql = sql.strip()

        sections[section.number] = section

    for idx, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if stripped.startswith("## Widget Details"):
            in_details = True
            continue
        if stripped.startswith("## ") and not stripped.startswith("## Widget Details") and in_details:
            if current is not None:
                finalize(current, sub_buffers)
                current = None
                current_sub = None
                sub_buffers = {}
            in_details = False
            continue
        if not in_details:
            continue

        m = SECTION_RE.match(raw)
        if m:
            if current is not None:
                finalize(current, sub_buffers)
            current = DetailedSection(number=int(m.group(1)), title=m.group(2).strip(), line=idx)
            current_sub = None
            sub_buffers = {}
            continue

        if current is None:
            continue

        sm = SUBHEADING_RE.match(raw)
        if sm:
            current_sub = sm.group(1).strip()
            sub_buffers.setdefault(current_sub, [])
            continue

        if current_sub is not None:
            sub_buffers[current_sub].append(raw)

    if current is not None:
        finalize(current, sub_buffers)

    return sections


def _extract_field(block: str, pattern: str) -> str:
    m = re.search(pattern, block)
    return m.group(1).strip() if m else ""


def _extract_description(block: str) -> str:
    m = re.search(r"\*\*Description:\*\*\s*\n((?:>.*\n?)+)", block)
    if not m:
        return ""
    quoted = m.group(1)
    text = re.sub(r"^>\s?", "", quoted, flags=re.MULTILINE).strip()
    return text


def _extract_json_block(block: str, label: str) -> dict | None:
    pattern = rf"\*\*{re.escape(label)}:\*\*\s*\n```json\s*\n(.*?)\n```"
    m = re.search(pattern, block, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _extract_sql_from_block(block: str, label_hint: str | None) -> str:
    if label_hint:
        pattern = rf"\*\*{re.escape(label_hint)}[^*]*\*\*\s*\n```sql\s*\n(.*?)\n```"
        m = re.search(pattern, block, flags=re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1)
    m = re.search(r"```sql\s*\n(.*?)\n```", block, flags=re.DOTALL)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Public parse entry point
# ---------------------------------------------------------------------------


def parse_review(path: Path) -> dict[str, Any]:
    text = path.read_text()
    lines = text.splitlines()
    summary = parse_summary(lines)
    details = parse_detailed_sections(lines)

    widgets: list[Widget] = []
    errors: list[str] = []

    for row in summary:
        status = row.status.strip()
        is_ready = status.startswith("✅ Ready")
        section = details.get(row.number)

        if is_ready and section is None:
            errors.append(
                f"Row {row.number} (line {row.line}) is marked Ready but has no '### {row.number}. <Title>' detailed section."
            )
            continue

        title = (section.save_title if section and section.save_title else row.widget_title).strip()
        display = (section.display if section else row.visualization).strip().lower() or "table"
        sql = section.sql if section else ""
        if is_ready and not sql:
            errors.append(
                f"Row {row.number} '{title}' is Ready but no SQL code block was found in its Recommended Approach. "
                "Stage 2 needs a `SQL equivalent (used for Stage 2 API creation)` block."
            )
            continue

        widgets.append(
            Widget(
                number=row.number,
                title=title,
                requirement=row.requirement,
                status=status,
                tier=row.tier,
                display=display,
                sql=sql,
                description=section.save_description if section else "",
                visualization_settings=(section.visualization_settings if section and section.visualization_settings else {}),
                is_ready=is_ready,
            )
        )

    return {
        "widgets": [asdict(w) for w in widgets],
        "summary_rows": [asdict(r) for r in summary],
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Update results back into the review file
# ---------------------------------------------------------------------------


def update_results(review_path: Path, results: list[dict]) -> None:
    """Update the Result column of the summary table and append a ## Results section.

    `results` items: {number, status, card_id, card_url, error}
    plus optionally a top-level dashboard entry {dashboard_id, dashboard_url, dashboard_name}.
    """
    by_num: dict[int, dict] = {}
    dashboard_info: dict | None = None
    for r in results:
        if "dashboard_url" in r and "number" not in r:
            dashboard_info = r
        elif "number" in r:
            by_num[int(r["number"])] = r

    text = review_path.read_text()
    lines = text.splitlines()

    in_summary = False
    header_cells: list[str] = []
    result_col_idx: int | None = None
    new_lines: list[str] = []

    for raw in lines:
        if raw.strip().startswith("## Summary"):
            in_summary = True
            new_lines.append(raw)
            continue
        if in_summary and raw.strip().startswith("## ") and not raw.strip().startswith("## Summary"):
            in_summary = False
            new_lines.append(raw)
            continue
        if in_summary and "|" in raw:
            cells = _split_row(raw)
            if not header_cells:
                header_cells = cells
                if "Result" in header_cells:
                    result_col_idx = header_cells.index("Result")
                new_lines.append(raw)
                continue
            if all(re.fullmatch(r":?-+:?", c or "-") for c in cells):
                new_lines.append(raw)
                continue
            if not cells or not cells[0].isdigit():
                new_lines.append(raw)
                continue
            num = int(cells[0])
            if num in by_num and result_col_idx is not None:
                entry = by_num[num]
                if entry.get("status") == "created" and entry.get("card_url"):
                    cells[result_col_idx] = f"[#{entry['card_id']}]({entry['card_url']})"
                elif entry.get("error"):
                    err = entry["error"].replace("|", "\\|").replace("\n", " ")
                    cells[result_col_idx] = f"❌ Error: {err[:200]}"
                new_lines.append("| " + " | ".join(cells) + " |")
                continue
        new_lines.append(raw)

    while new_lines and new_lines[-1].strip() == "":
        new_lines.pop()

    new_lines.append("")
    new_lines.append("---")
    new_lines.append("")
    new_lines.append("## Results")
    new_lines.append("")
    if dashboard_info:
        new_lines.append(f"**Dashboard:** [{dashboard_info.get('dashboard_name', 'View dashboard')}]({dashboard_info['dashboard_url']})")
        new_lines.append("")

    created = [r for r in by_num.values() if r.get("status") == "created"]
    failed = [r for r in by_num.values() if r.get("status") != "created"]
    new_lines.append(f"- Created: **{len(created)}**")
    new_lines.append(f"- Failed: **{len(failed)}**")
    if failed:
        new_lines.append("")
        new_lines.append("### Failures")
        new_lines.append("")
        for r in failed:
            err = (r.get("error") or "unknown error").replace("\n", " ")
            new_lines.append(f"- Row {r['number']}: {err}")
    new_lines.append("")

    review_path.write_text("\n".join(new_lines) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_parse(args) -> int:
    try:
        result = parse_review(Path(args.path))
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    if result["errors"]:
        for e in result["errors"]:
            print(f"WARNING: {e}", file=sys.stderr)
    print(json.dumps(result, indent=2))
    return 1 if result["errors"] and not args.allow_warnings else 0


def cmd_update_results(args) -> int:
    results = json.loads(Path(args.results_file).read_text())
    if not isinstance(results, list):
        print("results-file must contain a JSON array.", file=sys.stderr)
        return 2
    update_results(Path(args.review), results)
    print(f"Updated {args.review}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Parse and update widget-review.md.")
    sub = p.add_subparsers(dest="command", required=True)

    pp = sub.add_parser("parse", help="Parse widget-review.md to JSON")
    pp.add_argument("path")
    pp.add_argument("--allow-warnings", action="store_true",
                    help="Exit 0 even when parser warnings are reported")
    pp.set_defaults(func=cmd_parse)

    pu = sub.add_parser("update-results", help="Write Stage 2 results back into widget-review.md")
    pu.add_argument("--review", required=True)
    pu.add_argument("--results-file", required=True)
    pu.set_defaults(func=cmd_update_results)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
