#!/usr/bin/env python3
"""
prep_assignment.py — Bootstrap a local workspace for a Canvas assignment.

Finds the course + assignment by keyword, downloads the assignment PDF,
syllabus, and all lecture slides into a workspace folder, then extracts
every PDF to markdown so the contents are LLM-readable.

Usage:
    python3 scripts/prep_assignment.py <course> <assignment> [--workspace DIR]

Examples:
    python3 scripts/prep_assignment.py ME335 "Assignment 1"
    python3 scripts/prep_assignment.py ECE2150 "HW 2" --workspace ~/Desktop/senior_su

Prints a JSON summary on success so downstream agents can chain.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Slide footers like "5/10/2026 VM335 by Zhaoguang Wang 1" — common boilerplate
# in lecture exports. Skip when summarizing.
DATE_PREFIX_PATTERN = re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canvas_api import (
    download_file,
    list_assignments,
    list_course_files,
    list_courses,
)
from file_extractor import extract_to_markdown


@dataclass(frozen=True)
class CourseMatch:
    id: int
    name: str
    short: str  # e.g. "ME3350" extracted from "ME3350JSU2026"


@dataclass(frozen=True)
class AssignmentMatch:
    id: int
    name: str
    due_at: str | None
    has_submitted: bool


def find_course(keyword: str) -> CourseMatch:
    keyword_lc = keyword.lower()
    courses = list_courses()
    matches = [c for c in courses if keyword_lc in c["name"].lower()]
    if not matches:
        names = [c["name"] for c in courses]
        sys.exit(f"❌ No course matched '{keyword}'. Available: {names}")
    if len(matches) > 1:
        names = [c["name"] for c in matches]
        sys.exit(f"❌ Ambiguous course keyword '{keyword}': {names}. Be more specific.")
    c = matches[0]
    name = c["name"]
    # crude short-name extraction: split on "JSU" if present, else strip spaces
    short = name.split("JSU")[0] if "JSU" in name else name.replace(" ", "_")
    return CourseMatch(id=c["id"], name=name, short=short)


def find_assignment(course_id: int, keyword: str) -> AssignmentMatch:
    keyword_lc = keyword.lower()
    items = list_assignments(course_id)
    matches = [a for a in items if keyword_lc in a["name"].lower()]
    if not matches:
        names = [a["name"] for a in items]
        sys.exit(f"❌ No assignment matched '{keyword}'. Available: {names}")
    if len(matches) > 1:
        names = [a["name"] for a in matches]
        sys.exit(f"❌ Ambiguous assignment '{keyword}': {names}. Be more specific.")
    a = matches[0]
    return AssignmentMatch(
        id=a["id"],
        name=a["name"],
        due_at=a.get("due_at"),
        has_submitted=bool(a.get("has_submitted_submissions", False)),
    )


def categorize_file(filename: str) -> str:
    """Heuristic: classify a course-file display name."""
    fl = filename.lower()
    if "syllabus" in fl:
        return "syllabus"
    if "assignment" in fl or "homework" in fl or fl.startswith("hw"):
        return "assignment"
    lecture_tokens = ("lecture", " lec", "slide", "vm335", "vm 335", "vm-335", "ch ", "chapter")
    if any(t in fl for t in lecture_tokens):
        return "lecture"
    return "other"


def auto_summarize(md_path: Path, max_chars: int = 80) -> str:
    """Heuristic one-line summary from the first substantive markdown line.

    Skips headings, very short lines, and common metadata patterns.
    Returns '?' when nothing usable is found (auto-hw expects this).
    """
    if not md_path.exists():
        return "?"
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return "?"
    metadata_prefixes = (
        "Page ", "Slide ", "Lecture ", "Date:", "Instructor:", "Email:", "Office hour",
        "TA's office", "Teaching assistant",
    )
    bullet_prefixes = ("• ", "▪ ", "✓ ", "- ", "* ", "‒ ", "● ")
    # Require >=30 chars to filter title-like lines ("Heat Transfer", course codes,
    # author names). Real content lines are usually full sentences.
    min_content_len = 30
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if len(line) < min_content_len:
            continue
        # strip leading bullet so metadata prefix detection works on real start
        content = line
        for b in bullet_prefixes:
            if content.startswith(b):
                content = content[len(b):].strip()
                break
        if any(content.startswith(p) for p in metadata_prefixes):
            continue
        if DATE_PREFIX_PATTERN.match(content):
            continue
        ellipsis = "…" if len(line) > max_chars else ""
        return line[:max_chars] + ellipsis
    return "?"


def write_index(course_dir: Path, course_short: str, downloaded: list[dict[str, Any]], md_dir: Path) -> Path:
    """Write an auto-hw-compatible index.md (ASCII pipe tree + per-file summaries).

    Overwrites any existing index.md. Format documented in
    `~/.claude/skills/auto-hw/SKILL.md` step 2.
    """
    has_md_dir = md_dir.exists() and any(md_dir.iterdir())
    lines: list[str] = [f"# {course_short.lower()}", ""]
    n_root = len(downloaded)
    for i, d in enumerate(downloaded):
        is_last_root = (i == n_root - 1) and not has_md_dir
        prefix = "└──" if is_last_root else "├──"
        md_candidate = md_dir / (Path(d["name"]).stem + ".md")
        summary = auto_summarize(md_candidate)
        lines.append(f"{prefix} {d['name']} — {summary}")
    if has_md_dir:
        lines.append("└── _md/")
        md_files = sorted(p for p in md_dir.iterdir() if p.suffix == ".md")
        n_md = len(md_files)
        for j, p in enumerate(md_files):
            is_last = j == n_md - 1
            md_prefix = "    └──" if is_last else "    ├──"
            summary = auto_summarize(p)
            lines.append(f"{md_prefix} {p.name} — {summary}")
    index_path = course_dir / "index.md"
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("course", help="course name keyword (e.g., ME335)")
    parser.add_argument("assignment", help="assignment keyword (e.g., 'Assignment 1')")
    parser.add_argument(
        "--workspace",
        default="~/Desktop/senior_su",
        help="workspace root (default: ~/Desktop/senior_su)",
    )
    parser.add_argument(
        "--include-other",
        action="store_true",
        help="also download files that aren't lectures/syllabus/assignment",
    )
    args = parser.parse_args()

    print(f"🔍 Course lookup: '{args.course}'")
    course = find_course(args.course)
    print(f"  ✓ [{course.id}] {course.name}")

    print(f"🔍 Assignment lookup: '{args.assignment}'")
    assignment = find_assignment(course.id, args.assignment)
    print(f"  ✓ [{assignment.id}] {assignment.name}")
    print(f"    due_at:    {assignment.due_at}")
    print(f"    submitted: {assignment.has_submitted}")
    if assignment.has_submitted:
        print("  ⚠️  Canvas reports an existing submission. Re-doing / improving?")

    workspace_root = Path(args.workspace).expanduser()
    course_dir = workspace_root / course.short.lower()
    md_dir = course_dir / "_md"
    course_dir.mkdir(parents=True, exist_ok=True)
    md_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Workspace: {course_dir}")

    print("📦 Listing course files...")
    files = list_course_files(course.id)
    plan: list[tuple[dict[str, Any], str]] = []
    for f in files:
        cat = categorize_file(f["display_name"])
        if cat == "other" and not args.include_other:
            continue
        plan.append((f, cat))
    cats_seen = sorted({c for _, c in plan})
    print(f"  ✓ {len(plan)} files queued (categories: {cats_seen})")

    print("⬇️  Downloading...")
    downloaded: list[dict[str, Any]] = []
    for f, cat in plan:
        save_path = course_dir / f["display_name"]
        download_file(f["url"], str(save_path))
        size_kb = save_path.stat().st_size // 1024
        downloaded.append({
            "name": f["display_name"],
            "category": cat,
            "size_kb": size_kb,
            "path": str(save_path),
        })
        print(f"  ✓ {cat:10s} {f['display_name']}  ({size_kb}KB)")

    print("📝 Extracting PDFs → markdown...")
    extracted: list[str] = []
    for d in downloaded:
        if not d["name"].lower().endswith(".pdf"):
            continue
        md_path = md_dir / (Path(d["name"]).stem + ".md")
        extract_to_markdown(d["path"], str(md_path))
        extracted.append(str(md_path))
        print(f"  ✓ {md_path.name}")

    print("🗂️  Writing auto-hw-compatible index.md ...")
    index_path = write_index(course_dir, course.short, downloaded, md_dir)
    print(f"  ✓ {index_path}")

    summary = {
        "course": {"id": course.id, "name": course.name, "short": course.short},
        "assignment": {
            "id": assignment.id,
            "name": assignment.name,
            "due_at": assignment.due_at,
            "has_submitted": assignment.has_submitted,
        },
        "workspace": str(course_dir),
        "downloaded": downloaded,
        "extracted_md": extracted,
        "index_md": str(index_path),
    }

    print()
    print("=" * 60)
    print("✅ READY — next step is LLM analysis (see workflows/assignment-prep.md)")
    print("   or hand off to auto-hw skill for actual problem solving.")
    print("=" * 60)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
