#!/usr/bin/env python3
"""trace_check.py — executable requirements-traceability validator.

Validates the chain StRS -> SyRS -> SRS -> (eval cases / tests) for the
golden-path-agent-template blueprint (deliverable 2 of the requirements-
traceability work). Exits non-zero when any *active* check fails.

See tools/trace-check/README.md for the full ID grammar, the checks'
exact semantics, and the exit-code contract. This module is intentionally
a single file: parsing, the four checks, report generation, and the CLI
entrypoint. No classes are required; every unit is a plain function
operating on dicts/lists so it is trivial to unit-test in isolation
(see tests/test_trace_check.py).

Dependencies: Python 3 stdlib + pyyaml (already in requirements-dev.txt).
No new dependency is introduced.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import tokenize
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml

# ---------------------------------------------------------------------------
# Regex grammar (see README.md "ID conventions" for the rationale of each).
# ---------------------------------------------------------------------------

# StR definition, e.g. "- **StR-DX-01.** An agent developer shall..."
STR_DEF_RE = re.compile(r"\*\*(StR-[A-Z]+-\d+)\.\*\*")

# SysR definition, e.g. "- **SysR-P-F-01 — Template instantiation.** The..."
SYSR_DEF_RE = re.compile(r"\*\*(SysR-[A-Z]+-[A-Z]+-\d+)\s*—")

# SRS definition, e.g. "- **SRS-APR-F-01 — Proposal intake.** The service..."
SRS_DEF_RE = re.compile(r"\*\*(SRS-[A-Z]+-[A-Z]+-\d+)\s*—")

# Inline Trace line following a requirement's shall-statement, e.g.
# "*Trace:* SysR-P-F-08. *Verification:* T ..."
# Non-greedy: stops at the first period immediately before *Verification:*.
TRACE_RE = re.compile(r"\*Trace:\*\s*(.*?)\.\s*\*Verification:\*", re.DOTALL)

# Any StR-*/SysR-* token found inside a captured Trace span.
ID_TOKEN_IN_TRACE_RE = re.compile(r"\b(SysR-[A-Z]+-[A-Z]+-\d+|StR-[A-Z]+-\d+)\b")

# Generic "anywhere in the prose" token scanners, used by check (c).
STR_TOKEN_RE = re.compile(r"\b(StR-[A-Z]+-\d+)\b")
SYSR_TOKEN_RE = re.compile(r"\b(SysR-[A-Z]+-[A-Z]+-\d+)\b")
SRS_TOKEN_RE = re.compile(r"\b(SRS-[A-Z]+-[A-Z]+-\d+)\b")

# srs/DEFERRED.md bullet line, e.g. "- **SysR-P-PERF-03** — staging-only ..."
DEFERRED_RE = re.compile(
    r"^-\s*\*\*(SysR-[A-Z]+-[A-Z]+-\d+)\*\*\s*—\s*(.+)$", re.MULTILINE
)

# Test-file requirement-reference convention (this tool's own choice — see
# README.md "Test-file requirement-reference convention" for the rationale).
VERIFIES_RE = re.compile(r"#\s*verifies:\s*([A-Za-z0-9,\-\s]+)")

# Only SRS-F IDs are in scope for the "# verifies:" / "req:" convention.
SRS_F_ID_RE = re.compile(r"^SRS-[A-Z]+-F-\d+$")

# The five SRS documents this tool understands. Order is stable/deterministic
# (alphabetical) but not semantically significant.
SRS_FILENAMES = [
    "SRS-AGT.md",
    "SRS-APR.md",
    "SRS-EVH.md",
    "SRS-MIT.md",
    "SRS-RET.md",
]


# ---------------------------------------------------------------------------
# Parsing section — functions return plain dicts/lists.
# ---------------------------------------------------------------------------


def parse_str_definitions(text: str) -> List[str]:
    """Return the distinct StR-* IDs defined (bold) in StRS body text."""
    return sorted(set(STR_DEF_RE.findall(text)))


def parse_sysr_definitions(text: str) -> List[str]:
    """Return the distinct SysR-* IDs defined (bold) in SyRS body text."""
    return sorted(set(SYSR_DEF_RE.findall(text)))


def parse_srs_definitions(text: str) -> List[Dict]:
    """Return every SRS-*-*-NN bold definition occurrence, in document order.

    Each entry is ``{"id": str, "pos": int}`` where ``pos`` is the character
    offset of the match start (used both for span computation below and for
    line-number reporting). Occurrences are NOT deduplicated here — callers
    that need duplicate detection (check c) want every occurrence; callers
    that only need the requirement set can dedupe by id themselves.
    """
    return [{"id": m.group(1), "pos": m.start()} for m in SRS_DEF_RE.finditer(text)]


def parse_srs_requirements(text: str) -> List[Dict]:
    """Parse every SRS requirement in one document, with its own Trace line.

    For each bold SRS-*-*-NN definition, the requirement's own text "span"
    is defined as the text between the end of that definition's bold marker
    and the start of the *next* bold SRS-*-*-NN definition (or end of file
    for the last one). The first ``*Trace:* ... *Verification:*`` match
    found strictly inside that span is this requirement's own Trace line.

    This span-based approach is deliberate, not incidental: a document's
    Associated Documents section sometimes *quotes* another document's own
    Trace/Verification line in prose (srs/SRS-EVH.md does this for
    SRS-AGT-QUAL-01's trace line, before SRS-EVH's own first requirement is
    even defined). A naive "find every *Trace:* line in the whole document
    and zip it positionally against every bold definition" approach breaks
    on that document (14 Trace-shaped matches for 13 real requirements) and
    silently misattributes every requirement's trace after the mismatch.
    Span-based extraction confines the search to each requirement's own
    text and is immune to a quoted trace line appearing before any of this
    document's own requirements are defined.

    Returns a list of dicts:
        {"id": str, "pos": int, "has_trace": bool,
         "trace_text": Optional[str], "trace_targets": List[str]}
    """
    defs = list(SRS_DEF_RE.finditer(text))
    requirements: List[Dict] = []
    for i, m in enumerate(defs):
        req_id = m.group(1)
        span_start = m.end()
        span_end = defs[i + 1].start() if i + 1 < len(defs) else len(text)
        span_text = text[span_start:span_end]
        trace_match = TRACE_RE.search(span_text)
        if trace_match:
            trace_text = trace_match.group(1)
            trace_targets = ID_TOKEN_IN_TRACE_RE.findall(trace_text)
            has_trace = True
        else:
            trace_text = None
            trace_targets = []
            has_trace = False
        requirements.append(
            {
                "id": req_id,
                "pos": m.start(),
                "has_trace": has_trace,
                "trace_text": trace_text,
                "trace_targets": trace_targets,
            }
        )
    return requirements


def parse_deferred(text: str) -> List[Dict]:
    """Parse srs/DEFERRED.md's bullet-list format.

    Returns ``[{"sysr_id": str, "reason": str}, ...]``. Callers pass an
    empty string (or this function is simply not called) when the file
    does not exist on disk — an empty deferred set, not an error.
    """
    return [
        {"sysr_id": m.group(1), "reason": m.group(2).strip()}
        for m in DEFERRED_RE.finditer(text)
    ]


def parse_verifies_comments(text: str) -> List[str]:
    """Extract every SRS-*-F-* ID referenced by a real '# verifies: ...'
    Python *comment* — never text that merely looks like one because it
    sits inside a string literal.

    Uses Python's own tokenizer rather than a naive whole-file regex
    sweep, precisely because a regex sweep cannot distinguish a real
    comment from identical text inside a triple-quoted string literal.
    That distinction matters here for a concrete, real, self-referential
    reason: tools/trace-check's own tests/test_trace_check.py — which
    find_py_files() sweeps like any other file under tests/ — contains
    the literal text '# verifies: SRS-FAKE-F-03, SRS-FAKE-F-05' as
    *sample input* inside a triple-quoted fixture string, for unit-testing
    this very function in isolation
    (test_parse_verifies_comments_filters_to_f_category_only). A naive
    text-level sweep would misread that fixture string's contents as a
    live comment the instant check (d) runs without --docs-only, silently
    crediting whatever SRS ids happen to appear in the fixture as
    "verified" even though zero real tests reference them. tokenize
    cannot make that mistake: it already resolves string-literal
    boundaries before it ever emits a COMMENT token, so text inside a
    string is a STRING token, never a COMMENT token, regardless of what
    it contains. See
    tests/test_trace_check.py::test_parse_verifies_comments_ignores_ids_inside_string_literals
    and ::test_real_tests_own_test_file_contributes_no_spurious_verifies_ids
    for the regression tests this closes.

    Each COMMENT token's string is, by construction, exactly one physical
    line (Python's '#' syntax has no multi-line form), so scanning each
    COMMENT token independently preserves the same "line by line, never
    let '\\s' swallow following lines" property the previous line-based
    implementation relied on (see git history / README.md for that
    original failure mode).

    Text that does not tokenize as valid Python (e.g. a deliberately
    malformed fixture, or a real syntax error in an unrelated file) is
    handled by keeping whatever comments tokenized successfully before
    the failure and dropping the rest — a syntax error in one file must
    not crash the whole trace-check run over every other file.
    """
    comment_strings: List[str] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                comment_strings.append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass

    ids: List[str] = []
    for line in comment_strings:
        m = VERIFIES_RE.search(line)
        if not m:
            continue
        for tok in m.group(1).split(","):
            tok = tok.strip()
            if SRS_F_ID_RE.match(tok):
                ids.append(tok)
    return ids


def parse_eval_case_definitions(root: Path) -> Dict[str, Dict]:
    """Load every eval case id from eval/cases/domain/*.yaml and
    eval/cases/EXAMPLE-*.yaml.

    Handles both YAML shapes described in the mission spec: a domain file
    is a YAML *list* of case objects; an EXAMPLE-*.yaml file is a single
    YAML *mapping*. Returns ``{case_id: {"file": relpath, "tags": [...]}}``.
    """
    cases: Dict[str, Dict] = {}
    cases_dir = root / "eval" / "cases"
    domain_dir = cases_dir / "domain"

    def _record(item: Dict, file_path: Path) -> None:
        if not isinstance(item, dict):
            return
        cid = item.get("id")
        if not cid:
            return
        cases[cid] = {
            "file": _display_path(root, file_path),
            "tags": item.get("tags") or [],
        }

    if domain_dir.is_dir():
        for f in sorted(domain_dir.glob("*.yaml")):
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    _record(item, f)
            elif isinstance(data, dict):
                _record(data, f)

    if cases_dir.is_dir():
        for f in sorted(cases_dir.glob("EXAMPLE-*.yaml")):
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                _record(data, f)
            elif isinstance(data, list):
                for item in data:
                    _record(item, f)

    return cases


def eval_case_prefix_set(known_case_ids: List[str]) -> set:
    """Derive the set of case-id prefixes (e.g. {"KQA", "EXAMPLE", ...})
    from the real, loaded case-id set. Used to build a discriminating
    regex for eval-case-ID *references* inside SRS prose (see
    find_eval_case_ref_violations) — this avoids false positives on
    unrelated NNN-suffixed tokens in the same prose (DEC-001, PLAT-003,
    INC-10234, etc.) that are not eval case ids at all.
    """
    prefix_re = re.compile(r"^(.*)-(\d+)$")
    prefixes = set()
    for cid in known_case_ids:
        m = prefix_re.match(cid)
        if m:
            prefixes.add(m.group(1))
    return prefixes


def build_eval_case_ref_regex(prefixes: set) -> Optional[re.Pattern]:
    """Build the known-prefix eval-case reference regex.

    ``(?<!-)`` guards against matching a known case-id prefix as a bare
    *substring* of an unrelated, longer, hyphen-joined id — concretely,
    without this guard the real SysR id ``SysR-P-OPS-02`` would match
    this regex on ``OPS-02`` alone (the case-id prefix ``OPS`` sitting
    right after the ``SysR-P-`` segment's own hyphen), reporting a false
    orphan_eval_case violation for a perfectly valid SysR citation. Every
    compound id family in this tool's grammar (``SysR-*``, ``StR-*``,
    ``SRS-*-*-NN``) joins its segments with ``-``, so "not immediately
    preceded by a hyphen" is a general guard against this whole class of
    collision, not just the one instance (SysR-P-OPS-NN /
    eval-case-prefix OPS) confirmed to collide in this corpus today.
    """
    if not prefixes:
        return None
    alts = sorted((re.escape(p) for p in prefixes), key=len, reverse=True)
    pattern = r"(?<!-)\b(" + "|".join(alts) + r")-(\d+)(?:\.\.(\d+))?\b"
    return re.compile(pattern)


# A case-id-*shaped* token (>=1 uppercase letter, '-', digits, optional
# '..' range) found immediately after a backtick-quoted
# `eval/cases/...yaml` path mention — used by find_eval_case_refs_near_paths
# below to catch references whose prefix is *not* already a known case-id
# family (see that function's docstring for why this scoping is safe to
# leave unrestricted to known prefixes, unlike build_eval_case_ref_regex
# above).
EVAL_CASE_REF_RUN_RE = re.compile(
    r"`eval/cases/[\w./*-]+\.yaml`\s*\(?\s*"
    r"((?:(?<!-)[A-Z]+-\d+(?:\.\.\d+)?[,;\s]*)+)"
)
EVAL_CASE_ID_TOKEN_RE = re.compile(r"([A-Z]+)-(\d+)(?:\.\.(\d+))?")


def find_eval_case_refs_near_paths(text: str) -> List[Dict]:
    """Find every eval-case-ID-*shaped* reference token that immediately
    follows a backtick-quoted `eval/cases/...yaml` path mention —
    regardless of whether its prefix happens to already be a real,
    known case-id family.

    This is the fix for a real false-negative (blocker-severity):
    ``build_eval_case_ref_regex()`` above only ever recognizes a token as
    an eval-case reference at all if its prefix is already present in the
    real, loaded case-id set — so a wholly fabricated citation (e.g. a
    hallucinated ``FAKE-001..999``, or a typo'd prefix that doesn't match
    any real case family) is never even matched, let alone flagged as
    broken. That mechanism can only ever catch "wrong number within a
    real family," never a wholly invented family.

    Scoping this *unrestricted* token scan to "immediately follows a real
    `eval/cases/...yaml` path mention" is what makes it safe to run
    without a known-prefix allowlist. Confirmed empirically against the
    real corpus (all five srs/SRS-*.md documents) before landing this
    fix: every real eval-case-id citation in these documents' Evidence
    prose is written in exactly this position (immediately after, or
    inside the first parenthesized group immediately after, a concrete
    `eval/cases/<file>.yaml` backtick reference) — while unrelated
    ID-shaped tokens that appear elsewhere in the same prose (bare SRS
    category shorthand like `F-04` inside `SRS-APR-F-02/F-04`, mock-ITSM
    ids like `INC-10234`, corpus doc ids like `PLAT-003`, decision/finding
    ids like `DEC-001`) never sit directly after such a path mention, so
    a wider, unscoped "any shape" scan would have reintroduced exactly
    the kind of false positives build_eval_case_ref_regex()'s known-prefix
    restriction was originally written to avoid. This function keeps that
    original safety property by construction (tight structural scoping)
    instead of by an allowlist.

    Returns one ``{"prefix": str, "n1": str, "n2": Optional[str], "pos":
    int}`` entry per token found (ranges keep both endpoints so callers
    can build the same "both endpoints only" candidate set the rest of
    this tool uses for ranges).
    """
    results: List[Dict] = []
    for run_match in EVAL_CASE_REF_RUN_RE.finditer(text):
        run_text = run_match.group(1)
        run_start = run_match.start(1)
        for tok_match in EVAL_CASE_ID_TOKEN_RE.finditer(run_text):
            results.append(
                {
                    "prefix": tok_match.group(1),
                    "n1": tok_match.group(2),
                    "n2": tok_match.group(3),
                    "pos": run_start + tok_match.start(),
                }
            )
    return results


def find_py_files(root: Path) -> List[Path]:
    """Find every .py file under the directories this convention scans.

    Only tests/ has content today; agent/ and mcp_server/ are scanned too
    (per the spec: "the parser should scan any .py file passed to
    it, not hardcode tests/ as the only location") so that once
    agent/ or mcp_server/ gain '# verifies:' comments there, no code
    change is needed here.
    """
    py_files: List[Path] = []
    for dirname in ("tests", "agent", "mcp_server"):
        d = root / dirname
        if d.is_dir():
            py_files.extend(sorted(d.rglob("*.py")))
    return py_files


# ---------------------------------------------------------------------------
# Small path/line helpers.
# ---------------------------------------------------------------------------


def _display_path(root: Path, path: Path) -> str:
    """Render a path relative to --root when possible, else relative to
    root's parent (needed for StRS/SyRS, which live one level above the
    repository root — see README.md), else absolute."""
    for base in (root, root.parent):
        try:
            return str(path.relative_to(base))
        except ValueError:
            continue
    return str(path)


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _find_doc(root: Path, filename: str) -> Optional[Path]:
    """Locate a source document that may live at --root/srs (current
    location, since the J2/I1 reference-implementation reframe moved
    StRS_Agentic_AI_Platform_EN.md and SyRS-AGP-001_EN.md into srs/), at
    --root directly, or at --root's parent directory (pre-reframe
    location, kept as a fallback for an older checkout layout).
    """
    for base in (root / "srs", root, root.parent):
        candidate = base / filename
        if candidate.is_file():
            return candidate
    return None


def srs_category(srs_id: str) -> str:
    """Extract the category token from an SRS-<COMP>-<CAT>-<NN> id."""
    parts = srs_id.split("-")
    return parts[2] if len(parts) >= 4 else ""


# ---------------------------------------------------------------------------
# Checks section — one function per check, each returning
# {"status": "PASS"|"FAIL"|"SKIPPED", "violations": [...]}.
# ---------------------------------------------------------------------------


def check_a(sysr_ids: List[str], srs_requirements: List[Dict], deferred: List[Dict]) -> Dict:
    """Every SysR must be traced by >=1 SRS requirement, or deferred."""
    traced = set()
    for req in srs_requirements:
        for t in req["trace_targets"]:
            if t.startswith("SysR-"):
                traced.add(t)
    deferred_ids = {d["sysr_id"] for d in deferred}

    violations = []
    for sid in sysr_ids:
        if sid not in traced and sid not in deferred_ids:
            violations.append(
                {
                    "sysr_id": sid,
                    "reason": "not traced by any SRS requirement and not in srs/DEFERRED.md",
                }
            )
    return {"status": "PASS" if not violations else "FAIL", "violations": violations}


def check_b(srs_requirements: List[Dict], sysr_ids_set: set) -> Dict:
    """Every SRS requirement must have a Trace line citing >=1 real SysR."""
    violations = []
    for req in srs_requirements:
        sysr_cited = [t for t in req["trace_targets"] if t.startswith("SysR-")]
        valid_sysr_cited = [t for t in sysr_cited if t in sysr_ids_set]

        if not req["has_trace"]:
            reason = "no *Trace:* line found for this requirement"
        elif not req["trace_targets"]:
            reason = "Trace line cites zero resolvable SysR/StR IDs"
        elif not sysr_cited:
            reason = "Trace line cites only StR ID(s), no SysR ID"
        elif not valid_sysr_cited:
            reason = (
                "Trace line cites SysR ID(s) that are not defined in "
                "SyRS-AGP-001_EN.md"
            )
        else:
            continue

        violations.append({"srs_id": req["id"], "reason": reason})

    return {"status": "PASS" if not violations else "FAIL", "violations": violations}


def check_c(
    files_text: Dict[str, str],
    srs_files_text: Dict[str, str],
    all_srs_defs_by_file: Dict[str, List[Dict]],
    known_str_ids: set,
    known_sysr_ids: set,
    known_srs_ids: set,
    known_case_ids: set,
) -> Dict:
    """No broken/orphan IDs anywhere in the chain; no duplicate SRS ids;
    every eval-case-id reference in SRS Evidence prose resolves."""
    violations: List[Dict] = []

    # -- duplicate SRS id detection, across all five documents combined --
    locations = defaultdict(list)
    for file_label, defs in all_srs_defs_by_file.items():
        text = srs_files_text[file_label]
        for d in defs:
            locations[d["id"]].append(f"{file_label}:{_line_of(text, d['pos'])}")
    for sid, locs in locations.items():
        if len(locs) > 1:
            for loc in locs:
                violations.append({"token": sid, "kind": "duplicate_srs_id", "location": loc})

    # -- generic orphan token scan across the full check-(c) file set --
    for file_label, text in files_text.items():
        for m in STR_TOKEN_RE.finditer(text):
            tok = m.group(1)
            if tok not in known_str_ids:
                violations.append(
                    {"token": tok, "kind": "orphan_str", "location": f"{file_label}:{_line_of(text, m.start())}"}
                )
        for m in SYSR_TOKEN_RE.finditer(text):
            tok = m.group(1)
            if tok not in known_sysr_ids:
                violations.append(
                    {"token": tok, "kind": "orphan_sysr", "location": f"{file_label}:{_line_of(text, m.start())}"}
                )
        for m in SRS_TOKEN_RE.finditer(text):
            tok = m.group(1)
            if tok not in known_srs_ids:
                violations.append(
                    {"token": tok, "kind": "orphan_srs", "location": f"{file_label}:{_line_of(text, m.start())}"}
                )

    # -- eval-case-id reference orphan scan, srs/SRS-*.md files only --
    #
    # Two complementary mechanisms feed this scan (see README.md "Eval
    # case IDs" for the full rationale):
    #   1. `ref_re` — a known-prefix scan across each document's entire
    #      text. Catches "wrong number within a real family" typos
    #      anywhere in prose, e.g. citing KQA-099 when only KQA-001..015
    #      exist. Guards against matching a known prefix as a bare
    #      substring of a longer, unrelated hyphen-joined id (see
    #      build_eval_case_ref_regex()'s docstring).
    #   2. find_eval_case_refs_near_paths() — an unrestricted scan scoped
    #      to text immediately following a real `eval/cases/...yaml` path
    #      mention. Catches a *wholly fabricated* prefix (mechanism 1 can
    #      never even recognize such a token as a reference, since its
    #      prefix never appears in the real case-id set to begin with).
    # A reference caught by both (the common case for a real, known-good
    # prefix written in the usual "right after its own path mention"
    # position) is deduplicated by (prefix, n1, n2, pos) before being
    # checked, so it is never reported twice.
    prefixes = eval_case_prefix_set(sorted(known_case_ids))
    ref_re = build_eval_case_ref_regex(prefixes)
    for file_label, text in srs_files_text.items():
        refs = []
        if ref_re is not None:
            for m in ref_re.finditer(text):
                refs.append((m.group(1), m.group(2), m.group(3), m.start()))
        for r in find_eval_case_refs_near_paths(text):
            refs.append((r["prefix"], r["n1"], r["n2"], r["pos"]))

        seen_refs = set()
        for prefix, n1, n2, pos in refs:
            key = (prefix, n1, n2, pos)
            if key in seen_refs:
                continue
            seen_refs.add(key)
            candidates = [f"{prefix}-{n1}"]
            if n2:
                candidates.append(f"{prefix}-{n2}")
            missing = [c for c in candidates if c not in known_case_ids]
            for mid in missing:
                violations.append(
                    {
                        "token": mid,
                        "kind": "orphan_eval_case",
                        "location": f"{file_label}:{_line_of(text, pos)}",
                    }
                )

    return {"status": "PASS" if not violations else "FAIL", "violations": violations}


def check_d(srs_f_ids: List[str], py_files: List[Path], eval_cases: Dict[str, Dict]) -> Dict:
    """Every SRS-F requirement must be referenced by >=1 test file
    ('# verifies: <ID>') or >=1 eval case ('req:<ID>' tag).

    Always fully implemented (never stubbed); the CLI decides whether to
    invoke it at all based on --docs-only.
    """
    verified_by_test = set()
    for f in py_files:
        verified_by_test.update(parse_verifies_comments(f.read_text(encoding="utf-8")))

    verified_by_eval = set()
    for cid, info in eval_cases.items():
        for tag in info.get("tags") or []:
            if isinstance(tag, str) and tag.startswith("req:"):
                rid = tag[len("req:") :]
                if SRS_F_ID_RE.match(rid):
                    verified_by_eval.add(rid)

    violations = []
    for rid in srs_f_ids:
        if rid not in verified_by_test and rid not in verified_by_eval:
            violations.append(
                {
                    "srs_id": rid,
                    "reason": "not referenced by any '# verifies:' test comment or eval case 'req:' tag",
                }
            )

    return {"status": "PASS" if not violations else "FAIL", "violations": violations}


# ---------------------------------------------------------------------------
# Report section — human-readable formatter + JSON serializer.
# ---------------------------------------------------------------------------


def build_report(
    run_mode: str,
    sysr_ids: List[str],
    str_ids: List[str],
    srs_requirements: List[Dict],
    srs_f_ids: List[str],
    eval_cases: Dict[str, Dict],
    deferred: List[Dict],
    check_results: Dict[str, Dict],
) -> Dict:
    coverage = defaultdict(list)
    sysr_set = set(sysr_ids)
    for req in srs_requirements:
        for t in req["trace_targets"]:
            if t.startswith("SysR-") and t in sysr_set:
                coverage[t].append(req["id"])

    return {
        "run_mode": run_mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": check_results,
        "counts": {
            "sysr_total": len(sysr_ids),
            "str_total": len(str_ids),
            # Deduplicated by id, like every other count here — srs_requirements
            # itself is NOT deduplicated (parse_srs_definitions()/
            # parse_srs_requirements() deliberately return one entry per bold
            # definition *occurrence*, so check (c)'s duplicate-id detection
            # can see every occurrence). Without this dedup, a genuine
            # cross-document duplicate SRS id (already flagged as a check (c)
            # violation) would silently inflate this total relative to every
            # other id-based count in the same report — confusing to a reader
            # cross-referencing the two while diagnosing that violation.
            "srs_requirement_total": len({r["id"] for r in srs_requirements}),
            "srs_f_requirement_total": len(srs_f_ids),
            "eval_case_total": len(eval_cases),
        },
        "coverage": dict(coverage),
        "deferred": deferred,
    }


def print_human_summary(report: Dict) -> None:
    checks = report["checks"]
    counts = report["counts"]

    order = ["a", "b", "c", "d"]
    names = {
        "a": "(a) SysR -> SRS coverage",
        "b": "(b) SRS -> SysR trace validity",
        "c": "(c) No broken/orphan IDs",
        "d": "(d) SRS-F -> test/eval coverage",
    }

    print("=" * 72)
    print("trace-check report — run_mode=%s — generated_at=%s" % (report["run_mode"], report["generated_at"]))
    print("=" * 72)
    print(f"{'Check':40s} {'Status':10s} {'Violations':>10s}")
    print("-" * 72)
    for key in order:
        result = checks.get(key)
        if result is None:
            continue
        n = len(result.get("violations", []))
        print(f"{names[key]:40s} {result['status']:10s} {n:>10d}")
    print("-" * 72)

    idx = 1
    for key in order:
        result = checks.get(key)
        if result is None or not result.get("violations"):
            continue
        print(f"\n{names[key]} — violations:")
        for v in result["violations"]:
            detail = ", ".join(f"{k}={val}" for k, val in v.items())
            print(f"  {idx:3d}. {detail}")
            idx += 1

    sysr_total = counts["sysr_total"]
    traced_count = len(report["coverage"])
    untraced = sysr_total - traced_count
    deferred_ids = {d["sysr_id"] for d in report["deferred"]}

    print("\nCoverage summary:")
    print(f"  {traced_count}/{sysr_total} SysRs traced by >=1 SRS requirement")
    print(f"  {len(deferred_ids)} SysR(s) listed in srs/DEFERRED.md (of {untraced} untraced)")
    print(f"  {counts['srs_requirement_total']} SRS requirements across 5 documents")
    print(f"  {counts['srs_f_requirement_total']} SRS-F requirements")
    print(f"  {counts['eval_case_total']} eval cases loaded")

    # Non-fatal note, not a check failure: check (a) uses OR semantics
    # exactly as specified ("traced ... or listed in srs/DEFERRED.md"), so
    # a SysR id that is BOTH traced by a real SRS requirement AND listed
    # in srs/DEFERRED.md produces zero check violations. In practice that
    # combination usually indicates a srs/DEFERRED.md authoring mistake
    # (something marked deliberately out-of-scope that was, in fact,
    # implemented) — surfaced here for a human reviewer's judgment, not
    # as something this tool fails the run over.
    contradictory = sorted(set(report["coverage"].keys()) & deferred_ids)
    if contradictory:
        print("\nWARNING: SysR id(s) both traced by a real SRS requirement AND")
        print("listed in srs/DEFERRED.md — likely a srs/DEFERRED.md authoring")
        print("mistake (marked out-of-scope but actually implemented). Not a")
        print("check failure; needs reviewer judgment:")
        for sid in contradictory:
            print(f"  - {sid}")

    print("=" * 72)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate the StRS -> SyRS -> SRS -> (eval/tests) traceability chain."
    )
    parser.add_argument(
        "--docs-only",
        action="store_true",
        help="Skip check (d) (SRS-F -> test/eval coverage), which requires implementation-code artifacts.",
    )
    default_root = Path(__file__).resolve().parents[2]
    parser.add_argument(
        "--root",
        type=Path,
        default=default_root,
        help=f"Repository root to scan (default: {default_root})",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Path to write the machine-readable JSON report (default: <root>/reports/trace-check.json)",
    )
    args = parser.parse_args()

    root: Path = args.root.resolve()
    json_out: Path = (args.json_out if args.json_out is not None else root / "reports" / "trace-check.json")

    # --- locate and read the frozen source documents ---
    syrs_path = _find_doc(root, "SyRS-AGP-001_EN.md")
    strs_path = _find_doc(root, "StRS_Agentic_AI_Platform_EN.md")
    if syrs_path is None or strs_path is None:
        missing = []
        if syrs_path is None:
            missing.append("SyRS-AGP-001_EN.md")
        if strs_path is None:
            missing.append("StRS_Agentic_AI_Platform_EN.md")
        print(f"ERROR: could not locate required source document(s): {', '.join(missing)}", file=sys.stderr)
        print(f"       looked in {root} and {root.parent}", file=sys.stderr)
        sys.exit(2)

    syrs_text = syrs_path.read_text(encoding="utf-8")
    strs_text = strs_path.read_text(encoding="utf-8")

    sysr_ids = parse_sysr_definitions(syrs_text)
    str_ids = parse_str_definitions(strs_text)
    sysr_set = set(sysr_ids)
    str_set = set(str_ids)

    # --- read the five SRS documents ---
    srs_dir = root / "srs"
    srs_files_text: Dict[str, str] = {}
    all_srs_defs_by_file: Dict[str, List[Dict]] = {}
    all_srs_requirements: List[Dict] = []
    for fname in SRS_FILENAMES:
        fpath = srs_dir / fname
        if not fpath.is_file():
            print(f"ERROR: expected SRS document not found: {fpath}", file=sys.stderr)
            sys.exit(2)
        label = _display_path(root, fpath)
        text = fpath.read_text(encoding="utf-8")
        srs_files_text[label] = text
        all_srs_defs_by_file[label] = parse_srs_definitions(text)
        for req in parse_srs_requirements(text):
            req["file"] = label
            all_srs_requirements.append(req)

    known_srs_ids = {r["id"] for r in all_srs_requirements}
    srs_f_ids = sorted({r["id"] for r in all_srs_requirements if srs_category(r["id"]) == "F"})

    # --- srs/DEFERRED.md (optional; empty if absent) ---
    deferred_path = root / "srs" / "DEFERRED.md"
    deferred = parse_deferred(deferred_path.read_text(encoding="utf-8")) if deferred_path.is_file() else []

    # --- eval case definitions ---
    eval_cases = parse_eval_case_definitions(root)

    # --- the broader file set check (c) scans for orphan tokens ---
    findings_path = root / "srs" / "FINDINGS.md"
    decisions_path = root / "DECISIONS.md"
    review_index_path = root / "srs" / "REVIEW_INDEX.md"

    files_text: Dict[str, str] = {
        _display_path(root, strs_path): strs_text,
        _display_path(root, syrs_path): syrs_text,
    }
    files_text.update(srs_files_text)
    for p in (findings_path, decisions_path, review_index_path):
        if p.is_file():
            files_text[_display_path(root, p)] = p.read_text(encoding="utf-8")
    if deferred_path.is_file():
        files_text[_display_path(root, deferred_path)] = deferred_path.read_text(encoding="utf-8")

    # --- run checks a, b, c (always active) ---
    result_a = check_a(sysr_ids, all_srs_requirements, deferred)
    result_b = check_b(all_srs_requirements, sysr_set)
    result_c = check_c(
        files_text,
        srs_files_text,
        all_srs_defs_by_file,
        str_set,
        sysr_set,
        known_srs_ids,
        set(eval_cases.keys()),
    )

    # --- check (d): implemented fully; skipped in --docs-only mode ---
    if args.docs_only:
        result_d = {
            "status": "SKIPPED",
            "reason": "no implementation code exists yet to produce tests; --docs-only mode",
            "violations": [],
        }
    else:
        py_files = find_py_files(root)
        result_d = check_d(srs_f_ids, py_files, eval_cases)

    check_results = {"a": result_a, "b": result_b, "c": result_c, "d": result_d}

    report = build_report(
        run_mode="docs-only" if args.docs_only else "full",
        sysr_ids=sysr_ids,
        str_ids=str_ids,
        srs_requirements=all_srs_requirements,
        srs_f_ids=srs_f_ids,
        eval_cases=eval_cases,
        deferred=deferred,
        check_results=check_results,
    )

    print_human_summary(report)

    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"\nJSON report written to {json_out}")

    active_statuses = [check_results[k]["status"] for k in ("a", "b", "c")]
    if not args.docs_only:
        active_statuses.append(check_results["d"]["status"])
    exit_code = 0 if all(s == "PASS" for s in active_statuses) else 1
    sys.exit(exit_code)
