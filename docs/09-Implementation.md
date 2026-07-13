# 🛠️ Implementation

> Defines the implementation status and execution plan of The Archangel.
>
> Unlike the other specification documents, this file is expected to evolve continuously during development.
>
> It serves as the project's working implementation log and development guide.

---

# Purpose

This document answers one question:

> **"What are we building right now?"**

While the other documents define **how the platform should work**, this document tracks **what has been implemented, what is in progress, and what remains to be built.**

---

# Responsibilities

This document should contain

- Current implementation progress
- Development phases
- Feature checklists
- Component status
- Implementation notes
- Technical decisions
- Breaking changes
- Refactoring plans
- Known limitations
- Current priorities

---

# What Does NOT Belong Here

This document should not become

- The project vision
- The architecture specification
- The roadmap
- Bug reports
- Issue tracking
- User documentation

Those belong in their respective documents.

---

# Recommended Structure

Although the exact format is flexible, implementations should generally follow sections similar to

```text
Current Version

Development Phase

Completed

In Progress

Next Tasks

Known Issues

Technical Notes

Future Refactoring
```

This layout is only a recommendation and may evolve as the project grows.

---

# Development Workflow

Implementation should always follow the documented specifications.

Typical workflow

```text
Vision

↓

Architecture

↓

Implementation

↓

Testing

↓

Review

↓

Release
```

New features should be designed before they are implemented.

Whenever possible, update the specification documents before writing code.

---

# AI Agent Guidelines

AI coding agents should use this document as the primary source of implementation progress.

Before beginning work, an agent should

- Determine the current development phase
- Check completed tasks
- Identify the next implementation target
- Avoid duplicating completed work
- Update this document after completing significant milestones

This document should always represent the current state of development.

---

# Living Document

Unlike most files in `/docs`, this file is expected to change frequently.

Every completed feature, architectural change, or major refactor should be reflected here.

It should evolve alongside the codebase throughout the lifetime of The Archangel.

---

# Closing Statement

The Implementation document bridges the gap between planning and development.

It transforms the architectural specifications into actionable work, ensuring that contributors and AI agents always understand the current state of the project and what should be built next.