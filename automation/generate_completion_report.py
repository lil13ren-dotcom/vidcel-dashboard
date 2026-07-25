#!/usr/bin/env python3
"""Generate a standardized Claude Code completion report.

Combines a small human/Claude-authored JSON file (the narrative fields no
script can infer: objective, risks, blockers, evidence, suggested next
task) with auto-derived data (git file changes) into two outputs:

    automation/reports/latest_report.md    (human-readable)
    automation/reports/latest_report.json  (machine-readable, same fields)

Usage:
    python3 automation/generate_completion_report.py [path/to/task_meta.json]

Defaults to automation/reports/task_meta.json if no path given. See
automation/reports/task_meta.example.json for the expected schema.
"""
import json
import subprocess
import sys
import datetime
from pathlib import Path

AUTOMATION_DIR = Path(__file__).resolve().parent
ROOT = AUTOMATION_DIR.parent
REPORTS_DIR = AUTOMATION_DIR / "reports"

STOP_FLAGS = {
    "BLOCKED", "EVIDENCE_MISSING", "PRODUCTION_CHANGE", "ARCHITECTURE_CHANGE",
    "PAYMENT_CHANGE", "LEGAL_DECISION", "SECRET_REQUIRED", "DEPLOYMENT_REQUIRED",
}
CONTINUE_CATEGORIES = {
    "Documentation", "Tests", "Refactoring", "Lint", "Formatting",
    "Knowledge updates", "PM OS updates", "Task generation",
}


def run(cmd):
    try:
        out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
        return out.stdout.strip()
    except Exception as e:  # pragma: no cover - defensive only
        return f"(command failed: {e})"


def git_files_modified():
    """Union of staged, unstaged, and untracked files. Best-effort; a
    script cannot know which of these belong to *this* task versus
    leftover local state, so the human/Claude-authored task_meta.json
    'files_modified' field always wins if provided."""
    staged = run(["git", "diff", "--cached", "--name-only"])
    unstaged = run(["git", "diff", "--name-only"])
    untracked = run(["git", "ls-files", "--others", "--exclude-standard"])
    files = set()
    for block in (staged, unstaged, untracked):
        for line in block.splitlines():
            line = line.strip()
            if line:
                files.add(line)
    return sorted(files)


def load_task_meta(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: task metadata file not found: {path}", file=sys.stderr)
        print("See automation/reports/task_meta.example.json for the expected schema.", file=sys.stderr)
        sys.exit(1)
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_meta(meta: dict) -> list[str]:
    errors = []
    required = ["task_id", "objective", "category"]
    for field in required:
        if not meta.get(field):
            errors.append(f"missing required field: {field}")
    category = meta.get("category")
    if category and category not in CONTINUE_CATEGORIES and category != "Implementation":
        errors.append(
            f"unrecognized category {category!r} — expected one of "
            f"{sorted(CONTINUE_CATEGORIES)} or 'Implementation'"
        )
    bad_flags = set(meta.get("flags", [])) - STOP_FLAGS
    if bad_flags:
        errors.append(f"unrecognized flags: {sorted(bad_flags)} — expected one of {sorted(STOP_FLAGS)}")
    return errors


def build_report(meta: dict) -> tuple[str, dict]:
    files_modified = meta.get("files_modified") or git_files_modified()
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    flags = sorted(set(meta.get("flags", [])))
    should_stop = bool(flags)

    data = {
        "task_id": meta["task_id"],
        "objective": meta["objective"],
        "category": meta["category"],
        "generated_at": now,
        "files_modified": files_modified,
        "tests_executed": meta.get("tests_executed", []),
        "test_results": meta.get("test_results", ""),
        "risks": meta.get("risks", ""),
        "remaining_blockers": meta.get("remaining_blockers", ""),
        "evidence": meta.get("evidence", ""),
        "suggested_next_task": meta.get("suggested_next_task", ""),
        "flags": flags,
        "should_stop": should_stop,
    }

    lines = [
        f"# Completion Report — {data['task_id']}",
        "",
        f"- **Generated:** {data['generated_at']}",
        f"- **Category:** {data['category']}",
        f"- **Auto-stop triggered:** {'YES — ' + ', '.join(flags) if should_stop else 'no'}",
        "",
        "## Objective",
        data["objective"],
        "",
        "## Files modified",
        "\n".join(f"- `{f}`" for f in data["files_modified"]) or "_(none detected)_",
        "",
        "## Tests executed",
        "\n".join(f"- {t}" for t in data["tests_executed"]) or "_(none listed)_",
        "",
        "## Test results",
        data["test_results"] or "_(not provided)_",
        "",
        "## Risks",
        data["risks"] or "_(none noted)_",
        "",
        "## Remaining blockers",
        data["remaining_blockers"] or "_(none noted)_",
        "",
        "## Evidence",
        data["evidence"] or "_(none provided)_",
        "",
        "## Suggested next task",
        data["suggested_next_task"] or "_(none suggested)_",
        "",
    ]
    return "\n".join(lines), data


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    meta_path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPORTS_DIR / "task_meta.json"
    meta = load_task_meta(meta_path)

    errors = validate_meta(meta)
    if errors:
        print("ERROR: invalid task_meta.json:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    md, data = build_report(meta)

    (REPORTS_DIR / "latest_report.md").write_text(md, encoding="utf-8")
    (REPORTS_DIR / "latest_report.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Wrote {REPORTS_DIR / 'latest_report.md'}")
    print(f"Wrote {REPORTS_DIR / 'latest_report.json'}")
    if data["should_stop"]:
        print(f"AUTO-STOP: flags present ({', '.join(data['flags'])}) — pipeline will halt here.")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
