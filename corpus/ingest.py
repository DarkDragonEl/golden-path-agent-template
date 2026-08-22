"""Minimal corpus loading — not a chunk/embed/vector pipeline.

Phase B3.5 scope: load eval/corpus-manifest.yaml's identities, join each
with its body text from corpus/seed/<doc_id>.md, and gate retrievability
on governance-metadata completeness (SRS-RET-F-01: "A document for which
any of these attributes has not been attached shall not become
retrievable"). No ingestion pipeline beyond this — SRS-RET-F-02's
"documented refresh process" is documentation + a manual re-load of this
function, not automation; that stays out of scope here.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "eval" / "corpus-manifest.yaml"

REQUIRED_METADATA_FIELDS = (
    "title",
    "owner_role",
    "classification",
    "version",
    "effective_date",
    "access_policy",
    "source",
    "refresh_process",
)


def ingest(source_dir: str | Path = None) -> list[dict]:
    """Returns one dict per retrievable document: manifest metadata plus
    `passage_text` (the seed file's full body). A manifest entry missing
    any required governance field, or with no corresponding seed file, is
    skipped -- not retrievable -- per SRS-RET-F-01.
    """
    seed_dir = Path(source_dir) if source_dir else (REPO_ROOT / "corpus" / "seed")
    manifest = yaml.safe_load(MANIFEST_PATH.read_text())

    documents = []
    for entry in manifest.get("documents", []):
        doc_id = entry.get("doc_id")
        missing = [f for f in REQUIRED_METADATA_FIELDS if not entry.get(f)]
        if missing:
            # Not raised -- a document with incomplete governance metadata
            # simply never becomes retrievable, per SRS-RET-F-01.
            continue

        seed_path = seed_dir / f"{doc_id}.md"
        if not seed_path.exists():
            continue

        documents.append(
            {
                "doc_id": doc_id,
                "title": entry["title"],
                "owner_role": entry["owner_role"],
                "classification": entry["classification"],
                "version": entry["version"],
                "effective_date": entry["effective_date"],
                "access_policy": entry["access_policy"],
                "source": entry["source"],
                "refresh_process": entry["refresh_process"],
                "passage_text": seed_path.read_text().strip(),
            }
        )
    return documents


if __name__ == "__main__":
    import sys

    docs = ingest(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"{len(docs)} retrievable documents loaded.")
