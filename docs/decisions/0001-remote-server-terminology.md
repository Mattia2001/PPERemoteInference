# ADR 0001: Describe the deployment as a remote on-premise GPU server

## Status

Accepted.

## Context

The GPU server is inside the Idrotek private LAN and is not deployed within a mobile operator's 5G edge infrastructure. Mobile access will traverse a VPN and the operator network.

## Decision

Use **remote on-premise GPU server** in implementation and experimental reporting. The architecture may be described as edge-like, but not as a real MEC deployment.

## Consequences

Measured latency includes the actual VPN and network path. Results cannot be presented as measurements of an operator-provided MEC node. Migration to a real edge or data-centre deployment remains future work.
