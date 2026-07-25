#!/usr/bin/env python3
"""Task Runner: orchestrates report -> review package -> next-task draft.

    Claude Code completes a task
            |
            v
    automation/reports/task_meta.json   (written by hand or by Claude)
            |
            v
    generate_completion_report.py  -->  reports/latest_report.{md,json}
            |
            v
      any STOP flag present?
       /              \
     yes                no
      |                  |
      v                  v
    HALT.          generate_review_package.py --> review/review_request.md
    Print reason.         |
    Exit non-zero.        v
                   generate_next_task.py --> tasks/NEXT_TASK_DRAFT.md
                          |
                          v
                   Human reviews review_request.md + NEXT_TASK_DRAFT.md,
                   sends PASS / FAIL / BLOCKED back, and explicitly
                   approves (or rewrites) the next task before anything
                   is implemented. This script never does that step.

Usage:
    python3 automation/run_pm_pipeline.py [path/to/task_meta.json] [--base <branch>]

Exit code 0 = pipeline completed through next-task draft.
Exit code 2 = pipeline halted on an auto-stop flag (this is not a failure
              of the script -- it is the auto-stop rule working correctly).
Exit code 1 = task_meta.json was invalid.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

AUTOMATION_DIR = Path(__file__).resolve().parent
REPORTS_DIR = AUTOMATION_DIR / "reports"


def run_script(name: str, extra_args: list[str]) -> int:
    result = subprocess.run(
        [sys.executable, str(AUTOMATION_DIR / name), *extra_args],
    )
    return result.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("meta_path", nargs="?", default=None)
    parser.add_argument("--base", default=None)
    args = parser.parse_args()

    report_args = [args.meta_path] if args.meta_path else []
    rc = run_script("generate_completion_report.py", report_args)
    if rc != 0:
        print("Pipeline halted: task_meta.json failed validation. See errors above.", file=sys.stderr)
        return 1

    latest = REPORTS_DIR / "latest_report.json"
    with latest.open(encoding="utf-8") as f:
        data = json.load(f)

    if data.get("should_stop"):
        print("=" * 60)
        print(f"AUTO-STOP: {', '.join(data['flags'])}")
        print("Pipeline halted before generating the review package or next-task draft.")
        print("Human review required. See automation/reports/latest_report.md.")
        print("=" * 60)
        return 2

    review_args = ["--base", args.base] if args.base else []
    run_script("generate_review_package.py", review_args)
    run_script("generate_next_task.py", [])

    print("=" * 60)
    print("Pipeline complete. Nothing was auto-approved or auto-implemented.")
    print("Next: a human (or ChatGPT PM) reviews automation/review/review_request.md,")
    print("returns PASS / FAIL / BLOCKED, and explicitly approves")
    print("automation/tasks/NEXT_TASK_DRAFT.md (or a rewritten version of it) before")
    print("it becomes a real Task ID for Claude Code.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
