#!/usr/bin/env python3
"""Draft the next task, from the previous report and the project's Backlog.

This is deliberately NOT an AI task-planner -- it is an honest aggregation
tool. It carries forward whatever `suggested_next_task` the completion
report already contains (written by a human or by Claude at report time,
where the actual judgment belongs), and attaches the current open Backlog
items and Gate status as supporting context, into a single draft file:

    automation/tasks/NEXT_TASK_DRAFT.md

This file is NEVER executed automatically by anything in this automation
layer. It is a draft for a human to review, edit, and explicitly approve
before it becomes a real Task ID handed to Claude Code.

Usage:
    python3 automation/generate_next_task.py
"""
import datetime
import json
import re
import sys
from pathlib import Path

AUTOMATION_DIR = Path(__file__).resolve().parent
ROOT = AUTOMATION_DIR.parent
REPORTS_DIR = AUTOMATION_DIR / "reports"
TASKS_DIR = AUTOMATION_DIR / "tasks"
KNOWLEDGE_DIR = ROOT / "knowledge"


def load_latest_report() -> dict | None:
    path = REPORTS_DIR / "latest_report.json"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def extract_open_backlog_items(limit: int = 10) -> list[str]:
    """Best-effort extraction of numbered/bulleted Backlog.md items under
    the 'Awaiting project-owner decision' section. Text-parsing a markdown
    file is inherently fragile -- this is a convenience aid for the human
    reviewing the draft, not an authoritative source. Always says so."""
    path = KNOWLEDGE_DIR / "Backlog.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    marker = "## Awaiting project-owner decision"
    if marker not in text:
        return []
    section = text.split(marker, 1)[1]
    # Stop at the next top-level heading, if any
    section = re.split(r"\n## ", section, maxsplit=1)[0]
    items = re.findall(r"^\d+[a-z]?\.\s+\*\*(.+?)\*\*", section, flags=re.MULTILINE)
    return items[:limit]


def main():
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    report = load_latest_report()
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    lines = [
        "# Next Task Draft",
        "",
        f"- **Generated:** {now}",
        "- **Status:** DRAFT — not an approved Task ID. Requires explicit human",
        "  approval before Claude Code acts on this. Nothing in this automation",
        "  layer executes this file automatically.",
        "",
    ]

    if report is None:
        lines += [
            "## No previous completion report found",
            "",
            f"Expected `{REPORTS_DIR / 'latest_report.json'}` — run "
            "`generate_completion_report.py` first.",
            "",
        ]
    else:
        if report.get("should_stop"):
            lines += [
                f"## ⚠️ Previous task auto-stopped: {', '.join(report.get('flags', []))}",
                "",
                "Auto-stop flags were present on the previous task. This draft was "
                "still generated for visibility, but the pipeline itself would have "
                "halted before reaching this step in a real run — treat this section "
                "as informational, not a signal to proceed.",
                "",
            ]
        lines += [
            f"## From previous task: {report.get('task_id', '(unknown)')}",
            "",
            "**Suggested next task (as written in the previous completion report):**",
            "",
            report.get("suggested_next_task") or "_(previous report did not suggest one)_",
            "",
            "**Previous task's remaining blockers (for context):**",
            "",
            report.get("remaining_blockers") or "_(none noted)_",
            "",
        ]

    backlog_items = extract_open_backlog_items()
    lines += [
        "## Open Backlog items (best-effort extract from knowledge/Backlog.md)",
        "",
        "_Text-parsed from Backlog.md's 'Awaiting project-owner decision' section — "
        "not authoritative. Read the actual file for full context before picking one._",
        "",
    ]
    if backlog_items:
        lines += [f"- {item}" for item in backlog_items]
    else:
        lines += ["_(none found, or knowledge/Backlog.md is missing/differently structured)_"]

    lines += [
        "",
        "## Human review checklist before approving this as a real task",
        "",
        "- [ ] Does the suggested next task actually match current priorities?",
        "- [ ] Does it require a PRODUCTION_CHANGE / PAYMENT_CHANGE / SECRET_REQUIRED /",
        "      DEPLOYMENT_REQUIRED / ARCHITECTURE_CHANGE / LEGAL_DECISION step? If so,",
        "      make sure that's explicit in the task instructions, not implied.",
        "- [ ] Assign a real Task ID before handing this to Claude Code.",
        "",
    ]

    (TASKS_DIR / "NEXT_TASK_DRAFT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {TASKS_DIR / 'NEXT_TASK_DRAFT.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
