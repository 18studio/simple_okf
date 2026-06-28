---
type: User Flow
title: First Reasoning Onboarding Flow
description: First-release onboarding flow where a user completes a guided reasoning
  session and confirms a minimum profile.
tags:
- ai-buddy
- onboarding
- first-release
- reasoning
timestamp: '2026-06-28T00:00:00Z'
---

# First Reasoning Onboarding Flow

This is the primary first-release user path for AI Buddy.

AI Buddy targets a leader or small business operator who handles operational work personally and wants to make work more systematic, convenient, and productive.

## Goal

The first-release goal is to guide the user through an initial reasoning session, collect enough information to understand the user's work context, save the confirmed information into OKF, start creation of the user's isolated environment, and then open the normal dashboard.

## Flow boundaries

In the first release, the implemented path is limited to:

1. registration or sign-in;
2. first reasoning in the style of the `grillme` interaction pattern;
3. completion of the six required items in the [Onboarding Profile](../../data/entities/onboarding-profile.md);
4. final summary and explicit user confirmation;
5. saving the confirmed information into OKF;
6. starting user-environment creation through the Kubernetes operator;
7. preloader with environment-creation status;
8. transition to the normal dashboard.

Pages without implementation and without approved documentation must display a simple placeholder: **"Раздел в разработке"**.

## Reasoning interaction model

The first reasoning session is a free-form chat with a mandatory completeness checklist.

The user can describe themselves, their company or project, current work, problems, links, and any other useful context in their own words. AI Buddy extracts structured profile information from the conversation.

AI Buddy must be persistent and must not complete the session until all six required profile items are filled and the user has confirmed the final summary.

Questions are asked through chat, one at a time. If a question can be answered from already provided information, AI Buddy should use the existing information instead of asking again.

## Completion rule

The flow is considered successfully completed only when the user reaches the end of the scenario and confirms the final summary.

The confirmation action logs `first_reasoning_completed`.

## After confirmation

After confirmation:

1. the confirmed profile information is saved into OKF;
2. the backend starts the user-environment creation process through the Kubernetes operator;
3. the UI shows a preloader with current status and stage;
4. after environment creation is complete, the user sees the normal dashboard.

The exact UX of the dashboard is not defined in this concept and is tracked as a gap.

## Related concepts

- [Onboarding Profile](../../data/entities/onboarding-profile.md)
- [First Reasoning UX](../../ui/ux/first-reasoning.md)
- [First Reasoning Analytics](../functions/first-reasoning-analytics.md)
- [Backend Provisioning Architecture](../../architecture/adr/backend-rest-and-operator-provisioning.md)
- [First Release Gaps](../rules/first-release-gaps.md)
