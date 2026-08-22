from corpus.ingest import REQUIRED_METADATA_FIELDS, ingest


def test_all_twenty_manifest_documents_are_retrievable():
    # Every eval/corpus-manifest.yaml entry has complete governance
    # metadata and a corresponding corpus/seed/<doc_id>.md file.
    docs = ingest()
    assert len(docs) == 20
    doc_ids = {d["doc_id"] for d in docs}
    assert "PLAT-003" in doc_ids
    assert "KI-001" in doc_ids
    assert "SVC-003" in doc_ids


def test_every_document_carries_all_required_governance_fields():
    docs = ingest()
    for doc in docs:
        for field in REQUIRED_METADATA_FIELDS:
            assert doc.get(field), f"{doc['doc_id']} missing {field}"


def test_passage_text_is_the_seed_file_body():
    docs = {d["doc_id"]: d for d in ingest()}
    assert "build stage" in docs["PLAT-003"]["passage_text"]


def test_manifest_entry_missing_metadata_is_not_retrievable(tmp_path, monkeypatch):
    import corpus.ingest as ingest_module

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "documents:\n"
        "  - doc_id: TEST-001\n"
        "    title: Complete Doc\n"
        "    owner_role: Someone\n"
        "    classification: internal-public\n"
        "    version: '1.0'\n"
        "    effective_date: '2026-01-01'\n"
        "    access_policy: all\n"
        "    source: test\n"
        "    refresh_process: manual\n"
        "  - doc_id: TEST-002\n"
        "    title: Incomplete Doc\n"
        # missing owner_role, classification, etc.
        "    version: '1.0'\n"
    )
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()
    (seed_dir / "TEST-001.md").write_text("Complete content.")
    (seed_dir / "TEST-002.md").write_text("Incomplete content.")

    monkeypatch.setattr(ingest_module, "MANIFEST_PATH", manifest)
    docs = ingest_module.ingest(seed_dir)

    doc_ids = {d["doc_id"] for d in docs}
    assert doc_ids == {"TEST-001"}  # TEST-002 excluded: incomplete metadata


def test_manifest_entry_with_no_seed_file_is_not_retrievable(tmp_path, monkeypatch):
    import corpus.ingest as ingest_module

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "documents:\n"
        "  - doc_id: TEST-003\n"
        "    title: No File\n"
        "    owner_role: Someone\n"
        "    classification: internal-public\n"
        "    version: '1.0'\n"
        "    effective_date: '2026-01-01'\n"
        "    access_policy: all\n"
        "    source: test\n"
        "    refresh_process: manual\n"
    )
    seed_dir = tmp_path / "seed"
    seed_dir.mkdir()  # no TEST-003.md written

    monkeypatch.setattr(ingest_module, "MANIFEST_PATH", manifest)
    docs = ingest_module.ingest(seed_dir)

    assert docs == []
