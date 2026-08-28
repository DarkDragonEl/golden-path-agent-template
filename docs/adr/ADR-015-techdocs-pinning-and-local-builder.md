# ADR-015: TechDocs Generator Pinning and Local-Builder Wiring

## Context
This repository's docs are meant to render through the platform portal's real
TechDocs generator, not just build cleanly in isolation. That generator's
bundled environment has a fixed, specific set of installed Python packages; a
`mkdocs.yml` requesting a plugin it lacks (e.g. `mkdocstrings`) fails the live
build outright, since MkDocs raises on an unresolvable plugin entry point
rather than skipping it.

## Decision
The root `mkdocs.yml` — the file the portal actually reads — is pinned to
exactly what the portal's bundled generator has installed (`mkdocs`,
`mkdocs-techdocs-core`, `mkdocs-material`, live-verified versions, not PyPI
latest). A second file, `mkdocs.local.yml`, inherits from it and adds
`mkdocstrings` for a fuller local-only preview. The catalog entry is wired
for local generation (`backstage.io/techdocs-ref: dir:.`, a `builder: local`
app-config), so the portal renders these docs on demand with no separate
docs-publishing infrastructure.

## Consequences
- Adopters must not add a plugin to the root `mkdocs.yml` without first
  confirming it is installed in the portal's actual generator venv — the live
  pod's own installed packages are the source of truth, not documentation.
- Richer local-only tooling belongs in `mkdocs.local.yml`, never the root
  file, so local convenience never risks the live portal build.
- `builder: local` suits this project's single-replica demo deployment; a
  multi-replica production portal needs a different, out-of-process build
  path and should not be assumed to scale unchanged.
- GitOps-managed app-config (the techdocs ConfigMap) must land via a
  committed, synced change, not a live patch — selfHeal reverts those.
- A full authenticated browser round trip confirming the rendered docs page
  (only log-level confirmation exists) was not verified and remains open.

## Supersedes / Superseded-by
None.

## Journal
DEC-120, DEC-121
