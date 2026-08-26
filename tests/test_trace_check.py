"""Unit + smoke tests for tools/trace-check/trace_check.py.

`tools/trace-check` is not a valid Python package name (hyphen), so the
module is loaded directly from its file path via importlib, per this
repository's own convention for tool scripts outside the package tree.
"""

import importlib.util
import textwrap
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).resolve().parent.parent / "tools" / "trace-check" / "trace_check.py"
_spec = importlib.util.spec_from_file_location("trace_check", _MODULE_PATH)
trace_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(trace_check)


# ---------------------------------------------------------------------------
# Parsing: StR / SysR / SRS definitions
# ---------------------------------------------------------------------------


def test_parse_str_definitions_basic():
    text = textwrap.dedent(
        """
        ### 15.1 Developer experience

        - **StR-DX-01.** An agent developer shall be able to instantiate a template.
        - **StR-DX-02.** An agent developer shall be able to run locally.
        """
    )
    assert trace_check.parse_str_definitions(text) == ["StR-DX-01", "StR-DX-02"]


def test_parse_str_definitions_dedupes_and_sorts():
    text = "- **StR-USR-02.** X.\n- **StR-DX-01.** Y.\n- **StR-DX-01.** Y again.\n"
    assert trace_check.parse_str_definitions(text) == ["StR-DX-01", "StR-USR-02"]


def test_parse_sysr_definitions_basic():
    text = textwrap.dedent(
        """
        - **SysR-P-F-01 — Template instantiation.** The platform shall provide a template.
          *Trace:* StR-DX-01. *Verification:* D.

        - **SysR-A-F-01 — Grounded answers.** The agent shall answer questions.
          *Trace:* StR-USR-01. *Verification:* T.
        """
    )
    assert trace_check.parse_sysr_definitions(text) == ["SysR-A-F-01", "SysR-P-F-01"]


def test_parse_srs_definitions_returns_positions():
    text = "- **SRS-APR-F-01 — Proposal intake.** The service shall accept.\n"
    defs = trace_check.parse_srs_definitions(text)
    assert len(defs) == 1
    assert defs[0]["id"] == "SRS-APR-F-01"
    assert text[defs[0]["pos"] :].startswith("**SRS-APR-F-01")


# ---------------------------------------------------------------------------
# Parsing: inline Trace lines, span-based extraction
# ---------------------------------------------------------------------------


def test_parse_srs_requirements_basic_trace_extraction():
    text = textwrap.dedent(
        """
        - **SRS-APR-F-01 — Proposal intake.** The service shall accept a proposal.
          *Trace:* SysR-P-F-08. *Verification:* T (schema-reject cases).

        - **SRS-APR-F-02 — Lifecycle.** Each proposal shall transition once.
          *Trace:* SysR-P-F-08, StR-APR-01. *Verification:* T.
        """
    )
    reqs = trace_check.parse_srs_requirements(text)
    assert [r["id"] for r in reqs] == ["SRS-APR-F-01", "SRS-APR-F-02"]
    assert reqs[0]["has_trace"] is True
    assert reqs[0]["trace_targets"] == ["SysR-P-F-08"]
    assert reqs[1]["trace_targets"] == ["SysR-P-F-08", "StR-APR-01"]


def test_parse_srs_requirements_missing_trace_line():
    text = "- **SRS-XXX-F-01 — No trace.** The service shall do something with no trace line at all.\n"
    reqs = trace_check.parse_srs_requirements(text)
    assert len(reqs) == 1
    assert reqs[0]["has_trace"] is False
    assert reqs[0]["trace_targets"] == []


def test_parse_srs_requirements_ignores_qualifiers_around_ids():
    text = textwrap.dedent(
        """
        - **SRS-AGT-F-08 — Out-of-domain refusal.** The agent shall decline.
          *Trace:* SysR-A-F-01 (by extension), StR-USR-01. *Verification:* T.
        """
    )
    reqs = trace_check.parse_srs_requirements(text)
    assert reqs[0]["trace_targets"] == ["SysR-A-F-01", "StR-USR-01"]


def test_parse_srs_requirements_span_ignores_quoted_trace_line_before_first_definition():
    """Regression test for the srs/SRS-EVH.md edge case: a Trace/Verification
    line quoted in prose (e.g. in Associated Documents) before this
    document's own first requirement is defined must NOT be mistaken for
    that first requirement's own trace line. A flat document-wide
    findall-and-zip approach gets this wrong; the span-based approach
    must get it right.
    """
    text = textwrap.dedent(
        """
        ### Associated Documents

        - `srs/SRS-OTHER.md` states: *"...* *Trace:* SysR-Z-F-99. *Verification:* T
          (quoted from a different document, appears before any requirement of
          THIS document is defined)."*

        ## 1. Functional Requirements

        - **SRS-XXX-F-01 — Real requirement.** The service shall do the real thing.
          *Trace:* SysR-P-F-01. *Verification:* T.
        """
    )
    reqs = trace_check.parse_srs_requirements(text)
    assert len(reqs) == 1
    assert reqs[0]["id"] == "SRS-XXX-F-01"
    # Must be the requirement's OWN trace target, not the quoted one.
    assert reqs[0]["trace_targets"] == ["SysR-P-F-01"]
    assert "SysR-Z-F-99" not in reqs[0]["trace_targets"]


def test_parse_srs_requirements_handles_document_with_no_trailing_sections():
    """Regression test for srs/SRS-MIT.md's structure: interface-only depth,
    no section 7 Traceability, nothing after the last requirement's own
    Trace/Verification line except footer prose. Must not raise and must
    still extract the last requirement's trace correctly.
    """
    text = textwrap.dedent(
        """
        ## 4. Security Requirements (SRS-MIT-SEC-*)

        - **SRS-MIT-SEC-01 — No approval-bypass path.** The tool shall be reachable
          only through the approval-gated path.
          *Trace:* SysR-P-SEC-03, SysR-P-POL-01. *Verification:* I, T.

        ---

        *(Sections 5-7 omitted entirely for this document.)*
        """
    )
    reqs = trace_check.parse_srs_requirements(text)
    assert len(reqs) == 1
    assert reqs[0]["id"] == "SRS-MIT-SEC-01"
    assert reqs[0]["trace_targets"] == ["SysR-P-SEC-03", "SysR-P-POL-01"]


def test_srs_category():
    assert trace_check.srs_category("SRS-APR-F-01") == "F"
    assert trace_check.srs_category("SRS-AGT-QUAL-01") == "QUAL"
    assert trace_check.srs_category("SRS-MIT-IF-05") == "IF"


# ---------------------------------------------------------------------------
# Parsing: srs/DEFERRED.md
# ---------------------------------------------------------------------------


def test_parse_deferred_basic():
    text = textwrap.dedent(
        """
        # Deferred SysRs

        - **SysR-P-PERF-03** — staging-only rollback objective, not exercised in the demo.
        - **SysR-P-OPS-02** — rollback mechanism deferred to staging, per Annex A.
        """
    )
    deferred = trace_check.parse_deferred(text)
    assert deferred == [
        {"sysr_id": "SysR-P-PERF-03", "reason": "staging-only rollback objective, not exercised in the demo."},
        {"sysr_id": "SysR-P-OPS-02", "reason": "rollback mechanism deferred to staging, per Annex A."},
    ]


def test_parse_deferred_empty_string_yields_empty_list():
    assert trace_check.parse_deferred("") == []


# ---------------------------------------------------------------------------
# Parsing: '# verifies:' comments
# ---------------------------------------------------------------------------


def test_parse_verifies_comments_filters_to_f_category_only():
    # Fake, non-colliding IDs on purpose (consistent with the fake-ID
    # convention this file's check_d tests already use): using a real,
    # currently-unverified SRS-APR-F-* id here would make this fixture's
    # sample text collide with real coverage data the moment
    # find_py_files() sweeps this very file — see
    # test_parse_verifies_comments_ignores_ids_inside_string_literals and
    # test_real_tests_own_test_file_contributes_no_spurious_verifies_ids
    # below for the regression tests covering that hazard directly.
    text = textwrap.dedent(
        """
        def test_something():
            # verifies: SRS-FAKE-F-03, SRS-FAKE-F-05
            assert True

        def test_other():
            # verifies: SRS-FAKE-IF-01
            assert True
        """
    )
    ids = trace_check.parse_verifies_comments(text)
    assert ids == ["SRS-FAKE-F-03", "SRS-FAKE-F-05"]


def test_parse_verifies_comments_no_match_returns_empty():
    assert trace_check.parse_verifies_comments("# nothing to see here\n") == []


def test_parse_verifies_comments_ignores_ids_inside_string_literals():
    """Regression test for a real self-referential false-negative hazard:
    identical '# verifies: ...' text sitting inside a string literal
    (e.g. a triple-quoted fixture string — exactly the shape of this
    file's own test_parse_verifies_comments_filters_to_f_category_only
    fixture above) must never be mistaken for a live comment. A naive
    whole-file regex sweep cannot tell a string literal's contents from a
    real comment; the tokenize-based implementation can, because tokenize
    already resolves string-literal boundaries before it ever emits a
    COMMENT token.
    """
    text = textwrap.dedent(
        '''
        def test_fixture_only():
            sample_input = """
            # verifies: SRS-FAKE-F-09
            """
            assert sample_input

        def test_real():
            # verifies: SRS-FAKE-F-10
            assert True
        '''
    )
    ids = trace_check.parse_verifies_comments(text)
    assert ids == ["SRS-FAKE-F-10"]
    assert "SRS-FAKE-F-09" not in ids


def test_parse_verifies_comments_invalid_python_does_not_raise():
    """A .py file that fails to tokenize (e.g. an unterminated string)
    must not crash the whole trace-check run — it should simply
    contribute no ids, same as a file with no '# verifies:' comments."""
    text = 'x = "unterminated\n# verifies: SRS-FAKE-F-11\n'
    assert trace_check.parse_verifies_comments(text) == []


# ---------------------------------------------------------------------------
# Parsing: eval case ids (filesystem-backed, tmp_path)
# ---------------------------------------------------------------------------


def test_parse_eval_case_definitions_handles_list_and_dict_shapes(tmp_path):
    domain_dir = tmp_path / "eval" / "cases" / "domain"
    domain_dir.mkdir(parents=True)
    (domain_dir / "knowledge_qa.yaml").write_text(
        textwrap.dedent(
            """
            - id: KQA-001
              category: knowledge_qa
              tags: ["knowledge_qa", "read-only"]
            - id: KQA-002
              category: knowledge_qa
              tags: ["knowledge_qa", "read-only", "req:SRS-EVH-F-02"]
            """
        ),
        encoding="utf-8",
    )
    cases_dir = tmp_path / "eval" / "cases"
    (cases_dir / "EXAMPLE-001.yaml").write_text(
        "id: EXAMPLE-001\ndescription: placeholder\n", encoding="utf-8"
    )

    cases = trace_check.parse_eval_case_definitions(tmp_path)
    assert set(cases.keys()) == {"KQA-001", "KQA-002", "EXAMPLE-001"}
    assert cases["KQA-002"]["tags"] == ["knowledge_qa", "read-only", "req:SRS-EVH-F-02"]
    assert cases["EXAMPLE-001"]["tags"] == []


def test_parse_eval_case_definitions_missing_dirs_returns_empty(tmp_path):
    assert trace_check.parse_eval_case_definitions(tmp_path) == {}


# ---------------------------------------------------------------------------
# Eval-case-reference scanning (false-positive avoidance AND — the
# blocker-severity fix — false-negative closure for wholly fabricated
# eval-case-id citations)
# ---------------------------------------------------------------------------


def test_eval_case_prefix_set_derived_from_real_ids():
    known_ids = ["KQA-001", "KQA-002", "OPS-001", "EXAMPLE-001"]
    assert trace_check.eval_case_prefix_set(known_ids) == {"KQA", "OPS", "EXAMPLE"}


def test_eval_case_ref_regex_matches_bare_and_range_but_not_unrelated_prefixes():
    prefixes = {"KQA", "OPS"}
    regex = trace_check.build_eval_case_ref_regex(prefixes)
    text = "See KQA-001..015 and OPS-004, but not PLAT-001 or DEC-001 or SysR-P-OPS-02."
    matches = [(m.group(1), m.group(2), m.group(3)) for m in regex.finditer(text)]
    # Exact match set, not just "every matched prefix is KQA/OPS" — that
    # weaker assertion would not have caught the SysR-P-OPS-02 substring
    # collision below, since a spurious match on the "OPS-02" tail of
    # "SysR-P-OPS-02" also reports prefix "OPS" and would satisfy it.
    assert matches == [("KQA", "001", "015"), ("OPS", "004", None)]


def test_build_eval_case_ref_regex_excludes_prefix_matched_as_substring_of_longer_id():
    """Regression test for a real false-positive (major severity): without
    a guard, the known-prefix regex matches 'OPS-02' as a bare substring
    inside the unrelated, real, well-formed SysR id 'SysR-P-OPS-02' (or
    any other hyphen-joined id ending in a segment that happens to equal
    a known case-id prefix plus a number), because 'OPS' is a real
    eval-case prefix (eval/cases/domain/operational.yaml defines
    OPS-001..005) and the regex's original \\b word-boundary alone does
    not block a match starting right after a '-'. This must produce zero
    matches, not a spurious 'OPS-02' orphan_eval_case violation against a
    perfectly valid SysR citation.
    """
    regex = trace_check.build_eval_case_ref_regex({"OPS"})
    text = "*Trace:* SysR-P-OPS-02. *Verification:* T."
    assert list(regex.finditer(text)) == []
    # A real, standalone OPS-02 (not embedded in a longer id) must still match.
    assert [m.group(0) for m in regex.finditer("See OPS-02 directly.")] == ["OPS-02"]


def test_build_eval_case_ref_regex_empty_prefixes_returns_none():
    assert trace_check.build_eval_case_ref_regex(set()) is None


def test_find_eval_case_refs_near_paths_catches_wholly_fabricated_prefix():
    """Regression test for the blocker-severity false negative:
    build_eval_case_ref_regex()/eval_case_prefix_set() only ever
    recognize a token as an eval-case reference if its prefix is already
    a real, loaded case-id family — so a hallucinated prefix that matches
    NO real family (e.g. 'FAKE') is never even matched by that mechanism,
    let alone checked. find_eval_case_refs_near_paths() closes this gap
    by scanning, unrestricted by prefix, immediately after a real
    `eval/cases/...yaml` path mention — exactly where every real citation
    in these documents is written.
    """
    text = "Evidence: see `eval/cases/domain/fake.yaml` (FAKE-001..999) for verification."
    refs = trace_check.find_eval_case_refs_near_paths(text)
    assert [(r["prefix"], r["n1"], r["n2"]) for r in refs] == [("FAKE", "001", "999")]


def test_find_eval_case_refs_near_paths_ignores_unrelated_tokens_further_in_prose():
    """The scan must stay tightly scoped to text immediately after the
    path mention — it must not sweep in unrelated ID-shaped tokens
    (bare SRS category shorthand, mock-ITSM ids, corpus doc ids, decision
    ids) that appear later in the same long sentence, which is exactly
    the false-positive hazard an unscoped 'any shape' scan would
    reintroduce.
    """
    text = (
        "Evidence: `eval/cases/domain/draft_request.yaml` (DRQ-001..006) — "
        "consistent with, not a substitute for, a component-level test of "
        "SRS-APR-F-02/F-04 in isolation, per DEC-001 and INC-10234."
    )
    refs = trace_check.find_eval_case_refs_near_paths(text)
    assert [(r["prefix"], r["n1"], r["n2"]) for r in refs] == [("DRQ", "001", "006")]


# ---------------------------------------------------------------------------
# Check (a): SysR -> SRS coverage
# ---------------------------------------------------------------------------


def test_check_a_pass_when_traced_or_deferred():
    sysr_ids = ["SysR-P-F-01", "SysR-P-F-02"]
    srs_requirements = [{"id": "SRS-X-F-01", "trace_targets": ["SysR-P-F-01"]}]
    deferred = [{"sysr_id": "SysR-P-F-02", "reason": "out of demo scope"}]
    result = trace_check.check_a(sysr_ids, srs_requirements, deferred)
    assert result["status"] == "PASS"
    assert result["violations"] == []


def test_check_a_fail_when_neither_traced_nor_deferred():
    sysr_ids = ["SysR-P-F-01", "SysR-P-F-02"]
    srs_requirements = [{"id": "SRS-X-F-01", "trace_targets": ["SysR-P-F-01"]}]
    deferred = []
    result = trace_check.check_a(sysr_ids, srs_requirements, deferred)
    assert result["status"] == "FAIL"
    assert len(result["violations"]) == 1
    assert result["violations"][0]["sysr_id"] == "SysR-P-F-02"


# ---------------------------------------------------------------------------
# Check (b): SRS -> SysR trace validity
# ---------------------------------------------------------------------------


def test_check_b_all_violation_kinds():
    sysr_set = {"SysR-P-F-01"}
    srs_requirements = [
        {"id": "SRS-A-F-01", "has_trace": True, "trace_targets": ["SysR-P-F-01"]},  # valid, passes
        {"id": "SRS-A-F-02", "has_trace": False, "trace_targets": []},  # no trace line
        {"id": "SRS-A-F-03", "has_trace": True, "trace_targets": ["StR-USR-01"]},  # only StR
        {"id": "SRS-A-F-04", "has_trace": True, "trace_targets": ["SysR-P-F-99"]},  # unknown SysR
        {"id": "SRS-A-F-05", "has_trace": True, "trace_targets": []},  # zero resolvable ids
    ]
    result = trace_check.check_b(srs_requirements, sysr_set)
    assert result["status"] == "FAIL"
    failing_ids = {v["srs_id"] for v in result["violations"]}
    assert failing_ids == {"SRS-A-F-02", "SRS-A-F-03", "SRS-A-F-04", "SRS-A-F-05"}
    assert "SRS-A-F-01" not in failing_ids


def test_check_b_pass_when_all_valid():
    sysr_set = {"SysR-P-F-01"}
    srs_requirements = [{"id": "SRS-A-F-01", "has_trace": True, "trace_targets": ["SysR-P-F-01"]}]
    result = trace_check.check_b(srs_requirements, sysr_set)
    assert result["status"] == "PASS"
    assert result["violations"] == []


# ---------------------------------------------------------------------------
# Check (c): no broken/orphan IDs, no duplicate SRS ids, eval-case refs
# ---------------------------------------------------------------------------


def test_check_c_detects_orphan_tokens():
    files_text = {
        "doc1.md": "See StR-DX-01 and StR-DX-99 (does not exist) and SysR-P-F-01 and SysR-Z-Q-01 (fake).",
    }
    srs_files_text = {}
    all_srs_defs_by_file = {}
    result = trace_check.check_c(
        files_text=files_text,
        srs_files_text=srs_files_text,
        all_srs_defs_by_file=all_srs_defs_by_file,
        known_str_ids={"StR-DX-01"},
        known_sysr_ids={"SysR-P-F-01"},
        known_srs_ids=set(),
        known_case_ids=set(),
    )
    assert result["status"] == "FAIL"
    kinds = {(v["token"], v["kind"]) for v in result["violations"]}
    assert ("StR-DX-99", "orphan_str") in kinds
    assert ("SysR-Z-Q-01", "orphan_sysr") in kinds
    assert ("StR-DX-01", "orphan_str") not in kinds
    assert ("SysR-P-F-01", "orphan_sysr") not in kinds


def test_check_c_detects_duplicate_srs_id_across_documents():
    srs_files_text = {
        "srs/SRS-A.md": "- **SRS-DUP-F-01 — First copy.** Something.\n",
        "srs/SRS-B.md": "- **SRS-DUP-F-01 — Second copy.** Something else.\n",
    }
    all_srs_defs_by_file = {
        "srs/SRS-A.md": trace_check.parse_srs_definitions(srs_files_text["srs/SRS-A.md"]),
        "srs/SRS-B.md": trace_check.parse_srs_definitions(srs_files_text["srs/SRS-B.md"]),
    }
    result = trace_check.check_c(
        files_text=srs_files_text,
        srs_files_text=srs_files_text,
        all_srs_defs_by_file=all_srs_defs_by_file,
        known_str_ids=set(),
        known_sysr_ids=set(),
        known_srs_ids={"SRS-DUP-F-01"},
        known_case_ids=set(),
    )
    assert result["status"] == "FAIL"
    dup_violations = [v for v in result["violations"] if v["kind"] == "duplicate_srs_id"]
    assert len(dup_violations) == 2  # one per occurrence/location
    assert all(v["token"] == "SRS-DUP-F-01" for v in dup_violations)


def test_check_c_detects_orphan_eval_case_reference_range_endpoint():
    srs_files_text = {
        "srs/SRS-X.md": "Evidence: `eval/cases/domain/knowledge_qa.yaml` (KQA-001..099).",
    }
    result = trace_check.check_c(
        files_text=srs_files_text,
        srs_files_text=srs_files_text,
        all_srs_defs_by_file={},
        known_str_ids=set(),
        known_sysr_ids=set(),
        known_srs_ids=set(),
        known_case_ids={"KQA-001", "KQA-002"},  # KQA-099 does not exist
    )
    assert result["status"] == "FAIL"
    eval_violations = [v for v in result["violations"] if v["kind"] == "orphan_eval_case"]
    assert len(eval_violations) == 1
    assert eval_violations[0]["token"] == "KQA-099"


def test_check_c_detects_wholly_fabricated_eval_case_prefix():
    """End-to-end regression test for the blocker-severity false negative,
    exercised through check_c() itself (not just the helper function):
    an eval-case-id-shaped token whose prefix matches NO real case family
    at all must still be flagged as broken, not silently pass because its
    prefix was never even recognized as a reference.
    """
    srs_files_text = {
        "srs/SRS-X.md": "Evidence: see `eval/cases/domain/fake.yaml` (FAKE-001..999) for verification.",
    }
    result = trace_check.check_c(
        files_text=srs_files_text,
        srs_files_text=srs_files_text,
        all_srs_defs_by_file={},
        known_str_ids=set(),
        known_sysr_ids=set(),
        known_srs_ids=set(),
        known_case_ids={"KQA-001", "KQA-002"},  # no FAKE-* id exists anywhere
    )
    assert result["status"] == "FAIL"
    eval_violations = {
        v["token"] for v in result["violations"] if v["kind"] == "orphan_eval_case"
    }
    assert eval_violations == {"FAKE-001", "FAKE-999"}


def test_check_c_does_not_flag_sysr_id_colliding_with_eval_case_prefix_substring():
    """End-to-end regression test for the major-severity false positive:
    a real, valid SysR-* citation (e.g. SysR-P-OPS-02) must not be
    misread as a broken eval-case reference merely because its tail
    segment ('OPS-02') matches a real case-id prefix ('OPS') plus a
    number.
    """
    srs_files_text = {
        "srs/SRS-X.md": "*Trace:* SysR-P-OPS-02. *Verification:* T.",
    }
    result = trace_check.check_c(
        files_text=srs_files_text,
        srs_files_text=srs_files_text,
        all_srs_defs_by_file={},
        known_str_ids=set(),
        known_sysr_ids={"SysR-P-OPS-02"},
        known_srs_ids=set(),
        known_case_ids={"OPS-001", "OPS-002"},
    )
    eval_violations = [v for v in result["violations"] if v["kind"] == "orphan_eval_case"]
    assert eval_violations == []
    assert result["status"] == "PASS"


def test_check_c_pass_when_clean():
    files_text = {"doc1.md": "StR-DX-01 and SysR-P-F-01 are both real."}
    result = trace_check.check_c(
        files_text=files_text,
        srs_files_text={},
        all_srs_defs_by_file={},
        known_str_ids={"StR-DX-01"},
        known_sysr_ids={"SysR-P-F-01"},
        known_srs_ids=set(),
        known_case_ids=set(),
    )
    assert result["status"] == "PASS"
    assert result["violations"] == []


# ---------------------------------------------------------------------------
# Check (d): SRS-F -> test/eval coverage (logic tested directly, unreachable
# via the CLI in --docs-only mode today, per MISSION_PHASE_B0.md).
# ---------------------------------------------------------------------------


def test_check_d_finds_test_file_reference_and_flags_unreferenced(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_fake.py").write_text(
        "def test_x():\n    # verifies: SRS-FAKE-F-01\n    assert True\n",
        encoding="utf-8",
    )
    srs_f_ids = ["SRS-FAKE-F-01", "SRS-FAKE-F-02"]
    py_files = [tests_dir / "test_fake.py"]
    result = trace_check.check_d(srs_f_ids, py_files, eval_cases={})
    assert result["status"] == "FAIL"
    failing_ids = {v["srs_id"] for v in result["violations"]}
    assert failing_ids == {"SRS-FAKE-F-02"}
    assert "SRS-FAKE-F-01" not in failing_ids


def test_check_d_finds_eval_case_req_tag_reference():
    srs_f_ids = ["SRS-FAKE-F-03"]
    eval_cases = {"KQA-001": {"tags": ["knowledge_qa", "req:SRS-FAKE-F-03"]}}
    result = trace_check.check_d(srs_f_ids, py_files=[], eval_cases=eval_cases)
    assert result["status"] == "PASS"
    assert result["violations"] == []


def test_check_d_pass_when_all_referenced(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_fake.py").write_text(
        "# verifies: SRS-FAKE-F-01, SRS-FAKE-F-02\n", encoding="utf-8"
    )
    result = trace_check.check_d(
        ["SRS-FAKE-F-01", "SRS-FAKE-F-02"],
        [tests_dir / "test_fake.py"],
        eval_cases={},
    )
    assert result["status"] == "PASS"
    assert result["violations"] == []


# ---------------------------------------------------------------------------
# find_py_files
# ---------------------------------------------------------------------------


def test_find_py_files_scans_tests_agent_mcp_server_not_others(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "agent").mkdir()
    (tmp_path / "mcp_server").mkdir()
    (tmp_path / "other").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("", encoding="utf-8")
    (tmp_path / "agent" / "b.py").write_text("", encoding="utf-8")
    (tmp_path / "mcp_server" / "c.py").write_text("", encoding="utf-8")
    (tmp_path / "other" / "ignored.py").write_text("", encoding="utf-8")

    found = {p.name for p in trace_check.find_py_files(tmp_path)}
    assert found == {"test_a.py", "b.py", "c.py"}


def test_real_tests_own_test_file_contributes_no_spurious_verifies_ids():
    """Regression test for the self-referential contamination hazard
    against the REAL repository, not just an isolated fixture: once check
    (d) is invoked without --docs-only, find_py_files() sweeps
    tools/trace-check's own tests/test_trace_check.py (it lives under
    tests/, exactly like every real Phase B test will). This file's own
    fixture data for test_parse_verifies_comments_filters_to_f_category_only
    and test_parse_verifies_comments_ignores_ids_inside_string_literals
    exercises the '# verifies: ...' convention as *sample input* inside
    triple-quoted strings, not as real comments — parse_verifies_comments
    must not misread that as live coverage evidence. Confirmed directly
    against this repository's real tests/ directory, not a synthetic
    tmp_path fixture, so this cannot silently regress.
    """
    repo_root = Path(__file__).resolve().parent.parent
    py_files = trace_check.find_py_files(repo_root)
    this_file = Path(__file__).resolve()
    resolved = [p.resolve() for p in py_files]
    assert this_file in resolved, (
        "expected tools/trace-check's own test file to be swept by "
        "find_py_files() -- that is the precondition for the hazard "
        "this regression test guards against"
    )

    verified = set()
    for f in py_files:
        verified.update(trace_check.parse_verifies_comments(f.read_text(encoding="utf-8")))

    # Phase B has not started; no real test file anywhere in tests/
    # (this one included) has yet written a genuine '# verifies:'
    # comment referencing a real SRS-*-F-* id.
    assert verified == set(), (
        f"expected zero real '# verifies:' comments across tests/ before "
        f"Phase B begins, found: {sorted(verified)}"
    )


# ---------------------------------------------------------------------------
# Real-repository smoke/integration test — proves the regexes work on real
# formatting, not just on fixtures written to match this implementation.
# ---------------------------------------------------------------------------


def test_real_syrs_and_strs_id_counts_match_documents_own_claims():
    """SyRS-AGP-001_EN.md's own closing 'SysR index' line states 63 total,
    and its Annex T 'Orphan detection' note states 29/29 StRs traced (i.e.
    29 total StRs). Both are independently verified here against the real
    documents' own bold-definition markup, not hardcoded from any prompt.

    DECISIONS.md DEC-026: these two documents are workspace-level sources
    of truth (CLAUDE.md's own numbered list) that live one directory above
    this git repo's own root -- deliberately not duplicated into the repo,
    since they're shared workspace governance, not this deliverable's own
    content. That means a checkout of only this repo (a real Tekton
    fetch-source clone, any CI system, any other laptop) never has them --
    this was only ever passing by coincidence of running from this
    specific machine's directory layout, caught the first time this test
    ran in a genuinely isolated checkout (Phase C's own pipeline). Skips
    (not fails) when the parent-workspace files aren't present, so the
    real regression-guard value is kept for whoever runs from the full
    workspace layout, without breaking portability for everyone else.
    """
    repo_root = Path(__file__).resolve().parent.parent
    syrs_path = repo_root.parent / "SyRS-AGP-001_EN.md"
    strs_path = repo_root.parent / "StRS_Agentic_AI_Platform_EN.md"
    if not (syrs_path.is_file() and strs_path.is_file()):
        pytest.skip(
            "workspace-level source-of-truth docs not present outside the repo root "
            f"({syrs_path}, {strs_path}) -- expected in a standalone checkout, see DEC-026"
        )

    sysr_ids = trace_check.parse_sysr_definitions(syrs_path.read_text(encoding="utf-8"))
    str_ids = trace_check.parse_str_definitions(strs_path.read_text(encoding="utf-8"))

    assert len(sysr_ids) == 63, f"expected 63 distinct SysR ids, got {len(sysr_ids)}: {sysr_ids}"
    assert len(str_ids) == 29, f"expected 29 distinct StR ids, got {len(str_ids)}: {str_ids}"


def test_real_srs_documents_parse_without_error_and_match_known_counts():
    """Confirmed by direct grep against the real files during this tool's
    development: 25+20+13+6+11 = 75 total bold SRS definitions across the
    five documents, with srs/SRS-MIT.md (interface-only, no section 7)
    among them, proving the parser handles that structural difference.
    SRS-APR.md's count moved from 18 to 19 at Checkpoint B0-b, when
    SRS-APR-IF-05 (terminal-state proposal query) was added to close
    FIND-004 (DECISIONS.md DEC-008); and from 19 to 20 at Phase G kickoff
    (G0), when SRS-APR-QUAL-02 (held, never auto-approved, on shared-
    service unavailability) was added (DECISIONS.md DEC-098).
    """
    repo_root = Path(__file__).resolve().parent.parent
    srs_dir = repo_root / "srs"
    expected_per_file = {
        "SRS-AGT.md": 25,
        "SRS-APR.md": 20,
        "SRS-EVH.md": 13,
        "SRS-MIT.md": 6,
        "SRS-RET.md": 11,
    }
    total = 0
    for fname, expected_count in expected_per_file.items():
        text = (srs_dir / fname).read_text(encoding="utf-8")
        reqs = trace_check.parse_srs_requirements(text)
        assert len(reqs) == expected_count, f"{fname}: expected {expected_count} requirements, got {len(reqs)}"
        # Every real requirement in these five (already manually verified,
        # per each document's own text) currently carries its own inline
        # Trace line.
        for r in reqs:
            assert r["has_trace"], f"{fname}: {r['id']} unexpectedly has no Trace line"
        total += len(reqs)
    assert total == 75


def test_real_deferred_md_absent_yields_empty_deferred_set():
    """srs/DEFERRED.md does not exist yet at this point in Phase B0 (the
    orchestrator populates it after this tool exists) — confirms the
    documented 'treat as empty, do not error, do not create the file'
    contract against the real repository state.
    """
    repo_root = Path(__file__).resolve().parent.parent
    deferred_path = repo_root / "srs" / "DEFERRED.md"
    if deferred_path.is_file():
        # If a later run of this suite finds it already populated, the
        # parser must still handle it without error - not this test's
        # concern to assert emptiness in that case.
        trace_check.parse_deferred(deferred_path.read_text(encoding="utf-8"))
    else:
        assert trace_check.parse_deferred("") == []
