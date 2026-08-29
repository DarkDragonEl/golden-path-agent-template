"""Retrieval API/library contract.

Minimal working retrieval against corpus/seed/, per
srs/SRS-RET-IF-01 -- field names corrected
here from the pre-existing scaffold's snippet/source_uri (flagged as a
known update target in srs/REVIEW_INDEX.md) to the authoritative
passage_text/source, plus the two fields the scaffold was missing
(owner_role, effective_date).

Lexical (keyword-overlap) scoring, not embeddings/a vector store:
semantic matching wasn't needed to get the 15
knowledge_qa cases passing over 20 documents with fairly distinct topics.
Escalate to a real vector store only if that stops being true.

SRS-RET-F-03 (authorization filtering): interface-correct only. The
`user_id` parameter flows through this contract's signature so a real
identity-based filter has a place to plug in, but no filtering logic is
implemented against it yet -- this repo's `eval/cases/domain/` set has no
authorization-negative case to verify against (a recorded gap,
srs/SRS-AGT.md's own note at SRS-AGT-F-02), so building enforcement here
now would be unverifiable. TODO(domain): real per-document access-policy
enforcement once that eval-set gap closes.
"""

import re
from dataclasses import dataclass
from functools import lru_cache

from . import config
from corpus.ingest import ingest

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "does", "do", "for", "from",
    "has", "have", "how", "in", "is", "it", "of", "on", "or", "our", "per", "that",
    "the", "this", "to", "under", "was", "what", "when", "which", "who", "with",
}


@dataclass
class RetrievedChunk:
    doc_id: str
    title: str
    passage_text: str
    source: str
    classification: str
    version: str
    owner_role: str
    effective_date: str


def _words(text: str) -> set[str]:
    # len(w) > 1 excludes single-character tokens -- the real bug behind
    # the false-positive-retrieval finding above: `[a-z0-9]+`
    # splits a contraction like "What's" into "what" + a bare "s", and
    # that spurious "s" token then coincidentally "matched" any document
    # containing an unrelated possessive ("team's", "Curator's", ...),
    # inflating overlap counts with noise rather than real topical signal.
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS and len(w) > 1}


@lru_cache(maxsize=1)
def _corpus() -> list[dict]:
    return ingest()


def retrieve(
    query: str, top_k: int | None = None, filters: dict | None = None, user_id: str | None = None
) -> list[RetrievedChunk]:
    """Lexical retrieval over the ingested corpus, ranked by keyword
    overlap between the query and each document's title + body. `filters`
    and `user_id` are accepted per the interface contract (SRS-RET-IF-01,
    SRS-RET-F-03) but not yet applied -- see the module docstring.

    MIN_OVERLAP gates out noise matches: found via live testing that
    retrieval attaching a document on a single generic shared word (e.g.
    "incident", "current", "status" -- present in nearly every procedure
    document) for a query that isn't actually a knowledge question at all
    (an ITSM record-ID lookup) confused tool selection badly enough to
    break it, on a query that had previously been reliable. Requiring
    at least two shared significant words is enough to filter every
    single-word coincidental match seen in that failure while still
    matching every real eval/cases/domain/knowledge_qa.yaml-style query
    (see tests/test_retrieval_client.py's 11 real-query regression check).
    """
    k = top_k if top_k is not None else config.RETRIEVAL_TOP_K
    query_words = _words(query)
    if not query_words:
        return []

    MIN_OVERLAP = 2
    scored = []
    for doc in _corpus():
        doc_words = _words(doc["title"]) | _words(doc["passage_text"])
        overlap = query_words & doc_words
        if len(overlap) < MIN_OVERLAP:
            continue
        # Title matches count double -- a query naming a document by its
        # actual title should rank that document first even if the body
        # text happens to share fewer raw words with a longer document.
        score = len(overlap) + len(query_words & _words(doc["title"]))
        scored.append((score, doc))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [
        RetrievedChunk(
            doc_id=doc["doc_id"],
            title=doc["title"],
            passage_text=doc["passage_text"],
            source=doc["source"],
            classification=doc["classification"],
            version=doc["version"],
            owner_role=doc["owner_role"],
            effective_date=doc["effective_date"],
        )
        for _, doc in scored[:k]
    ]
