# Phase F2 — STOP 3 conditional-clearance evidence

Owner conditionally cleared STOP 3 pending evidence for three checks
(not assertion). This report captures the actual commands run and their
real output for each, plus F2's own literal-sweep/boundary-count results
on the record (previously only summarized in chat, not evidenced in a
committed artifact).

## 1. Repo-side effects of `skeleton/` on the built image

**(a) `skeleton/` is outside the Containerfile `COPY` list:**

```
$ grep -n "^COPY" Containerfile
10:COPY requirements.txt .
14:COPY agent/ ./agent/
15:COPY mcp_server/ ./mcp_server/
16:COPY approval_service/ ./approval_service/
17:COPY policy/ ./policy/
18:COPY corpus/ingest.py ./corpus/ingest.py
19:COPY --chmod=0755 entrypoint.sh ./entrypoint.sh

$ grep -n "skeleton" Containerfile
(no output -- zero references)
```

**(b) The built image is byte-identical before and after every Phase F
commit, not just "should be" — built both and compared:**

Built from `ff4102e` (the commit immediately before any Phase F1/F2 file
existed) in one worktree, and from `ccd6b81` (current HEAD, `skeleton/`
+ `template-schema.json` + `tools/verify_skeleton.py` + `catalog-info.yaml`
+ all `DECISIONS.md`/`PINS.md`/`docs/` changes present) in another,
both via `podman build -t <tag> -f Containerfile .`:

```
$ podman images --format "{{.Repository}}:{{.Tag}}  {{.ID}}  {{.Digest}}" | grep skeleton
localhost/test-before-skeleton:latest  92f10722065b  sha256:826786ccf5b26d92cee00c6f3174a6e2c97203f74d8ba520b8fd05e310cd6e96
localhost/test-after-skeleton:latest   92f10722065b  sha256:826786ccf5b26d92cee00c6f3174a6e2c97203f74d8ba520b8fd05e310cd6e96
```

Image ID and digest are identical. `podman inspect --format '{{.Id}}'`
on both returns the same value
(`92f10722065b504c499b9e46f7ab44038a8318cc17f1acd3d525610d714b9716`).
Test images removed after comparison.

## 2. Run what the pipeline runs, locally, against repo root

Reproduced the exact commands from `ci/pr-checks.yaml` /
`pipelines/tasks/unit-tests.yaml` / `pipelines/tasks/eval-gate-offline.yaml`
/ the `Makefile`'s `lint` target, inside a `python:3.12-slim` container
with the repo root bind-mounted (matching the pipeline's own
`pip install -r requirements.txt -r requirements-dev.txt` step), against
the actual current worktree content (`skeleton/` present):

**pytest — collection first, to prove `skeleton/tests/` isn't picked up:**
```
$ pytest -q --collect-only 2>&1 | tail -3
...
252 tests collected in 4.24s
```
252 matches the pre-existing baseline exactly — `pyproject.toml`'s
`testpaths = ["tests"]` scopes collection to the top-level `tests/`
directory only; `skeleton/tests/` (210-file skeleton's own copy) is a
different, unlisted directory and is never scanned.

**pytest — full run:**
```
$ pytest -q
........................................................................ [ 28%]
........................................................................ [ 57%]
........................................................................ [ 85%]
..........................s.........                                     [100%]
251 passed, 1 skipped, 1 warning in 28.39s
```

**lint (`Makefile`'s exact command, scoped to `agent mcp_server eval` —
sibling directories to `skeleton/`, never matched):**
```
$ python -m py_compile $(find agent mcp_server eval -name '*.py')
LINT PASS: all agent/mcp_server/eval .py files compile
```

**eval-gate (`ci/pr-checks.yaml`'s exact command):**
```
$ AGENT_MODEL_MODE=fake python -m eval.cli run --all
[PASS] EXAMPLE-001
[PASS] EXAMPLE-002

2/2 cases passed
```
2/2, not 4/4 — confirms `eval.cli`'s case loader isn't picking up
`skeleton/eval/cases/`'s duplicate fixtures either.

**No other repo-wide linter config exists** (`.flake8`, `ruff.toml`,
`setup.cfg`, `.pylintrc` all absent; `pyproject.toml`/`Makefile`/
`ci/pr-checks.yaml`/`pipelines/tasks/*.yaml` grepped for `ruff`/`flake8`/
`pylint`/`mypy` — zero hits) that could glob repo-wide and pick up
`skeleton/`'s template-syntax files some other way.

## 3. Substitution-order guarantee (longest-match-first, not incidental)

**Positive example** — a single source line containing both a suffixed
identifier and the bare base identifier side by side
(`pipelines/bootstrap/otel-collector.yaml:104`):
```
SOURCE:   # already-pushed image (golden-path-agent-ci/golden-path-agent),
SKELETON: # already-pushed image (${{ values.name }}-ci/${{ values.name }}),
```
Both resolved correctly and independently — no cross-contamination.

**Repo-slug case** (`pyproject.toml`), where the *longer* pattern
(`golden-path-agent-template`) must be matched before the *shorter* one
(`golden-path-agent`) or it's shadowed:
```
SOURCE:   name = "golden-path-agent-template"
SKELETON: name = "${{ values.repoName }}"
```

**Negative control — same three rules, reversed (shortest-first) order,
proving the ordering is load-bearing, not coincidentally correct:**
```
$ echo 'name = "golden-path-agent-template"' | sed \
    -e 's/golden-path-agent/${{ values.name }}/g' \
    -e 's/golden-path-agent-template/${{ values.repoName }}/g' \
    -e 's/DarkDragonEl\/golden-path-agent-template/${{ values.repoOwner }}\/${{ values.repoName }}/g'
name = "${{ values.name }}-template"
```
Wrong: `golden-path-agent` is consumed first, stranding `-template`
outside any placeholder — the `repoName` pattern can no longer match
because its target substring no longer exists. The actual rule order
used (`DarkDragonEl/golden-path-agent-template` → `golden-path-agent-template`
→ `golden-path-agent`, longest-to-shortest, applied in exactly this
sequence via ordered `sed -e` expressions) avoids this by construction,
confirmed by the correct output above matching `skeleton/pyproject.toml`'s
actual committed content.

## 4. `verify_skeleton.py` — on the record

```
$ python3 tools/verify_skeleton.py
Rendering skeleton/ with test values into .../.skeleton-verify-scratch ...
PASS: zero surviving 'golden-path-agent' occurrences in the rendered output
PASS: zero unresolved template placeholders in the rendered output

All checks passed. (210 skeleton files rendered and swept.)
$ echo $?
0
```

**Boundary DoD, by count:**
```
$ grep -c '@mcp\.tool' mcp_server/server.py
5
$ grep -c '@mcp\.tool' skeleton/mcp_server/server.py
5
```
Identical count — no scaffold-invoking sixth tool exists in the skeleton.

## Summary

| Check | Result |
|---|---|
| `skeleton/` outside Containerfile `COPY` list | Confirmed (grep, zero hits) |
| Built image digest unaffected | Confirmed identical (`sha256:826786cc...`, both builds) |
| `pytest -q` (252 tests, scope confirmed) | 251 passed, 1 skipped |
| `py_compile` lint (scope confirmed) | Pass |
| `eval.cli run --all` (2/2, scope confirmed) | 2/2 passed |
| Substitution order (positive + negative control) | Confirmed load-bearing, correct as committed |
| `verify_skeleton.py` | Exit 0, both checks pass |
| Boundary tool count | 5 == 5 |

All three STOP-3 conditions satisfied with executed evidence, not
assertion. Proceeding to F3 per owner authorization.
