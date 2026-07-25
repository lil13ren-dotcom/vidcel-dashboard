#!/usr/bin/env python3
"""Task Runner: orchestrates report -> [quality checks] -> decision package.

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
    generate_decision_    generate_review_package.py --> review/review_request.md,
    package.py            reports/quality_checks.json
    (status: BLOCKED,            |
     derived from flags           v
     alone -- no checks    generate_decision_package.py --> review/review_decision.json,
     run)                  review/review_summary.md, review/next_task_draft.md
      |                    (status: FAIL if any quality check failed, else PASS)
      v                           |
    HALT.                         v
    Exit code 2.           generate_next_task.py --> tasks/NEXT_TASK_DRAFT.md
    Human review                  (freeform, Backlog-aware suggestion --
    required.                      separate from the deterministic
                                    next_task_draft.md above)
                                   |
                                   v
                            Human (or ChatGPT PM) reads review_decision.json
                            (or review_summary.md), sends PASS / FAIL / BLOCKED
                            back, and explicitly approves (or rewrites) the next
                            task before anything is implemented. This script
                            never does that step.

Usage:
    python3 automation/run_pm_pipeline.py [path/to/task_meta.json] [--base <branch>] [--root <path>]

Exit code 0 = pipeline completed and review_decision.json's status is PASS.
Exit code 2 = pipeline halted on an auto-stop flag before quality checks ran
              (this is not a failure of the script -- it is the auto-stop
              rule working correctly). A BLOCKED review_decision.json is
              still generated.
Exit code 3 = pipeline completed but review_decision.json's status is FAIL
              (at least one quality check failed).
Exit code 1 = task_meta.json was invalid.

Exit codes 0/2/3 are intended to be directly consumable by a CI step (e.g.
GitHub Actions `run:` step exit status) without parsing any output.
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
    parser.add_argument("--root", default=None, help="Target repo to run quality checks against (default: vidcel-dashboard)")
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
        run_script("generate_decision_package.py", [])
        print("=" * 60)
        print(f"AUTO-STOP: {', '.join(data['flags'])}")
        print("Pipeline halted before running quality checks or the freeform next-task draft.")
        print("A BLOCKED review_decision.json was still generated -- see automation/review/.")
        print("Human review required. See automation/reports/latest_report.md.")
        print("=" * 60)
        return 2

    review_args = []
    if args.base:
        review_args += ["--base", args.base]
    if args.root:
        review_args += ["--root", args.root]
    run_script("generate_review_package.py", review_args)
    run_script("generate_decision_package.py", [])
    run_script("generate_next_task.py", [])

    with (AUTOMATION_DIR / "review" / "review_decision.json").open(encoding="utf-8") as f:
        decision = json.load(f)

    print("=" * 60)
    print("Pipeline complete. Nothing was auto-approved or auto-implemented.")
    print(f"Decision: status={decision['status']} risk={decision['risk']}")
    print("Next: a human (or ChatGPT PM) reads automation/review/review_decision.json")
    print("(or review_summary.md), returns PASS / FAIL / BLOCKED, and explicitly")
    print("approves a next task (automation/review/next_task_draft.md or")
    print("automation/tasks/NEXT_TASK_DRAFT.md) before it becomes a real Task ID")
    print("for Claude Code.")
    print("=" * 60)
    return 3 if decision["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
