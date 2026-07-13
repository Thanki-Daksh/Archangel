# 👾 Agents

> Defines every autonomous agent within The Archangel.
>
> This document specifies the purpose, responsibilities, communication model, lifecycle, and engineering rules for every agent in the system.
>
> Agents are autonomous workers coordinated by the Commander and supervised by the Guardian.
>
> Every agent owns **one responsibility**.

---

# Philosophy

The Archangel is **not** built around one giant AI loop.

Instead, it is composed of multiple specialized agents.

Each agent performs exactly one responsibility.

This provides:

- Easier debugging
- Better testing
- Better scalability
- Easier model replacement
- Lower coupling
- Clear ownership

Instead of

```
LLM

↓

Everything
```

The system becomes

```
Collectors

↓

Intelligence

↓

Scoring

↓

Storage

↓

Notifications

↓

Export
```

---

# Agent Architecture

```
                   User
                     │
                     ▼
                CLI Interface
                     │
                     ▼
              Commander Agent
                     │
      ┌──────────────┼──────────────┐
      ▼              ▼              ▼
 Collector      Intelligence     Storage
      │              │
      └──────┐  ┌────┘
             ▼  ▼
          Scoring
              │
              ▼
       Notification
              │
              ▼
            Export
```

Guardian supervises the entire system.

---

# Shared Lifecycle

Every agent follows the same lifecycle.

```
Created

↓

Initialized

↓

Starting

↓

Running

↓

Stopping

↓

Stopped
```

The Commander controls startup.

The Guardian monitors health.

---

# Shared Rules

Every agent must:

- own one responsibility
- communicate through events
- expose health information
- support graceful shutdown
- recover safely after restart

Every agent must **not**:

- modify another agent's internal state
- bypass the Event Bus
- directly call unrelated agents
- contain unrelated business logic

---

# Guardian Agent

## Purpose

The Guardian supervises the health of the platform.

It never performs business logic.

---

## Responsibilities

- Monitor all agents
- Detect crashes
- Detect stalled queues
- Restart failed agents
- Publish health events
- Collect runtime metrics

---

## Health States

```
✅ Healthy

⚠️ Degraded

❌ Offline
```

---

## Events

Consumes

- AgentStarted
- AgentStopped
- AgentHeartbeat
- AgentFailure

Produces

- HealthChanged
- RestartRequested
- SystemHealthy
- SystemDegraded

---

## Forbidden

Guardian never

- collects leads
- performs AI analysis
- stores data
- sends notifications

---

# Commander Agent

## Purpose

The Commander orchestrates the platform.

Every startup and shutdown operation begins here.

---

## Responsibilities

- Start agents
- Stop agents
- Register agents
- Route commands
- Coordinate runtime
- Initialize subsystems

---

## Events

Consumes

- CLICommand
- ShutdownRequest
- StartupRequest

Produces

- AgentStart
- AgentStop
- RuntimeReady
- RuntimeShutdown

---

## Forbidden

Commander never

- analyzes posts
- scores leads
- stores data

It coordinates.

Nothing more.

---

# Collector Agent

## Purpose

The Collector gathers raw information.

Nothing else.

---

## Responsibilities

- Receive data from collectors
- Normalize payloads
- Validate payloads
- Publish RawPost events

---

## Sources

Examples

- Telegram
- Reddit
- Discord
- GitHub
- RSS

Future plugins should integrate here.

---

## Output

```
RawPostEvent
```

---

## Forbidden

Collectors never

- call AI
- score leads
- send notifications
- write databases

---

# Intelligence Agent

## Purpose

The Intelligence Agent is the reasoning engine.

It converts raw information into structured understanding.

---

## Responsibilities

Determine

- Is this a lead?
- Confidence
- Estimated budget
- Urgency
- Category
- Duplicate detection
- Recommended response
- Relevant tags

---

## Input

```
RawPostEvent
```

---

## Output

```
LeadAnalysisEvent
```

---

## Forbidden

The Intelligence Agent never

- stores information
- sends notifications
- exports reports

---

# Scoring Agent

## Purpose

Rank opportunities.

---

## Responsibilities

Generate a numerical Lead Score.

Possible factors

- Confidence
- Budget
- Urgency
- Recency
- Keyword relevance
- Source quality

---

## Example

```
Confidence

+

Budget

+

Urgency

+

Keyword Match

+

Recency

=

Lead Score
```

---

## Output

```
LeadScoredEvent
```

---

# Storage Agent

## Purpose

Persist information.

---

## Responsibilities

Store

- Raw posts
- Analysis
- Scores
- Metadata
- Runtime history

Possible storage backends

- SQLite
- JSON
- PostgreSQL

---

## Forbidden

Storage never

- performs AI analysis
- sends notifications
- exports data

---

# Notification Agent

## Purpose

Deliver completed opportunities.

---

## Responsibilities

Send notifications through

- Telegram
- Discord
- Email
- Desktop

---

## Input

```
LeadStoredEvent
```

---

## Output

```
LeadDeliveredEvent
```

---

## Forbidden

Notifications never

- analyze data
- modify leads
- store information

---

# Export Agent

## Purpose

Generate external reports.

---

## Formats

- CSV
- JSON
- Markdown
- Excel

---

## Responsibilities

Transform stored leads into export formats.

---

## Forbidden

Exporters never

- analyze data
- notify users
- collect information

---

# Outreach Agent (Future)

## Purpose

Generate personalized outreach.

This agent will only operate after a lead has been approved.

---

## Planned Workflow

```
Lead Approved

↓

Generate proposal

↓

Generate email

↓

Wait for approval

↓

Send
```

This agent will always require explicit user approval before sending messages.

---

# Communication Model

Agents never communicate directly.

Correct

```
Collector

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

Notification
```

Incorrect

```
Collector

↓

Storage.save()

↓

Notification.send()

↓

AI.analyze()
```

Direct dependencies increase coupling.

Events reduce coupling.

---

# Startup Order

```
Guardian

↓

Commander

↓

Collector

↓

Intelligence

↓

Scoring

↓

Storage

↓

Notification

↓

Export
```

The platform is operational only after every critical agent reports READY.

---

# Shutdown Order

```
Stop Collectors

↓

Finish AI Queue

↓

Finish Scoring

↓

Flush Storage

↓

Finish Notifications

↓

Finish Exports

↓

Shutdown
```

Every shutdown should preserve pending work whenever possible.

---

# Future Agents

Potential additions include

- Memory Agent
- Analytics Agent
- Scheduler Agent
- Workflow Agent
- Plugin Manager
- Cache Agent
- Learning Agent

These should integrate through the Event Bus without requiring architectural changes.

---

# Engineering Principles

When creating a new agent, the following questions should all have clear answers:

- What is this agent responsible for?
- What events does it consume?
- What events does it publish?
- What information does it own?
- What is it explicitly forbidden from doing?

If any answer is unclear, the agent's responsibilities should be reconsidered.

---

# Closing Statement

Agents are the foundation of The Archangel.

They transform the platform from a simple lead scraper into an autonomous intelligence system.

By separating responsibilities into independent, event-driven workers, The Archangel remains modular, scalable, maintainable, and adaptable as new capabilities are added.