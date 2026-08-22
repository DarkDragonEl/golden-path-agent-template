from agent.retrieval_client import RetrievedChunk, retrieve

# Each pair is (query, expected doc_id near/at the top) -- drawn directly
# from real eval/cases/domain/knowledge_qa.yaml queries, so this doubles
# as a regression check that retrieval actually finds what those cases need.
_KQA_STYLE_QUERIES = [
    ("What are the stages of the CI pipeline reference architecture?", "PLAT-003"),
    ("Under the Namespace Request and Quota Policy, who approves a namespace quota increase?", "PLAT-002"),
    ("What does the Container Platform Cluster Topology Standard say about namespaces?", "PLAT-001"),
    ("What must a team do before publishing a new service catalog entry?", "PLAT-004"),
    ("What does the Network Segmentation and Ingress Standard say about namespace traffic?", "PLAT-005"),
    ("What is the Golden Path Container Image Baseline's stance on base image provenance?", "PLAT-006"),
    ("Who is responsible for reviewing production access requests?", "PROC-004"),
    ("When should an incident be escalated per the Incident Escalation Procedure?", "PROC-006"),
    ("Is there a documented workaround for the ingress certificate renewal race condition?", "KI-003"),
    ("What known error explains why a service catalog entry might not appear immediately?", "KI-004"),
    ("What is the guaranteed backup frequency for the Managed Database Namespace Add-on?", "SVC-003"),
]


def test_retrieved_chunk_field_shape_matches_srs_ret_if_01():
    results = retrieve("CI pipeline reference architecture stages")
    assert results
    fields = set(results[0].__dict__.keys())
    assert fields == {
        "doc_id", "title", "passage_text", "source", "classification", "version",
        "owner_role", "effective_date",
    }
    assert isinstance(results[0], RetrievedChunk)


def test_top_k_limits_result_count():
    results = retrieve("namespace platform standard procedure", top_k=2)
    assert len(results) <= 2


def test_query_with_no_recognizable_words_returns_nothing():
    assert retrieve("###!!!???") == []


def test_kqa_style_queries_retrieve_the_expected_document():
    misses = []
    for query, expected_doc_id in _KQA_STYLE_QUERIES:
        results = retrieve(query, top_k=3)
        found_ids = [r.doc_id for r in results]
        if expected_doc_id not in found_ids:
            misses.append((query, expected_doc_id, found_ids))
    assert not misses, f"queries that didn't retrieve their expected doc in top 3: {misses}"


def test_must_refuse_if_absent_facts_are_genuinely_absent_from_every_document():
    # KQA-003 / KQA-015: verify absence corpus-wide, not just in the cited
    # document -- these are refusal-to-fabricate tests, which only hold if
    # the gap is real everywhere, not just in the one cited doc.
    from corpus.ingest import ingest

    all_text = " ".join(d["passage_text"].lower() for d in ingest())
    assert "maximum execution time" not in all_text or "no maximum execution time" in all_text
    assert "backup frequency" not in all_text or "no documented backup frequency" in all_text
