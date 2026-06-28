---
type: Function Requirement
title: First Reasoning Analytics
description: Analytics events and metrics for the first reasoning onboarding flow.
tags:
- ai-buddy
- analytics
- onboarding
- first-release
timestamp: '2026-06-28T00:00:00Z'
---

# First Reasoning Analytics

The first release must measure completion and engagement during the first reasoning onboarding flow.

## Metrics

AI Buddy must measure:

1. time to complete the first reasoning flow;
2. number of user messages;
3. number of characters or words sent by the user;
4. number of links added by the user;
5. number of filled required checklist items from the [Onboarding Profile](../../data/entities/onboarding-profile.md);
6. successful completion of the flow.

Successful completion means that the user reached the end of the scenario and confirmed the final summary.

## Events

The first release logs these events:

- `first_reasoning_started` — the user started the scenario.
- `first_reasoning_user_message_sent` — the user sent a message.
- `first_reasoning_link_added` — the user added a link in chat.
- `first_reasoning_checklist_item_filled` — AI Buddy filled one of the required checklist items.
- `first_reasoning_completed` — the user confirmed the final summary and reached the end.

File attachment analytics are not part of the first release because file uploads are deferred.

## Related concepts

- [First Reasoning Onboarding Flow](../flows/first-reasoning-onboarding.md)
- [First Reasoning UX](../../ui/ux/first-reasoning.md)
- [First Release Gaps](../rules/first-release-gaps.md)
