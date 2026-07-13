# 🔄 Pipeline

> Defines how information flows through The Archangel.
>
> This document specifies the lifecycle of a lead, from the moment it is discovered to the moment it is delivered to the user.
>
> Every stage in the pipeline has a single responsibility and communicates through events.
>
> This document is considered the source of truth for data flow within the platform.

---

# Philosophy

The Archangel is built around a processing pipeline.

Raw information enters the system.

Intelligence is added at each stage.

The output is a curated, high-value opportunity rather than an unfiltered post.

Every stage should improve the quality of the information before passing it to the next stage.

---

# High-Level Pipeline

```text
                  Internet
                      │
                      ▼
              Source Plugins
                      │
                      ▼
                Collector Agent
                      │
               RawPostEvent
                      │
                      ▼
           Intelligence Agent
                      │
            LeadAnalysisEvent
                      │
                      ▼
             Scoring Agent
                      │
             LeadScoredEvent
                      │
                      ▼
             Storage Agent
                      │
             LeadStoredEvent
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
 Notification Agent        Export Agent
          │
          ▼
         User
```

Every stage communicates through events.

No stage should directly invoke another stage.

---

# Pipeline Goals

The processing pipeline should always be

- Deterministic
- Modular
- Observable
- Replaceable
- Fault Tolerant
- Event Driven

Each stage should perform exactly one responsibility.

---

# Stage 1 — Collection

Responsible Agent

```
Collector Agent
```

Purpose

Retrieve raw content from supported platforms.

Possible sources include

- Telegram
- Reddit
- Discord
- GitHub
- RSS
- Future plugins

Collectors should never analyze information.

Their responsibility ends once raw content has been normalized.

Output

```
RawPostEvent
```

---

# Raw Post Format

Every collector should normalize incoming content into a common structure.

Example

```json
{
  "source": "telegram",
  "channel": "Python Jobs",
  "author": "john_doe",
  "content": "...",
  "timestamp": "...",
  "url": "...",
  "metadata": {}
}
```

Every collector must produce the same schema regardless of the original platform.

---

# Stage 2 — Intelligence

Responsible Agent

```
Intelligence Agent
```

Purpose

Understand the collected information.

The Intelligence Agent determines

- Is this actually a lead?
- Is someone hiring?
- Estimated budget
- Urgency
- Confidence
- Technologies
- Required skills
- Category
- Duplicate probability
- Recommended action

Output

```
LeadAnalysisEvent
```

---

# AI Output

Example

```json
{
  "lead": true,
  "confidence": 0.94,
  "estimated_budget": "$500-$1000",
  "urgency": "High",
  "category": "Automation",
  "tags": [
    "Python",
    "Telegram",
    "AI"
  ]
}
```

AI output should always be structured.

Free-form text should be avoided whenever possible.

---

# Stage 3 — Scoring

Responsible Agent

```
Scoring Agent
```

Purpose

Prioritize opportunities.

Every accepted lead receives a numerical score.

Possible scoring factors

- Confidence
- Budget
- Urgency
- Keyword Match
- Source Quality
- Recency
- Historical Success

Example

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

Output

```
LeadScoredEvent
```

---

# Stage 4 — Storage

Responsible Agent

```
Storage Agent
```

Purpose

Persist all processed information.

Store

- Raw posts
- AI analysis
- Lead score
- Metadata
- Runtime history
- Export history

Storage is responsible for persistence only.

Output

```
LeadStoredEvent
```

---

# Stage 5 — Notification

Responsible Agent

```
Notification Agent
```

Purpose

Notify the user when a valuable opportunity has been identified.

Possible channels

- Telegram
- Discord
- Desktop
- Email

Notifications should be configurable.

Output

```
LeadDeliveredEvent
```

---

# Stage 6 — Export

Responsible Agent

```
Export Agent
```

Purpose

Generate external representations of stored leads.

Supported formats

- CSV
- JSON
- Markdown
- Excel

Exporting should never modify stored information.

---

# Event Flow

The complete runtime flow should resemble

```text
Internet

↓

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

LeadStoredEvent

↓

Notification

↓

LeadDeliveredEvent
```

Every transition should occur through the Event Bus.

---

# Event Bus

The Event Bus is the communication backbone of the platform.

Every stage publishes events.

Every stage subscribes to events.

Stages should never directly invoke one another.

Correct

```text
Collector

↓

RawPostEvent

↓

Intelligence
```

Incorrect

```text
Collector

↓

Intelligence.analyze()
```

Direct dependencies increase coupling.

Events improve modularity.

---

# Error Recovery

Failures should remain isolated.

Example

```text
Collector

✓

Intelligence

✓

Scoring

✗

Storage

Waiting

Notification

Waiting
```

The Guardian should detect failures and restart affected agents without stopping the entire platform.

---

# Duplicate Detection

The Intelligence Agent should identify duplicate opportunities before scoring.

Possible strategies

- URL comparison
- Content similarity
- Author comparison
- Hash comparison
- AI similarity

Duplicate handling should occur before Storage whenever possible.

---

# Filtering

Not every collected post should continue through the pipeline.

Examples

- Spam
- Advertisements
- Duplicate posts
- Blacklisted keywords
- Low-confidence leads

Filtering should reduce unnecessary AI and storage work.

---

# Queue Management

Each stage should process events independently.

Every stage should maintain its own queue.

Example

```text
Collector Queue

↓

Analysis Queue

↓

Scoring Queue

↓

Storage Queue

↓

Notification Queue
```

Independent queues improve reliability and throughput.

---

# Parallel Processing

Whenever possible, stages should operate concurrently.

Example

```text
Collector A

┐

Collector B

├────► Analysis

Collector C

┘
```

The pipeline should support multiple collectors without changing downstream logic.

---

# Observability

Every pipeline stage should expose runtime metrics.

Possible metrics

- Events processed
- Queue length
- Processing time
- Errors
- Success rate
- Average latency

These metrics allow the Guardian to monitor platform health.

---

# Pipeline Rules

The following rules should never be violated.

## Rule 1

Collectors only collect.

---

## Rule 2

Intelligence only analyzes.

---

## Rule 3

Scoring only ranks.

---

## Rule 4

Storage only persists.

---

## Rule 5

Notifications only deliver.

---

## Rule 6

Exports only transform stored data.

---

## Rule 7

Every stage communicates through events.

---

## Rule 8

No stage should bypass another stage.

---

## Rule 9

Every event should have a well-defined schema.

---

## Rule 10

Every stage should be independently testable.

---

# Future Pipeline Extensions

The architecture should support inserting new stages without rewriting the pipeline.

Possible additions

```text
Collector

↓

Normalizer

↓

Translation

↓

Intelligence

↓

Memory

↓

Scoring

↓

Storage
```

or

```text
Storage

↓

Outreach

↓

Approval

↓

Message Delivery
```

The Event Bus should make these additions straightforward.

---

# Closing Statement

The pipeline is the operational backbone of The Archangel.

Every opportunity discovered by the platform travels through the same predictable lifecycle—from collection, to intelligence, to prioritization, to persistence, and finally to delivery.

By keeping each stage independent and event-driven, the pipeline remains modular, scalable, fault tolerant, and easy to extend as The Archangel evolves into a fully autonomous lead intelligence platform.