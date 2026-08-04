# ADR 0002: Use Docker Compose before Kubernetes

## Status

Accepted.

## Context

The current target is one server with one consumer GPU. The immediate objective is to validate end-to-end remote inference, not multi-node orchestration.

## Decision

Build and benchmark the first deployment with Docker Compose. Add Kubernetes and Helm only after service boundaries, resource consumption and operational requirements are stable.

## Consequences

The initial system stays easy to inspect and reproduce. Deployment definitions must avoid assumptions that would prevent later migration to Kubernetes.
