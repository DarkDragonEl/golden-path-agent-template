# G6 (Stage 3) — Gitea Scaffolder dynamic plugin: time-boxed spike report

Directive: build a working `publish:gitea` RHDH dynamic plugin, wire it into the live
instance, and prove a real Scaffolder task (the browser-wizard code path) can create+push
to a real Gitea repo. Time-boxed to roughly one working session.

## Bottom line

**The hard technical uncertainty is resolved, with a real artifact to show for it: the
Gitea scaffolder module builds and packages cleanly as an RHDH dynamic plugin, using the
exact same first-party tool RHDH's own maintainers used for the already-bundled
GitHub/GitLab modules.** The spike did not reach a live, wizard-triggered end-to-end test —
not because anything technical broke, but because the cluster session token expired
mid-spike (`oc whoami` now returns `Unauthorized`) after a large, legitimate build
operation ran long. Per this project's own explicit policy
(`scripts/bootstrap.sh`'s header: *"Never runs `oc login` — credential handling stays the
owner's own one-time step"*), re-authenticating is not this session's call to make, so the
live-cluster half of the spike stops here, cleanly, rather than attempting a workaround
around a stated security boundary. **This is very likely the same session/`oc` config the
coordinating session itself uses — the coordinator may need to re-authenticate too before
picking this up.**

What's left is short and mechanical, not another round of discovery — see "What's left" below.

## 1. Pin (per `PINS.md` convention, drafted here, not committed)

| Component | Realization | Channel/Version | Support level | Verified date | Source URL | Notes |
|---|---|---|---|---|---|---|
| RHDH dynamic-plugin build tool | `redhat-developer/rhdh-dynamic-plugin-factory` container image | `quay.io/rhdh-community/dynamic-plugins-factory:1.10`, digest `sha256:ab3ab5eb73ba2f2080697f334478b9987c68468ce878d18802a4baeb90dac96c` | community (`redhat-developer` org, no official support — this image tag line is explicitly the RHDH-1.10-targeted build per the repo's own tag scheme) | 2026-08-26 | https://github.com/redhat-developer/rhdh-dynamic-plugin-factory · `quay.io/rhdh-community/dynamic-plugins-factory` | Repo's own git tags are `1.8.0`/`1.9.1` (no `1.10.0` git tag exists), but the **container image** tag `1.10` is real, pulls cleanly, and bakes in `RHDH_CLI_VERSION=1.10.7` — confirmed by exec'ing into the pulled image and reading its own `default.env`, not inferred from the tag name alone. This is the correct artifact to pin, not a git ref of the source repo. |
| Backstage source (for the Gitea module itself) | `backstage/backstage` monorepo, `plugins/scaffolder-backend-module-gitea` | tag `v1.49.0` | community (upstream Backstage core) | 2026-08-26 | https://github.com/backstage/backstage | **Not an arbitrary choice** — confirmed live that `backend-defaults@0.16.0` (the version actually running inside this RHDH 1.10.3 instance's own pod, read via `find`/`cat package.json` inside the container) matches exactly `backstage/backstage@v1.49.0`'s own `packages/backend-defaults/package.json`. Building the module from a mismatched Backstage version risks a peer-dependency/API mismatch at load time — this ref is the one that actually corresponds to what's running. |

## 2. TLS/reachability pre-check — passed clean, no CA work needed

Tested live, with a real request from inside the running RHDH pod (`oc exec ... curl -sv
https://golden-path-agent-gitea-golden-path-agent-gitea.apps.cluster-hj7xp.dyn.redhatworkshops.io/api/v1/version`)
**before** touching the plugin build, per the directive's own instruction not to assume
this from config inspection. Result: clean `TLSv1.3` handshake, `HTTP/1.1 200 OK`,
`{"version":"1.25.5"}`. This is the **same** Route host `integrations.gitea`'s read-only
entry already uses (`deploy/kustomize/overlays/rhdh/catalog-locations-config.yaml`, from
G1's earlier work) — the cluster's own trusted wildcard cert covers it, exactly as it
already covers RHDH's and Keycloak's own Routes. **No CA mounting needed, no host-literal
mismatch found** — unlike the read-side `GithubUrlReader`-vs-`GiteaIntegration` gap G1 hit
earlier this phase, this specific concern did not reproduce here. Worth re-confirming once
the actual `publish:gitea` action runs for real (it makes its own `fetch()` calls from
Node.js, not curl — a different HTTP client, in principle capable of its own quirks — but
no reason found yet to expect one).

## 3. Building the plugin — real, working recipe (with two real bugs found and worked around)

### Config used

`config/source.json`:
```json
{
  "repo": "https://github.com/backstage/backstage",
  "repo-ref": "v1.49.0",
  "workspace-path": "."
}
```

`config/plugins-list.yaml`:
```yaml
plugins/scaffolder-backend-module-gitea:
```

(`workspace-path: "."` because `backstage/backstage` is itself the plugin workspace root —
per the factory's own README: *"A standalone Backstage repository may have its workspace
be the repository itself."* No `--embed-package` needed — the `plugins-list.yaml` example
in the factory's own README showing `--embed-package @backstage/plugin-scaffolder-backend-module-github`
is for a *different* case; the Gitea module, like the GitHub one, is a full,
independently-exportable `backend-plugin-module` in its own right — confirmed via its own
`package.json`'s `backstage.role: backend-plugin-module` field, checked live via `gh api`
before assuming the plugins-list.yaml shape.)

### Real bug #1: `source.json`'s actual required field differs from the factory's own README and from the locally-clonable `1.9.1` git tag

The factory's published README (and the git tag `1.9.1` checked out locally for reference)
document `source.json` as just `{"repo": ..., "repo-ref": ...}`. **The actual code running
inside the pinned `:1.10` container image is newer than any published git tag** and reads
an additional, undocumented-in-the-README `"workspace-path"` field directly from
`source.json` (confirmed by `grep`-ing the *running container's own* `source_config.py`,
not the locally-cloned reference, once the mismatch was suspected) — omitting it produces
`ConfigurationError: workspace-path is required` before any real work starts. Fix: add
`"workspace-path": "."` to `source.json` directly (also confirmed that `--workspace-path`
as a bare CLI flag, or `-e WORKSPACE_PATH=...`, do **not** substitute for this in the
`source.json`-driven remote-fetch code path — only the `source.json` field satisfies it
there; the CLI flag only matters in the separate `--use-local` code path, see bug #2).

### Real bug #2 (really a real *inefficiency*, not a bug): the factory's remote-source path always does a full, unshallowed `git clone`

Confirmed live: a `git clone https://github.com/backstage/backstage <dest>` with **no
`--depth`** is what the factory's own `SourceConfig.clone()` runs. `backstage/backstage`'s
full history is large enough that this pulled ~7GB over the network and was still doing
disk-bound checkout work 20+ minutes in — a real, material cost for a monorepo this size,
not encountered by the factory's own example configs (which target the much smaller
`backstage/community-plugins` repo). **Worked around, not fixed upstream**: did a manual
shallow clone myself (`git clone --depth 1 --branch v1.49.0 ...`, 464MB, a few minutes) and
re-ran the factory with `--use-local --workspace-path .` pointing at the pre-cloned
directory — the factory's own `--use-local` flag exists exactly for this case (skip its own
clone, use a repo you already have). This dropped total build time from "still running past
20 minutes" to a clean, complete run in a few more minutes (yarn install ~5 min, TypeScript
compile + export + package, all successful).

### Result: real, successful build

```
INFO     Exporting plugins using RHDH CLI
INFO     ========== Exporting backend plugin plugins/scaffolder-backend-module-gitea ==========
INFO       > npx --yes @red-hat-developer-hub/cli@1.10.7 plugin export
INFO     ========== Packaging Container localhost/default/backstage-plugin-scaffolder-backend-module-gitea:0.2.19 ==========
INFO       > npx --yes @red-hat-developer-hub/cli@1.10.7 plugin package --container-tool buildah --tag ...
INFO     ========== Moving backend plugin plugins/scaffolder-backend-module-gitea archive into /outputs ==========
INFO     PUBLISHED_EXPORTS<<EOF
         localhost/default/backstage-plugin-scaffolder-backend-module-gitea:0.2.19
         EOF
INFO     Plugin export completed successfully
INFO     All operations completed successfully
```

Real artifact on disk (this machine, `/tmp/factory-run/outputs/`, not committed to the repo
— a 4.5MB binary tarball doesn't belong in git history, and this exact path won't survive
past this session anyway):
`backstage-plugin-scaffolder-backend-module-gitea-dynamic-0.2.19.tgz` (4,575,700 bytes),
integrity hash `sha512-jdGsTO1ZGp4odrvIYmUFMtEFSUmSOdnMnkj/HL6NoFsy7fwzEOnOz7a906+zy0cpOOsmdRmur8DuPiV/tpppCg==`.

**Important limitation on this specific artifact, stated plainly**: the factory ran with
`--no-push-images` (deliberately, to inspect success before committing to a registry
destination), and the container packaging step (`buildah`, invoked by the RHDH CLI's own
`plugin package` step) ran **inside the ephemeral factory container itself**, which was
started with `--rm`. That means the *container image*
(`localhost/default/backstage-plugin-scaffolder-backend-module-gitea:0.2.19`) that buildah
built no longer exists anywhere — it died with the container. **Only the `.tgz` npm-package
archive survived**, because that specific artifact was written to the host-mounted
`/outputs` directory. A future run needs to either re-run with `--push-images` and real
registry env vars (pushing directly out of the same ephemeral container before it's
removed), or mount `/var/lib/containers`-equivalent storage so the built image survives
the container's own removal. This is a real, avoidable rerun, not a dead end — the *build
itself* is proven to work; only the *distribution* step needs redoing with the registry
destination wired in from the start.

## 4. Read confirmed: exactly the credential this project already has, no new wiring needed conceptually

Read the actual `publish:gitea` action source at the pinned ref
(`plugins/scaffolder-backend-module-gitea/src/actions/gitea.ts`, `v1.49.0`) before assuming
anything about credentials:

- It creates the repo via `POST {gitea-base-url}/api/v1/orgs/{owner}/repos` — the **org**
  creation path, matching this project's own `golden-path-agent-projects` org exactly (not
  the alternate "under a user" path the action also supports but this project doesn't need).
- It authenticates via `getGiteaRequestOptions(config)` from `@backstage/integration`'s own
  `GiteaIntegrationConfig` — i.e., the **same** `integrations.gitea` config block G1 already
  established for reading (`deploy/kustomize/overlays/rhdh/catalog-locations-config.yaml`),
  just needing `username`/`password` fields added (currently absent, since the read-only use
  case needed none). The `password` field is Gitea's own convention for "API token, not
  literal password" here — the exact `golden-path-agent-scaffolder` token G1 already proved
  live to actual destruction (`DEC-100`) is the correct credential, not a new one to
  provision.
- Action `id: 'publish:gitea'`, registered by a completely standard
  `createBackendModule({pluginId: 'scaffolder', moduleId: 'gitea', ...})` — no unusual
  registration mechanism, no reason to expect RHDH's dynamic-plugin loader to reject it
  differently than the already-loaded GitHub/GitLab equivalents.
- Full real input schema (read directly from source, not guessed): `repoUrl`, `description`,
  optional `defaultBranch`/`repoVisibility`/`gitCommitMessage`/`gitAuthorName`/
  `gitAuthorEmail`/`sourcePath`/`signCommit`. Standard `RepoUrlPicker`-shaped output for
  `repoUrl` is exactly what every other publish action in this ecosystem already expects.

**Not yet verified live** (blocked on cluster access, see below): whether RHDH's own
`RepoUrlPicker` frontend component correctly recognizes a Gitea host once
`integrations.gitea` gains write credentials — this is a frontend concern, separate from
the backend action just proven to build, and genuinely unverified either way.

## 5. What's left — short, mechanical, blocked only on cluster session access

1. **Re-run the build with `--push-images`**, pointed at this cluster's own internal
   registry (reachable via `oc port-forward -n openshift-image-registry svc/image-registry
   5000:5000`, confirmed reachable earlier this session before the token expired — a plain
   `curl http://localhost:5000/v2/` needs registry auth to succeed, which needs a fresh
   `oc whoami -t` bearer token as the registry password once logged back in). This avoids
   losing the built image to container teardown a second time.
2. **Author a new `dynamic-plugins.yaml` ConfigMap** referencing the pushed image, alongside
   the existing bundled set (confirmed live, before the token expired, that the current
   `backstage-dynamic-plugins-golden-path-agent` ConfigMap's real shape is:
   `includes: [dynamic-plugins.default.yaml]` plus explicit `plugins: [{package: oci://...,
   disabled: false}, ...]` entries for the two Lightspeed plugins already added on top of the
   default set — the new Gitea entry is one more list item in that same shape, not a
   structural change). Point the `Backstage` CR's own `spec.application.dynamicPluginsConfigMapName`
   at the new ConfigMap (confirmed live: this field is currently **unset** — the operator is
   generating today's ConfigMap automatically — this will be the first time this project
   customizes RHDH's dynamic-plugin set at all).
3. **Add write credentials to `integrations.gitea`** (`username`/`password` fields, pulling
   the token from the already-proven `golden-path-agent-gitea-scaffolder-token` Secret —
   confirm it's still there and unexpired before assuming so, per this project's own
   verify-don't-assume discipline).
4. **Add a `publish:gitea` step to a *test copy* of the template** (per the original
   directive — don't touch the real, live `template.yaml` until this is proven), using the
   real input schema confirmed in §4.
5. **Run one real Scaffolder task** through RHDH's real `POST /api/scaffolder/v2/tasks`
   endpoint and confirm, live: task completes, a real repo exists in Gitea, real content is
   in it.
6. Clean up the test artifacts (the ConfigMap can stay if the plugin genuinely works;
   the test-copy template and the test repo in Gitea should not).

None of this requires further research — every open question the directive posed (pin the
factory, pre-check TLS, confirm the build recipe, confirm the credential shape) has a
confirmed, live answer above. What's left is applying already-known changes and running
already-scoped commands, which needs a live, authenticated cluster session this one no
longer has.

## Drafted decision entry (placeholder `DEC-1xx`; NOT committed, per this session's
governance — the coordinating session lands this at merge, regardless of whether the spike
is later completed or abandoned)

```
## DEC-1xx — G6 Path A spike: the Gitea scaffolder dynamic plugin builds
and packages successfully using the same first-party tooling RHDH's own
maintainers used for the bundled GitHub/GitLab modules; live RHDH wiring
and the end-to-end wizard test are not yet done, blocked on cluster
session expiry mid-spike, not on any technical wall

**Context**: `DEC-110` chose Path B (CLI-first publish) as G6's first
slice and named Path A (a custom Gitea Scaffolder dynamic plugin) as a
real, non-blocking follow-up. The owner directed a time-boxed spike on
Path A before settling for Path B alone, since a working plugin would
restore the original design's `STOP 8` (owner runs the wizard through a
real browser).

**Pinned**: `quay.io/rhdh-community/dynamic-plugins-factory:1.10`
(digest `sha256:ab3ab5eb73ba2f2080697f334478b9987c68468ce878d18802a4baeb90dac96c`)
-- the RHDH-1.10-targeted build tool, bakes in `RHDH_CLI_VERSION=1.10.7`,
confirmed live by exec'ing into the image, not inferred from its tag
name. Backstage source pinned to `backstage/backstage@v1.49.0`,
confirmed to match this RHDH instance's own live `@backstage/backend-
defaults@0.16.0` -- not an arbitrary choice, checked against what's
actually running.

**TLS pre-check, passed clean**: a real `curl` from inside the RHDH pod
against Gitea's own Route (the same host the read-only `integrations.gitea`
entry already uses) succeeded with a clean TLS handshake and `200 OK` --
no CA mounting needed, no host-literal mismatch found, unlike the
read-side `GithubUrlReader`-vs-`GiteaIntegration` gap found earlier this
phase.

**The plugin builds and packages successfully** -- real, live evidence,
not a dry run: `npx @red-hat-developer-hub/cli@1.10.7 plugin export` and
`plugin package` both completed, producing a real dynamic-plugin archive
(`backstage-plugin-scaffolder-backend-module-gitea-dynamic-0.2.19.tgz`,
4,575,700 bytes, real integrity hash recorded). Two real issues found and
worked around: (1) the factory's own `:1.10` container image reads an
undocumented `workspace-path` field directly from `source.json` --
different from both the published README and the source at the git tag
that can actually be cloned locally for reference, only discovered by
reading the *running container's own* source once the mismatch was
suspected; (2) the factory's remote-clone path always does a full,
unshallowed `git clone` with no depth limit, which for a monorepo the
size of `backstage/backstage` pulled ~7GB and was still running 20+
minutes in -- worked around with a manual shallow clone plus the
factory's own documented `--use-local` flag, not a factory bug fix.

**Read directly, not assumed**: the actual `publish:gitea` action source
at the pinned ref confirms it authenticates via the exact same
`integrations.gitea` config block (`@backstage/integration`'s
`GiteaIntegrationConfig`) G1 already established for reading, needing
only `username`/`password` fields added -- the already-proven
`golden-path-agent-scaffolder` machine-account token (`DEC-100`), not a
new credential. It creates repos via the org-scoped API path, matching
this project's own `golden-path-agent-projects` org exactly. Full real
input schema recorded for whoever picks this up next.

**Not completed this spike, and why**: live RHDH wiring (a new
`dynamic-plugins.yaml` ConfigMap, pointing the `Backstage` CR's currently-
unset `dynamicPluginsConfigMapName` at it), the `integrations.gitea`
write-credential addition, a test-template `publish:gitea` step, and the
actual end-to-end Scaffolder-task test. **Blocked by the cluster session
token expiring mid-spike** (`oc whoami` now returns `Unauthorized`) after
the legitimate build work ran long -- not by any technical dead end. Per
this project's own explicit policy (`scripts/bootstrap.sh`: "Never runs
`oc login` -- credential handling stays the owner's own one-time step"),
re-authenticating is not this session's call to make. The coordinating
session very likely shares the same `oc` session/config and may need to
re-authenticate too before resuming this work.

**Status**: Spike substantially de-risked Path A -- the build itself,
the hardest open question, is proven to work with a real artifact in
hand. What remains is short, mechanical, and fully scoped (§5 of
`reports/feature-g6-scaffolder-plugin-spike.md`), not further discovery.
Recommend resuming this spike (or handing the remaining steps to a fresh
session) once cluster access is restored, rather than defaulting to
Path B alone by default -- Path A is closer to done than the original
time-box anticipated.
```
