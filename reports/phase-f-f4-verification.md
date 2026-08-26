# Phase F4 — RHDH platform stand-up, execution-based verification

Definition of Done per the owner's authorization: STOP 5's bar is "the
owner could open the portal URL and log in." Every check below is a
command actually run against the live showcase cluster, not a
documentation claim — following this project's own "verification by
execution" discipline (`DEC-089`/`DEC-090` established the same pattern
for F2/F3; this phase found four more real gaps only execution surfaced).

## 1. Operator and CSV

```
$ oc get csv -n openshift-operators | grep -i rhdh
rhdh-operator.v1.10.3   Red Hat Developer Hub Operator   1.10.3   rhdh-operator.v1.10.2   Succeeded
$ oc get subscription rhdh -n openshift-operators -o jsonpath='{.status.state}'
AtLatestKnown
```

Installed via `scripts/bootstrap.sh --with-rhdh`, reusing the existing
`wait_for_csv`/`approve_pending_installplan` function bodies (`DEC-080`
precedent) rather than a new install path.

## 2. Database

```
$ oc get pods -n golden-path-agent-rhdh
NAME                                          READY   STATUS    RESTARTS   AGE
backstage-golden-path-agent-95c679f4f-xnscq   2/2     Running   0          7m33s
golden-path-agent-rhdh-db-7448dcbcc-48d2c     1/1     Running   0          64m
```

Real gap found live: RHDH creates one Postgres database per backend
plugin at startup (`backstage_plugin_search`, `_events`, etc.), not just
the single database the S2I `postgresql` image provisions by default.
The `rhdh` role initially lacked `CREATEDB`, causing a crash-loop
(`permission denied to create database`) until `ALTER ROLE rhdh
CREATEDB;` was applied via the image's own passwordless local `postgres`
superuser. Documented as a required manual step in `postgres.yaml`'s own
header comment (not automated — Postgres is GitOps-managed, applied
after `bootstrap.sh`'s own `--with-rhdh` block runs).

## 3. GitOps sync

```
$ oc get application golden-path-agent-rhdh -n openshift-gitops \
    -o jsonpath='{.status.sync.status}{" "}{.status.health.status}{" "}{.status.sync.revision}'
Synced Healthy 916de56641f82ff6667cc5c782a317777d064f24
```

Real gap found live: the first sync attempt failed outright (`services
is forbidden ... cannot create resource`) because the
`golden-path-agent-rhdh` namespace was missing the
`argocd.argoproj.io/managed-by: openshift-gitops` label that triggers
the auto-created RoleBinding granting the ArgoCD application-controller
write access — present on `demo-prod`, deliberately absent on
`ephemeral-test`, simply forgotten here. Fixed by adding the label
(live, then backfilled into `pipelines/bootstrap/namespaces.yaml`).

## 4. Auth flow — full OIDC login, end to end

Driven programmatically from inside the cluster (`oc exec` into the
`golden-path-agent` pod — the same external-DNS limitation this project
already has for the approver-ui per `DEC-074`, not a new gap): Keycloak
Authorization Code + PKCE flow against the real `demo-approver` user,
through to a resolved `backstageIdentity.token`.

```
Got Backstage token, len: 616
```

Four real config gaps were found and fixed live before this succeeded,
each one only surfacing once the backend actually ran (not from docs):

| # | Symptom | Fix |
|---|---|---|
| 1 | Backend refused to start: `"the oidc provider no longer supports the 'scope' configuration option"` | `scope` → `additionalScopes: [profile, email]` |
| 2 | OIDC `redirect_uri` defaulted to `http://localhost:7007/...` | Added `app.baseUrl`/`backend.baseUrl`/`backend.cors.origin` bound to the real Ingress host (kept out of git, anonymity rule) |
| 3 | `"Authentication failed, authentication requires session support"` | Added `auth.session.secret` |
| 4 | Sign-in would fail with no catalog `User` entity for the Keycloak identity | `environment: production` + `providers.oidc.production` + `signIn.resolvers` with `dangerouslyAllowSignInWithoutUserInCatalog: true` (sandbox-scope decision, `DEC-092`) |

The very first of these (fix 1) was attempted as a live `oc apply` patch
before being committed — ArgoCD's `selfHeal: true` silently reverted it
within about a minute, confirmed by inspecting the live ConfigMap's own
content still holding the old value. Every fix after that point landed
in the committed manifest first. This is the single most consequential
operational lesson of the phase (`PINS.md`).

## 5. `catalog-info.yaml` visible — F1's own smoke test

The hardest gap of the phase. Sequence of elimination, each step a real
command, not an assumption:

1. ConfigMap mounted correctly in the pod — confirmed (`cat` matched
   expected content).
2. Passed to the backend via `--config` in the right order — confirmed
   (`oc get pod -o jsonpath='{.spec.containers[...].args}'`).
3. Target URL reachable from inside the pod — confirmed (`curl` returned
   a clean `HTTP/2 200` with correct content-length).
4. Entity lookup (`/api/catalog/entities/by-name/component/default/golden-path-agent`)
   still 404'd, and no relevant catalog log lines appeared at all under
   several different search terms.

Root cause, found in the backend's own log once searched broadly enough:

```
catalog warn Unable to read url, NotAllowedError: Reading from
'https://raw.githubusercontent.com/.../catalog-info.yaml' is not
allowed. You may need to configure an integration for the target host,
or add it to the configured list of allowed hosts at
'backend.reading.allow'
```

This is Backstage's own `UrlReader` security guard — unrelated to
network reachability, DNS, or the config-loading order already verified
clean. Any host not explicitly allow-listed is refused even when the URL
is public and reachable. Fixed by adding `backend.reading.allow` for
`raw.githubusercontent.com`. Re-verified live after the ArgoCD sync +
pod restart:

```
$ curl .../api/catalog/entities/by-name/component/default/golden-path-agent
{
  "metadata": {
    "namespace": "default",
    "annotations": {
      "backstage.io/managed-by-location": "url:https://raw.githubusercontent.com/DarkDragonEl/golden-path-agent-template/main/catalog-info.yaml",
      ...
```

`/api/catalog/entities` kind counts after the fix: `{'Plugin': 46,
'Package': 59, 'Location': 1, 'Component': 1}` — the `Location` and
`Component` entries are F1's own file, now real. (`/api/catalog/locations`
staying `[]` throughout is expected Backstage behavior for
statically-configured locations — that endpoint only lists
dynamically-added ones — and was not itself a symptom.)

## 6. Resource utilization

```
$ oc adm top pods -n golden-path-agent-rhdh
NAME                                          CPU(cores)   MEMORY(bytes)
backstage-golden-path-agent-95c679f4f-xnscq   86m          931Mi
golden-path-agent-rhdh-db-7448dcbcc-48d2c     12m          267Mi
```

Comfortably inside the headroom `PINS.md`'s F0 row already confirmed
(worker nodes at 3–4% CPU / 16–17% memory before this stand-up).

## 7. Deviations from F0's own research

None material. Every F0 research finding (operator install mode,
Route/Ingress toggle behavior, external-DB support) held exactly as
researched. All six gaps found in sections 2–5 above are new, live-only
findings — the kind F0's static research could not have surfaced, and
the exact reason this project's execution-based verification discipline
exists.

## Verdict

STOP 5's bar — "the owner could open the portal URL and log in" — is
met with execution evidence: operator `Succeeded`, database healthy,
ArgoCD `Synced`/`Healthy`, a full OIDC login proven end to end, and F1's
`catalog-info.yaml` now live and queryable in the catalog. See `DEC-093`
for the decision record and the two items intentionally left open
(`OBJ-01` full portal exposure, `SysR-P-F-13`/`OS-09` second-team
acceptance).
