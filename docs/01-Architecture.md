# 🏛️ System Architecture

> Defines the architecture of The Archangel.
>
> This document explains how every major subsystem communicates, why the architecture exists, and the responsibilities of every layer.
>
> This document is considered the architectural source of truth.

---

# Architecture Philosophy

The Archangel follows a modular, event-driven architecture.

Instead of building one large application where every component depends on every other component, the system is divided into independent modules with clearly defined responsibilities.

Each subsystem owns one area of responsibility and communicates through the Event Bus.

No subsystem should directly manipulate another subsystem's internal state.

---

# High-Level Architecture

```
                    User
                      │
                      ▼
                 CLI Interface
                      │
                      ▼
                Commander Agent
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
  Runtime Engine             Guardian Agent
         │
         ▼
     Event Bus
         │
 ┌───────┼────────────────────────────────────┐
 ▼       ▼         ▼         ▼        ▼       ▼
Collectors Analysis Scoring Storage Notifications Export
```

Every component is independent.

Every component communicates using events.

---

# Core Components

The platform is composed of the following primary layers.

```
CLI

↓

Engine

↓

Agents

↓

Subsystems

↓

Infrastructure
```

Each layer has a clearly defined responsibility.

---

# CLI Layer

Purpose

Provide the user interface.

The CLI never performs business logic.

Its only responsibility is converting user commands into engine operations.

Example

```
archangel summon
```

↓

```
CLI

↓

Engine.start()
```

Never

```
CLI

↓

Collector

↓

Database

↓

Notification
```

The CLI should never know how the system works internally.

---

# Engine Layer

The Engine is the heart of the platform.

It coordinates the runtime.

Responsibilities

- Startup
- Shutdown
- Runtime lifecycle
- Event loop
- Plugin loading
- Agent registration
- Scheduler
- Configuration loading

The Engine does not perform AI analysis.

It does not collect data.

It does not store data.

It simply coordinates the platform.

---

# Agent Layer

Agents represent autonomous decision makers.

Each agent owns exactly one responsibility.

Current agents

- Guardian
- Commander
- Collector
- Intelligence
- Scoring
- Storage
- Notification
- Export

Future

- Outreach
- Memory

Agents communicate through events.

Agents never directly manipulate another agent.

---

# Subsystem Layer

Subsystems implement functionality.

Examples

Collectors

AI Analysis

Storage

Notifications

Exports

Plugins

Configuration

These are libraries.

They are not orchestrators.

---

# Infrastructure Layer

Infrastructure provides shared services.

Examples

Logging

Configuration

Utilities

Networking

Filesystem

Infrastructure should contain no business logic.

---

# Runtime Lifecycle

The platform has four runtime states.

```
Stopped

↓

Starting

↓

Running

↓

Stopping
```

Only the Engine controls state transitions.

---

# Startup Sequence

Executing

```
archangel summon
```

starts the following sequence.

```
Display Banner

↓

Load Configuration

↓

Validate Configuration

↓

Initialize Logger

↓

Initialize Event Bus

↓

Initialize Storage

↓

Load Plugins

↓

Spawn Guardian

↓

Spawn Commander

↓

Spawn Collector Agent

↓

Spawn Intelligence Agent

↓

Spawn Scoring Agent

↓

Spawn Notification Agent

↓

Run Health Check

↓

Mission Operational
```

The platform is not considered running until every critical component reports READY.

---

# Shutdown Sequence

Executing

```
archangel terminate
```

starts a graceful shutdown.

```
Freeze Guardian

↓

Stop accepting new work

↓

Stop Collectors

↓

Flush Event Queue

↓

Complete AI Analysis

↓

Save Database

↓

Complete Notifications

↓

Finish Exports

↓

Unload Plugins

↓

Close Logger

↓

Shutdown
```

No data should be lost during shutdown.

---

# Event Bus

The Event Bus is the communication backbone.

No subsystem should communicate directly with another subsystem.

Instead

```
Collector

↓

NewPostEvent

↓

Analysis
```

instead of

```
Collector

↓

Analysis.process()
```

This reduces coupling.

---

# Event Flow

Example

```
Telegram Collector

↓

RawPostEvent

↓

Intelligence

↓

LeadAnalysisEvent

↓

Scoring

↓

LeadScoredEvent

↓

Storage

↓

LeadStoredEvent

↓

Notification

↓

LeadDeliveredEvent
```

Each stage only understands the event it receives.

---

# Plugin Architecture

Every external source should be implemented as a plugin.

Examples

```
Telegram

Discord

Reddit

GitHub

RSS
```

The Engine discovers plugins automatically.

Collectors should never be hardcoded.

---

# Storage Architecture

Storage is abstracted behind one interface.

Possible implementations

```
SQLite

JSON

PostgreSQL

Future cloud databases
```

Switching storage providers should not require changes elsewhere.

---

# AI Architecture

The AI system is responsible for reasoning.

It determines

- Is this a lead?
- Confidence
- Budget
- Urgency
- Tags
- Duplicate detection
- Recommended action

The AI never writes directly to storage.

The AI never sends notifications.

---

# Notification Architecture

Notifications subscribe to completed leads.

Possible channels

- Telegram
- Discord
- Email
- Desktop

Notification systems should not know where the data originated.

---

# Error Handling

Every component should fail independently.

Example

```
Discord Collector crashes
```

Guardian detects failure.

↓

Collector restarted.

↓

System continues running.

The entire platform should never terminate because one collector failed.

---

# Scalability

The architecture should support

- multiple collectors
- multiple AI providers
- multiple storage providers
- multiple notification systems

without rewriting the engine.

---

# Engineering Rules

The following rules should never be violated.

## Rule 1

One component owns one responsibility.

---

## Rule 2

Communication happens through events.

---

## Rule 3

Collectors never perform AI analysis.

---

## Rule 4

AI never writes directly to storage.

---

## Rule 5

Storage never performs notifications.

---

## Rule 6

The CLI never performs business logic.

---

## Rule 7

The Engine coordinates.

It does not own business logic.

---

## Rule 8

Plugins should extend functionality.

They should never require engine modifications.

---

# Future Architecture

Future capabilities should plug into the existing architecture.

Examples

```
Memory Agent

↓

Event Bus

↓

Everything works.
```

or

```
LinkedIn Plugin

↓

Collector

↓

No Engine Changes
```

If adding a feature requires rewriting the Engine, the architecture should be reconsidered.

---

# Architecture Goals

The architecture should always optimize for:

- Modularity
- Maintainability
- Replaceability
- Observability
- Testability
- Scalability
- AI-assisted development

These goals take priority over clever implementations.

---

# Closing Statement

The architecture of The Archangel is designed to remain stable for years.

Collectors, AI models, storage providers, notification channels, export, and plugins should evolve independently while the Engine continues coordinating the platform through a consistent event-driven runtime.

Every architectural decision should move the system toward that goal.