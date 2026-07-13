# ⚙️ Configuration

> Defines the configuration system of The Archangel.
>
> This document specifies how configuration is organized, validated, loaded, and used throughout the platform.
>
> The configuration system should be predictable, extensible, and easy for both humans and AI agents to understand.
>
> This document is the source of truth for all configuration-related behavior.

---

# Philosophy

The Archangel should never require users to modify source code.

Everything that changes the platform's behavior should be configurable.

Instead of

```python
TELEGRAM_CHANNELS = [...]
```

the user should edit

```yaml
configs/sources.yaml
```

Configuration belongs outside the application.

---

# Design Goals

The configuration system should be

- Human-readable
- Easy to validate
- Modular
- Versioned
- Extensible
- AI-friendly
- Backward compatible whenever possible

---

# Configuration Directory

All user-editable configuration files live inside

```text
configs/
```

Example

```text
configs/

config.yaml

sources.yaml

keywords.yaml

notifications.yaml

storage.yaml

scoring.yaml

analysis.yaml
```

Each configuration file owns one responsibility.

---

# Configuration Loading

During

```bash
archangel summon
```

the Engine should perform the following sequence.

```text
Load Configuration

↓

Validate Configuration

↓

Apply Defaults

↓

Initialize Components

↓

Start Runtime
```

The platform must never start with invalid configuration.

---

# Configuration Hierarchy

Configuration should be loaded in the following order.

```text
Built-in Defaults

↓

Configuration Files

↓

Environment Variables

↓

CLI Flags
```

Each layer overrides the previous one.

Highest priority always wins.

---

# Main Configuration

`config.yaml` contains global runtime settings.

Example

```yaml
runtime:
  debug: false
  log_level: INFO
  timezone: UTC

plugins:
  auto_discovery: true

guardian:
  enabled: true

engine:
  workers: auto
```

This file should remain relatively small.

---

# Sources Configuration

`sources.yaml`

Defines where information is collected.

Example

```yaml
telegram:
  enabled: true

reddit:
  enabled: true

github:
  enabled: true

discord:
  enabled: false

rss:
  enabled: true
```

Each source should expose only source-specific settings.

---

# Keywords

`keywords.yaml`

Defines what the user is looking for.

Example

```yaml
include:
  - python
  - automation
  - ai
  - backend
  - flutter

exclude:
  - internship
  - unpaid
  - volunteer
```

Collectors should use these keywords to reduce unnecessary processing.

---

# Analysis Configuration

`analysis.yaml`

Controls AI behavior.

Example

```yaml
provider: gemini
model: gemini-3.5-flash
temperature: 0.2
confidence_threshold: 0.80
detect_duplicates: true
```

The Intelligence Agent should read only this configuration.

---

# Scoring Configuration

`scoring.yaml`

Controls opportunity ranking.

Example

```yaml
weights:
  confidence: 40
  urgency: 25
  budget: 20
  keywords: 10
  recency: 5
```

Weights should be configurable.

Hardcoded scoring should be avoided.

---

# Notifications Configuration

`notifications.yaml`

Example

```yaml
telegram:
  enabled: true

discord:
  enabled: false

desktop:
  enabled: true

email:
  enabled: false
```

Each notification provider owns its own settings.

---

# Storage Configuration

`storage.yaml`

Example

```yaml
provider: sqlite

database:
  path: data/archangel.db

backup:
  enabled: true
  interval: daily
```

Changing storage providers should not require code changes.

---

# Plugin Configuration

Each plugin should own its own configuration.

Example

```yaml
telegram:
  api_id: ...
  api_hash: ...
  session: archangel
  channels:
    - Python Jobs
    - Remote Jobs
    - Freelance India
```

Plugins should never read unrelated configuration.

---

# Environment Variables

Sensitive information should never be stored in configuration files.

Instead, use environment variables.

Example

```text
OPENAI_API_KEY
GEMINI_API_KEY
TELEGRAM_API_ID
TELEGRAM_API_HASH
```

Configuration files may reference environment variables when necessary.

---

# CLI Overrides

CLI flags should temporarily override configuration.

Example

```bash
archangel summon --debug
archangel summon --config configs/dev.yaml
archangel summon --log-level DEBUG
```

CLI overrides should affect only the current execution.

They should never modify configuration files.

---

# Default Values

Every configuration option should define a sensible default.

Example

```yaml
guardian:
  enabled: true
```

Users should not be required to configure every option.

---

# Validation

Every configuration file should be validated before runtime.

Checks include

- Required fields
- Valid data types
- Missing values
- Invalid enum values
- Invalid file paths
- Duplicate entries

Invalid configuration should prevent startup.

---

# Error Messages

Configuration errors should be descriptive.

Bad

```text
Configuration Error
```

Good

```text
Invalid configuration detected.

File:   configs/storage.yaml
Field:  provider
Expected: sqlite | postgres
Received: mysql
```

The user should immediately know what needs to be fixed.

---

# Configuration Versioning

Configuration should support versioning.

Example

```yaml
version: 1
```

Future migrations should upgrade older configurations automatically whenever possible.

---

# Hot Reload (Future)

Future versions may support configuration reloading without restarting the platform.

Example

```bash
archangel reload
```

or

```bash
archangel config reload
```

Changes should propagate safely to affected components.

---

# AI Development Guidelines

Configuration files should remain

- Small
- Focused
- Predictable
- Independent

Each file should own one concern.

Avoid creating one massive configuration file containing every setting.

---

# Engineering Rules

## Rule 1

Never hardcode user configuration.

---

## Rule 2

Sensitive values belong in environment variables.

---

## Rule 3

Each configuration file owns one responsibility.

---

## Rule 4

Invalid configuration must stop startup.

---

## Rule 5

Defaults should exist for every optional setting.

---

## Rule 6

CLI flags override configuration temporarily.

---

## Rule 7

Plugins should only read their own configuration.

---

## Rule 8

Configuration should be validated before any agent starts.

---

# Example Configuration Layout

```text
configs/

config.yaml

sources.yaml

keywords.yaml

analysis.yaml

scoring.yaml

notifications.yaml

storage.yaml
```

This layout should remain simple and easy to navigate.

---

# Closing Statement

Configuration is the control panel of The Archangel.

A user should be able to customize the platform's behavior—from enabled sources and AI models to scoring rules and notification channels—without touching the source code.

A well-designed configuration system keeps the Engine generic, the agents focused, and the platform adaptable as new capabilities are introduced.