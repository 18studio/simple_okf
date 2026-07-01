---
type: Architecture Decision
status: draft
title: Backend REST API and Kubernetes Operator Provisioning
description: Architecture decision for UI-backend communication and deferred user-environment
  provisioning.
tags:
- ai-buddy
- backend
- rest-api
- kubernetes
- operator
- onboarding
timestamp: '2026-06-28T00:00:00Z'
---

# Backend REST API and Kubernetes Operator Provisioning

## Decision

The backend communicates with the web UI through REST API.

After the user confirms the final summary in the first reasoning onboarding flow, the backend starts user-environment creation through a Kubernetes operator.

## User environment

The target architecture is an isolated Kubernetes namespace per user.

The environment is expected to include user-specific secrets and storage or service configuration for components such as Qdrant, OpenSearch, and an S3 bucket.

The exact implementation details and operator stages are not finalized and are tracked as a gap.

## Status delivery to UI

For the first release, the recommended status delivery mechanism is REST polling.

The UI should poll an endpoint for environment-creation status while showing a preloader. The response should provide the current status and stage in a UI-friendly form.

## Timing

Full user-environment creation is triggered after the first reasoning flow is completed and the user confirms the final summary.

## Related concepts

- [First Reasoning Onboarding Flow](../../requirements/flows/first-reasoning-onboarding.md)
- [First Release Gaps](../../requirements/rules/first-release-gaps.md)
