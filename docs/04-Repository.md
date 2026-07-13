# 📁 Repository Structure

> Defines the directory layout, ownership, and engineering conventions for The Archangel.
>
> The repository is designed around modularity. Every directory exists for a single purpose and should have a clearly defined responsibility.
>
> This document is the source of truth for repository organization.

---

# Design Philosophy

The repository should feel like a professional software project rather than a collection of Python scripts.

Every folder must have a clear purpose.

A developer or AI agent should be able to understand where new code belongs without guessing.

If you're unsure where a file belongs, the repository structure should answer that question.

---

# Root Structure

```text
The_Archangel/
│
├── archangel/
├── configs/
├── data/
├── docs/
├── logs/
├── tests/
│
├── README.md
├── ARCHANGEL.md
├── pyproject.toml
├── uv.lock
├── .gitignore
└── LICENSE
```

---

# Repository Overview

| Directory | Purpose |
|-----------|---------|
| `archangel/` | Main application source code |
| `configs/` | User configuration files |
| `data/` | Runtime databases and exported data |
| `docs/` | Project specifications and documentation |
| `logs/` | Runtime logs |
| `tests/` | Automated testing |

---

# Source Tree

The entire application lives inside

```text
archangel/
```

The project should never place application logic in the repository root.

---

# Source Layout

```text
archangel/
│
├── cli/
├── engine/
├── agents/
├── collectors/
├── analysis/
├── scoring/
├── storage/
├── notifications/
├── export/
├── plugins/
├── config/
├── events/
├── utils/
└── assets/
```

Every folder owns exactly one area of responsibility.

---

# cli/

Purpose

Contains the command-line interface.

Responsibilities

- Parse commands
- Parse flags
- Display output
- Render banners
- Format tables
- Handle user interaction

The CLI must never contain business logic.

---

# engine/

Purpose

Contains the runtime engine.

Responsibilities

- Startup
- Shutdown
- Runtime lifecycle
- Scheduler
- Event routing
- Plugin loading
- Service registration

The engine coordinates the platform.

It does not perform business logic.

---

# agents/

Purpose

Contains every autonomous agent.

Examples

```text
Guardian

Commander

Collector

Intelligence

Scoring

Storage

Notification

Export
```

Every agent owns one responsibility.

---

# collectors/

Purpose

Contains source-specific collectors.

Examples

```text
telegram/

reddit/

discord/

github/

rss/
```

Collectors retrieve raw information.

They never perform AI analysis.

---

# analysis/

Purpose

Contains AI reasoning logic.

Responsibilities

- Prompt construction
- Model abstraction
- Lead detection
- Budget estimation
- Confidence calculation
- Categorization
- Duplicate detection

No storage code belongs here.

---

# scoring/

Purpose

Calculate lead quality.

Responsibilities

- Score calculation
- Ranking
- Prioritization
- Filtering

Only scoring logic belongs here.

---

# storage/

Purpose

Persist data.

Responsibilities

- SQLite
- JSON
- PostgreSQL (future)
- Database migrations
- Repository layer

All persistent data passes through this module.

---

# notifications/

Purpose

Deliver notifications.

Possible implementations

```text
Telegram

Discord

Email

Desktop
```

Notification logic belongs nowhere else.

---

# export/

Purpose

Generate exports.

Supported formats

- CSV
- JSON
- Markdown
- Excel

Exporters transform stored data.

They never modify it.

---

# plugins/

Purpose

Contains dynamically loaded plugins.

Example

```text
plugins/

telegram/

reddit/

discord/

github/
```

Adding a new source should ideally only require adding a new plugin.

The Engine should discover plugins automatically.

---

# config/

Purpose

Internal configuration models.

Responsibilities

- Schema validation
- Defaults
- Configuration loading
- Configuration parsing

This is different from

```text
configs/
```

which stores the user's editable configuration files.

---

# events/

Purpose

Defines the Event Bus contracts.

Examples

```text
RawPostEvent

LeadAnalysisEvent

LeadScoredEvent

LeadStoredEvent

NotificationSentEvent
```

Every event should be represented as a strongly typed model.

---

# utils/

Purpose

Shared utilities.

Examples

- Logging
- Time utilities
- Helpers
- Constants
- Formatting
- Retry helpers

Utilities should remain generic.

Business logic should never live here.

---

# assets/

Purpose

Static resources.

Examples

- ASCII banners
- Icons
- Templates
- Prompt files
- Default exports

---

# configs/

Purpose

Contains editable user configuration.

Examples

```text
config.yaml

keywords.yaml

sources.yaml

notifications.yaml
```

These files should be safe for users to modify.

---

# data/

Purpose

Persistent runtime data.

Examples

```text
SQLite database

JSON storage

Exports

Cache

Temporary files
```

The application should automatically create this directory if it does not exist.

---

# logs/

Purpose

Runtime logging.

Possible files

```text
runtime.log

errors.log

debug.log
```

Logs should rotate automatically.

---

# docs/

Purpose

Project documentation.

Current structure

```text
docs/

00-Vision.md

01-Architecture.md

02-Agents.md

03-CLI.md

04-Repository.md

05-Pipeline.md

06-Plugin-System.md

07-Configuration.md

08-Roadmap.md

09-Implementation.md

diagrams/
```

Documentation is considered part of the project.

Major architectural changes should update these files.

---

# tests/

Purpose

Automated testing.

Possible organization

```text
unit/

integration/

performance/

fixtures/
```

Tests should mirror the application structure whenever possible.

---

# Root Files

## README.md

Public-facing project overview.

---

## ARCHANGEL.md

Primary development specification.

This document provides coding agents and contributors with implementation context, engineering conventions, architectural expectations, and project-specific guidance.

It should always reflect the current state of the project.

---

## pyproject.toml

Python project configuration.

Defines

- dependencies
- build system
- scripts
- project metadata

This is the canonical project configuration.

---

## uv.lock

Dependency lockfile managed by `uv`.

Should always be committed.

---

## .gitignore

Defines ignored files and directories.

Should exclude

- virtual environments
- caches
- compiled files
- runtime data
- secrets

---

## LICENSE

Project license.

---

# Repository Rules

Every file must have an obvious home.

Avoid creating miscellaneous directories.

Avoid generic names like

```text
misc/

random/

stuff/

helpers2/
```

If a new folder is needed, its purpose should be immediately understandable.

---

# Ownership Rules

Every module owns its own responsibility.

Examples

Collectors own collection.

Storage owns persistence.

Notifications own messaging.

No module should assume ownership of another module's responsibilities.

---

# AI Development Guidelines

The repository should be optimized for AI-assisted development.

Folders should be:

- predictable
- descriptive
- isolated
- modular

Coding agents should never need to guess where new functionality belongs.

---

# Future Expansion

The structure should support future additions such as

- Web dashboard
- REST API
- Analytics
- Cloud deployment
- Team collaboration
- Memory systems
- Autonomous outreach

These additions should fit naturally into the existing repository without requiring major architectural changes.

---

# Closing Statement

The repository structure is the physical representation of The Archangel's architecture.

A clean repository encourages clean code.

Every directory should exist for a reason, every module should have a single responsibility, and every contributor—human or AI—should be able to navigate the project confidently.