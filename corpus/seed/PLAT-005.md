# Network Segmentation and Ingress Standard

This standard defines the default network posture between namespaces on
the platform.

Namespace-to-namespace traffic is denied by default. Explicit network
policies are required to allow cross-namespace traffic — a team that
needs one namespace to reach another must define and apply a network
policy naming the source and destination namespaces and the allowed
ports; without that policy in place, traffic between the two namespaces
is blocked at the platform level regardless of application-level
configuration.

Ingress from outside the cluster is likewise denied by default and must
be explicitly configured per namespace. This standard is maintained by
Network Security Engineering and is reviewed annually or immediately
after any confirmed segmentation incident.
