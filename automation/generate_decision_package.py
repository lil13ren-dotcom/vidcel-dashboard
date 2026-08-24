#!/usr/bin/env python3
"""Generate the structured PM decision package (PM-AUTO-03).

Converts the completion report (and, if available, this cycle's quality
check results) into three files under `automation/review/`:

    review_summary.md    human-readable summary
    review_decision.json machine-readable, fixed-schema decision
    next_task_draft.md   structured draft for the next task -- never
                          executed automatically

Every field in review_decision.json has one fixed meaning and is derived
from structured inputs only (task_meta.json fields via latest_report.json,
and quality_checks.json's per-check status). Nothing here parses free-form
prose (risks/blockers/evidence text) to decide status or risk -- see
automation/schemas/review_decision.schema.json for the full contract.

Status derivation, in order:
    1. `status_override` in task_meta.json, if set -- always wins.
    2. Any auto-stop flag present (`should_stop`) -> BLOCKED.
    3. quality_checks.json (from this cycle) has n_fail > 0 -> FAIL.
    4. Otherwise -> PASS.

"This cycle" for step 3 means quality_checks.json's own `generated_at`
is not older than latest_report.json's -- a stale leftover from an
earlier, unrelated run is never trusted to fail (or pass) this task.

Usage:
    python3 automation/generate_decision_package.py
"""
import datetime
import json
import sys
from pathlib import Path

AUTOMATION_DIR = Path(__file__).resolve().parent
REPORTS_DIR = AUTOMATION_DIR / "reports"
REVIEW_DIR = AUTOMATION_DIR / "review"

STOP_FLAGS_ORDER = [
    "BLOCKED", "EVIDENCE_MISSING", "PRODUCTION_CHANGE", "ARCHITECTURE_CHANGE",
    "PAYMENT_CHANGE", "LEGAL_DECISION", "SECRET_REQUIRED", "DEPLOYMENT_REQUIRED",
]


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_report() -> dict:
    report = load_json(REPORTS_DIR / "latest_report.json")
    if report is None:
        print(
            f"ERROR: {REPORTS_DIR / 'latest_report.json'} not found. "
            "Run generate_completion_report.py first.",
            file=sys.stderr,
        )
        sys.exit(1)
    return report


def load_fresh_quality_checks(report: dict) -> dict | None:
    """Only trust quality_checks.json if it was generated at or after the
    completion report it's supposed to belong to -- otherwise it's a
    leftover from a previous, unrelated run."""
    quality = load_json(REPORTS_DIR / "quality_checks.json")
    if quality is None:
        return None
    report_ts = report.get("generated_at")
    quality_ts = quality.get("generated_at")
    if report_ts and quality_ts and quality_ts < report_ts:
        return None
    return quality


def determine_status(report: dict, quality: dict | None) -> tuple[str, str]:
    override = report.get("status_override")
    if override:
        return override, f"explicit status_override={override!r} in task_meta.json"

    flags = report.get("flags") or []
    if report.get("should_stop") or flags:
        return "BLOCKED", f"auto-stop flag(s) present: {', '.join(flags)}"

    if quality is not None:
        n_fail = quality.get("n_fail", sum(1 for c in quality.get("checks", []) if c.get("status") == "FAIL"))
        if n_fail:
            fail_names = [c["name"] for c in quality.get("checks", []) if c.get("status") == "FAIL"]
            return "FAIL", f"{n_fail} quality check(s) failed: {', '.join(fail_names)}"
        return "PASS", "no auto-stop flags; all quality checks in quality_checks.json passed"

    return (
        "PASS",
        "no auto-stop flags; no quality-check evidence found for this run "
        "(quality_checks.json missing or stale) -- defaults to PASS by absence "
        "of a failure signal, not by inference",
    )


def determine_next_task(status: str, report: dict) -> str | None:
    if status == "FAIL":
        return f"REWORK-{report['task_id']}"
    if status == "BLOCKED":
        return None
    return report.get("next_task_id") or None


def recommendation_for(status: str, task_id: str) -> str:
    if status == "PASS":
        return (
            "PASS — approved to proceed. Requires explicit human sign-off before "
            "next_task_draft.md is turned into a real Task ID."
        )
    if status == "FAIL":
        return (
            f"FAIL — do not proceed. Rework required on {task_id}; "
            "see next_task_draft.md for scope."
        )
    return (
        f"BLOCKED — do not proceed. Resolve the blocker(s) on {task_id} listed "
        "below before any further action."
    )


def build_review_summary(report: dict, decision: dict) -> str:
    lines = [
        f"# Review Summary — {report['task_id']}",
        "",
        f"- **Generated:** {decision['generated_at']}",
        f"- **Status:** {decision['status']}",
        f"- **Risk:** {decision['risk']}",
        "",
        "## Objective",
        report.get("objective") or "_(none provided)_",
        "",
        "## Files changed",
        "\n".join(f"- `{f}`" for f in report.get("files_modified", [])) or "_(none detected)_",
        "",
        "## Tests executed",
        "\n".join(f"- {t}" for t in report.get("tests_executed", [])) or "_(none listed)_",
        "",
        "## Results",
        report.get("test_results") or "_(not provided)_",
        "",
        "## Risks",
        report.get("risks") or "_(none noted)_",
        "",
        "## Remaining blockers",
        report.get("remaining_blockers") or "_(none noted)_",
        "",
        "## Evidence summary",
        report.get("evidence") or "_(none provided)_",
        "",
        "## Recommendation",
        decision["_recommendation"],
        "",
    ]
    return "\n".join(lines)


def build_next_task_draft(report: dict, decision: dict, quality: dict | None) -> str:
    task_id = report["task_id"]
    status = decision["status"]
    now = decision["generated_at"]

    if status == "FAIL":
        title = f"REWORK: {task_id}"
        objective = f"Fix the failing check(s) from {task_id} before any new scope begins."
        if quality is not None:
            fail_names = [c["name"] for c in quality.get("checks", []) if c.get("status") == "FAIL"]
        else:
            fail_names = []
        scope = "\n".join(f"- {n}" for n in fail_names) if fail_names else (
            f"- {report.get('remaining_blockers') or report.get('risks') or '(see review_summary.md)'}"
        )
        deliverables = "All items listed in Scope must pass. No new features or unrelated changes."
        validation = "Re-run the same failing check(s) and confirm PASS. Do not mark this rework complete on a partial re-run."
    elif status == "BLOCKED":
        title = f"UNBLOCK: {task_id}"
        objective = f"Resolve the blocker(s) preventing {task_id} from completing."
        scope = report.get("remaining_blockers") or (
            f"Auto-stop flag(s): {', '.join(report.get('flags', []))}"
        )
        deliverables = f"Whatever removes the blocker(s) in Scope. Do not resume {task_id} until this is done."
        validation = f"Re-run {task_id}'s original validation once unblocked."
    else:  # PASS
        title = report.get("next_task_id") or "(unassigned — human to pick a Task ID)"
        objective = report.get("suggested_next_task") or "_(none suggested in the completion report)_"
        scope = (
            "Not yet scoped by this automation — PM to define based on the "
            "objective above and current Backlog/Gate priorities."
        )
        deliverables = "TBD — to be defined when this draft is turned into a real Task ID."
        validation = "TBD — define alongside deliverables."

    lines = [
        "# Next Task Draft",
        "",
        f"- **Generated:** {now}",
        f"- **Derived from:** {task_id} (status: {status})",
        "- **Status:** DRAFT — not an approved Task ID. Requires explicit human",
        "  approval before Claude Code acts on this. Nothing in this automation",
        "  layer executes this file automatically.",
        "",
        "## Title",
        title,
        "",
        "## Objective",
        objective,
        "",
        "## Scope",
        scope,
        "",
        "## Deliverables",
        deliverables,
        "",
        "## Validation requirements",
        validation,
        "",
        "## Stop conditions",
        "Halt and require human approval before proceeding if any of these apply:",
        "\n".join(f"- {f}" for f in STOP_FLAGS_ORDER),
        "",
    ]
    return "\n".join(lines)


def main():
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    report = load_report()
    quality = load_fresh_quality_checks(report)

    status, reason = determine_status(report, quality)
    risk = report.get("risk") or "MEDIUM"
    next_task = determine_next_task(status, report)
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    decision = {
        "task_id": report["task_id"],
        "status": status,
        "risk": risk,
        "blocked": status == "BLOCKED",
        "next_task": next_task,
        "requires_human_approval": True,
        "generated_at": now,
        "reason": reason,
    }
    decision["_recommendation"] = recommendation_for(status, report["task_id"])

    (REVIEW_DIR / "review_decision.json").write_text(
        json.dumps({k: v for k, v in decision.items() if not k.startswith("_")}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (REVIEW_DIR / "review_summary.md").write_text(
        build_review_summary(report, decision), encoding="utf-8"
    )
    (REVIEW_DIR / "next_task_draft.md").write_text(
        build_next_task_draft(report, decision, quality), encoding="utf-8"
    )

    print(f"Wrote {REVIEW_DIR / 'review_decision.json'}")
    print(f"Wrote {REVIEW_DIR / 'review_summary.md'}")
    print(f"Wrote {REVIEW_DIR / 'next_task_draft.md'}")
    print(f"Decision: status={status} risk={risk} blocked={decision['blocked']} next_task={next_task!r}")
    print(f"Reason: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
