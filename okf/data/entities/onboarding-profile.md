---
type: Data Entity
status: draft
title: Onboarding Profile
description: Minimum user profile captured during the first reasoning onboarding flow.
tags:
- ai-buddy
- onboarding
- okf
- profile
timestamp: '2026-06-28T00:00:00Z'
---

# Onboarding Profile

The onboarding profile is the minimum structured information that AI Buddy must collect during the first reasoning session before the first-release onboarding flow can be completed.

The profile is filled from a free-form conversation, not from a rigid form. AI Buddy extracts candidate values from the conversation and shows progress in a checklist.

## Required fields

1. **Position / role** — who the person is in the company or project.
2. **Industry / activity context** — the area in which the company, project, or team operates.
3. **Area of responsibility** — the tasks the person regularly handles themselves.
4. **Key communications** — who the person most often communicates with at work and about what.
5. **Main current difficulty** — what creates friction, consumes time, or creates chaos.
6. **Desired change** — what the person wants to improve in the near future.

## Checklist behavior

Each required field can have one of these statuses:

- **Not filled** — there is no usable information, or the user marked the current AI wording as incorrect.
- **Partially filled** — AI Buddy has some information, but not enough for a confident wording.
- **Filled** — AI Buddy has formulated the field and the user has not rejected it.

If the user marks a checklist wording as incorrect, the item is reset to **Not filled** and AI Buddy asks follow-up questions through the chat.

## Relationships

This profile is captured by the [First Reasoning Onboarding Flow](../../requirements/flows/first-reasoning-onboarding.md) and persisted into the user's OKF base after final confirmation.
