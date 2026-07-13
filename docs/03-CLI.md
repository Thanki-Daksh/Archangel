# 🖥️ Command Line Interface (CLI)

> Defines the command-line interface of The Archangel.
>
> The CLI is the primary interface between the user and the platform.
> Every interaction with The Archangel begins here.
>
> The CLI should feel like a professional developer tool while maintaining the identity of The Archangel.

---

# Philosophy

The CLI is intentionally designed around a small set of memorable commands.

The user should never need to remember complicated syntax.

Instead of

```
python main.py --run --telegram --watch
```

The experience should be

```bash
archangel
```

or

```bash
archangel summon
```

Both commands should behave identically.

Running `archangel` without a subcommand should automatically invoke `archangel summon`.

Simple.

Readable.

Memorable.

---

# Design Principles

The CLI should always be:

- Fast
- Predictable
- Discoverable
- Scriptable
- Minimal
- Human-friendly

Every command should perform one task well.

---

# Naming Convention

Commands follow a verb-first structure.

Examples

```
archangel summon
archangel terminate
archangel watch
archangel doctor
```

Avoid unnecessary flags whenever possible.

Good

```
archangel scan
```

Bad

```
python main.py --execute-scan-now
```

---

# Startup Experience

When executed

```bash
archangel
```

or

```bash
archangel summon
```

the platform should display the official startup banner and begin the runtime initialization sequence.

The default startup banner is:

```text
 █████╗ ██████╗  ██████╗██╗  ██╗ █████╗ ███╗   ██╗ ██████╗ ███████╗██╗
██╔══██╗██╔══██╗██╔════╝██║  ██║██╔══██╗████╗  ██║██╔════╝ ██╔════╝██║
███████║██████╔╝██║     ███████║███████║██╔██╗ ██║██║  ███╗█████╗  ██║
██╔══██║██╔══██╗██║     ██╔══██║██╔══██║██║╚██╗██║██║   ██║██╔══╝  ██║
██║  ██║██║  ██║╚██████╗██║  ██║██║  ██║██║ ╚████║╚██████╔╝███████╗███████╗
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚══════╝

               Opportunity is revealed to those who seek.
```

After displaying the banner, the CLI should begin the initialization sequence.

Example

```text
⚔️ Summoning The Archangel...

Loading configuration...
Initializing logging...
Creating Event Bus...
Loading plugins...
Initializing storage...
Awakening Guardian...
Starting Commander...
Starting Collectors...
Starting Intelligence...
Starting Scoring...
Connecting Notification Services...
Performing health checks...

═══════════════════════════════════════════════════════════════

Mission Status : OPERATIONAL
Guardian       : HEALTHY
Runtime        : READY

The Archangel has descended.

═══════════════════════════════════════════════════════════════
```

### Startup Output Rules

The CLI must never display completed status indicators (`✓`) for operations that have not actually finished.

Incorrect

```text
✓ Configuration loaded
```

before the configuration has finished loading.

Instead, display active progress messages while work is still being performed.

```text
Loading configuration...
```

Only after the operation has completed may the CLI display

```text
✓ Configuration loaded
```

or immediately continue to the next initialization step.

The CLI must always reflect the real runtime state of the platform. Progress indicators should never be misleading or displayed prematurely for cosmetic purposes.

The startup sequence should always follow the documented initialization order and should terminate immediately if a critical subsystem fails to initialize.

---

# Shutdown Experience

Executing

```
archangel terminate
```

should gracefully stop every running subsystem.

Example

```
⚔️ The Archangel returns to the heavens.

Leads Collected : 47
Runtime         : 4h 12m
Errors          : 0

Mission Complete.
```

Shutdown should never abruptly terminate the platform.

---

# Command Reference

---

## summon

Purpose

Start the platform.

Syntax

```
archangel summon
```

Responsibilities

- Load configuration
- Initialize logging
- Load plugins
- Initialize Event Bus
- Spawn agents
- Perform health checks
- Enter running state

Possible Flags

```
--debug
--verbose
--config <path>
```

---

## terminate

Purpose

Gracefully stop the platform.

Syntax

```
archangel terminate
```

Responsibilities

- Stop collectors
- Flush queues
- Save storage
- Finish notifications
- Shutdown runtime

---

## status

Purpose

Display current runtime information.

Syntax

```
archangel status
```

Example Output

```
Mission Status
✅ Operational

Collectors      5
Queued Events   18
Leads Today     42
Runtime         03:17:48
Memory          182 MB
```

---

## watch

Purpose

Display a live event stream.

Syntax

```
archangel watch
```

Example

```
[Telegram]
New Post
↓
AI Analysis
↓
Lead Accepted
↓
Stored
↓
Notification Sent
```

Useful for monitoring runtime activity.

---

## scan

Purpose

Run one complete scan.

Unlike

```
summon
```

the platform exits after completing the scan.

---

## doctor

Purpose

Run platform diagnostics.

Checks include

- Configuration
- Database
- Plugin integrity
- Event Bus
- Storage
- API Keys
- Network
- Runtime permissions

Example

```
Database     ✅
Plugins      ✅
Network      ✅
Configuration✅

Overall Status: HEALTHY
```

---

## config

Purpose

Inspect or edit configuration.

Examples

```
archangel config
archangel config edit
archangel config validate
```

---

## export

Purpose

Export collected opportunities.

Supported formats

- CSV
- JSON
- Markdown
- Excel

Example

```
archangel export csv
archangel export json
```

---

## logs

Purpose

Display runtime logs.

Examples

```
archangel logs
archangel logs errors
archangel logs runtime
```

---

## purge

Purpose

Remove temporary runtime data.

Examples

- Cache
- Temporary exports
- Old logs

This command should never remove important data without confirmation.

---

## update

Purpose

Update plugins and platform resources.

Future functionality may include

- Plugin updates
- Prompt updates
- Configuration migrations

---

## version

Purpose

Display version information.

Example

```
The Archangel
Version       1.0.0
Python        3.x
Build         Release
```

---

## help

Purpose

Display available commands.

```
archangel help
archangel help summon
```

---

# Exit Codes

```
0   Success
1   General Error
2   Configuration Error
3   Plugin Error
4   Storage Error
5   Network Error
6   Runtime Failure
```

Exit codes should remain consistent across releases.

---

# Output Philosophy

The CLI should communicate progress clearly.

Avoid

```
Done.
```

Prefer

```
✓ Configuration Loaded
✓ Plugins Initialized
✓ Guardian Ready

Mission Operational
```

Progress builds confidence.

---

# Logging Levels

The CLI should support multiple verbosity levels.

```
Normal
↓
Verbose
↓
Debug
```

Users should control how much information they receive.

---

# Error Messages

Errors should be actionable.

Bad

```
Error
```

Good

```
Storage initialization failed.

Reason:   Database file is locked.
Suggestion: Close any application using the database and retry.
```

The user should always know:

- What failed
- Why it failed
- How to fix it

---

# Future Commands

Potential additions

```
archangel restart
archangel benchmark
archangel plugins
archangel memory
archangel workflow
archangel dashboard
archangel profile
```

Future commands should follow the same naming philosophy.

---

# CLI Principles

The CLI should always remain

- Fast
- Minimal
- Predictable
- Consistent
- Scriptable

Business logic belongs inside the Engine.

The CLI should never become the Engine.

---

# Closing Statement

The CLI is more than a command runner.

It represents the public face of The Archangel.

Every command should be memorable, every output should be informative, and every interaction should reinforce the feeling that the user is operating a disciplined, autonomous intelligence platform rather than a collection of Python scripts.