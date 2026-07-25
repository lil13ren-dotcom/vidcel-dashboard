# Git diff

Root: `/home/user/vidcel-dashboard`

### Uncommitted changes

diff --git a/automation/README.md b/automation/README.md
index 0280669..c84bf85 100644
--- a/automation/README.md
+++ b/automation/README.md
@@ -1,4 +1,4 @@
-# PM Automation Layer (PM-AUTO-01)
+# PM Automation Layer (PM-AUTO-01 / 02 / 03)
 
 Reduces manual copy-paste between the PM (ChatGPT/human) and Claude Code by
 standardizing completion reports, auto-collecting review material, and
@@ -25,32 +25,51 @@ generate_completion_report.py  -->  reports/latest_report.{md,json}
  yes                         no
   |                           |
   v                           v
-HALT. Print reason.    generate_review_package.py --> review/review_request.md
-Exit code 2.                  |
-Human review required.        v
-                        generate_next_task.py --> tasks/NEXT_TASK_DRAFT.md
-                               |
-                               v
-                        Human (or ChatGPT PM) reviews review_request.md,
-                        returns PASS / FAIL / BLOCKED, and explicitly
-                        approves (or rewrites) NEXT_TASK_DRAFT.md before
-                        it becomes a real Task ID. This automation layer
-                        never does that step itself.
+generate_decision_       generate_review_package.py --> review/review_request.md,
+package.py                                              reports/quality_checks.json
+(status: BLOCKED)               |
+  |                             v
+  v                      generate_decision_package.py --> review/review_decision.json,
+HALT. Exit code 2.       review/review_summary.md, review/next_task_draft.md
+Human review required.   (status: PASS or FAIL)
+                                 |
+                                 v
+                          generate_next_task.py --> tasks/NEXT_TASK_DRAFT.md
+                          (freeform, Backlog-aware -- separate from the
+                           deterministic next_task_draft.md above)
+                                 |
+                                 v
+                          Human (or ChatGPT PM) reads review_decision.json
+                          (or review_summary.md), returns PASS / FAIL / BLOCKED,
+                          and explicitly approves (or rewrites) a next task
+                          before it becomes a real Task ID. This automation
+                          layer never does that step itself.
 ```
 
-`run_pm_pipeline.py` runs all three stages in order and stops itself the
-moment a stop-flag appears — this is the "Task Runner" in the architecture
-diagram.
+`run_pm_pipeline.py` runs every stage in order and stops itself the moment
+a stop-flag appears — this is the "Task Runner" in the architecture diagram.
+Its own exit code mirrors the decision (0 = PASS, 2 = BLOCKED, 3 = FAIL, 1 =
+invalid `task_meta.json`), so it's directly usable as a CI gate. See
+[`DECISION_PACKAGE.md`](./DECISION_PACKAGE.md) for the full design of the
+structured decision layer (PM-AUTO-03) — status/risk derivation rules, the
+JSON schema, and worked examples.
 
 ## Folder structure
 
 ```
 automation/
   README.md                       this file
+  DECISION_PACKAGE.md             design doc for the structured decision layer (PM-AUTO-03)
   generate_completion_report.py   stage 1
-  generate_review_package.py      stage 2 (skipped on auto-stop)
-  generate_next_task.py           stage 3 (skipped on auto-stop)
+  generate_review_package.py      stage 2a (skipped on auto-stop) -- quality checks
+  generate_decision_package.py    stage 2b -- deterministic PASS/FAIL/BLOCKED decision
+  generate_next_task.py           stage 3 (skipped on auto-stop) -- freeform, Backlog-aware
   run_pm_pipeline.py              orchestrator
+  schemas/
+    review_decision.schema.json    JSON Schema (draft-07) for review_decision.json
+  examples/
+    pass/, fail/, blocked/          real, generated example decision packages, each with
+                                     the task_meta.json fixture that produced it
   reports/
     task_meta.json                 input you write per task (overwritten/committed
                                     each run — history lives in git log, not in
@@ -63,11 +82,14 @@ automation/
     quality_checks.json            output — machine-readable per-check status/exit code,
                                     from the review stage
   review/
-    review_request.md              output — the review package
+    review_request.md              output — the quality-check review package (stage 2a)
+    review_decision.json           output — fixed-schema PASS/FAIL/BLOCKED decision (stage 2b)
+    review_summary.md              output — human-readable summary (stage 2b)
+    next_task_draft.md             output — structured, status-driven next-task draft (stage 2b)
     screenshots/                   optional — drop images here before running;
                                     they'll be listed (never generated) in the package
   tasks/
-    NEXT_TASK_DRAFT.md              output — draft only, never auto-approved
+    NEXT_TASK_DRAFT.md              output — freeform, Backlog-aware draft (stage 3), never auto-approved
 ```
 
 The project's existing top-level `knowledge/` folder (`Decision_Log.md`,
@@ -94,17 +116,21 @@ location for context.
    repo's `automation/`. Quality-check discovery reads the target repo's own
    `pyproject.toml`/`alembic.ini`, so this works against any repo without
    per-repo hardcoding.
-3. If it halts (exit code 2), the reason is printed and in
-   `latest_report.md` — resolve it like any other PM OS blocker (see
-   `knowledge/Decision_Log.md`'s pattern for prior blockers, e.g. G1-12) and
-   don't just remove the flag to make the pipeline continue.
-4. If it completes (exit code 0), hand `automation/review/review_request.md`
-   to the PM (ChatGPT or a human) for PASS / FAIL / BLOCKED.
-5. On PASS, review `automation/tasks/NEXT_TASK_DRAFT.md`, edit it as
-   needed, assign it a real Task ID, and get explicit approval before it
-   goes to Claude Code. The draft is intentionally not polished enough to
-   send as-is — it's a starting point built from whatever the previous
-   report's `suggested_next_task` said, plus open Backlog items.
+3. If it halts (exit code 2), `automation/review/review_decision.json` still
+   has `status: "BLOCKED"` and a `reason` — resolve it like any other PM OS
+   blocker (see `knowledge/Decision_Log.md`'s pattern for prior blockers,
+   e.g. G1-12) and don't just remove the flag to make the pipeline continue.
+4. Otherwise, hand `automation/review/review_decision.json` (or the
+   human-readable `review_summary.md`) to the PM (ChatGPT or a human) for
+   PASS / FAIL / BLOCKED. Exit code 3 means the decision is already FAIL —
+   see `automation/review/next_task_draft.md`, which will be titled
+   `REWORK: <task_id>`. `review/review_request.md` has the full per-check
+   detail (commands, exit codes, captured output) behind the decision.
+5. On PASS, review `automation/review/next_task_draft.md` (structured,
+   status-aware) and/or `automation/tasks/NEXT_TASK_DRAFT.md` (freeform,
+   Backlog-aware), edit as needed, assign a real Task ID, and get explicit
+   approval before it goes to Claude Code. Neither draft is polished enough
+   to send as-is.
 
 ## Example workflow
 
@@ -158,22 +184,29 @@ pipeline halts regardless of what `category` says.
 
 - Does not write, edit, or deploy product code.
 - Does not touch Stripe, the production Apps Script, or Google Sheets.
-- Does not decide PASS/FAIL/BLOCKED — that's the PM's call, human or
-  ChatGPT, reading `review_request.md`.
-- Does not approve or execute `NEXT_TASK_DRAFT.md` — that requires an
-  explicit human action outside this tooling.
+- Does not decide anything a human should decide — `review_decision.json`'s
+  `status`/`risk` are *derived and reported*, not a substitute for the PM
+  actually reading `review_summary.md`/`review_request.md` and choosing
+  what happens next. `requires_human_approval` is always `true`.
+- Does not approve or execute `next_task_draft.md` / `NEXT_TASK_DRAFT.md` —
+  that requires an explicit human action outside this tooling.
 - Does not install any dependency. pytest/mypy/ruff/npm are only invoked
   if already present in the environment *and* configured in the repo;
   otherwise each is reported as skipped, not silently ignored.
+- Does not parse free-form prose (risks/blockers/evidence text) to decide
+  status or risk — see `DECISION_PACKAGE.md` for exactly which fields are
+  explicit input versus derived.
 
 ## Remaining manual steps
 
 - Writing `task_meta.json`'s narrative fields (objective, risks, evidence,
-  suggested next task) — this is deliberately not automated; it's the
-  actual PM judgment.
-- Reading `review_request.md` and deciding PASS/FAIL/BLOCKED.
-- Reviewing and approving (or rewriting) `NEXT_TASK_DRAFT.md` before it
-  becomes a real Task ID.
+  suggested next task) and its explicit `risk`/`next_task_id` fields — this
+  is deliberately not automated; it's the actual PM judgment.
+- Reading `review_decision.json`/`review_summary.md` and deciding what
+  happens next (the automation reports PASS/FAIL/BLOCKED, it doesn't act
+  on it).
+- Reviewing and approving (or rewriting) `next_task_draft.md` or
+  `NEXT_TASK_DRAFT.md` before either becomes a real Task ID.
 - Dropping screenshots into `automation/review/screenshots/` before running,
   if visual evidence is relevant — nothing captures them automatically.
 
@@ -191,3 +224,15 @@ reverted. **Still not validated:** npm-build detection against a repo
 with a real `package.json`/build script — `ai-lead-os` is pure Python, so
 only the "no package.json, correctly skipped" path has been exercised for
 that check specifically.
+
+## Validated (PM-AUTO-03, 2026-07-25)
+
+All three decision-package scenarios were run for real and validated
+against the JSON Schema (see `automation/examples/{pass,fail,blocked}/`):
+a clean run (no flags, no failing checks) → `status: PASS`; a run with
+`flags: ["SECRET_REQUIRED"]` → `status: BLOCKED`, quality checks and the
+freeform next-task generator correctly skipped, `review_decision.json`
+still generated with `requires_human_approval: true`; a run against
+`ai-lead-os` with a deliberately-injected, reverted Ruff violation →
+`status: FAIL`, `next_task: "REWORK-<task_id>"`. Full evidence in
+`knowledge/Decision_Log.md`'s PM-AUTO-03 entry.
diff --git a/automation/generate_completion_report.py b/automation/generate_completion_report.py
index 69ae468..822e403 100755
--- a/automation/generate_completion_report.py
+++ b/automation/generate_completion_report.py
@@ -32,6 +32,8 @@ CONTINUE_CATEGORIES = {
     "Documentation", "Tests", "Refactoring", "Lint", "Formatting",
     "Knowledge updates", "PM OS updates", "Task generation",
 }
+RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}
+STATUS_VALUES = {"PASS", "FAIL", "BLOCKED"}
 
 
 def run(cmd):
@@ -83,6 +85,14 @@ def validate_meta(meta: dict) -> list[str]:
     bad_flags = set(meta.get("flags", [])) - STOP_FLAGS
     if bad_flags:
         errors.append(f"unrecognized flags: {sorted(bad_flags)} — expected one of {sorted(STOP_FLAGS)}")
+    risk = meta.get("risk")
+    if risk is not None and risk not in RISK_LEVELS:
+        errors.append(f"unrecognized risk {risk!r} — expected one of {sorted(RISK_LEVELS)}")
+    status_override = meta.get("status_override")
+    if status_override is not None and status_override not in STATUS_VALUES:
+        errors.append(
+            f"unrecognized status_override {status_override!r} — expected one of {sorted(STATUS_VALUES)}"
+        )
     return errors
 
 
@@ -105,6 +115,9 @@ def build_report(meta: dict) -> tuple[str, dict]:
         "remaining_blockers": meta.get("remaining_blockers", ""),
         "evidence": meta.get("evidence", ""),
         "suggested_next_task": meta.get("suggested_next_task", ""),
+        "next_task_id": meta.get("next_task_id") or None,
+        "risk": meta.get("risk") or "MEDIUM",
+        "status_override": meta.get("status_override") or None,
         "flags": flags,
         "should_stop": should_stop,
     }
@@ -114,6 +127,8 @@ def build_report(meta: dict) -> tuple[str, dict]:
         "",
         f"- **Generated:** {data['generated_at']}",
         f"- **Category:** {data['category']}",
+        f"- **Risk:** {data['risk']}",
+        f"- **Status override:** {data['status_override'] or '_(none — status will be derived automatically)_'}",
         f"- **Auto-stop triggered:** {'YES — ' + ', '.join(flags) if should_stop else 'no'}",
         "",
         "## Objective",
diff --git a/automation/generate_review_package.py b/automation/generate_review_package.py
index ffcaa5f..cf8dca5 100755
--- a/automation/generate_review_package.py
+++ b/automation/generate_review_package.py
@@ -31,6 +31,7 @@ Usage:
     python3 automation/generate_review_package.py [--root <path>] [--base <branch>]
 """
 import argparse
+import datetime
 import json
 import shutil
 import subprocess
@@ -260,9 +261,19 @@ def main():
         encoding="utf-8",
     )
 
+    n_pass = sum(1 for c in checks if c.status == "PASS")
+    n_fail = sum(1 for c in checks if c.status == "FAIL")
+    n_skip = sum(1 for c in checks if c.status == "SKIPPED")
+    overall = "FAIL" if n_fail else ("PASS (with skips)" if n_skip else "PASS")
+
     quality_checks_json = {
         "root": str(root),
         "use_uv": runner.use_uv,
+        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
+        "overall": overall,
+        "n_pass": n_pass,
+        "n_fail": n_fail,
+        "n_skip": n_skip,
         "checks": [
             {
                 "name": c.name, "command": c.command, "status": c.status,
@@ -275,11 +286,6 @@ def main():
         json.dumps(quality_checks_json, indent=2, ensure_ascii=False), encoding="utf-8"
     )
 
-    n_pass = sum(1 for c in checks if c.status == "PASS")
-    n_fail = sum(1 for c in checks if c.status == "FAIL")
-    n_skip = sum(1 for c in checks if c.status == "SKIPPED")
-    overall = "FAIL" if n_fail else ("PASS (with skips)" if n_skip else "PASS")
-
     summary_table = "\n".join(
         f"| {c.name} | {c.status} | {c.exit_code if c.exit_code is not None else '-'} |"
         for c in checks
diff --git a/automation/reports/latest_report.json b/automation/reports/latest_report.json
index 002f911..46a5e4f 100644
--- a/automation/reports/latest_report.json
+++ b/automation/reports/latest_report.json
@@ -1,28 +1,44 @@
 {
-  "task_id": "PM-AUTO-02",
-  "objective": "Validate the PM-AUTO-01 automation against the real ai-lead-os repository: confirm the review-package generator discovers and executes Ruff check, Ruff format check, mypy strict, pytest+coverage, and Alembic check using ai-lead-os's actual configured tooling, and that the completion report / review package / next-task-draft pipeline runs end to end.",
-  "category": "Tests",
-  "generated_at": "2026-07-25T06:15:50+00:00",
+  "task_id": "PM-AUTO-03",
+  "objective": "Implement a structured PM decision package (review_summary.md, review_decision.json, next_task_draft.md) that converts the PM review into machine-readable, deterministic files, eliminating manual interpretation of review comments for the next development cycle.",
+  "category": "Implementation",
+  "generated_at": "2026-07-25T06:43:26+00:00",
   "files_modified": [
+    "automation/generate_decision_package.py",
+    "automation/generate_completion_report.py",
     "automation/generate_review_package.py",
-    "automation/run_pm_pipeline.py"
+    "automation/run_pm_pipeline.py",
+    "automation/schemas/review_decision.schema.json",
+    "automation/DECISION_PACKAGE.md",
+    "automation/README.md",
+    "automation/reports/task_meta.example.json",
+    "automation/examples/pass/task_meta.json",
+    "automation/examples/pass/review_decision.json",
+    "automation/examples/pass/review_summary.md",
+    "automation/examples/pass/next_task_draft.md",
+    "automation/examples/fail/task_meta.json",
+    "automation/examples/fail/review_decision.json",
+    "automation/examples/fail/review_summary.md",
+    "automation/examples/fail/next_task_draft.md",
+    "automation/examples/blocked/task_meta.json",
+    "automation/examples/blocked/review_decision.json",
+    "automation/examples/blocked/review_summary.md",
+    "automation/examples/blocked/next_task_draft.md"
   ],
   "tests_executed": [
-    "uv run ruff check . (ai-lead-os, manual baseline)",
-    "uv run ruff format --check . (ai-lead-os, manual baseline)",
-    "uv run mypy src (ai-lead-os, manual baseline)",
-    "uv run alembic upgrade head / alembic check (ai-lead-os, manual baseline)",
-    "uv run pytest --cov=ai_lead_os (ai-lead-os, manual baseline)",
-    "automation/generate_review_package.py --root /workspace/ai-lead-os (Scenario 1)",
-    "automation/run_pm_pipeline.py --root /workspace/ai-lead-os (Scenario 1, full pipeline)",
-    "automation/generate_review_package.py --root /workspace/ai-lead-os (Scenario 2, with an injected Ruff violation)",
-    "automation/generate_review_package.py --root /workspace/ai-lead-os (post-restore re-run, confirms clean state)"
+    "python3 automation/run_pm_pipeline.py automation/examples/pass/task_meta.json (Scenario 1)",
+    "python3 automation/run_pm_pipeline.py automation/examples/blocked/task_meta.json (Scenario 2)",
+    "python3 automation/run_pm_pipeline.py automation/examples/fail/task_meta.json --root /workspace/ai-lead-os (Scenario 3, with an injected Ruff violation)",
+    "jsonschema.validate() of all 3 example review_decision.json files against schemas/review_decision.schema.json"
   ],
-  "test_results": "Scenario 1: all 6 checks (Ruff check, Ruff format check, mypy strict, Alembic upgrade head, Alembic check, pytest with coverage) discovered from ai-lead-os's pyproject.toml/alembic.ini and executed via `uv run`. All PASS, exit code 0, output matches the manually-run baseline exactly: 'All checks passed!' (ruff), '314 files already formatted' (ruff format), 'Success: no issues found in 195 source files' (mypy), 'No new upgrade operations detected.' (alembic check), '1006 passed in 190.87s', 91.07% coverage (>=90% threshold). Scenario 2: a throwaway file with 2 unused imports + 1 unused variable was added under a temp scratch directory in ai-lead-os; the automation correctly reported 'Overall: FAIL (5 passed, 1 failed, 0 skipped)', script exit code 1, Ruff check status FAIL with the real F401/F841 ruff output captured verbatim in test_results.md, and all 5 other checks still correctly PASS -- no false PASS on the failing check, no false FAIL bleeding into unrelated checks. After deleting the scratch file/dir and `git checkout -- README.md`, ai-lead-os's `git status --short` returned empty and a final re-run returned to 'Overall: PASS (6 passed, 0 failed, 0 skipped)', confirming full restoration.",
-  "risks": "generate_completion_report.py and generate_next_task.py still operate only on vidcel-dashboard's own git state (by design -- they track this PM task, not ai-lead-os's business logic), so --root only applies to generate_review_package.py. This is intentional but worth documenting clearly. Also fixed a redundant/confusing (but not incorrect in practice) guard clause in run_pytest_with_coverage()'s pyproject.toml detection during this task -- see knowledge/Decision_Log.md.",
+  "test_results": "Scenario 1 (PASS): no flags, no failing checks (ran against vidcel-dashboard, which has no Python tooling configured -- all checks SKIPPED, 0 FAIL) -> status=PASS, next_task='PM-AUTO-04' (from next_task_id), review/review_decision.json + review_summary.md + next_task_draft.md all generated, exit code 0. Scenario 2 (BLOCKED): flags=['SECRET_REQUIRED'] -> status=BLOCKED, quality-check stage and freeform next-task generator both correctly skipped, review_decision.json still generated (blocked=true, next_task=null, requires_human_approval=true), exit code 2. Scenario 3 (FAIL): no flags, a throwaway Ruff-violating file was added to ai-lead-os -> 1 quality check FAILed -> status=FAIL, next_task='REWORK-PM-AUTO-03-EXAMPLE-FAIL' (ignoring the fixture's suggested_next_task text), recommendation updated to 'do not proceed', exit code 3; ai-lead-os fully reverted afterward (git status --short empty). All 3 review_decision.json outputs validated successfully against schemas/review_decision.schema.json via the jsonschema library.",
+  "risks": "risk field does not currently gate the pipeline (informational only, documented as a known limitation in DECISION_PACKAGE.md). The quality_checks.json freshness check compares ISO timestamp strings, which is correct given both files use the same isoformat/timezone convention but is not a fully general-purpose timestamp comparison -- also documented as a limitation.",
   "remaining_blockers": "",
-  "evidence": "See automation/reports/quality_checks.json, automation/reports/test_results.md, and automation/review/review_request.md (current contents reflect the final clean re-run). A minimal harmless doc-only change (one comment line appended to ai-lead-os/README.md) was made to produce a valid git diff for the git-diff/git-status detection check in Scenario 1; a throwaway Ruff-violating file was added for Scenario 2. Both were fully reverted before this task closed -- ai-lead-os's git status --short is empty. ai-lead-os is read-only in this session (no push access) -- no commits were made there.",
-  "suggested_next_task": "PM-AUTO-03: wire the automation into the actual Claude Code <-> ChatGPT PM handoff for a real upcoming task (e.g. the next Gate 1 item), replacing the manual copy-paste flow for the first time on a live task rather than a validation run.",
+  "evidence": "See automation/review/review_decision.json (this task's own real run, appended below), automation/examples/{pass,fail,blocked}/ for the three validated scenario packages, and knowledge/Decision_Log.md's PM-AUTO-03 entry for full narrative evidence.",
+  "suggested_next_task": "PM-AUTO-04: wire review_decision.json / run_pm_pipeline.py's exit code into an actual GitHub Actions workflow step, so a real CI run gates on PASS/FAIL/BLOCKED automatically.",
+  "next_task_id": "PM-AUTO-04",
+  "risk": "LOW",
+  "status_override": null,
   "flags": [],
   "should_stop": false
 }
\ No newline at end of file
diff --git a/automation/reports/latest_report.md b/automation/reports/latest_report.md
index 0e79e21..b0856bd 100644
--- a/automation/reports/latest_report.md
+++ b/automation/reports/latest_report.md
@@ -1,38 +1,53 @@
-# Completion Report — PM-AUTO-02
+# Completion Report — PM-AUTO-03
 
-- **Generated:** 2026-07-25T06:15:50+00:00
-- **Category:** Tests
+- **Generated:** 2026-07-25T06:43:26+00:00
+- **Category:** Implementation
+- **Risk:** LOW
+- **Status override:** _(none — status will be derived automatically)_
 - **Auto-stop triggered:** no
 
 ## Objective
-Validate the PM-AUTO-01 automation against the real ai-lead-os repository: confirm the review-package generator discovers and executes Ruff check, Ruff format check, mypy strict, pytest+coverage, and Alembic check using ai-lead-os's actual configured tooling, and that the completion report / review package / next-task-draft pipeline runs end to end.
+Implement a structured PM decision package (review_summary.md, review_decision.json, next_task_draft.md) that converts the PM review into machine-readable, deterministic files, eliminating manual interpretation of review comments for the next development cycle.
 
 ## Files modified
+- `automation/generate_decision_package.py`
+- `automation/generate_completion_report.py`
 - `automation/generate_review_package.py`
 - `automation/run_pm_pipeline.py`
+- `automation/schemas/review_decision.schema.json`
+- `automation/DECISION_PACKAGE.md`
+- `automation/README.md`
+- `automation/reports/task_meta.example.json`
+- `automation/examples/pass/task_meta.json`
+- `automation/examples/pass/review_decision.json`
+- `automation/examples/pass/review_summary.md`
+- `automation/examples/pass/next_task_draft.md`
+- `automation/examples/fail/task_meta.json`
+- `automation/examples/fail/review_decision.json`
+- `automation/examples/fail/review_summary.md`
+- `automation/examples/fail/next_task_draft.md`
+- `automation/examples/blocked/task_meta.json`
+- `automation/examples/blocked/review_decision.json`
+- `automation/examples/blocked/review_summary.md`
+- `automation/examples/blocked/next_task_draft.md`
 
 ## Tests executed
-- uv run ruff check . (ai-lead-os, manual baseline)
-- uv run ruff format --check . (ai-lead-os, manual baseline)
-- uv run mypy src (ai-lead-os, manual baseline)
-- uv run alembic upgrade head / alembic check (ai-lead-os, manual baseline)
-- uv run pytest --cov=ai_lead_os (ai-lead-os, manual baseline)
-- automation/generate_review_package.py --root /workspace/ai-lead-os (Scenario 1)
-- automation/run_pm_pipeline.py --root /workspace/ai-lead-os (Scenario 1, full pipeline)
-- automation/generate_review_package.py --root /workspace/ai-lead-os (Scenario 2, with an injected Ruff violation)
-- automation/generate_review_package.py --root /workspace/ai-lead-os (post-restore re-run, confirms clean state)
+- python3 automation/run_pm_pipeline.py automation/examples/pass/task_meta.json (Scenario 1)
+- python3 automation/run_pm_pipeline.py automation/examples/blocked/task_meta.json (Scenario 2)
+- python3 automation/run_pm_pipeline.py automation/examples/fail/task_meta.json --root /workspace/ai-lead-os (Scenario 3, with an injected Ruff violation)
+- jsonschema.validate() of all 3 example review_decision.json files against schemas/review_decision.schema.json
 
 ## Test results
-Scenario 1: all 6 checks (Ruff check, Ruff format check, mypy strict, Alembic upgrade head, Alembic check, pytest with coverage) discovered from ai-lead-os's pyproject.toml/alembic.ini and executed via `uv run`. All PASS, exit code 0, output matches the manually-run baseline exactly: 'All checks passed!' (ruff), '314 files already formatted' (ruff format), 'Success: no issues found in 195 source files' (mypy), 'No new upgrade operations detected.' (alembic check), '1006 passed in 190.87s', 91.07% coverage (>=90% threshold). Scenario 2: a throwaway file with 2 unused imports + 1 unused variable was added under a temp scratch directory in ai-lead-os; the automation correctly reported 'Overall: FAIL (5 passed, 1 failed, 0 skipped)', script exit code 1, Ruff check status FAIL with the real F401/F841 ruff output captured verbatim in test_results.md, and all 5 other checks still correctly PASS -- no false PASS on the failing check, no false FAIL bleeding into unrelated checks. After deleting the scratch file/dir and `git checkout -- README.md`, ai-lead-os's `git status --short` returned empty and a final re-run returned to 'Overall: PASS (6 passed, 0 failed, 0 skipped)', confirming full restoration.
+Scenario 1 (PASS): no flags, no failing checks (ran against vidcel-dashboard, which has no Python tooling configured -- all checks SKIPPED, 0 FAIL) -> status=PASS, next_task='PM-AUTO-04' (from next_task_id), review/review_decision.json + review_summary.md + next_task_draft.md all generated, exit code 0. Scenario 2 (BLOCKED): flags=['SECRET_REQUIRED'] -> status=BLOCKED, quality-check stage and freeform next-task generator both correctly skipped, review_decision.json still generated (blocked=true, next_task=null, requires_human_approval=true), exit code 2. Scenario 3 (FAIL): no flags, a throwaway Ruff-violating file was added to ai-lead-os -> 1 quality check FAILed -> status=FAIL, next_task='REWORK-PM-AUTO-03-EXAMPLE-FAIL' (ignoring the fixture's suggested_next_task text), recommendation updated to 'do not proceed', exit code 3; ai-lead-os fully reverted afterward (git status --short empty). All 3 review_decision.json outputs validated successfully against schemas/review_decision.schema.json via the jsonschema library.
 
 ## Risks
-generate_completion_report.py and generate_next_task.py still operate only on vidcel-dashboard's own git state (by design -- they track this PM task, not ai-lead-os's business logic), so --root only applies to generate_review_package.py. This is intentional but worth documenting clearly. Also fixed a redundant/confusing (but not incorrect in practice) guard clause in run_pytest_with_coverage()'s pyproject.toml detection during this task -- see knowledge/Decision_Log.md.
+risk field does not currently gate the pipeline (informational only, documented as a known limitation in DECISION_PACKAGE.md). The quality_checks.json freshness check compares ISO timestamp strings, which is correct given both files use the same isoformat/timezone convention but is not a fully general-purpose timestamp comparison -- also documented as a limitation.
 
 ## Remaining blockers
 _(none noted)_
 
 ## Evidence
-See automation/reports/quality_checks.json, automation/reports/test_results.md, and automation/review/review_request.md (current contents reflect the final clean re-run). A minimal harmless doc-only change (one comment line appended to ai-lead-os/README.md) was made to produce a valid git diff for the git-diff/git-status detection check in Scenario 1; a throwaway Ruff-violating file was added for Scenario 2. Both were fully reverted before this task closed -- ai-lead-os's git status --short is empty. ai-lead-os is read-only in this session (no push access) -- no commits were made there.
+See automation/review/review_decision.json (this task's own real run, appended below), automation/examples/{pass,fail,blocked}/ for the three validated scenario packages, and knowledge/Decision_Log.md's PM-AUTO-03 entry for full narrative evidence.
 
 ## Suggested next task
-PM-AUTO-03: wire the automation into the actual Claude Code <-> ChatGPT PM handoff for a real upcoming task (e.g. the next Gate 1 item), replacing the manual copy-paste flow for the first time on a live task rather than a validation run.
+PM-AUTO-04: wire review_decision.json / run_pm_pipeline.py's exit code into an actual GitHub Actions workflow step, so a real CI run gates on PASS/FAIL/BLOCKED automatically.
diff --git a/automation/reports/quality_checks.json b/automation/reports/quality_checks.json
index 64d5fb5..ab4e1f8 100644
--- a/automation/reports/quality_checks.json
+++ b/automation/reports/quality_checks.json
@@ -1,12 +1,17 @@
 {
   "root": "/workspace/ai-lead-os",
   "use_uv": true,
+  "generated_at": "2026-07-25T06:41:07+00:00",
+  "overall": "FAIL",
+  "n_pass": 5,
+  "n_fail": 1,
+  "n_skip": 0,
   "checks": [
     {
       "name": "Ruff check",
       "command": "uv run ruff check .",
-      "status": "PASS",
-      "exit_code": 0,
+      "status": "FAIL",
+      "exit_code": 1,
       "reason": ""
     },
     {
diff --git a/automation/reports/task_meta.example.json b/automation/reports/task_meta.example.json
index ada0a39..dbfe941 100644
--- a/automation/reports/task_meta.example.json
+++ b/automation/reports/task_meta.example.json
@@ -14,6 +14,14 @@
   "remaining_blockers": "",
   "evidence": "",
   "suggested_next_task": "",
+  "next_task_id": null,
+  "_next_task_id_note": "Optional. A short label/ID for the next task (e.g. 'PM-AUTO-04'), used verbatim as review_decision.json's `next_task` field when status is PASS. Deliberately separate from the free-text `suggested_next_task` above -- the decision package never parses that prose to derive a next_task value. Leave null if no next task is assigned yet; review_decision.json will record `next_task: null` rather than guessing.",
+  "risk": "MEDIUM",
+  "_risk_options": ["LOW", "MEDIUM", "HIGH"],
+  "_risk_note": "Optional, defaults to MEDIUM if omitted (a deliberately conservative default, not a guess). This is a human/Claude judgment call -- the automation never infers risk from file counts, diff size, or prose.",
+  "status_override": null,
+  "_status_override_options": ["PASS", "FAIL", "BLOCKED", null],
+  "_status_override_note": "Optional. If set, review_decision.json's `status` uses this value directly instead of the automatically-derived one (flags present -> BLOCKED; any quality check FAIL -> FAIL; otherwise PASS). Use this only when the automatic derivation would be wrong for a reason the automation can't see (e.g. a manual review found the deliverable insufficient even though all checks passed).",
   "flags": [],
   "_flags_options": [
     "BLOCKED", "EVIDENCE_MISSING", "PRODUCTION_CHANGE", "ARCHITECTURE_CHANGE",
diff --git a/automation/reports/task_meta.json b/automation/reports/task_meta.json
index 6ec960b..635ea10 100644
--- a/automation/reports/task_meta.json
+++ b/automation/reports/task_meta.json
@@ -1,26 +1,42 @@
 {
-  "task_id": "PM-AUTO-02",
-  "objective": "Validate the PM-AUTO-01 automation against the real ai-lead-os repository: confirm the review-package generator discovers and executes Ruff check, Ruff format check, mypy strict, pytest+coverage, and Alembic check using ai-lead-os's actual configured tooling, and that the completion report / review package / next-task-draft pipeline runs end to end.",
-  "category": "Tests",
+  "task_id": "PM-AUTO-03",
+  "objective": "Implement a structured PM decision package (review_summary.md, review_decision.json, next_task_draft.md) that converts the PM review into machine-readable, deterministic files, eliminating manual interpretation of review comments for the next development cycle.",
+  "category": "Implementation",
   "files_modified": [
+    "automation/generate_decision_package.py",
+    "automation/generate_completion_report.py",
     "automation/generate_review_package.py",
-    "automation/run_pm_pipeline.py"
+    "automation/run_pm_pipeline.py",
+    "automation/schemas/review_decision.schema.json",
+    "automation/DECISION_PACKAGE.md",
+    "automation/README.md",
+    "automation/reports/task_meta.example.json",
+    "automation/examples/pass/task_meta.json",
+    "automation/examples/pass/review_decision.json",
+    "automation/examples/pass/review_summary.md",
+    "automation/examples/pass/next_task_draft.md",
+    "automation/examples/fail/task_meta.json",
+    "automation/examples/fail/review_decision.json",
+    "automation/examples/fail/review_summary.md",
+    "automation/examples/fail/next_task_draft.md",
+    "automation/examples/blocked/task_meta.json",
+    "automation/examples/blocked/review_decision.json",
+    "automation/examples/blocked/review_summary.md",
+    "automation/examples/blocked/next_task_draft.md"
   ],
   "tests_executed": [
-    "uv run ruff check . (ai-lead-os, manual baseline)",
-    "uv run ruff format --check . (ai-lead-os, manual baseline)",
-    "uv run mypy src (ai-lead-os, manual baseline)",
-    "uv run alembic upgrade head / alembic check (ai-lead-os, manual baseline)",
-    "uv run pytest --cov=ai_lead_os (ai-lead-os, manual baseline)",
-    "automation/generate_review_package.py --root /workspace/ai-lead-os (Scenario 1)",
-    "automation/run_pm_pipeline.py --root /workspace/ai-lead-os (Scenario 1, full pipeline)",
-    "automation/generate_review_package.py --root /workspace/ai-lead-os (Scenario 2, with an injected Ruff violation)",
-    "automation/generate_review_package.py --root /workspace/ai-lead-os (post-restore re-run, confirms clean state)"
+    "python3 automation/run_pm_pipeline.py automation/examples/pass/task_meta.json (Scenario 1)",
+    "python3 automation/run_pm_pipeline.py automation/examples/blocked/task_meta.json (Scenario 2)",
+    "python3 automation/run_pm_pipeline.py automation/examples/fail/task_meta.json --root /workspace/ai-lead-os (Scenario 3, with an injected Ruff violation)",
+    "jsonschema.validate() of all 3 example review_decision.json files against schemas/review_decision.schema.json"
   ],
-  "test_results": "Scenario 1: all 6 checks (Ruff check, Ruff format check, mypy strict, Alembic upgrade head, Alembic check, pytest with coverage) discovered from ai-lead-os's pyproject.toml/alembic.ini and executed via `uv run`. All PASS, exit code 0, output matches the manually-run baseline exactly: 'All checks passed!' (ruff), '314 files already formatted' (ruff format), 'Success: no issues found in 195 source files' (mypy), 'No new upgrade operations detected.' (alembic check), '1006 passed in 190.87s', 91.07% coverage (>=90% threshold). Scenario 2: a throwaway file with 2 unused imports + 1 unused variable was added under a temp scratch directory in ai-lead-os; the automation correctly reported 'Overall: FAIL (5 passed, 1 failed, 0 skipped)', script exit code 1, Ruff check status FAIL with the real F401/F841 ruff output captured verbatim in test_results.md, and all 5 other checks still correctly PASS -- no false PASS on the failing check, no false FAIL bleeding into unrelated checks. After deleting the scratch file/dir and `git checkout -- README.md`, ai-lead-os's `git status --short` returned empty and a final re-run returned to 'Overall: PASS (6 passed, 0 failed, 0 skipped)', confirming full restoration.",
-  "risks": "generate_completion_report.py and generate_next_task.py still operate only on vidcel-dashboard's own git state (by design -- they track this PM task, not ai-lead-os's business logic), so --root only applies to generate_review_package.py. This is intentional but worth documenting clearly. Also fixed a redundant/confusing (but not incorrect in practice) guard clause in run_pytest_with_coverage()'s pyproject.toml detection during this task -- see knowledge/Decision_Log.md.",
+  "test_results": "Scenario 1 (PASS): no flags, no failing checks (ran against vidcel-dashboard, which has no Python tooling configured -- all checks SKIPPED, 0 FAIL) -> status=PASS, next_task='PM-AUTO-04' (from next_task_id), review/review_decision.json + review_summary.md + next_task_draft.md all generated, exit code 0. Scenario 2 (BLOCKED): flags=['SECRET_REQUIRED'] -> status=BLOCKED, quality-check stage and freeform next-task generator both correctly skipped, review_decision.json still generated (blocked=true, next_task=null, requires_human_approval=true), exit code 2. Scenario 3 (FAIL): no flags, a throwaway Ruff-violating file was added to ai-lead-os -> 1 quality check FAILed -> status=FAIL, next_task='REWORK-PM-AUTO-03-EXAMPLE-FAIL' (ignoring the fixture's suggested_next_task text), recommendation updated to 'do not proceed', exit code 3; ai-lead-os fully reverted afterward (git status --short empty). All 3 review_decision.json outputs validated successfully against schemas/review_decision.schema.json via the jsonschema library.",
+  "risks": "risk field does not currently gate the pipeline (informational only, documented as a known limitation in DECISION_PACKAGE.md). The quality_checks.json freshness check compares ISO timestamp strings, which is correct given both files use the same isoformat/timezone convention but is not a fully general-purpose timestamp comparison -- also documented as a limitation.",
   "remaining_blockers": "",
-  "evidence": "See automation/reports/quality_checks.json, automation/reports/test_results.md, and automation/review/review_request.md (current contents reflect the final clean re-run). A minimal harmless doc-only change (one comment line appended to ai-lead-os/README.md) was made to produce a valid git diff for the git-diff/git-status detection check in Scenario 1; a throwaway Ruff-violating file was added for Scenario 2. Both were fully reverted before this task closed -- ai-lead-os's git status --short is empty. ai-lead-os is read-only in this session (no push access) -- no commits were made there.",
-  "suggested_next_task": "PM-AUTO-03: wire the automation into the actual Claude Code <-> ChatGPT PM handoff for a real upcoming task (e.g. the next Gate 1 item), replacing the manual copy-paste flow for the first time on a live task rather than a validation run.",
+  "evidence": "See automation/review/review_decision.json (this task's own real run, appended below), automation/examples/{pass,fail,blocked}/ for the three validated scenario packages, and knowledge/Decision_Log.md's PM-AUTO-03 entry for full narrative evidence.",
+  "suggested_next_task": "PM-AUTO-04: wire review_decision.json / run_pm_pipeline.py's exit code into an actual GitHub Actions workflow step, so a real CI run gates on PASS/FAIL/BLOCKED automatically.",
+  "next_task_id": "PM-AUTO-04",
+  "risk": "LOW",
+  "status_override": null,
   "flags": []
 }
diff --git a/automation/reports/test_results.md b/automation/reports/test_results.md
index 8267978..31cecd2 100644
--- a/automation/reports/test_results.md
+++ b/automation/reports/test_results.md
@@ -3,11 +3,40 @@
 Root: `/workspace/ai-lead-os`
 Invocation mode: uv run <tool>
 
-### Ruff check — PASS (exit code 0)
+### Ruff check — FAIL (exit code 1)
 `uv run ruff check .`
 
 ```
-All checks passed!
+F401 [*] `os` imported but unused
+ --> scratch_pm_auto03_tmp/__pmauto03_ruff_violation.py:1:8
+  |
+1 | import os
+  |        ^^
+2 | import sys
+  |
+help: Remove unused import: `os`
+
+F401 [*] `sys` imported but unused
+ --> scratch_pm_auto03_tmp/__pmauto03_ruff_violation.py:2:8
+  |
+1 | import os
+2 | import sys
+  |        ^^^
+  |
+help: Remove unused import: `sys`
+
+F841 Local variable `x` is assigned to but never used
+ --> scratch_pm_auto03_tmp/__pmauto03_ruff_violation.py:6:5
+  |
+5 | def unused_var_example():
+6 |     x = 1
+  |     ^
+7 |     return
+  |
+help: Remove assignment to unused variable `x`
+
+Found 3 errors.
+[*] 2 fixable with the `--fix` option (1 hidden fix can be enabled with the `--unsafe-fixes` option).
 ```
 
 
@@ -15,7 +44,7 @@ All checks passed!
 `uv run ruff format --check .`
 
 ```
-314 files already formatted
+315 files already formatted
 ```
 
 
@@ -356,6 +385,6 @@ src/ai_lead_os/webhook/receiver.py                                        85
 ------------------------------------------------------------------------------------------------------------------
 TOTAL                                                                  13691    958   2864    431    91%
 Required test coverage of 90.0% reached. Total coverage: 91.08%
-======================= 1006 passed in 190.99s (0:03:10) =======================
+======================= 1006 passed in 180.34s (0:03:00) =======================
 ```
 
diff --git a/automation/review/review_request.md b/automation/review/review_request.md
index 25f1787..f47d640 100644
--- a/automation/review/review_request.md
+++ b/automation/review/review_request.md
@@ -2,11 +2,11 @@
 
 Root: `/workspace/ai-lead-os`
 
-## Overall: PASS (6 passed, 0 failed, 0 skipped)
+## Overall: FAIL (5 passed, 1 failed, 0 skipped)
 
 | Check | Status | Exit code |
 |---|---|---|
-| Ruff check | PASS | 0 |
+| Ruff check | FAIL | 1 |
 | Ruff format check | PASS | 0 |
 | mypy (strict) | PASS | 0 |
 | Alembic upgrade head | PASS | 0 |
@@ -15,7 +15,7 @@ Root: `/workspace/ai-lead-os`
 
 ## Git status
 ```
-(clean working tree)
+?? scratch_pm_auto03_tmp/
 ```
 
 ### Build — SKIPPED
diff --git a/automation/run_pm_pipeline.py b/automation/run_pm_pipeline.py
index ab493c5..7c04b16 100755
--- a/automation/run_pm_pipeline.py
+++ b/automation/run_pm_pipeline.py
@@ -1,5 +1,5 @@
 #!/usr/bin/env python3
-"""Task Runner: orchestrates report -> review package -> next-task draft.
+"""Task Runner: orchestrates report -> [quality checks] -> decision package.
 
     Claude Code completes a task
             |
@@ -15,24 +15,41 @@
      yes                no
       |                  |
       v                  v
-    HALT.          generate_review_package.py --> review/review_request.md
-    Print reason.         |
-    Exit non-zero.        v
-                   generate_next_task.py --> tasks/NEXT_TASK_DRAFT.md
-                          |
-                          v
-                   Human reviews review_request.md + NEXT_TASK_DRAFT.md,
-                   sends PASS / FAIL / BLOCKED back, and explicitly
-                   approves (or rewrites) the next task before anything
-                   is implemented. This script never does that step.
+    generate_decision_    generate_review_package.py --> review/review_request.md,
+    package.py            reports/quality_checks.json
+    (status: BLOCKED,            |
+     derived from flags           v
+     alone -- no checks    generate_decision_package.py --> review/review_decision.json,
+     run)                  review/review_summary.md, review/next_task_draft.md
+      |                    (status: FAIL if any quality check failed, else PASS)
+      v                           |
+    HALT.                         v
+    Exit code 2.           generate_next_task.py --> tasks/NEXT_TASK_DRAFT.md
+    Human review                  (freeform, Backlog-aware suggestion --
+    required.                      separate from the deterministic
+                                    next_task_draft.md above)
+                                   |
+                                   v
+                            Human (or ChatGPT PM) reads review_decision.json
+                            (or review_summary.md), sends PASS / FAIL / BLOCKED
+                            back, and explicitly approves (or rewrites) the next
+                            task before anything is implemented. This script
+                            never does that step.
 
 Usage:
-    python3 automation/run_pm_pipeline.py [path/to/task_meta.json] [--base <branch>]
+    python3 automation/run_pm_pipeline.py [path/to/task_meta.json] [--base <branch>] [--root <path>]
 
-Exit code 0 = pipeline completed through next-task draft.
-Exit code 2 = pipeline halted on an auto-stop flag (this is not a failure
-              of the script -- it is the auto-stop rule working correctly).
+Exit code 0 = pipeline completed and review_decision.json's status is PASS.
+Exit code 2 = pipeline halted on an auto-stop flag before quality checks ran
+              (this is not a failure of the script -- it is the auto-stop
+              rule working correctly). A BLOCKED review_decision.json is
+              still generated.
+Exit code 3 = pipeline completed but review_decision.json's status is FAIL
+              (at least one quality check failed).
 Exit code 1 = task_meta.json was invalid.
+
+Exit codes 0/2/3 are intended to be directly consumable by a CI step (e.g.
+GitHub Actions `run:` step exit status) without parsing any output.
 """
 import argparse
 import json
@@ -69,9 +86,11 @@ def main():
         data = json.load(f)
 
     if data.get("should_stop"):
+        run_script("generate_decision_package.py", [])
         print("=" * 60)
         print(f"AUTO-STOP: {', '.join(data['flags'])}")
-        print("Pipeline halted before generating the review package or next-task draft.")
+        print("Pipeline halted before running quality checks or the freeform next-task draft.")
+        print("A BLOCKED review_decision.json was still generated -- see automation/review/.")
         print("Human review required. See automation/reports/latest_report.md.")
         print("=" * 60)
         return 2
@@ -82,16 +101,22 @@ def main():
     if args.root:
         review_args += ["--root", args.root]
     run_script("generate_review_package.py", review_args)
+    run_script("generate_decision_package.py", [])
     run_script("generate_next_task.py", [])
 
+    with (AUTOMATION_DIR / "review" / "review_decision.json").open(encoding="utf-8") as f:
+        decision = json.load(f)
+
     print("=" * 60)
     print("Pipeline complete. Nothing was auto-approved or auto-implemented.")
-    print("Next: a human (or ChatGPT PM) reviews automation/review/review_request.md,")
-    print("returns PASS / FAIL / BLOCKED, and explicitly approves")
-    print("automation/tasks/NEXT_TASK_DRAFT.md (or a rewritten version of it) before")
-    print("it becomes a real Task ID for Claude Code.")
+    print(f"Decision: status={decision['status']} risk={decision['risk']}")
+    print("Next: a human (or ChatGPT PM) reads automation/review/review_decision.json")
+    print("(or review_summary.md), returns PASS / FAIL / BLOCKED, and explicitly")
+    print("approves a next task (automation/review/next_task_draft.md or")
+    print("automation/tasks/NEXT_TASK_DRAFT.md) before it becomes a real Task ID")
+    print("for Claude Code.")
     print("=" * 60)
-    return 0
+    return 3 if decision["status"] == "FAIL" else 0
 
 
 if __name__ == "__main__":
diff --git a/automation/tasks/NEXT_TASK_DRAFT.md b/automation/tasks/NEXT_TASK_DRAFT.md
index 53007ac..05aeab0 100644
--- a/automation/tasks/NEXT_TASK_DRAFT.md
+++ b/automation/tasks/NEXT_TASK_DRAFT.md
@@ -1,15 +1,15 @@
 # Next Task Draft
 
-- **Generated:** 2026-07-25T06:19:09+00:00
+- **Generated:** 2026-07-25T06:41:07+00:00
 - **Status:** DRAFT — not an approved Task ID. Requires explicit human
   approval before Claude Code acts on this. Nothing in this automation
   layer executes this file automatically.
 
-## From previous task: PM-AUTO-02
+## From previous task: PM-AUTO-03-EXAMPLE-FAIL
 
 **Suggested next task (as written in the previous completion report):**
 
-PM-AUTO-03: wire the automation into the actual Claude Code <-> ChatGPT PM handoff for a real upcoming task (e.g. the next Gate 1 item), replacing the manual copy-paste flow for the first time on a live task rather than a validation run.
+This suggestion is intentionally ignored -- on FAIL, next_task always becomes REWORK-<task_id>, not this text.
 
 **Previous task's remaining blockers (for context):**
