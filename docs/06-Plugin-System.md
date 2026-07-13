# 🔌 Plugin System

> Defines the plugin architecture of The Archangel.
>
> Plugins allow The Archangel to expand beyond its built-in capabilities without requiring modifications to the core engine.
>
> Every external integration—whether a collector, notifier, export, or future extension—should be implemented as a plugin whenever possible.
>
> This document is the source of truth for plugin development.

---

# Philosophy

The Archangel is designed to grow.

New platforms appear.

APIs change.

New AI providers emerge.

The core engine should **not** require modifications every time a new integration is added.

Instead, functionality should be extended through plugins.

Think of the Engine as the operating system.

Plugins are applications running on top of it.

---

# Why Plugins?

Without plugins

```
Engine

↓

Telegram Code

↓

Discord Code

↓

GitHub Code

↓

Reddit Code

↓

Everything Mixed Together
```

With plugins

```
Engine

↓

Plugin Manager

↓

Telegram Plugin

Reddit Plugin

GitHub Plugin

Discord Plugin

RSS Plugin
```

The Engine stays clean.

Plugins remain isolated.

---

# Goals

The plugin system should be

- Modular
- Discoverable
- Replaceable
- Independent
- Easy to Develop
- Easy to Debug
- AI-Friendly

Adding a plugin should require little to no changes to the Engine.

---

# Plugin Directory

All plugins live inside

```text
archangel/plugins/
```

Example

```text
plugins/

telegram/

reddit/

discord/

github/

rss/

email/

desktop/
```

Each plugin owns its own directory.

---

# Plugin Structure

Example

```text
telegram/

plugin.py

manifest.yaml

config.py

README.md
```

Every plugin should be self-contained.

---

# Plugin Manifest

Each plugin should expose metadata describing itself.

Example

```yaml
name: Telegram
id: telegram
version: 1.0.0
author: The Archangel
type: collector
enabled: true
```

The Engine should never guess plugin information.

---

# Plugin Types

The Archangel supports multiple plugin categories.

---

## Collector Plugins

Responsible for collecting information.

Examples

- Telegram
- Reddit
- Discord
- GitHub
- RSS
- X (Future)

Collector plugins publish

```
RawPostEvent
```

---

## Notification Plugins

Responsible for messaging.

Examples

- Telegram
- Discord
- Email
- Desktop

Notification plugins subscribe to

```
LeadStoredEvent
```

---

## Export Plugins

Responsible for exports.

Examples

- CSV
- JSON
- Markdown
- Excel
- PDF (Future)

---

## AI Plugins (Future)

Responsible for AI providers.

Examples

- Gemini
- OpenAI
- Anthropic
- DeepSeek
- Local Models

Switching providers should not affect the Intelligence Agent.

---

## Storage Plugins (Future)

Possible implementations

- SQLite
- PostgreSQL
- MongoDB
- Cloud Storage

---

# Plugin Lifecycle

Every plugin follows the same lifecycle.

```
Discovered

↓

Loaded

↓

Validated

↓

Initialized

↓

Running

↓

Stopping

↓

Unloaded
```

The Engine controls every transition.

---

# Discovery

During startup

```
archangel summon
```

the Engine scans

```text
archangel/plugins/
```

Every valid plugin is discovered automatically.

No plugin should require manual registration.

---

# Loading

The Plugin Manager loads every enabled plugin.

Disabled plugins should be ignored.

Failed plugins should not prevent unrelated plugins from loading.

---

# Validation

Before initialization, every plugin should be validated.

Checks include

- Manifest exists
- Compatible version
- Valid configuration
- Required dependencies
- Required permissions

Invalid plugins should be skipped with an error message.

---

# Initialization

During initialization a plugin may

- Connect to APIs
- Authenticate
- Load configuration
- Create clients
- Register event listeners

Initialization should never perform long-running work.

---

# Runtime

Once initialized

plugins become event subscribers.

Example

```
RawPostEvent

↓

Telegram Notification Plugin
```

or

```
LeadStoredEvent

↓

Discord Notification Plugin
```

Plugins remain idle until they receive events they subscribe to.

---

# Shutdown

During

```
archangel terminate
```

plugins should

- close network connections
- save state
- flush buffers
- release resources

Plugins should support graceful shutdown.

---

# Plugin Communication

Plugins should never communicate directly.

Correct

```
Telegram Collector

↓

RawPostEvent

↓

Intelligence
```

Incorrect

```
Telegram Plugin

↓

Discord Plugin
```

Communication always occurs through the Event Bus.

---

# Plugin Responsibilities

Plugins should

- Integrate external services
- Publish events
- Subscribe to events
- Translate external APIs into internal events

Plugins should **not**

- Control the runtime
- Modify the Engine
- Access unrelated plugins
- Bypass the Event Bus

---

# Configuration

Every plugin should maintain its own configuration.

Example

```yaml
telegram:
    enabled: true
    api_id: ...
    api_hash: ...
    channels:
        - Python Jobs
        - Freelance India
```

Plugin configuration should remain isolated.

---

# Error Handling

Plugin failures should never crash the platform.

Example

```
Telegram Plugin

✗ Failed

↓

Guardian detects failure

↓

Restart Plugin

↓

Platform continues running
```

Plugins fail independently.

---

# Security

Plugins should never access resources they do not own.

Examples

A Telegram plugin should not modify

- Storage
- Other plugins
- Engine internals

The Engine should provide controlled interfaces.

---

# Version Compatibility

Every plugin should declare

- Plugin version
- Minimum Archangel version
- Maximum supported version (optional)

Incompatible plugins should not load.

---

# Development Guidelines

When creating a new plugin, answer these questions.

- What problem does this plugin solve?
- What events does it publish?
- What events does it subscribe to?
- What configuration does it require?
- What permissions does it need?
- What external services does it use?

If these questions cannot be answered clearly, the plugin should be redesigned.

---

# Example

Adding a GitHub collector should look like

```
plugins/

github/

plugin.py

manifest.yaml

config.py
```

No Engine code should need modification.

Running

```
archangel summon
```

should automatically discover the plugin and begin collecting GitHub opportunities.

---

# Future Plugin Marketplace

The architecture should eventually support third-party plugins.

Possible examples

- LinkedIn Collector
- Upwork Collector
- Fiverr Collector
- Slack Notifications
- Notion Exporter
- Google Sheets Exporter
- CRM Integrations
- AI Providers

Installing a plugin should be as simple as dropping it into the `plugins/` directory or installing it through a future plugin manager.

---

# Engineering Rules

## Rule 1

Every plugin owns one responsibility.

---

## Rule 2

Plugins communicate only through events.

---

## Rule 3

Plugins should never modify Engine internals.

---

## Rule 4

Plugins should be discoverable automatically.

---

## Rule 5

Plugins should be independently testable.

---

## Rule 6

Plugin failures should never stop the platform.

---

## Rule 7

Every plugin should include documentation and a manifest.

---

## Rule 8

Adding a plugin should not require changing existing plugins.

---

# Closing Statement

The plugin system is the foundation of The Archangel's extensibility.

Rather than embedding integrations directly into the Engine, every external capability should exist as an isolated, self-contained plugin with clearly defined responsibilities.

This allows The Archangel to evolve from a lead intelligence platform into a flexible ecosystem capable of adapting to new services, new AI providers, and new workflows without compromising its architecture.