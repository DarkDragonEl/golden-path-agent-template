# Code comment policy

Applied repo-wide by Phase H4 (`DECISIONS.md` `DEC-114` onward). Every
`#`/docstring comment citing a `DEC-NNN` falls into one of three
categories — this page states the policy; `reports/docs-audit.md`'s
comment census applied it to every hit found under `agent/`,
`mcp_server/`, `approval_service/`, `scripts/`, `pipelines/`, `deploy/`,
`platform/`.

## The three categories

**(a) Contract or invariant, plus a pointer — keep as-is.** A short
(generally ≤3–4 line) statement of a *current* rule, precondition, or
guarantee the code enforces, with a `DEC-NNN` citation for context. This
is documentation the reader needs at the point of use — not history.
Examples already in this codebase: `agent/nodes/tool_invoke.py`'s
`evidence_refs` scoping note, `agent/telemetry.py`'s read-only-w.r.t.-
model-inputs invariant, the DEC-083 rotation-warning text in
`scripts/bootstrap.sh`. **Never slim a category-(a) comment** — some of
these (operator-facing warnings especially) must stay prominent enough
that someone running a script at 2am sees them without opening
`DECISIONS.md`.

**(b) Narrative that duplicates a `DECISIONS.md` entry — slim to a
pointer.** A longer explanation of *why* something is the way it is,
where that same reasoning is already fully recorded under the `DEC-NNN`
it cites (or a nearby, correctly-findable one). Slimming loses nothing,
since the full story survives in the decision log. The slimmed form is
the same shape as an (a) comment: state the current fact/contract in
≤3 lines, keep the `DEC-NNN` pointer verbatim.

**(c) Narrative that exists only in this comment — migrate before
slimming, never slim first.** The comment contains specific detail
(exact error text, a root cause, a file/function name from reading
someone else's source, a decision that was never actually logged) that
is genuinely *not* recoverable from `DECISIONS.md` under any number. Per
Phase H's own hard rule, this content is moved into `DECISIONS.md` (as
an addendum to the entry it should have lived under, or a brand-new
entry if none fits — see `DEC-040`'s retroactive reconstruction and
`DEC-119`'s misattribution correction for both shapes) *before* the
comment is touched. `reports/docs-audit.md`'s category-(c) list and its
"H4a — migration mapping" table are the authoritative record of every
item this applied to and where its content now lives — a slimmed
category-(c) comment's pointer must cite the **new home** from that
table, not the number the original comment happened to cite (which was
often wrong, or missing entirely).

## What this policy does not cover

Runtime **data** that happens to contain narrative prose — e.g.
`eval/cli.py`'s `KNOWN_GAP_TOLERANCES` dict, whose `"rationale"` string
values are printed in gate reports — is not a comment and is out of
scope for slimming. Touching it would change program output, not just
readability.

## Verification for every slimming change

- `git diff` per file must show only comment/blank-line hunks — a diff
  touching any non-comment line is a bug in the slimming pass, not a
  refactor.
- Python/shell files: `make test` and `make eval-fast` stay green;
  `bash -n` on every touched shell script.
- YAML under a kustomize tree (`deploy/kustomize/...`): diff the
  **rendered** output (`oc kustomize <overlay>`) before and after, not
  the source — must be byte-identical except for whitespace inside
  comment-only regions the renderer already strips. Tekton
  `Pipeline`/`Task` YAML not part of a kustomize tree: diff the
  **parsed** YAML structure (comments aren't part of it once parsed).
- Python files under `agent/`, `mcp_server/`, `approval_service/` are
  baked into container images (`Containerfile.agent`/`.mcp`/`.approval`)
  — per `CLAUDE.md`'s workflow rule, changes there go through a feature
  branch and the pipeline's own promotion-gate checks before merging,
  even though the change is comment-only. `scripts/`, `pipelines/`,
  `deploy/`, `platform/` are not copied into any image and may commit
  directly to `main`, per the same rule's docs/non-image-tooling
  exception.
