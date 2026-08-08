#!/usr/bin/env python3
"""Validate and resolve CI-supplied path inputs before the PM pipeline runs.

`task_meta_path` and `target_root` are workflow_dispatch free-text fields
and must never be trusted directly: this resolves each against a given
workspace root and rejects anything that escapes it (`..` traversal, an
absolute path outside the workspace), then confirms the resolved path
exists as the expected type (a file for task_meta_path, a directory for
target_root) before anything downstream uses it. This never executes,
sources, or evaluates the input -- it is only ever used as a literal path
argument.

Usage:
    python3 automation/validate_ci_inputs.py \
        --workspace /path/to/checkout \
        --task-meta-path automation/reports/task_meta.json \
        --target-root . \
        [--github-output /path/to/GITHUB_OUTPUT]

Exit code 0: both inputs are valid. Resolved absolute paths are printed
             and, if --github-output is given, appended to that file as
             `task_meta_path=...` / `target_root=...`.
Exit code 1: at least one input is invalid. Reason printed to stderr.
"""
import argparse
import sys
from pathlib import Path


def resolve_within(workspace: Path, raw: str, label: str) -> Path:
    """Resolve `raw` against `workspace` and reject any result that isn't
    actually inside it. `workspace` must already be an absolute, resolved
    path."""
    if raw is None or not raw.strip():
        raise ValueError(f"{label} must not be empty")

    candidate = Path(raw)
    candidate = candidate.resolve() if candidate.is_absolute() else (workspace / candidate).resolve()

    try:
        candidate.relative_to(workspace)
    except ValueError:
        raise ValueError(
            f"{label}={raw!r} resolves to {candidate}, which is outside the "
            f"workspace ({workspace}) -- rejected"
        )
    return candidate


def validate(workspace_raw: str, task_meta_path_raw: str, target_root_raw: str) -> tuple[Path, Path]:
    """Returns (task_meta_path, target_root) as resolved, verified paths,
    or raises ValueError with a human-readable reason."""
    workspace = Path(workspace_raw).resolve()
    if not workspace.is_dir():
        raise ValueError(f"--workspace {workspace} is not a directory")

    task_meta_path = resolve_within(workspace, task_meta_path_raw, "task_meta_path")
    target_root = resolve_within(workspace, target_root_raw, "target_root")

    if not task_meta_path.is_file():
        raise ValueError(f"task_meta_path resolved to {task_meta_path}, which is not a file")
    if not target_root.is_dir():
        raise ValueError(f"target_root resolved to {target_root}, which is not a directory")

    return task_meta_path, target_root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--task-meta-path", required=True)
    parser.add_argument("--target-root", required=True)
    parser.add_argument("--github-output", default=None)
    args = parser.parse_args()

    try:
        task_meta_path, target_root = validate(args.workspace, args.task_meta_path, args.target_root)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"task_meta_path -> {task_meta_path}")
    print(f"target_root -> {target_root}")

    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as f:
            f.write(f"task_meta_path={task_meta_path}\n")
            f.write(f"target_root={target_root}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
