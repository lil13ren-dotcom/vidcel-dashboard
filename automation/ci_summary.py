#!/usr/bin/env python3
"""Build a GitHub Actions Step Summary + structured outputs from a PM
pipeline run, without fabricating a decision when data is missing.

Classifies the run into exactly one of PASS / BLOCKED / FAIL / ERROR by
cross-checking the pipeline's own exit code against review_decision.json's
`status` field, when that file is present and valid. The two are expected
to agree; a missing file, malformed JSON, or a mismatch between the exit
code and the recorded status is reported as ERROR rather than silently
trusting either source alone -- this script never invents a PASS/BLOCKED/
FAIL decision that the pipeline itself didn't produce.

Never reads or renders the *content* of next_task_draft.md -- callers only
ever reference it by filename (e.g. for upload), never execute it.

Usage:
    python3 automation/ci_summary.py \
        --exit-code <int> \
        [--decision-path automation/review/review_decision.json] \
        [--quality-path automation/reports/quality_checks.json] \
        [--report-path automation/reports/latest_report.json] \
        [--summary-out $GITHUB_STEP_SUMMARY] \
        [--github-output $GITHUB_OUTPUT]

Always exits 0 -- this script reports on the run, it does not gate it.
Gating on the classification is the caller's job (see
.github/workflows/pm-pipeline.yml's "Enforce PASS-only success" step).
"""
import argparse
import json
import sys
from pathlib import Path

EXIT_CODE_LABELS = {0: "PASS", 2: "BLOCKED", 3: "FAIL"}
STATUS_EMOJI = {"PASS": "✅", "BLOCKED": "\U0001F6AB", "FAIL": "❌", "ERROR": "⚠️"}


def load_json_safe(path: Path | None) -> tuple[dict | None, str | None]:
    """Returns (data, error). `data` is None if the file is missing or not
    valid JSON -- both cases are reported via `error`, never silently
    treated as an empty/default decision."""
    if path is None:
        return None, "not provided"
    if not path.exists():
        return None, f"file not found: {path}"
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f), None
    except json.JSONDecodeError as e:
        return None, f"invalid JSON in {path}: {e}"


def classify(exit_code: int, decision: dict | None) -> tuple[str, str]:
    """Returns (status, reason). Never invents a decision: if the exit code
    implies PASS/BLOCKED/FAIL but review_decision.json disagrees or can't be
    read, the result is ERROR, not a guess in either direction."""
    expected = EXIT_CODE_LABELS.get(exit_code)
    if expected is None:
        return "ERROR", (
            f"pipeline exit code {exit_code} is not one of 0 (PASS), 2 (BLOCKED), "
            "3 (FAIL) -- treated as an unexpected/infrastructure error"
        )
    if decision is None:
        return "ERROR", f"exit code was {exit_code} ({expected}) but review_decision.json could not be read"
    decision_status = decision.get("status")
    if decision_status != expected:
        return "ERROR", (
            f"exit code {exit_code} implies {expected}, but review_decision.json reports "
            f"status={decision_status!r} -- treated as an anomaly, not resolved in either direction"
        )
    return expected, decision.get("reason", "")


def build_summary(
    status: str,
    exit_code: int,
    decision: dict | None,
    decision_err: str | None,
    quality: dict | None,
    quality_err: str | None,
    report: dict | None,
) -> str:
    emoji = STATUS_EMOJI.get(status, "❓")
    task_id = (decision or {}).get("task_id") or (report or {}).get("task_id") or "(unknown)"

    lines = [
        f"# PM Pipeline Result: {emoji} {status}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Task ID | `{task_id}` |",
        f"| Exit code | `{exit_code}` |",
        f"| Status | **{status}** |",
    ]

    if decision is not None:
        lines += [
            f"| Risk | {decision.get('risk', '(unknown)')} |",
            f"| Blocked | {decision.get('blocked')} |",
            f"| Next task | {decision.get('next_task') or '_(none)_'} |",
            f"| Requires human approval | {decision.get('requires_human_approval')} |",
            f"| Reason | {decision.get('reason', '')} |",
        ]
    else:
        lines.append(f"| review_decision.json | ⚠️ unavailable ({decision_err}) |")

    if quality is not None:
        lines.append(
            f"| Quality checks | {quality.get('n_pass', '?')} passed, "
            f"{quality.get('n_fail', '?')} failed, {quality.get('n_skip', '?')} skipped |"
        )
        failing = [c["name"] for c in quality.get("checks", []) if c.get("status") == "FAIL"]
        if failing:
            lines.append(f"| Failing checks | {', '.join(failing)} |")
    else:
        lines.append(f"| quality_checks.json | _(not available: {quality_err})_ |")

    lines += [
        "",
        "**Human approval is always required before any next task begins. "
        "`next_task_draft.md`, if uploaded, is a draft only and is never "
        "executed automatically by this workflow.**",
        "",
    ]
    if status != "PASS":
        lines.append(f"⚠️ This run is **{status}** -- it must not be treated as a passing result.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--decision-path", default=None)
    parser.add_argument("--quality-path", default=None)
    parser.add_argument("--report-path", default=None)
    parser.add_argument("--summary-out", default=None)
    parser.add_argument("--github-output", default=None)
    args = parser.parse_args()

    decision, decision_err = load_json_safe(Path(args.decision_path) if args.decision_path else None)
    quality, quality_err = load_json_safe(Path(args.quality_path) if args.quality_path else None)
    report, _ = load_json_safe(Path(args.report_path) if args.report_path else None)

    status, reason = classify(args.exit_code, decision)

    # A decision file is only trustworthy for *this* run once classify()
    # has actually confirmed it matches the exit code. On ERROR, `decision`
    # may be a stale, unrelated, committed-from-a-previous-run file (e.g.
    # validate_ci_inputs.py failed before the pipeline ever touched it) --
    # never display its fields as if they describe this run.
    trusted_decision = decision if status != "ERROR" else None
    trusted_decision_err = decision_err if status != "ERROR" else reason
    # Same reasoning as trusted_decision: latest_report.json and
    # quality_checks.json could equally be stale, committed leftovers from
    # a previous run if the pipeline never got as far as regenerating them
    # this time (e.g. input validation failed before the pipeline started).
    trusted_report = report if status != "ERROR" else None
    trusted_quality = quality if status != "ERROR" else None
    trusted_quality_err = quality_err if status != "ERROR" else "pipeline did not run this cycle -- not trusted"

    summary = build_summary(
        status, args.exit_code, trusted_decision, trusted_decision_err,
        trusted_quality, trusted_quality_err, trusted_report,
    )

    if args.summary_out:
        with open(args.summary_out, "a", encoding="utf-8") as f:
            f.write(summary + "\n")
    else:
        print(summary)

    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as f:
            f.write(f"status={status}\n")
            f.write(f"risk={(trusted_decision or {}).get('risk', '')}\n")
            f.write(f"next_task={(trusted_decision or {}).get('next_task') or ''}\n")
            f.write(f"classification_reason={reason}\n")

    print(f"Classified as {status}: {reason}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
