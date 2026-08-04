# ADR 0003: Offload frames, not application components

## Status

Accepted.

## Context

Alternatives included transferring code, containers, neural-network partitions or application components.

## Decision

Transfer only encoded frames, stable frame identifiers and the minimum request metadata. Return detections and timing metadata.

## Consequences

The protocol remains explicit and measurable. Application migration and split inference are outside the thesis scope and may be discussed as future work.
