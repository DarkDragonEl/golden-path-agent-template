"""Census and lint for build-journal vocabulary leaking into the blueprint.

The blueprint (this repository) is meant to read as a clean, self-contained,
publishable artifact. Its build journal -- decision numbers, phase/STOP
narrative, worktree/session vocabulary -- belongs in the separate
`agent-roadmap` history repository, not here. This script has two jobs:

1. Census: count how many places each journal-vocabulary pattern appears,
   per top-level path and per file, so a move/rewrite plan can be sized
   against real numbers instead of estimates.
2. Lint: fail (non-zero exit) on any occurrence that isn't on an explicit,
   dated, rationale-carrying allowlist -- the same convention already used
   by tools/check_config_contract.py's KNOWN_SECRET_SHADOWED/KNOWN_PLACEHOLDERS
   and eval/cli.py's KNOWN_GAP_TOLERANCES. Both allowlists below start empty:
   every current occurrence is an unreviewed finding, and that is the
   correct state before anything has been triaged.

Scope: this repository only (tools/journal_census.py never looks above its
own repo root). The sibling workspace root that contains this repo is a
separate, non-git scratch area with its own one-time classification pass --
not a recurring lint target, and never will be, since this script becomes a
CI gate that runs inside this repo's own pipeline with no checkout of
anything above it.

File discovery is git-aware (`git ls-files --cached --others
--exclude-standard`), not a filesystem walk: gitignored runtime artifacts
(eval run logs, secrets, caches) are never source or doc content anyone
would edit or move, and a raw walk would count them anyway, wildly
inflating the numbers this script exists to make trustworthy. Two
directories are hard-excluded regardless: `.claude/worktrees/` (live git
worktrees -- full checkouts of this same repo at other branches; counting
their contents would multiply every number by the worktree count) and
`.git/` (never tracked content in the first place, excluded defensively).

Usage: `python tools/journal_census.py [--format table|json] [--output PATH]`.
Exit 1 with every unallowed finding printed on any occurrence not covered
by ALLOWLIST_PATHS/ALLOWLIST_PREFIXES; exit 0 otherwise.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parent.parent
SELF_PATH = "tools/journal_census.py"

HARD_EXCLUDE_PREFIXES = (".claude/worktrees/", ".git/")

# Pattern name -> compiled regex. "OI" is a keep-list (legitimate Annex-A
# open-item requirement IDs, e.g. OI-02/OI-03/OI-04 -- these belong in
# blueprint content and are never a finding); every other pattern is
# journal/session vocabulary that should not appear in the blueprint.
PATTERNS = {
    "DEC": re.compile(r"DEC-\d{3}"),
    "OI": re.compile(r"OI-\d{2}"),
    "PHASE": re.compile(r"Phase [A-H]\d?[a-z]?\b"),
    "STOP": re.compile(r"STOP \d"),
    "HANDOFF": re.compile(r"HANDOFF"),
    "WORKTREE": re.compile(r"worktree", re.IGNORECASE),
    "COORD_SESSION": re.compile(r"coordinating session"),
    "WAVE": re.compile(r"Wave [βγ]"),
    "CHECKPOINT": re.compile(r"Checkpoint (?:[A-Z]\d?[a-z]?|\d+)\b"),
    "MISSION": re.compile(r"MISSION_(UNATTENDED|PHASE)"),
    "STAGE": re.compile(r"Stage [1-4]\b"),
}

KEEP_LIST_PATTERNS = {"OI"}

# --- Allowlists ----------------------------------------------------------
# Exact (relative path, pattern name) -> dated reason. Populated by later
# stages (e.g. I7) as specific occurrences are reviewed and accepted.
ALLOWLIST_PATHS: dict[tuple[str, str], str] = {
    ("eval/reporter.py", "WORKTREE"): (
        "'worktree' here means a git worktree's clean/dirty state, the "
        "input to _default_build_reference's commit-hash-vs-'local-dev-"
        "uncommitted' choice -- a real, shipped build-reference mechanism "
        "in this code, not build-session narrative about how this repo "
        "itself was developed. -- I3, 2026-08-28."
    ),
    ("skeleton/eval/reporter.py", "WORKTREE"): (
        "Same git-worktree-state meaning as the main-tree eval/reporter.py "
        "entry above -- this file is its skeleton counterpart. -- I4, "
        "2026-08-28."
    ),
}

# (path prefix, pattern name) -> dated reason.
ALLOWLIST_PREFIXES: dict[tuple[str, str], str] = {
    ("docs/adr/", "DEC"): (
        "Each ADR's own \"## Journal\" line cites the DEC-NNN entry (or "
        "entries) in agent-roadmap/DECISIONS.md it distills -- expected, "
        "not journal leakage: this is the one place in the blueprint an "
        "ADR is supposed to point back at its source decision. -- I2, "
        "2026-08-28."
    ),
}


def discover_files(root: Path) -> list[str]:
    """Tracked + untracked-but-not-gitignored files, as repo-relative
    posix paths. Deliberately not `--others` alone or a filesystem walk --
    tracked files must be included even if a later .gitignore change would
    otherwise hide them, and untracked-but-real content (e.g. a report
    drafted but not yet committed) must still be counted."""
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True, text=True, check=True,
    )
    out = []
    for rel in result.stdout.splitlines():
        if rel == SELF_PATH:
            continue
        if any(rel.startswith(p) for p in HARD_EXCLUDE_PREFIXES):
            continue
        out.append(rel)
    return sorted(out)


def bucket_for(rel_path: str) -> str:
    """Top-level-path bucket for the census table. A root-level file is
    its own bucket (e.g. "DECISIONS.md"); a directory buckets by its first
    path segment (e.g. "skeleton/"), except docs/adr/ is broken out from
    the rest of docs/ -- that split is exactly where I3's allowlist prefix
    will matter once docs/adr/ exists, so it's cheap to report separately
    from the start rather than retrofit later."""
    parts = rel_path.split("/")
    if len(parts) == 1:
        return parts[0]
    if parts[0] == "docs" and len(parts) > 1 and parts[1] == "adr":
        return "docs/adr/"
    return parts[0] + "/"


def is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return b"\x00" in f.read(8192)
    except OSError:
        return True


def scan(root: Path, files: list[str]) -> dict:
    """Returns {rel_path: {pattern_name: [line_no, ...]}} for every file
    with at least one hit."""
    hits: dict[str, dict[str, list[int]]] = {}
    for rel in files:
        path = root / rel
        if not path.is_file() or is_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        file_hits: dict[str, list[int]] = {}
        for name, pattern in PATTERNS.items():
            lines = [text.count("\n", 0, m.start()) + 1 for m in pattern.finditer(text)]
            if lines:
                file_hits[name] = lines
        if file_hits:
            hits[rel] = file_hits
    return hits


def is_allowed(rel_path: str, pattern_name: str) -> bool:
    if (rel_path, pattern_name) in ALLOWLIST_PATHS:
        return True
    return any(
        rel_path.startswith(prefix) and pattern_name == pat
        for (prefix, pat) in ALLOWLIST_PREFIXES
    )


def build_report(root: Path) -> dict:
    files = discover_files(root)
    hits = scan(root, files)

    files_scanned_by_bucket: dict[str, int] = {}
    for rel in files:
        b = bucket_for(rel)
        files_scanned_by_bucket[b] = files_scanned_by_bucket.get(b, 0) + 1

    per_bucket: dict[str, dict[str, int]] = {}
    per_file: dict[str, dict[str, int]] = {}
    findings = []
    keep_list_total = 0

    for rel, file_hits in hits.items():
        b = bucket_for(rel)
        per_bucket.setdefault(b, {})
        per_file[rel] = {}
        for pattern_name, lines in file_hits.items():
            count = len(lines)
            per_file[rel][pattern_name] = count
            per_bucket[b][pattern_name] = per_bucket[b].get(pattern_name, 0) + count
            if pattern_name in KEEP_LIST_PATTERNS:
                keep_list_total += count
                continue
            if not is_allowed(rel, pattern_name):
                findings.append({
                    "path": rel, "pattern": pattern_name, "count": count,
                    "lines": lines,
                })

    return {
        "files_scanned_total": len(files),
        "files_scanned_by_bucket": files_scanned_by_bucket,
        "per_bucket": per_bucket,
        "per_file": per_file,
        "keep_list_total": keep_list_total,
        "findings": sorted(findings, key=lambda f: (-f["count"], f["path"], f["pattern"])),
    }


def render_table(report: dict) -> str:
    lines = []
    lines.append(f"Files scanned: {report['files_scanned_total']}")
    lines.append("")
    lines.append("Per-bucket counts (non-OI patterns; OI reported separately):")
    for bucket in sorted(report["per_bucket"]):
        counts = report["per_bucket"][bucket]
        non_oi = {k: v for k, v in counts.items() if k not in KEEP_LIST_PATTERNS}
        if not non_oi:
            continue
        total = sum(non_oi.values())
        scanned = report["files_scanned_by_bucket"].get(bucket, 0)
        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(non_oi.items(), key=lambda kv: -kv[1]))
        lines.append(f"  {bucket:<40} files_scanned={scanned:<5} total={total:<6} {breakdown}")
    lines.append("")
    lines.append(f"OI-\\d{{2}} keep-list occurrences (never a finding): {report['keep_list_total']}")
    lines.append("")
    lines.append("Per-file findings (non-OI, sorted by count desc):")
    for f in report["findings"]:
        lines.append(f"  {f['path']:<60} {f['pattern']:<14} count={f['count']}")
    lines.append("")
    lines.append(f"Total unallowed findings: {len(report['findings'])} across "
                  f"{len({f['path'] for f in report['findings']})} files")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["table", "json"], default="table")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    report = build_report(REPO_ROOT)
    rendered = json.dumps(report, indent=2) if args.format == "json" else render_table(report)

    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n")

    if report["findings"]:
        print(f"\n{len(report['findings'])} unallowed journal-signal finding(s). "
              f"See ALLOWLIST_PATHS/ALLOWLIST_PREFIXES in tools/journal_census.py.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
