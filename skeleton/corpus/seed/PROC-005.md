# Certificate Rotation Procedure

This procedure governs how TLS certificates used by platform-managed
ingress are rotated.

Certificates are rotated automatically before expiry by the platform's
certificate-management automation, coordinated with the Network Security
Engineer role. Renewal is initiated well ahead of the certificate's
expiry date so that a slow or failed renewal attempt still leaves time
for manual intervention before the certificate actually expires. A known
race condition can occasionally affect ingress certificate renewal — see
the corresponding known error record for the current workaround if a
renewal appears stuck.

This procedure is reviewed on every certificate-authority change, per the
Network Segmentation and Ingress Standard's ownership.
