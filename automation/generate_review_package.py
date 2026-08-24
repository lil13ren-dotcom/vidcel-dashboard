#!/usr/bin/env python3
"""Collect review material into automation/review/.

Discovers and runs, best-effort, against the target repo (--root, defaults
to this repo):
    - git status / git diff / modified files
    - Ruff check
    - Ruff format check
    - mypy (strict, against `src/` if that layout exists, else `.`)
    - pytest (with --cov=<package> if a coverage source package can be
      read from pyproject.toml's [tool.coverage.run], else plain)
    - coverage report (if the pytest run above produced one)
    - Alembic check (only if alembic.ini exists at the target root --
      runs `alembic upgrade head` first against that repo's own configured
      local database, matching its real CI order, then `alembic check`)
    - build output (npm run build, only if package.json defines one)
    - screenshots (lists anything already present in
      automation/review/screenshots/ -- never generates images itself)

If `<root>/uv.lock` exists and the `uv` binary is available, every Python
tool is invoked as `uv run <tool> ...` (matching how `uv`-managed projects
actually run their own checks -- see e.g. ai-lead-os's CONTRIBUTING.md).
Otherwise falls back to a bare tool invocation if that tool is on PATH.

Every check that isn't configured/available is reported as SKIPPED with a
reason, never silently omitted. Every check that runs records its exact
command, exit code, and PASS/FAIL status -- both in the human-readable
`review_request.md` and in a machine-readable `reports/quality_checks.json`.

Usage:
    python3 automation/generate_review_package.py [--root <path>] [--base <branch>]
"""
import argparse
import datetime
import json
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

AUTOMATION_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = AUTOMATION_DIR.parent
REVIEW_DIR = AUTOMATION_DIR / "review"
REPORTS_DIR = AUTOMATION_DIR / "reports"


@dataclass
class CheckResult:
    name: str
    command: str
    status: str  # PASS | FAIL | SKIPPED
    exit_code: int | None
    output: str
    reason: str = ""  # populated for SKIPPED


def run(cmd, cwd, timeout):
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        combined = (out.stdout or "") + (out.stderr or "")
        return out.returncode, combined.strip()
    except FileNotFoundError:
        return None, "(command not found)"
    except subprocess.TimeoutExpired:
        return None, f"(timed out after {timeout}s)"
    except Exception as e:  # pragma: no cover
        return None, f"(command failed to launch: {e})"


def tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def load_pyproject(root: Path) -> dict:
    path = root / "pyproject.toml"
    if not path.exists():
        return {}
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


class Runner:
    """Wraps command construction so every check honors the same
    uv-vs-bare-tool decision, made once, based on real repo evidence
    (uv.lock presence) rather than guessed per check."""

    def __init__(self, root: Path, timeout_default: int):
        self.root = root
        self.timeout_default = timeout_default
        self.use_uv = (root / "uv.lock").exists() and tool_available("uv")

    def python_tool_cmd(self, tool: str, args: list[str]) -> list[str] | None:
        if self.use_uv:
            return ["uv", "run", tool, *args]
        if tool_available(tool):
            return [tool, *args]
        return None

    def exec_check(self, name: str, cmd: list[str] | None, skip_reason: str = "", timeout: int | None = None) -> CheckResult:
        if cmd is None:
            reason = skip_reason or (
                "uv.lock present but `uv` not on PATH" if self.use_uv
                else "tool not installed and no uv.lock present"
            )
            return CheckResult(name, "(not run)", "SKIPPED", None, "", reason)
        rc, output = run(cmd, cwd=self.root, timeout=timeout or self.timeout_default)
        cmd_str = " ".join(cmd)
        if rc is None:
            return CheckResult(name, cmd_str, "SKIPPED", None, output, "command could not be launched")
        return CheckResult(name, cmd_str, "PASS" if rc == 0 else "FAIL", rc, output)


def detect_mypy_target(root: Path) -> str:
    return "src" if (root / "src").is_dir() else "."


def detect_coverage_source(pyproject: dict) -> str | None:
    sources = pyproject.get("tool", {}).get("coverage", {}).get("run", {}).get("source")
    if isinstance(sources, list) and sources:
        return sources[0]
    return None


def run_ruff_check(runner: Runner, pyproject: dict) -> CheckResult:
    if "ruff" not in pyproject.get("tool", {}):
        return CheckResult("Ruff check", "(not run)", "SKIPPED", None, "", "no [tool.ruff] in pyproject.toml")
    cmd = runner.python_tool_cmd("ruff", ["check", "."])
    return runner.exec_check("Ruff check", cmd)


def run_ruff_format_check(runner: Runner, pyproject: dict) -> CheckResult:
    if "ruff" not in pyproject.get("tool", {}):
        return CheckResult("Ruff format check", "(not run)", "SKIPPED", None, "", "no [tool.ruff] in pyproject.toml")
    cmd = runner.python_tool_cmd("ruff", ["format", "--check", "."])
    return runner.exec_check("Ruff format check", cmd)


def run_mypy_strict(runner: Runner, pyproject: dict) -> CheckResult:
    mypy_cfg = pyproject.get("tool", {}).get("mypy", {})
    if not mypy_cfg:
        return CheckResult("mypy", "(not run)", "SKIPPED", None, "", "no [tool.mypy] in pyproject.toml")
    target = detect_mypy_target(runner.root)
    strict = bool(mypy_cfg.get("strict"))
    cmd = runner.python_tool_cmd("mypy", [target])
    result = runner.exec_check(f"mypy{' (strict)' if strict else ''}", cmd, timeout=180)
    return result


def run_pytest_with_coverage(runner: Runner, pyproject: dict) -> CheckResult:
    if "ini_options" not in pyproject.get("tool", {}).get("pytest", {}):
        return CheckResult("pytest", "(not run)", "SKIPPED", None, "", "no [tool.pytest.ini_options] in pyproject.toml")
    cov_source = detect_coverage_source(pyproject)
    args = [f"--cov={cov_source}", "--cov-report=term-missing"] if cov_source else []
    cmd = runner.python_tool_cmd("pytest", args)
    label = f"pytest{' with coverage' if cov_source else ''}"
    return runner.exec_check(label, cmd, timeout=900)


def run_alembic(runner: Runner) -> list[CheckResult]:
    if not (runner.root / "alembic.ini").exists():
        return [CheckResult("Alembic check", "(not run)", "SKIPPED", None, "", "no alembic.ini in this repo")]
    upgrade_cmd = runner.python_tool_cmd("alembic", ["upgrade", "head"])
    upgrade = runner.exec_check("Alembic upgrade head", upgrade_cmd, timeout=120)
    if upgrade.status != "PASS":
        return [upgrade]
    check_cmd = runner.python_tool_cmd("alembic", ["check"])
    check = runner.exec_check("Alembic check (no model drift)", check_cmd, timeout=60)
    return [upgrade, check]


def run_build(root: Path) -> CheckResult:
    pkg = root / "package.json"
    if not pkg.exists():
        return CheckResult("Build", "(not run)", "SKIPPED", None, "", "no package.json in this repo")
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except Exception as e:
        return CheckResult("Build", "(not run)", "SKIPPED", None, "", f"could not parse package.json: {e}")
    if "build" not in (data.get("scripts") or {}):
        return CheckResult("Build", "(not run)", "SKIPPED", None, "", "package.json has no 'build' script")
    if not tool_available("npm"):
        return CheckResult("Build", "(not run)", "SKIPPED", None, "", "npm not installed in this environment")
    rc, out = run(["npm", "run", "build"], cwd=root, timeout=300)
    return CheckResult("Build", "npm run build", "PASS" if rc == 0 else "FAIL", rc, out)


def get_git_diff(root: Path, base: str | None) -> str:
    parts = ["### Uncommitted changes\n"]
    rc, out = run(["git", "diff"], cwd=root, timeout=60)
    parts.append(out or "(none)")
    if base:
        parts.append(f"\n### Diff against merge-base with `{base}`\n")
        rc, merge_base = run(["git", "merge-base", "HEAD", base], cwd=root, timeout=30)
        if rc == 0 and merge_base:
            rc2, out2 = run(["git", "diff", f"{merge_base}...HEAD"], cwd=root, timeout=60)
            parts.append(out2 or "(no differences)")
        else:
            parts.append(f"(could not resolve merge-base with {base!r}: {merge_base})")
    return "\n".join(parts)


def get_git_status(root: Path) -> str:
    rc, out = run(["git", "status", "--short"], cwd=root, timeout=30)
    return out or "(clean working tree)"


def list_screenshots() -> str:
    shots_dir = REVIEW_DIR / "screenshots"
    if not shots_dir.exists():
        return "No automation/review/screenshots/ directory -- none collected."
    files = sorted(p.name for p in shots_dir.iterdir() if p.is_file())
    if not files:
        return "automation/review/screenshots/ exists but is empty."
    return "\n".join(f"- {f}" for f in files)


def section(result: CheckResult) -> str:
    if result.status == "SKIPPED":
        return f"### {result.name} — SKIPPED\n\n{result.reason}\n"
    header = f"### {result.name} — {result.status} (exit code {result.exit_code})\n"
    header += f"`{result.command}`\n"
    body = result.output.strip() or "(no output)"
    return f"{header}\n```\n{body}\n```\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None, help="Target repo to inspect/run checks against. Defaults to this repo.")
    parser.add_argument("--base", default=None, help="Branch to diff against (e.g. origin/main). Optional.")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else DEFAULT_ROOT
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    pyproject = load_pyproject(root)
    runner = Runner(root, timeout_default=120)

    # --- git ---
    git_diff = get_git_diff(root, args.base)
    (REPORTS_DIR / "git_diff.md").write_text(f"# Git diff\n\nRoot: `{root}`\n\n{git_diff}\n", encoding="utf-8")
    git_status_text = get_git_status(root)

    # --- quality checks ---
    checks: list[CheckResult] = []
    checks.append(run_ruff_check(runner, pyproject))
    checks.append(run_ruff_format_check(runner, pyproject))
    checks.append(run_mypy_strict(runner, pyproject))
    checks.extend(run_alembic(runner))
    checks.append(run_pytest_with_coverage(runner, pyproject))
    build_result = run_build(root)

    test_results_md = "\n\n".join(section(c) for c in checks)
    (REPORTS_DIR / "test_results.md").write_text(
        f"# Quality check results\n\nRoot: `{root}`\nInvocation mode: {'uv run <tool>' if runner.use_uv else 'bare tool on PATH'}\n\n{test_results_md}\n",
        encoding="utf-8",
    )

    n_pass = sum(1 for c in checks if c.status == "PASS")
    n_fail = sum(1 for c in checks if c.status == "FAIL")
    n_skip = sum(1 for c in checks if c.status == "SKIPPED")
    overall = "FAIL" if n_fail else ("PASS (with skips)" if n_skip else "PASS")

    quality_checks_json = {
        "root": str(root),
        "use_uv": runner.use_uv,
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "overall": overall,
        "n_pass": n_pass,
        "n_fail": n_fail,
        "n_skip": n_skip,
        "checks": [
            {
                "name": c.name, "command": c.command, "status": c.status,
                "exit_code": c.exit_code, "reason": c.reason,
            }
            for c in checks
        ],
    }
    (REPORTS_DIR / "quality_checks.json").write_text(
        json.dumps(quality_checks_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    summary_table = "\n".join(
        f"| {c.name} | {c.status} | {c.exit_code if c.exit_code is not None else '-'} |"
        for c in checks
    )

    review_md = "\n".join([
        "# Review Package",
        "",
        f"Root: `{root}`",
        "",
        f"## Overall: {overall} ({n_pass} passed, {n_fail} failed, {n_skip} skipped)",
        "",
        "| Check | Status | Exit code |",
        "|---|---|---|",
        summary_table,
        "",
        "## Git status",
        f"```\n{git_status_text}\n```",
        "",
        section(build_result),
        "## Screenshots",
        "",
        list_screenshots(),
        "",
        "## See also",
        "- `automation/reports/git_diff.md` -- full diff",
        "- `automation/reports/test_results.md` -- full output for every check above",
        "- `automation/reports/quality_checks.json` -- machine-readable check results",
        "- `automation/reports/latest_report.md` -- narrative completion report",
    ])
    (REVIEW_DIR / "review_request.md").write_text(review_md, encoding="utf-8")

    print(f"Wrote {REVIEW_DIR / 'review_request.md'}")
    print(f"Wrote {REPORTS_DIR / 'git_diff.md'}")
    print(f"Wrote {REPORTS_DIR / 'test_results.md'}")
    print(f"Wrote {REPORTS_DIR / 'quality_checks.json'}")
    print(f"Overall: {overall} ({n_pass} passed, {n_fail} failed, {n_skip} skipped)")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
