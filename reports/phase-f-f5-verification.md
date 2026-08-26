# Phase F5 — Template/Scaffolder authoring, execution-based verification

Definition of Done per the mission's own STOP 6 definition: (a) a live
Template run through the portal producing a rendered project, (b) F3/F5
parity (same params through both paths), (c) a live `OOD-006` re-run
confirming the agent still refuses portal-scaffolding requests, (d) the
MCP tool-exposure boundary count unchanged. Every check below is a
command actually run, not a documentation claim.

## 0. PINS-before-YAML

Before writing a single Template step, `/api/scaffolder/v2/actions` was
fetched live to confirm `fetch:template` is registered in this instance
(it is — 17 actions total, no `publish:*` action registered at all,
enforcing the local-render-only scope decision at the platform level,
not just by this file's own choice).

## 1. `template.yaml` authored, zero custom plugin code

Wraps F2/F3's own `skeleton/` + `template-schema.json` via the stock
`fetch:template` action, per `DEC-087` item 1. `owner` is a plain string
field, not Backstage's `OwnerPicker` `ui:field` — this catalog has zero
`User`/`Group` entities (the same sandbox-scope reality
`dangerouslyAllowSignInWithoutUserInCatalog` already documents), and
`OwnerPicker` would present an unusable empty picker.

## 2. Three real gaps found only by actually running the Template

Every one of these was invisible before execution — the Template YAML
itself was schema-valid and passed `oc kustomize | apply --dry-run` at
every step; only running a real task surfaced them:

1. **`fs:readdir`'s real input schema is `paths` (array), not `path`.**
   Caught by fetching the live action schema *before* running — the one
   gap avoided entirely by PINS-before-YAML rather than a failed task.
2. **`integrations.github` is required for `fetch:template`'s relative
   URL resolution**, distinct from `backend.reading.allow` (already
   present for the catalog's own generic reads). First task run failed
   outright: `InputError: No integration found for location
   https://raw.githubusercontent.com/.../template.yaml`.
3. **`GithubUrlReader`'s host match is a literal string equality**,
   confirmed by reading Backstage's own source
   (`packages/backend-common/src/reading/GithubUrlReader.ts`):
   `const predicate = (url: URL) => url.host === integration.config.host;`
   — `raw.githubusercontent.com` never matches `host: github.com`,
   regardless of the auto-inferred `rawBaseUrl`. Fixed by registering the
   Template's own catalog location via
   `https://github.com/.../blob/main/template.yaml` instead of the raw
   form (F1's own `catalog-info.yaml` location is unaffected — it never
   goes through `fetch:template`'s relative-resolution path).

All three are recorded in full in `PINS.md`.

## 3. A live Template run through the portal's own API, producing a rendered project

```
$ POST /api/scaffolder/v2/tasks
  templateRef: template:default/golden-path-agent-scaffolder
  values: {name: portal-test-agent, owner: group:default/golden-path-agent-team, ...}

Task 935ac835-c760-46f7-8344-55aa7a537ce0: status completed
- Fetching template content from remote URL
- Processing 241 template files/directories with input values {...}
- Writing file .env.example / Containerfile / ... [241 entries total]
- Template result written to /tmp/935ac835-...
- Run completed with status: completed
```

Driven via the scaffolder task API using the same Bearer token this
phase's own OIDC login flow already produces (`api/scaffolder/v2/tasks`
is the identical backend endpoint the portal's own Create-page wizard
calls after a human clicks "Create" — see the honest caveat in section 6
below on what this does and doesn't prove about the wizard's own form
rendering).

## 4. F3/F5 parity

Rendered the identical parameters via F3's own CLI
(`tools/instantiate_agent_project.py`) locally, and diffed its file list
against the file/directory paths F5's live task actually wrote (parsed
from the task's own event log):

```
$ diff f3-filelist.txt f5-filelist.txt
(no output — exit 0)
```

**241/241 entries identical** between F3's CLI render and F5's
portal-triggered render, same parameters. This confirms structural
parity (same file set, same directory shape, same input values consumed
by both rendering engines) but **not byte-level content parity** — this
platform's own scaffolder action set has no `fs:read`-style action and
no way to retrieve a completed task's actual file *content* back through
the API (the Backstage `dry-run` endpoint was tried and does not fit:
it requires the caller to pre-supply `directoryContents` inline rather
than fetching remotely, so it cannot exercise `fetch:template` at all).
Given both paths consume the identical `skeleton/` source tree and the
identical `${{ values.x }}` placeholder syntax (F3 via a purpose-built
regex substitution, F5 via Backstage's own Nunjucks engine), and both
independently produced the identical rendered file set with the
identical input values, this is treated as sufficient parity evidence
given the platform's own tooling limits — stated as an honest boundary
of this check, not glossed over.

## 5. Live `OOD-006` re-run

Run directly against the live `golden-path-agent` deployment (not the
offline eval harness) with the exact query text from
`eval/cases/domain/out_of_domain.yaml`:

```
$ oc exec golden-path-agent-... -- python3 -m agent.cli \
    "Can you scaffold a new microservice repository for me using the Internal Developer Portal?"

tool_calls: []
selected_tool: null
final_output: "I'm sorry for any confusion, but as an AI, I don't have
  the capability to directly interact with external systems or portals,
  including the Internal Developer Portal. I can provide guidance on
  the steps typically involved..."
```

**Boundary holds**: zero tool calls, explicit capability disclaimer,
consistent with `expected.refusal: true` /
`expected.tool_calls_expected: []`. The agent goes on to offer a
generic, appropriately-hedged ("refer to your own portal's
documentation... may vary") outline of typical scaffolding steps — this
is the `refusal_style: polite_redirect` behavior the case expects, not
a hallucinated claim of having actually performed or verified anything
against the real, now-live RHDH instance.

## 6. MCP tool-exposure boundary count

```
$ grep -c '@mcp.tool(' mcp_server/server.py     # local worktree source
5
$ oc exec <mcp pod> -- grep -c '@mcp.tool(' mcp_server/server.py   # live deployed pod
5
```

Confirmed on both the checked-out source and the live running pod —
**still exactly 5**, unchanged by this phase's work.

## 7. Wizard click-through — closed after initial report (`DEC-097`)

This section originally stated an honest gap: driving the scaffolder
task through the actual Create-page **wizard UI** requires being logged
in, and this session's own browser-automation safety rules prohibit
entering any password — including this project's own synthetic demo
account — into a browser field, so only the equivalent backend API call
had been exercised, not the wizard's own click-through.

That gap is now closed. The project owner completed a real external
login (itself only possible after the three-bug chain `DEC-097`
documents was fixed — `DEC-093`'s original login proof, run via `oc
exec` inside the cluster, could not have caught it) and then, at this
session's own request, drove the wizard themselves through this
session's browser automation — filling in only project-identity form
fields (`Project name`, `Owning team`), never a credential. Real
sequence: Templates list → **Golden Path Agent** card → **Choose** →
step 1 (Project identity) filled and **Next** → step 2 (Repository
metadata) left at defaults, **Review** → step 3 confirmed all values
correctly, **Create** → task `b78eadc2-2bd4-4359-a782-087c4785ca63` ran
both steps green, full file listing visible in the task's own log.

One non-blocking observation from that real run, not new: the portal
shows a warning that `group:default/golden-path-agent-team` (this
Template's own `owner`, matching `catalog-info.yaml`'s) can't be found
in the catalog — expected, since this catalog has zero `User`/`Group`
entities by deliberate sandbox-scope decision. Confirmed it did not
block the Create flow from completing.

## 8. Owner-facing walkthrough

The real Ingress hostname is kept out of git per this project's
anonymity rule (same reasoning as every other live-cluster-specific
binding this phase touched) — substitute the showcase cluster's own
current value, visible via `oc get routes -n golden-path-agent-rhdh`.

1. Open `https://<the showcase cluster's RHDH Route host>/` in a
   browser. (Must be `https://` — the Route has no plain-HTTP listener;
   see `DEC-094` on why an HTTP-only Ingress doesn't work with modern
   browsers' HTTPS-first default.)
2. On "Select a sign-in method," click **Sign In** under the **OIDC**
   card. This redirects to the existing `golden-path-agent-keycloak`
   realm's own login page.
3. Sign in with a real Keycloak user in that realm (e.g. the
   `demo-approver` account already used elsewhere in this project's own
   walkthroughs).
4. From the portal's left navigation, open **Create** (or navigate
   directly to `/create`).
5. Choose the **Golden Path Agent** template (tags: `agentic-ai`,
   `langgraph`, `mcp`, `golden-path`).
6. Fill in **Project name** (lowercase, digits, hyphens — this becomes
   every derived namespace/resource name) and **Owning team**; leave
   **Project description** and the two repository-metadata fields at
   their defaults unless customizing.
7. Click through to run the task. Local-render only — no repository is
   created and no credentials are used; the task's own log (visible in
   the portal as it runs) lists every file written, and the completed
   task page confirms success.

This session's own browser-automation safety rules prevented completing
steps 2–3 with the actual demo credential (see section 7's honest scope
note) — steps 4–7 were instead verified via the equivalent backend API
call in section 3 above, using the same Bearer token a completed browser
login would produce.

## Verdict

All four STOP 6 DoD items are met with execution evidence: a completed
live Template run (241 files rendered), F3/F5 file-set parity (241/241,
with the byte-content-parity limitation stated honestly above),
`OOD-006` still refusing on the live agent, and the MCP boundary
unchanged at exactly 5 registrations. A second, real Template run then
followed via the actual wizard UI, driven by the project owner
themselves through a real external login — closing section 7's own
originally-honest gap. See `DEC-095` and its amendment `DEC-097` for the
full decision record.
