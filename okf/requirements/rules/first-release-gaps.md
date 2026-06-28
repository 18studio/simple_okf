---
type: Gap
title: First Release Gaps
description: Open questions and deferred product areas discovered during first-release
  planning.
tags:
- ai-buddy
- gap
- first-release
- planning
timestamp: '2026-06-28T00:00:00Z'
---

# First Release Gaps

These items are intentionally unresolved or deferred from the first-release scope.

## Deferred UX work

- Normal dashboard UX must be designed separately.
- Knowledge-base replenishment UX and gamification must be designed separately.
- A2A agent connection screen and wizard must be designed separately.
- Preloader stages and copy for environment creation must be worked out separately.

## Deferred backend and platform work

- Detailed backend/operator architecture requires a separate decision process.
- Kubernetes operator stages and exact mapping to user-facing preloader statuses are not defined yet.
- Exact user-environment resources, provisioning failure states, and retry behavior are not defined yet.

## Deferred data ingestion

- File uploads during first reasoning are not part of the first release.
- `first_reasoning_file_attached` is not part of first-release analytics.
- Parsing content behind pasted links is not required in the first release.

## Placeholder rule

Until an area has implementation and approved documentation, its UI page must use the [Placeholder Page](../../ui/ux/placeholder-page.md).

## Related concepts

- [First Reasoning Onboarding Flow](../flows/first-reasoning-onboarding.md)
- [Backend Provisioning Architecture](../../architecture/adr/backend-rest-and-operator-provisioning.md)
- [First Reasoning UX](../../ui/ux/first-reasoning.md)
