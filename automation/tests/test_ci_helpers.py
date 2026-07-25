#!/usr/bin/env python3
"""Unit tests for the PM-AUTO-04 CI helper scripts.

stdlib-only (unittest), matching the rest of automation/'s no-new-
dependency convention. These test the Python logic that
pm-pipeline.yml calls into -- they do not require GitHub Actions and
can (and should) be run locally:

    python3 -m unittest discover -s automation/tests -v

The workflow YAML's structure is checked separately in
TestWorkflowYamlShape, using PyYAML if available (a dev-time-only
dependency for this test, never a runtime dependency of the workflow
itself) and skipped if it isn't installed.
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

AUTOMATION_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = AUTOMATION_DIR.parent


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validate_ci_inputs = _load_module("validate_ci_inputs", AUTOMATION_DIR / "validate_ci_inputs.py")
ci_summary = _load_module("ci_summary", AUTOMATION_DIR / "ci_summary.py")


class TestPathValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name).resolve()
        (self.workspace / "automation" / "reports").mkdir(parents=True)
        (self.workspace / "automation" / "reports" / "task_meta.json").write_text("{}")
        (self.workspace / "other_repo").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_relative_paths_resolve_inside_workspace(self):
        task_meta, root = validate_ci_inputs.validate(
            str(self.workspace), "automation/reports/task_meta.json", "."
        )
        self.assertEqual(task_meta, self.workspace / "automation" / "reports" / "task_meta.json")
        self.assertEqual(root, self.workspace)

    def test_valid_subdirectory_target_root(self):
        _, root = validate_ci_inputs.validate(
            str(self.workspace), "automation/reports/task_meta.json", "other_repo"
        )
        self.assertEqual(root, self.workspace / "other_repo")

    def test_rejects_dotdot_traversal_out_of_workspace(self):
        with self.assertRaises(ValueError) as ctx:
            validate_ci_inputs.validate(
                str(self.workspace), "automation/reports/task_meta.json", "../../../etc"
            )
        self.assertIn("outside the workspace", str(ctx.exception))

    def test_rejects_absolute_path_outside_workspace(self):
        with self.assertRaises(ValueError) as ctx:
            validate_ci_inputs.validate(str(self.workspace), "automation/reports/task_meta.json", "/etc")
        self.assertIn("outside the workspace", str(ctx.exception))

    def test_rejects_nonexistent_task_meta_file(self):
        with self.assertRaises(ValueError) as ctx:
            validate_ci_inputs.validate(str(self.workspace), "does/not/exist.json", ".")
        self.assertIn("not a file", str(ctx.exception))

    def test_rejects_nonexistent_target_root_directory(self):
        with self.assertRaises(ValueError) as ctx:
            validate_ci_inputs.validate(
                str(self.workspace), "automation/reports/task_meta.json", "no_such_dir"
            )
        self.assertIn("not a directory", str(ctx.exception))

    def test_rejects_empty_input(self):
        with self.assertRaises(ValueError):
            validate_ci_inputs.validate(str(self.workspace), "", ".")

    def test_target_root_that_is_a_file_not_a_directory_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            validate_ci_inputs.validate(
                str(self.workspace), "automation/reports/task_meta.json",
                "automation/reports/task_meta.json",
            )
        self.assertIn("not a directory", str(ctx.exception))


class TestExitCodeClassification(unittest.TestCase):
    def test_exit_0_matching_pass_decision_is_pass(self):
        status, reason = ci_summary.classify(0, {"status": "PASS"})
        self.assertEqual(status, "PASS")

    def test_exit_2_matching_blocked_decision_is_blocked(self):
        status, _ = ci_summary.classify(2, {"status": "BLOCKED"})
        self.assertEqual(status, "BLOCKED")

    def test_exit_3_matching_fail_decision_is_fail(self):
        status, _ = ci_summary.classify(3, {"status": "FAIL"})
        self.assertEqual(status, "FAIL")

    def test_exit_1_is_always_error_regardless_of_decision(self):
        status, reason = ci_summary.classify(1, {"status": "PASS"})
        self.assertEqual(status, "ERROR")
        self.assertIn("not one of 0", reason)

    def test_unknown_exit_code_is_error(self):
        status, _ = ci_summary.classify(42, None)
        self.assertEqual(status, "ERROR")

    def test_missing_decision_with_pass_exit_code_is_error_not_pass(self):
        """No fabricated success: exit 0 alone is not enough to claim PASS."""
        status, reason = ci_summary.classify(0, None)
        self.assertEqual(status, "ERROR")
        self.assertIn("could not be read", reason)

    def test_exit_code_decision_mismatch_is_error(self):
        """Exit code says PASS but the decision file disagrees -- must not
        silently resolve in either direction."""
        status, reason = ci_summary.classify(0, {"status": "FAIL"})
        self.assertEqual(status, "ERROR")
        self.assertIn("anomaly", reason)


class TestLoadJsonSafe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_reports_not_found_not_empty_dict(self):
        data, err = ci_summary.load_json_safe(self.dir / "does_not_exist.json")
        self.assertIsNone(data)
        self.assertIn("not found", err)

    def test_malformed_json_reports_error_not_partial_data(self):
        bad = self.dir / "malformed.json"
        bad.write_text("{not valid json,,,")
        data, err = ci_summary.load_json_safe(bad)
        self.assertIsNone(data)
        self.assertIn("invalid JSON", err)

    def test_valid_json_loads(self):
        good = self.dir / "good.json"
        good.write_text(json.dumps({"status": "PASS"}))
        data, err = ci_summary.load_json_safe(good)
        self.assertEqual(data, {"status": "PASS"})
        self.assertIsNone(err)

    def test_none_path_reports_not_provided(self):
        data, err = ci_summary.load_json_safe(None)
        self.assertIsNone(data)
        self.assertEqual(err, "not provided")


class TestSummaryGeneration(unittest.TestCase):
    def test_pass_summary_mentions_pass_and_no_warning(self):
        decision = {
            "task_id": "T-1", "status": "PASS", "risk": "LOW", "blocked": False,
            "next_task": "T-2", "requires_human_approval": True, "reason": "ok",
        }
        summary = ci_summary.build_summary("PASS", 0, decision, None, None, "not provided", None)
        self.assertIn("PASS", summary)
        self.assertIn("T-1", summary)
        self.assertNotIn("must not be treated as a passing result", summary)

    def test_blocked_summary_carries_warning_and_next_task_none(self):
        decision = {
            "task_id": "T-1", "status": "BLOCKED", "risk": "HIGH", "blocked": True,
            "next_task": None, "requires_human_approval": True, "reason": "flag present",
        }
        summary = ci_summary.build_summary("BLOCKED", 2, decision, None, None, "not provided", None)
        self.assertIn("BLOCKED", summary)
        self.assertIn("must not be treated as a passing result", summary)

    def test_fail_summary_shows_failing_checks(self):
        decision = {
            "task_id": "T-1", "status": "FAIL", "risk": "MEDIUM", "blocked": False,
            "next_task": "REWORK-T-1", "requires_human_approval": True, "reason": "1 check failed",
        }
        quality = {"n_pass": 5, "n_fail": 1, "n_skip": 0, "checks": [{"name": "Ruff check", "status": "FAIL"}]}
        summary = ci_summary.build_summary("FAIL", 3, decision, None, quality, None, None)
        self.assertIn("REWORK-T-1", summary)
        self.assertIn("Ruff check", summary)

    def test_error_summary_reports_missing_decision_explicitly(self):
        summary = ci_summary.build_summary(
            "ERROR", 1, None, "file not found: review_decision.json", None, "not provided", None
        )
        self.assertIn("ERROR", summary)
        self.assertIn("unavailable", summary)

    def test_never_renders_next_task_draft_file_contents(self):
        """build_summary() takes no next_task_draft.md file path/content
        argument at all -- it can only ever reference the artifact by the
        `next_task` ID string from review_decision.json, never by reading
        and embedding the draft file's own markdown body."""
        import inspect
        params = inspect.signature(ci_summary.build_summary).parameters
        self.assertNotIn("next_task_draft", " ".join(params).lower())
        self.assertNotIn("draft_path", " ".join(params).lower())


class TestMainSuppressesStaleDataOnError(unittest.TestCase):
    """Regression test: if validate_ci_inputs.py fails before the pipeline
    runs, review_decision.json / latest_report.json / quality_checks.json
    on disk are leftovers from a previous, unrelated run (in real CI, they
    could even be stale files already committed to the repo). main() must
    not display their fields as if they describe the current ERROR run."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        stale_decision = {
            "task_id": "STALE-PREVIOUS-TASK", "status": "FAIL", "risk": "HIGH",
            "blocked": False, "next_task": "REWORK-STALE-PREVIOUS-TASK",
            "requires_human_approval": True, "reason": "stale reason from a prior run",
        }
        (self.dir / "decision.json").write_text(json.dumps(stale_decision))
        (self.dir / "report.json").write_text(json.dumps({"task_id": "STALE-PREVIOUS-TASK"}))
        self.summary_out = self.dir / "summary.md"
        self.github_output = self.dir / "gh_output.txt"

    def tearDown(self):
        self.tmp.cleanup()

    def _run_main_with_exit_code_1(self):
        argv = [
            "ci_summary.py", "--exit-code", "1",
            "--decision-path", str(self.dir / "decision.json"),
            "--report-path", str(self.dir / "report.json"),
            "--summary-out", str(self.summary_out),
            "--github-output", str(self.github_output),
        ]
        old_argv = sys.argv
        sys.argv = argv
        try:
            ci_summary.main()
        finally:
            sys.argv = old_argv

    def test_stale_task_id_and_reason_do_not_appear_in_summary(self):
        self._run_main_with_exit_code_1()
        summary_text = self.summary_out.read_text()
        self.assertIn("ERROR", summary_text)
        self.assertNotIn("STALE-PREVIOUS-TASK", summary_text)
        self.assertNotIn("stale reason from a prior run", summary_text)

    def test_stale_next_task_is_not_emitted_as_github_output(self):
        self._run_main_with_exit_code_1()
        output_text = self.github_output.read_text()
        self.assertIn("status=ERROR", output_text)
        self.assertNotIn("REWORK-STALE-PREVIOUS-TASK", output_text)
        self.assertIn("next_task=\n", output_text)


class TestWorkflowYamlShape(unittest.TestCase):
    """Static assertions on .github/workflows/pm-pipeline.yml -- checks the
    workflow's *shape* (triggers, permissions, always()-gated steps) without
    actually running it. This is the local, dependency-light substitute for
    exercising real GitHub Actions runtime behavior, which this test suite
    cannot do."""

    @classmethod
    def setUpClass(cls):
        cls.path = REPO_ROOT / ".github" / "workflows" / "pm-pipeline.yml"
        cls.text = cls.path.read_text(encoding="utf-8")
        try:
            import yaml
            cls.parsed = yaml.safe_load(cls.text)
        except ImportError:
            cls.parsed = None

    def test_workflow_file_exists(self):
        self.assertTrue(self.path.exists())

    def test_parses_as_valid_yaml(self):
        if self.parsed is None:
            self.skipTest("PyYAML not installed -- skipping YAML parse check")
        self.assertIsInstance(self.parsed, dict)

    def test_only_workflow_dispatch_trigger(self):
        if self.parsed is None:
            self.skipTest("PyYAML not installed")
        # YAML parses the bare key `on` as boolean True in PyYAML 5.x/6.x
        # depending on version quirks -- handle both `on` and True as the key.
        triggers = self.parsed.get("on", self.parsed.get(True))
        self.assertIn("workflow_dispatch", triggers)
        self.assertNotIn("push", triggers)
        self.assertNotIn("pull_request", triggers)

    def test_declares_required_inputs(self):
        if self.parsed is None:
            self.skipTest("PyYAML not installed")
        triggers = self.parsed.get("on", self.parsed.get(True))
        inputs = triggers["workflow_dispatch"]["inputs"]
        for name in ("task_meta_path", "target_root", "artifact_retention_days"):
            self.assertIn(name, inputs)

    def test_least_privilege_permissions(self):
        if self.parsed is None:
            self.skipTest("PyYAML not installed")
        self.assertEqual(self.parsed.get("permissions"), {"contents": "read"})

    def test_upload_step_runs_always(self):
        self.assertIn("Upload PM pipeline artifacts", self.text)
        upload_block = self.text.split("Upload PM pipeline artifacts", 1)[1][:400]
        self.assertIn("if: always()", upload_block)

    def test_summary_step_runs_always(self):
        self.assertIn("Build CI summary", self.text)
        summary_block = self.text.split("Build CI summary", 1)[1][:400]
        self.assertIn("if: always()", summary_block)

    def test_gate_step_runs_always(self):
        self.assertIn("Enforce PASS-only success", self.text)
        gate_block = self.text.split("Enforce PASS-only success", 1)[1][:400]
        self.assertIn("if: always()", gate_block)

    def test_no_broad_artifact_globs(self):
        """Artifact `path:` must be an explicit list of known filenames --
        never a directory wildcard that could pick up unrelated files."""
        self.assertNotIn("automation/**", self.text)
        self.assertNotIn("automation/*\n", self.text)

    def test_pins_actions_to_major_versions(self):
        for action in ("actions/checkout@v", "actions/setup-python@v", "actions/upload-artifact@v"):
            self.assertIn(action, self.text)

    def test_does_not_execute_next_task_draft(self):
        # The file is only ever referenced by path (for upload), never
        # piped into a shell, python -c, or similar execution.
        for bad_pattern in ("cat automation/review/next_task_draft.md |", "python3 automation/review/next_task_draft.md"):
            self.assertNotIn(bad_pattern, self.text)


if __name__ == "__main__":
    unittest.main()
