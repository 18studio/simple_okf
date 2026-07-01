---
type: UX Screen
status: draft
title: First Reasoning UX
description: UX behavior for the first reasoning chat and completeness checklist.
tags:
- ai-buddy
- onboarding
- ux
- reasoning
timestamp: '2026-06-28T00:00:00Z'
---

# First Reasoning UX

The first reasoning UI is a chat-based onboarding screen with a visible checklist of required profile items.

## Main interaction

The conversation is free-form, but AI Buddy tracks mandatory completeness using the [Onboarding Profile](../../data/entities/onboarding-profile.md).

The checklist must be visible during the session so the user understands how AI Buddy perceives them and which areas are still missing or incomplete.

## Checklist items

The checklist contains these items:

1. Position / role.
2. Industry / activity context.
3. Area of responsibility.
4. Key communications.
5. Main current difficulty.
6. Desired change.

## User correction behavior

The user does not directly edit checklist text.

When the user clicks or selects a wording that is wrong, the user can mark it as incorrect. The corresponding item is reset to **Not filled**, and AI Buddy asks clarifying questions through chat.

## Links

In the first release, the user can add links directly in the chat by pasting URLs. Links are recognized and stored as separate context items.

File uploads are not part of the first release and are tracked as a gap.

## Final confirmation

When all checklist items are filled, AI Buddy shows a final summary. The user must explicitly confirm the summary to complete the flow.

## Related concepts

- [First Reasoning Onboarding Flow](../../requirements/flows/first-reasoning-onboarding.md)
- [First Reasoning Analytics](../../requirements/functions/first-reasoning-analytics.md)
- [First Release Gaps](../../requirements/rules/first-release-gaps.md)
