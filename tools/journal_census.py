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
   and eval/cli.py's KNOWN_GAP_TOLERANCES.

Three allowlist mechanisms, in increasing precision:
- ALLOWLIST_PATHS: an exact (relative path, pattern name) exempts the whole
  file for that pattern.
- ALLOWLIST_PREFIXES: an exact (path prefix, pattern name) exempts every
  file under that prefix for that pattern.
- LINE_EXEMPT_RULES (I5 addendum, 2026-08-30): exempts only specific,
  computed line numbers within one file for one pattern -- everywhere else
  in that same file, the pattern still counts as an unreviewed finding even
  though the file is not blanket-allowlisted. Used where a file is meant to
  carry exactly one deliberate pointer to the journal (e.g. each ADR's own
  "## Journal" citation line) and nothing else.

All three start empty or narrow: every occurrence not covered by one of them
is an unreviewed finding, and that is the correct state before anything has
been triaged.

Also lints the DEC pattern against **file names**, not just file contents --
a decision number can hide in an identifier (`dec009`, no hyphen) that would
otherwise leak straight through a content-only regex.

Scope: this repository only (tools/journal_census.py never looks above its
own repo root). The sibling workspace root that contains this repo is a
separate, non-git scratch area with its own one-time classification pass --
not a recurring lint target, and never will be, since this script becomes a
CI gate that runs inside this repo's own pipeline with no checkout of
anything above it.

File discovery is git-aware (`git ls-files --cached --others
--exclude-standard` for the working tree, or `git ls-tree -r --name-only
<ref>` for a specific ref in --diff mode), not a filesystem walk:
gitignored runtime artifacts (eval run logs, secrets, caches) are never
source or doc content anyone would edit or move, and a raw walk would count
them anyway, wildly inflating the numbers this script exists to make
trustworthy. Two directories are hard-excluded regardless:
`.claude/worktrees/` (live git worktrees -- full checkouts of this same repo
at other branches; counting their contents would multiply every number by
the worktree count) and `.git/` (never tracked content in the first place,
excluded defensively).

Usage:
  python tools/journal_census.py [--format table|json] [--output PATH]
    Full census + lint against the working tree. Exit 1 with every
    unallowed finding printed on any occurrence not covered by the
    allowlists above; exit 0 otherwise.

  python tools/journal_census.py --diff BASE_REF [--format table|json] [--output PATH]
    Regression gate (I5 Phase 0.2): compares unallowed-finding counts per
    (path, pattern) between BASE_REF and the working tree. Exits 1 only if
    the diff *adds* new unallowed occurrences (a file/pattern combination's
    count went up, or a new file/pattern combination with findings
    appeared), regardless of the repo-wide total -- this blocks regressions
    without blocking the incremental I5/I6/I7 cleanup itself. Line-number
    drift within an unrelated part of a file does not, by itself, register
    as a regression; only a net increase in unallowed occurrence count for
    a given (path, pattern) does.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
SELF_PATH = "tools/journal_census.py"

# handoff/ (I5 Phase 0.1, 2026-08-30): this cleanup mission's own
# checkpoint reports live there, and they are necessarily *about* the
# very patterns below (citing DEC-999 as a worked example, discussing
# what HANDOFF/ROADMAP/WORKTREE catch, etc.) -- that is meta-commentary
# on the lint, not journal vocabulary leaking into the blueprint, and an
# allowlist entry per report would just be noise. These reports are
# mission-scoped, reviewed by the owner, and not meant to be permanent
# blueprint content.
HARD_EXCLUDE_PREFIXES = (".claude/worktrees/", ".git/", "handoff/")

# Pattern name -> compiled regex. "OI" is a keep-list (legitimate Annex-A
# open-item requirement IDs, e.g. OI-02/OI-03/OI-04 -- these belong in
# blueprint content and are never a finding); every other pattern is
# journal/session vocabulary that should not appear in the blueprint.
#
# DEC (I5 Phase 0.1, 2026-08-30): widened to case-insensitive with an
# optional hyphen so it also catches decision numbers hiding inside an
# identifier (`dec009`, `test_dec046_...`) -- the original `DEC-\d{3}`
# shape missed exactly this, confirmed live in eval/domain_scorer.py's
# check_dec009_route_assertion() and tests/test_dec009_route_assertion.py.
# A plain `\bdec-?\d{3}\b` does NOT actually catch those: `\b` treats `_`
# as a word character, so there's no boundary between `_` and `d` in
# `check_dec009_...` and the pattern silently fails to match. Using an
# explicit "not preceded by a letter" lookbehind (still blocks a false
# positive like `codec_005`, which has a letter -- 'o' -- immediately
# before "dec") and "not followed by a digit" lookahead (so a 4+ digit
# run like `dec0091` isn't partially matched) instead of `\b` on both
# sides is what actually delivers the stated goal.
PATTERNS = {
    "DEC": re.compile(r"(?<![a-zA-Z])dec-?\d{3}(?!\d)", re.IGNORECASE),
    "OI": re.compile(r"OI-\d{2}"),
    "PHASE": re.compile(r"Phase [A-H]\b"),
    "STOP": re.compile(r"STOP \d"),
    "HANDOFF": re.compile(r"HANDOFF"),
    "WORKTREE": re.compile(r"worktree", re.IGNORECASE),
    "COORD_SESSION": re.compile(r"coordinating session"),
    "WAVE": re.compile(r"Wave [βγ]"),
    "CHECKPOINT": re.compile(r"Checkpoint [A-Z]\d?[a-z]?\b"),
    "MISSION": re.compile(r"MISSION_(UNATTENDED|PHASE)"),
    "STAGE": re.compile(r"Stage [1-4]\b"),
    # I5 Phase 0.1 additions: the private journal's *identity* leaking into
    # the blueprint, independent of any specific DEC-NNN citation.
    "DECISIONS_MD": re.compile(r"DECISIONS\.md"),
    "ROADMAP": re.compile(r"agent-roadmap"),
}

KEEP_LIST_PATTERNS = {"OI"}

# Sentinel "line number" for a hit found in a file's own path rather than
# its content (DEC pattern only -- see discover_files/scan).
FILENAME_LINE = 0

# --- Allowlists ----------------------------------------------------------
# Exact (relative path, pattern name) -> dated reason.
ALLOWLIST_PATHS: dict[tuple[str, str], str] = {
    ("docs/adr/ADR-022-skeleton-design.md", "HANDOFF"): (
        "Documents the skeleton generator's real file-exclusion set "
        "(DECISIONS.md, HANDOFF.md, PINS.md, reports/, srs/, phase docs "
        "are excluded from every rendered project) -- an architectural "
        "fact, not journal narrative. Narrow to this one file, not the "
        "docs/adr/ prefix, so a future ADR that leaks real session-"
        "handoff narrative still gets caught. -- I2, 2026-08-28."
    ),
    ("docs/adr/index.md", "WORKTREE"): (
        "Cites the literal slug name of a rejected ADR candidate "
        "(worktree-isolation-single-governance-owner, DEC-099) for "
        "traceability -- the word is part of a real decision's name, "
        "not narrative about session worktree mechanics. -- I2, "
        "2026-08-28."
    ),
}

# (path prefix, pattern name) -> dated reason. Currently empty: the former
# blanket ("docs/adr/", "DEC") entry was replaced (I5 Phase 0.1,
# 2026-08-30) by the line-precise Journal-citation rule below, so a
# DEC-NNN reference anywhere else in an ADR's prose body is no longer
# silently allowed just for living under docs/adr/.
ALLOWLIST_PREFIXES: dict[tuple[str, str], str] = {}


def _journal_citation_lines(text: str) -> set[int]:
    """docs/adr/*.md: the line(s) allowed to carry a DEC-NNN citation -- the
    single line immediately under each '## Journal' heading, the one place
    an ADR is expected to point back at the decision(s) it distills.
    Everywhere else in the same file, DEC-NNN is still an unreviewed
    finding. -- I5 Phase 0.1, 2026-08-30."""
    lines = text.splitlines()
    exempt: set[int] = set()
    for i, line in enumerate(lines):
        if line.strip() == "## Journal":
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                exempt.add(j + 1)
    return exempt


def _readme_decision_history_line(text: str) -> set[int]:
    """README.md's closing "Decision history:" paragraph -- the single
    approved pointer to the sibling journal repo. -- I5 Phase 0.1,
    2026-08-30."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("Decision history:"):
            return {i + 1}
    return set()


def _adr_index_intro_lines(text: str) -> set[int]:
    """docs/adr/index.md's opening paragraph, before the ADR table -- the
    single approved pointer to the sibling journal repo. -- I5 Phase 0.1,
    2026-08-30."""
    lines = text.splitlines()
    exempt: set[int] = set()
    started = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not started:
            if not stripped or stripped.startswith("#"):
                continue
            started = True
        if not stripped:
            break
        exempt.add(i + 1)
    return exempt


# (relative path) -> {pattern name -> function(file_text) -> allowed line
# numbers}. Unlike ALLOWLIST_PATHS/ALLOWLIST_PREFIXES (whole-file), these
# exempt only specific, named lines. -- I5 Phase 0.1, 2026-08-30.
LINE_EXEMPT_RULES: dict[str, dict[str, Callable[[str], set[int]]]] = {
    "README.md": {
        "DECISIONS_MD": _readme_decision_history_line,
        "ROADMAP": _readme_decision_history_line,
    },
    "docs/adr/index.md": {
        "DECISIONS_MD": _adr_index_intro_lines,
        "ROADMAP": _adr_index_intro_lines,
    },
}


def _line_exempt_rule(rel_path: str, pattern_name: str) -> Optional[Callable[[str], set[int]]]:
    if pattern_name == "DEC" and rel_path.startswith("docs/adr/") and rel_path.endswith(".md"):
        return _journal_citation_lines
    return LINE_EXEMPT_RULES.get(rel_path, {}).get(pattern_name)


def discover_files(root: Path, ref: Optional[str] = None) -> list[str]:
    """Tracked + untracked-but-not-gitignored files (working tree) when
    ref is None; the tracked tree at a specific git ref otherwise (--diff
    mode). Deliberately not `--others` alone or a filesystem walk --
    tracked files must be included even if a later .gitignore change would
    otherwise hide them, and untracked-but-real content (e.g. a report
    drafted but not yet committed) must still be counted in working-tree
    mode."""
    if ref is None:
        cmd = ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"]
    else:
        cmd = ["git", "-C", str(root), "ls-tree", "-r", "--name-only", ref]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = []
    for rel in result.stdout.splitlines():
        if rel == SELF_PATH:
            continue
        if any(rel.startswith(p) for p in HARD_EXCLUDE_PREFIXES):
            continue
        out.append(rel)
    return sorted(out)


def is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return b"\x00" in f.read(8192)
    except OSError:
        return True


def read_file_text(root: Path, rel: str, ref: Optional[str] = None) -> Optional[str]:
    """A file's text content in the working tree (ref=None) or as of a
    specific git ref (--diff mode), or None if it doesn't exist there,
    can't be read, or is binary."""
    if ref is None:
        path = root / rel
        if not path.is_file() or is_binary(path):
            return None
        try:
            return path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return None
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{ref}:{rel}"],
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    raw = result.stdout
    if b"\x00" in raw[:8192]:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def discover_files_walk(root: Path) -> list[str]:
    """Plain filesystem walk (not git-aware) -- for scanning a rendered,
    non-git output directory such as a freshly instantiated skeleton
    project, where there is no git index/ref to query. Used by
    tools/verify_skeleton.py's journal-vocabulary check (I5 Phase 0.4),
    not by the main CLI entry point above."""
    out = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
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


def scan(root: Path, files: list[str], ref: Optional[str] = None) -> dict:
    """Returns {rel_path: {pattern_name: [line_no, ...]}} for every file
    with at least one hit. One list entry per match (not per distinct
    line) -- two citations on the same line must count as two occurrences,
    same as the original content-only scan. A DEC hit on the file's own
    name/path is recorded at FILENAME_LINE (0), alongside any content
    hits."""
    hits: dict[str, dict[str, list[int]]] = {}
    for rel in files:
        file_hits: dict[str, list[int]] = {}

        if PATTERNS["DEC"].search(rel):
            file_hits["DEC"] = [FILENAME_LINE]

        text = read_file_text(root, rel, ref)
        if text is not None:
            for name, pattern in PATTERNS.items():
                lines = [text.count("\n", 0, m.start()) + 1 for m in pattern.finditer(text)]
                if lines:
                    file_hits[name] = file_hits.get(name, []) + lines

        if file_hits:
            hits[rel] = file_hits
    return hits


def is_allowed_whole_file(rel_path: str, pattern_name: str) -> bool:
    if (rel_path, pattern_name) in ALLOWLIST_PATHS:
        return True
    return any(
        rel_path.startswith(prefix) and pattern_name == pat
        for (prefix, pat) in ALLOWLIST_PREFIXES
    )


def exempt_lines_for(root: Path, rel_path: str, pattern_name: str, ref: Optional[str] = None) -> set[int]:
    rule = _line_exempt_rule(rel_path, pattern_name)
    if rule is None:
        return set()
    text = read_file_text(root, rel_path, ref)
    if text is None:
        return set()
    return rule(text)


def build_report(root: Path, ref: Optional[str] = None) -> dict:
    files = discover_files(root, ref)
    return build_report_for_files(root, files, ref)


def build_report_for_files(root: Path, files: list[str], ref: Optional[str] = None) -> dict:
    """The census/lint logic (allowlists, line-exempt rules) applied to an
    already-known file list, so a caller with its own file discovery (e.g.
    discover_files_walk, for a rendered non-git output directory) doesn't
    need a git repo at `root` at all. build_report() above is the git-aware
    convenience wrapper most callers want."""
    hits = scan(root, files, ref)

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
            if is_allowed_whole_file(rel, pattern_name):
                continue
            exempt = exempt_lines_for(root, rel, pattern_name, ref)
            remaining = [ln for ln in lines if ln not in exempt]
            if remaining:
                findings.append({
                    "path": rel, "pattern": pattern_name, "count": len(remaining),
                    "lines": remaining,
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
    lines.append("Per-file findings (non-OI, sorted by count desc; a DEC line of 0 means the")
    lines.append("filename itself, not file content):")
    for f in report["findings"]:
        lines.append(f"  {f['path']:<60} {f['pattern']:<14} count={f['count']}")
    lines.append("")
    lines.append(f"Total unallowed findings: {len(report['findings'])} across "
                  f"{len({f['path'] for f in report['findings']})} files")
    return "\n".join(lines)


def findings_index(report: dict) -> dict[tuple[str, str], int]:
    return {(f["path"], f["pattern"]): f["count"] for f in report["findings"]}


def diff_regressions(base_report: dict, current_report: dict) -> list[dict]:
    """(path, pattern) combinations whose unallowed-occurrence count is
    higher now than at base_report's ref -- a net increase, not a raw
    line-number match, so unrelated line drift elsewhere in a file never
    registers as a false regression."""
    base_idx = findings_index(base_report)
    current_idx = findings_index(current_report)
    regressions = []
    for (path, pattern), cur_count in current_idx.items():
        base_count = base_idx.get((path, pattern), 0)
        if cur_count > base_count:
            regressions.append({
                "path": path, "pattern": pattern,
                "base_count": base_count, "current_count": cur_count,
                "added": cur_count - base_count,
            })
    return sorted(regressions, key=lambda r: (-r["added"], r["path"], r["pattern"]))


def render_diff(regressions: list[dict], base_ref: str) -> str:
    lines = [f"Diff against {base_ref}:"]
    if not regressions:
        lines.append("  No new unallowed journal-signal occurrences.")
        return "\n".join(lines)
    for r in regressions:
        lines.append(
            f"  {r['path']:<60} {r['pattern']:<14} {r['base_count']} -> {r['current_count']} (+{r['added']})"
        )
    lines.append("")
    lines.append(f"{len(regressions)} file/pattern combination(s) gained new unallowed "
                  f"occurrences since {base_ref}.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["table", "json"], default="table")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--diff", metavar="BASE_REF", default=None,
        help="Regression-only mode: exit non-zero only if this diff against "
             "BASE_REF adds new unallowed findings, regardless of the "
             "repo-wide total (I5 Phase 0.2)."
    )
    args = parser.parse_args()

    current_report = build_report(REPO_ROOT)

    if args.diff:
        base_report = build_report(REPO_ROOT, ref=args.diff)
        regressions = diff_regressions(base_report, current_report)
        if args.format == "json":
            rendered = json.dumps({"base_ref": args.diff, "regressions": regressions}, indent=2)
        else:
            rendered = render_diff(regressions, args.diff)
        print(rendered)
        if args.output:
            args.output.write_text(rendered + "\n")
        if regressions:
            print(f"\n{len(regressions)} new unallowed journal-signal occurrence(s) added "
                  f"since {args.diff}.", file=sys.stderr)
            return 1
        return 0

    rendered = json.dumps(current_report, indent=2) if args.format == "json" else render_table(current_report)

    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n")

    if current_report["findings"]:
        print(f"\n{len(current_report['findings'])} unallowed journal-signal finding(s). "
              f"See ALLOWLIST_PATHS/ALLOWLIST_PREFIXES/LINE_EXEMPT_RULES in tools/journal_census.py.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
