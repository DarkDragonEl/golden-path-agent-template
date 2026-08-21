# Container Platform Cluster Topology Standard

This standard defines how clusters and namespaces relate to each other on
the internal container platform.

Each cluster is subdivided into namespaces. Namespaces are the unit of
workload isolation within a cluster: every team's workloads run inside one
or more namespaces, and the platform enforces resource, network, and
access boundaries at the namespace level, not at the cluster level. A
single cluster may host many namespaces belonging to different teams, each
isolated from the others by default.

Namespace creation and quota follow the Namespace Request and Quota
Policy. Workload placement within a namespace is the owning team's
responsibility once the namespace exists.
