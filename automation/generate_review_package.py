#!/usr/bin/env python3
"""Collect review material into automation/review/.

Gathers, best-effort:
    - git diff (uncommitted, and against the merge-base with the default
      remote branch if one is configured)
    - modified file list
    - pytest output (only if pytest is installed AND a pytest config
      exists in the repo -- never installs anything)
    - mypy output (same condition, for mypy config)
    - ruff output (same condition, for ruff config)
    - build output (npm run build, only if package.json defines one)
    - coverage summary (only if pytest-cov produced one)
    - screenshots (lists anything already present in
      automation/review/screenshots/ -- never generates images itself)

Every tool that isn't configured/available is reported as "not configured
in this repo" rather than silently omitted, so the review package is
honest about what wasn't checked, not just what was.

Usage:
    python3 automation/generate_review_package.py [--base <branch>]
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

AUTOMATION_DIR = Path(__file__).resolve().parent
ROOT = AUTOMATION_DIR.parent
REVIEW_DIR = AUTOMATION_DIR / "review"


def run(cmd, timeout=120):
    try:
        out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        combined = (out.stdout or "") + (out.stderr or "")
        return out.returncode, combined.strip()
    except FileNotFoundError:
        return None, "(tool not installed)"
    except Exception as e:  # pragma: no cover
        return None, f"(command failed: {e})"


def section(title, body):
    return f"## {title}\n\n```\n{body}\n```\n" if body.strip() else f"## {title}\n\n_(no output)_\n"


def get_git_diff(base: str | None) -> str:
    parts = []
    parts.append("### Uncommitted changes\n")
    rc, out = run(["git", "diff"])
    parts.append(out or "(none)")
    if base:
        parts.append(f"\n### Diff against merge-base with `{base}`\n")
        rc, merge_base = run(["git", "merge-base", "HEAD", base])
        if rc == 0 and merge_base:
            rc2, out2 = run(["git", "diff", f"{merge_base}...HEAD"])
            parts.append(out2 or "(no differences)")
        else:
            parts.append(f"(could not resolve merge-base with {base!r}: {merge_base})")
    return "\n".join(parts)


def get_modified_files() -> str:
    rc, out = run(["git", "status", "--short"])
    return out or "(clean working tree)"


def tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def run_pytest() -> str:
    config_present = any((ROOT / f).exists() for f in ("pytest.ini", "pyproject.toml", "setup.cfg"))
    if not tool_available("pytest"):
        return "pytest not installed in this environment -- skipped."
    if not config_present:
        return "No pytest config found in this repo (pytest.ini/pyproject.toml/setup.cfg) -- skipped."
    rc, out = run(["pytest", "-q"])
    return out or "(pytest produced no output)"


def run_mypy() -> str:
    if not tool_available("mypy"):
        return "mypy not installed in this environment -- skipped."
    config_present = any((ROOT / f).exists() for f in ("mypy.ini", "pyproject.toml", "setup.cfg"))
    if not config_present:
        return "No mypy config found in this repo -- skipped."
    rc, out = run(["mypy", "."])
    return out or "(mypy produced no output)"


def run_ruff() -> str:
    if not tool_available("ruff"):
        return "ruff not installed in this environment -- skipped."
    config_present = any((ROOT / f).exists() for f in ("ruff.toml", "pyproject.toml", ".ruff.toml"))
    if not config_present:
        return "No ruff config found in this repo -- skipped."
    rc, out = run(["ruff", "check", "."])
    return out or "(ruff produced no output)"


def run_build() -> str:
    pkg = ROOT / "package.json"
    if not pkg.exists():
        return "No package.json in this repo -- skipped."
    import json
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except Exception as e:
        return f"Could not parse package.json: {e}"
    if "build" not in (data.get("scripts") or {}):
        return "package.json has no 'build' script -- skipped."
    if not tool_available("npm"):
        return "npm not installed in this environment -- skipped."
    rc, out = run(["npm", "run", "build"], timeout=300)
    return out or "(build produced no output)"


def run_coverage() -> str:
    cov_file = ROOT / ".coverage"
    if not cov_file.exists():
        return "No .coverage file found (run pytest with --cov to produce one) -- skipped."
    if not tool_available("coverage"):
        return "coverage tool not installed -- skipped."
    rc, out = run(["coverage", "report"])
    return out or "(coverage produced no output)"


def list_screenshots() -> str:
    shots_dir = REVIEW_DIR / "screenshots"
    if not shots_dir.exists():
        return "No automation/review/screenshots/ directory -- none collected."
    files = sorted(p.name for p in shots_dir.iterdir() if p.is_file())
    if not files:
        return "automation/review/screenshots/ exists but is empty."
    return "\n".join(f"- {f}" for f in files)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=None, help="Branch to diff against (e.g. origin/main). Optional.")
    args = parser.parse_args()

    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    git_diff = get_git_diff(args.base)
    (REVIEW_DIR.parent / "reports" / "git_diff.md").write_text(
        f"# Git diff\n\n{git_diff}\n", encoding="utf-8"
    )

    test_results = "\n\n".join([
        section("pytest", run_pytest()),
        section("mypy", run_mypy()),
        section("ruff", run_ruff()),
    ])
    (REVIEW_DIR.parent / "reports" / "test_results.md").write_text(
        f"# Test results\n\n{test_results}\n", encoding="utf-8"
    )

    review_md = "\n".join([
        "# Review Package",
        "",
        "## Modified files",
        f"```\n{get_modified_files()}\n```",
        "",
        section("Build output", run_build()),
        section("Coverage", run_coverage()),
        "## Screenshots",
        "",
        list_screenshots(),
        "",
        "## See also",
        "- `automation/reports/git_diff.md` -- full diff",
        "- `automation/reports/test_results.md` -- pytest/mypy/ruff output",
        "- `automation/reports/latest_report.md` -- narrative completion report",
    ])
    (REVIEW_DIR / "review_request.md").write_text(review_md, encoding="utf-8")

    print(f"Wrote {REVIEW_DIR / 'review_request.md'}")
    print(f"Wrote {REVIEW_DIR.parent / 'reports' / 'git_diff.md'}")
    print(f"Wrote {REVIEW_DIR.parent / 'reports' / 'test_results.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
