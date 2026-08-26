# Previewing this documentation site locally

This whole `docs/` tree, plus `mkdocs.yml` at the repo root, is the same
source RHDH's live TechDocs plugin renders for this project's catalog
entity — see `docs/architecture.md` for where that entity lives, and
`catalog-info.yaml`'s `backstage.io/techdocs-ref` annotation for the
wiring. Two ways to preview it yourself:

## Plain preview (matches what RHDH renders)

```
pip install -r requirements-docs.txt
mkdocs serve
```

Open `http://127.0.0.1:8000`. This uses `mkdocs.yml` exactly as written —
the same plugin set (`mkdocs-techdocs-core` only) confirmed live in
RHDH's own generator venv (`PINS.md`'s Phase H section), so what you see
here is what the live TechDocs page shows.

## Fuller local preview, with a generated API reference

```
pip install -r requirements-docs-local.txt
mkdocs serve -f mkdocs.local.yml
```

This adds `docs/reference/api.md` — a docstring-generated reference for
every module under `agent/`, `mcp_server/`, `approval_service/`, and
`eval/`. **This section does not appear on the live RHDH page** — RHDH's
own bundled generator venv (`/opt/techdocs-venv` inside the running
`backstage-golden-path-agent` pod) does not have `mkdocstrings` installed,
confirmed by exec'ing into it directly rather than assumed. Adding it
there would mean shipping a custom RHDH image, which is out of scope for
this milestone — `mkdocs.local.yml` exists so the fuller reference is
still one command away for anyone working on this repo directly.

## Validating before committing a docs change

```
mkdocs build --strict
```

Run this — not just `mkdocs serve` — before committing any change to
`docs/`, `mkdocs.yml`, or its `nav`. `--strict` fails the build on a
broken internal link or an orphaned page (one that exists in `docs/` but
isn't reachable from `nav`), the same class of problem the CI link-check
step (`ci/pr-checks.yaml`'s `lychee` stage) catches for prose-level links.
