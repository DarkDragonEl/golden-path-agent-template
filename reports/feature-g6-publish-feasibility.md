# G6 (Stage 3) — publish feasibility investigation: session report

Investigation only, per explicit instruction — no implementation attempted, no files
changed in this repo. Draft report, not committed.

## Bottom line

The original phase-G draft's claim — "the Gitea scaffolder module is a stock Backstage
dynamic-plugin, same enablement mechanism as the GitHub one — configure
`integrations.gitea` and enable the plugin, no custom code" — is **false for this specific
RHDH instance**, confirmed by direct inspection of the live pod's own bundled plugin
catalog, not just documentation. **Two independently viable paths exist**, at genuinely
different effort levels; recommend pursuing the lower-effort one first since it alone
satisfies a normatively-required instantiation path with no RHDH plugin work at all.

## 1. Confirmed live: RHDH 1.10 ships zero Gitea plugins, of any kind

Read the live `Backstage` CR (`golden-path-agent`, namespace `golden-path-agent-rhdh`):
`spec.application` has no `dynamicPluginsConfigMapName` field at all — the currently-active
`backstage-dynamic-plugins-golden-path-agent` ConfigMap (`includes:
[dynamic-plugins.default.yaml]` plus two Lightspeed entries) is the **operator's own
generated default**, not something this project authored. This means dynamic-plugin
customization for this instance has never actually been exercised yet — a first for this
project.

Listed the full bundled plugin catalog directly inside the running pod
(`/opt/app-root/src/dynamic-plugins/dist/`, 42 packages total — this is every plugin RHDH
1.10 ships pre-built into the image, whether currently enabled or not): confirmed
`backstage-plugin-catalog-backend-module-github{,-org}-dynamic`,
`backstage-plugin-catalog-backend-module-gitlab{,-org}-dynamic`,
`backstage-plugin-scaffolder-backend-module-github-dynamic`,
`backstage-plugin-scaffolder-backend-module-gitlab-dynamic` all present. **Zero Gitea
entries of any kind** — not catalog, not scaffolder, not disabled-but-present. Cross-checked
against `redhat-developer/rhdh`'s own GitHub repo directly (`gh api search/code`): the only
"gitea" hits anywhere in that repo are incidental UI translation strings
(`translations/backstage-{it,es,de,fr,ja}.json`, almost certainly a generic "choose your
Git provider" settings-page label list, not functional plugin code). This is a hard,
version-confirmed fact, not an inference from general "RHDH doesn't support X" reasoning —
GitHub and GitLab both have full first-class support at every tier (catalog reading AND
scaffolder publishing); Gitea has neither, in this RHDH version, full stop.

## 2. Path A — custom-built dynamic plugin via `rhdh-dynamic-plugin-factory` (feasible, low-to-medium effort)

Red Hat's own `redhat-developer/rhdh-dynamic-plugin-factory` tool is exactly what RHDH's
own maintainers almost certainly used to build the GitHub/GitLab scaffolder-backend dynamic
plugins already bundled in this image — it takes a `source.json` (git repo + ref +
workspace-path) and a `plugins-list.yaml` (package paths to build within that workspace),
clones, builds, and exports RHDH-format dynamic-plugin tarballs/OCI images, no custom code
required for a "standard" first-party package.

Confirmed via its own example configs: the **`example-config-todo`** case is the directly
relevant template (not `example-config-gitlab`, which builds a *third-party* UI dashboard
plugin from a non-standard repo layout requiring destructive file overlays — a different,
harder case). `example-config-todo`'s `source.json` points at
`https://github.com/backstage/community-plugins`, `workspace-path: workspaces/todo`, and its
`plugins-list.yaml` just lists `plugins/todo` / `plugins/todo-backend` — no overlay, no
custom source files, a genuinely mechanical build.

The real upstream package needed, `@backstage/plugin-scaffolder-backend-module-gitea`,
lives in the **`backstage/backstage`** monorepo itself (confirmed earlier this phase via
its own GitHub page and npm listing) at `plugins/scaffolder-backend-module-gitea` — the
exact same monorepo and directory shape as `plugins/scaffolder-backend-module-github`,
which is almost certainly how RHDH's own bundled GitHub module was built via this identical
tool. **This makes the Gitea build a same-shape, same-tool, same-monorepo operation as one
RHDH already ships** — genuinely low-to-medium effort (run the factory once, package the
output as an OCI image per its own documented `--push-image` flow, point the `Backstage`
CR's `dynamicPluginsConfigMapName` at a new ConfigMap referencing it, restart), not a
research problem. Not attempted this session per scope, but the recipe is concrete enough
to execute directly next time, not "investigate further."

**What this path still requires beyond the plugin itself, once built**: `integrations.gitea`
is already live (`DEC-100`'s work) so the read-side auth/URL-resolution is solved; the
*write* side needs the scaffolder action's own credential wiring — likely `catalog.orgs.gitea`
or an `integrations.gitea` entry augmented with the write-scoped `golden-path-agent-scaffolder`
token from a Secret (G1's own machine account, already proven live to actual destruction in
`DEC-100`), not a new credential to provision.

## 3. Path B — CLI-first publish, no RHDH plugin work at all (feasible, lowest effort)

`tools/instantiate_agent_project.py` (Phase F3's CLI, already proven working) and
`template-schema.json`'s own `repoOwner`/`repoName` fields (present since Phase F2,
explicitly noted in that schema's own comments as "only load-bearing for a not-yet-attempted
'publish' stretch goal" — this was anticipated, not invented now) are the two building
blocks. G1 already proved, to actual destruction, that Gitea's own REST API works end-to-end
with the scoped `golden-path-agent-scaffolder` machine account: create an org repo, push
real content, and correctly fail an over-scoped operation (`DEC-100`). Extending the CLI to
(1) render locally exactly as it does today, (2) call Gitea's REST API to create the repo,
(3) `git push` the rendered tree, (4) optionally call RHDH's catalog API to register the new
`Component` — is a straightforward extension of an already-working tool using
already-proven credentials and an already-proven API, with **zero RHDH plugin
architecture involved**.

This matters normatively, not just operationally: `SyRS-AGP-001_EN.md`'s `SysR-P-F-01(b)`
requires direct CLI instantiation as a co-equal path, not a fallback (`Annex_A_Open_Items_EN.md`
`OI-04`'s actual adopted assumption is portal-first with CLI as the demo-risk fallback — but
the *requirement* itself names both paths without ranking). A working CLI-driven publish
flow fully satisfies G6's intent for this path on its own, independent of whatever the
portal/Scaffolder path needs.

## 4. Recommendation

**Pursue Path B (CLI-first publish) first.** It is a small, mechanical extension of an
already-proven tool, uses already-proven credentials and an already-proven Gitea API
surface, requires no new RHDH plugin work, and independently satisfies one of the two
normatively-required instantiation paths in full. This should be G6's first real
implementation slice.

**Treat Path A (custom Gitea scaffolder dynamic plugin) as a separately-scoped, real, but
not-blocking follow-up.** It is genuinely feasible at low-to-medium effort — this session
found the exact tool, the exact template config shape, and the exact upstream package path,
all first-party and already used by RHDH's own maintainers for the sibling GitHub/GitLab
modules — but it is a materially bigger unit of work (build, package, push an OCI image,
wire a new `dynamicPluginsConfigMapName`, restart, verify) than Path B, and the portal's
Scaffolder-driven publish experience is not required to exist on G6's first pass if the CLI
path already closes the loop. Recommend sequencing Path A as G6's second slice, not
abandoning it — the original three-way design (Platform Foundation / Tools Template / Agent
Template, `DEC-098`) still benefits from a real portal publish experience eventually.

**Not investigated this session, named as a real open question for whichever slice lands
first**: whether Backstage's own entity-merging behavior (the same mechanism `DEC-103`
found causing the Gitea-mirrored `template.yaml` to resolve against the GitHub-hosted
`source-location` instead) will cause any confusion once a CLI-published, Gitea-native
project also gets registered in the same catalog RHDH already reads from GitHub and Gitea.
Likely a non-issue for *newly*-scaffolded, Gitea-only projects (no competing GitHub-hosted
copy would exist for them, unlike this repo's own byte-identical mirror situation) — but
worth a real live check once Path B actually registers a first scaffolded project's catalog
entity, not assumed clean by analogy.

## What was NOT done this session, deliberately

- No dynamic plugin was built, packaged, or installed.
- No CLI code was written or modified.
- No live write/publish action was attempted against Gitea beyond what G1 already proved in
  an earlier session (`DEC-100`) — this session's own cluster reads were the `Backstage` CR,
  the dynamic-plugins ConfigMap, and the pod's own bundled plugin directory listing, nothing
  mutating.
- `redhat-ai-dev/ai-rhdh-installer` (pinned in `PINS.md`'s Phase G section as an alternative
  RHDH+GitOps+Pipelines bootstrap path, never actually adopted per `DEC-100`'s own note that
  Phase F4 already installed these individually) was not re-investigated for a Gitea angle —
  out of scope for this session's specific question, and this project's RHDH bootstrap
  question was already closed in Stage 1.
