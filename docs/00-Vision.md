# ⚔ Vision

> *The North Star of The Archangel.*

---

# Purpose

The Archangel exists to eliminate the repetitive process of manually searching the internet for software development opportunities.

Instead of constantly checking Telegram groups, Reddit communities, Discord servers, GitHub issues, or future platforms, The Archangel continuously watches them on the user's behalf.

The system's purpose is not simply to collect posts.

Its purpose is to understand information, identify valuable opportunities, remove noise, and deliver only actionable leads.

Every architectural decision should support that objective.

---

# Mission

Build an autonomous intelligence platform capable of discovering, understanding, ranking, and organizing opportunities from multiple online sources with minimal user intervention.

The developer should spend time building software—not searching for work.

---

# Long-Term Vision

The Archangel should become a reusable intelligence platform rather than a collection of automation scripts.

It should be capable of adapting to new platforms, new AI models, new storage systems, and new workflows without requiring major architectural changes.

The core engine should remain stable while everything around it evolves independently.

---

# The Problem

Freelance developers often spend hours searching for work.

Typical workflow:

Internet

↓

Telegram

↓

Discord

↓

Reddit

↓

GitHub

↓

Forums

↓

Repeat tomorrow.

Most posts are:

- irrelevant
- duplicates
- outdated
- low quality
- scams
- impossible to verify

Finding valuable opportunities requires significant manual effort.

---

# The Solution

The Archangel performs continuous observation instead.

```
Internet

↓

Collectors

↓

AI Analysis

↓

Lead Scoring

↓

Storage

↓

Notification

↓

Developer
```

The user only reviews opportunities worth their attention.

---

# Philosophy

The project is built around several engineering principles.

## Intelligence Over Collection

Collecting information has little value without understanding it.

Every piece of collected information should be analyzed before reaching the user.

The platform should answer:

- Is this a legitimate opportunity?
- Is the author actually looking for developers?
- How valuable is this project?
- How urgent is it?
- Should the user even care?

---

## Modularity

Everything should be replaceable.

Collectors.

AI models.

Storage systems.

Notification systems.

Exporters.

Nothing should require rewriting unrelated components.

If replacing one component breaks half the project, the architecture has failed.

---

## One Responsibility

Every component has one job.

Examples:

Collector

Collects.

Nothing else.

Storage

Stores.

Nothing else.

Notification

Sends notifications.

Nothing else.

This separation makes the platform easier to understand, test, and extend.

---

## Event Driven

Components should communicate through events rather than direct dependencies.

Instead of:

Collector

↓

Storage

↓

Notification

Use:

Collector

↓

NewPostEvent

↓

Analysis

↓

LeadScoredEvent

↓

Storage

↓

Notification

This allows new functionality to subscribe without modifying existing code.

---

## CLI First

The CLI is the primary interface.

The project should feel like professional developer tools such as Git, Docker, Ruff, or UV.

The CLI should expose a clean, memorable command set while keeping all business logic inside the engine.

Example:

```
archangel summon
archangel terminate
archangel status
archangel watch
archangel doctor
```

The CLI parses commands.

The engine performs the work.

---

## AI First

The project should be understandable by both humans and coding agents.

Documentation should remove ambiguity wherever possible.

A coding agent should be able to read the documentation and understand:

- why the architecture exists
- how components communicate
- what each module owns
- what each module must never do

Documentation is considered part of the architecture.

---

# Identity

The Archangel is **not**:

- a Telegram scraper
- a Reddit bot
- a Discord monitor
- a keyword scanner
- another automation script

The Archangel **is**:

- a lead intelligence platform
- an event-driven system
- an AI-assisted decision engine
- a modular developer tool

The distinction matters.

New features should strengthen the platform rather than turning it into a collection of unrelated utilities.

---

# Design Goals

The platform should strive to be:

- Modular
- Predictable
- Maintainable
- Extensible
- Observable
- Testable
- AI-friendly

Every design decision should improve at least one of these qualities.

---

# Non-Goals

The project is intentionally **not** trying to become:

- a CRM
- a project management platform
- a chat application
- a marketplace
- a social network
- a low-code automation tool

Those problems belong elsewhere.

The Archangel focuses on one thing:

Finding opportunities.

---

# Success Criteria

The project is considered successful when:

- New sources can be added without modifying the engine.
- New AI providers can replace existing ones easily.
- New storage backends require minimal work.
- Every component can be tested independently.
- Every agent has one responsibility.
- The platform can run continuously with minimal maintenance.

---

# Guiding Principles

When uncertain, prefer:

Clarity over cleverness.

Composition over complexity.

Explicitness over hidden behavior.

Small modules over giant classes.

Events over tight coupling.

Readable code over magical abstractions.

Maintainability over premature optimization.

Consistency over novelty.

---

# Future

The current goal is lead intelligence.

The architecture, however, should support future capabilities such as:

- additional online sources
- improved AI reasoning
- autonomous outreach
- analytics
- dashboards
- cloud deployment
- collaborative workflows

These should be implemented as extensions rather than architectural rewrites.

---

# Final Statement

The Archangel is designed to become a long-term engineering project.

Its purpose is not merely to automate searching.

Its purpose is to become an intelligent platform that continuously discovers opportunities, understands them, and presents only the information that deserves the developer's attention.

Every line of code should move the project closer to that vision.

---

*"Opportunity is revealed to those who seek."*

⚔️