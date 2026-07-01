---
type: Function Requirement
status: draft
title: Chat Link Capture During First Reasoning
description: Requirement to capture URLs pasted into the first reasoning chat as separate
  knowledge-context items.
tags:
- ai-buddy
- onboarding
- links
- okf
timestamp: '2026-06-28T00:00:00Z'
---

# Chat Link Capture During First Reasoning

During the first reasoning onboarding flow, the user can add links by pasting URLs directly into the chat.

AI Buddy must recognize these URLs and save them as separate context items, not only as raw message text.

## First-release behavior

For the first release:

- the primary link input method is pasting URLs into the chat;
- parsed links are stored separately from normal chat text;
- the content behind the links does not have to be parsed;
- each stored link should remain associated with the first reasoning context.

## Analytics

Each recognized link produces the `first_reasoning_link_added` event described in [First Reasoning Analytics](first-reasoning-analytics.md).

## Related concepts

- [First Reasoning Onboarding Flow](../flows/first-reasoning-onboarding.md)
- [First Reasoning UX](../../ui/ux/first-reasoning.md)
