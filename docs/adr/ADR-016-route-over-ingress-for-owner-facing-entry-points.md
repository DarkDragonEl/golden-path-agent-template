# ADR-016: Route over Ingress for owner-facing entry points

## Context
This project held an Ingress-only precedent for externally-facing
bindings, held provisionally: attempt it first, and if it can't cleanly
work within about an hour of effort, take a Route as a documented
one-off exception rather than a silent deviation. Every owner-facing
entry point hit that wall — OpenShift's Ingress-to-Route translation
requires an explicit TLS Secret, while a native Route can inherit the
router's own trusted wildcard certificate with no cert fields at all.

## Decision
Every owner-facing external entry point (the portal, and Keycloak's
externally-reachable binding) uses a native `Route` (`termination:
edge`, `insecureEdgeTerminationPolicy: Redirect`, no cert fields), not
an `Ingress`. Each Route is applied out-of-band, never git-committed,
since its hostname is anonymity-sensitive.

## Consequences
- Browsers get the cluster's already-trusted certificate; no
  self-signed-cert warning.
- Keycloak's `hostname.strict: false` derives its issuer from the Host
  header it receives, so giving Keycloak its own Route (not a
  port-forward/hosts-file workaround, as used for internal-only tools)
  keeps the issuer a real, externally-resolvable hostname matching what
  backend token validation already expects — the property that makes
  browser login work for a genuinely owner-facing surface.
- The Keycloak Route also needs `spec.proxy.headers: xforwarded` so
  Keycloak reports `https://` endpoints consistent with edge
  termination; without it, direct token-exchange calls get
  redirect-bounced and fail.
- Ingress-only is not universal here — it holds until an owner-facing
  surface needs TLS Ingress can't cleanly provide. Neither Route object
  nor its hostname is committed to git or GitOps-managed.

## Supersedes / Superseded-by
None.

## Journal
DEC-094, DEC-097, DEC-074, DEC-087 (item 3 only)
