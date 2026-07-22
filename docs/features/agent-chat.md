# 💬 Agent Chat — Direct Subsystem Communication & Universal CLI Commands

Why talk to a generic AI bot that tries to do everything when you can speak directly to the specialized agents running Archangel?

Agent Chat gives every core subsystem in Archangel—from the Web Collector to the Database Storage engine—its own dedicated AI persona, topic-routing hub, multi-agent groupchat room, and universal slash-command pass-through.

---

## ⚡ 4 Ways to Interact with Agents

You can interact with Archangel's 7 core agents in 4 flexible ways:

### 1. Interactive Single-Agent Chat Mode
Type `<agent> chat` or `archangel.agents.<agent>` in the terminal or REPL to drop into a dedicated sub-shell for that agent:

```bash
archangel.main> collector chat
```

This opens the `archangel.agents.collector>` prompt for continuous back-and-forth conversation with that specific domain expert.

| Command | Prompt | Target Subsystem & Purpose |
| :--- | :--- | :--- |
| `collector chat` | `archangel.agents.collector>` | Web scraping, RSS feeds, Reddit JSON API, X/Twitter search |
| `commander chat` | `archangel.agents.commander>` | Platform orchestration, agent tasks, workflow status |
| `intelligence chat` | `archangel.agents.intelligence>` | Lead classification rules, buyer intent, complaint phrases |
| `scoring chat` | `archangel.agents.scoring>` | Urgency formulas, lead ranking metrics, budget rating |
| `guardian chat` | `archangel.agents.guardian>` | System health checks, diagnostic errors, error logs |
| `storage chat` | `archangel.agents.storage>` | SQLite WAL database stats, lead export formats, schema |
| `notification chat` | `archangel.agents.notification>` | Telegram bot alerts, Discord webhooks, message formatting |

---

### 2. Central Agent Topic-Routing Hub (`agents`)
Type `agents` or `archangel.agents` to enter the central agent hub (`archangel.agents>`).

In this hub, **all 7 agents are present**. Type any question without specifying an agent name, and the Hub automatically analyzes the subject and routes your message to the matching domain expert agent.

---

### 3. Multi-Agent Groupchat Room (`groupchat`)
Type `groupchat` or `archangel.agents.groupchat` to enter the multi-agent collaboration room (`archangel.agents.groupchat>`).

Throw a high-level goal into the room:
> *"Find 5 Python scraping leads on Reddit, score them, save to storage, and alert Telegram"*

The groupchat engine runs an optimized, non-yapping collaboration loop (2–4 agents maximum respond sequentially):

```text
archangel.agents.groupchat> Find 5 Python scraping leads and notify Telegram

(the commander agent is typing...)
archangel.agents.commander>
  Initiating group workflow. Assigning data discovery to Collector.

(the collector agent is typing...)
archangel.agents.collector>
  Found 5 Reddit posts matching 'Python scraping'. Passing to Intelligence for classification.

(the intelligence agent is typing...)
archangel.agents.intelligence>
  Analyzed 5 posts: 3 verified demand-side leads. Passing to Storage.

(the notification agent is typing...)
archangel.agents.notification>
  Dispatched Telegram alert for 3 top leads. Task complete.
```

**Key UI & Engine Features:**
- **Animated Typing Indicators**: Live `the <agent> agent is typing...` status animation appears while the agent works and disappears automatically once finished.
- **Single Header**: Header panel shows online agents count and active `⬢ Busy` status badges without spamming the console.
- **Clean Exit**: Exiting any chat mode outputs a clean blank line (`\n`) back to `archangel.main>`.

---

### 4. Universal Slash Commands (`/`)
You can execute **any system command from anywhere** inside any chat room or groupchat by prefixing it with a slash (`/`):

```text
archangel.agents.groupchat> /start telegram
archangel.agents.collector> /status
archangel.agents.commander> /logs
archangel.agents.intelligence> /models
```

- If you type `/start telegram`, `/status`, `/logs`, `/config`, etc., Archangel executes the system command directly.
- Chat-specific slash commands like `/models` (switch provider), `/key` (manage API keys), and `/clear` (clear screen) continue to work seamlessly.

---

## 🛡️ High-Availability LLM Failover

Archangel features an automatic multi-provider fallback engine. If your active LLM provider encounters a 500 Internal Server Error, 503 Outage, Rate Limit (429), or Network Timeout:

1. The system silently catches the failure without crashing your chat or spamming error logs.
2. It automatically switches to the next available API provider in your environment (`GROQ` → `OPENCODEZEN` → `OPENROUTER` → `GEMINI` → `OPENAI` → `ANTHROPIC`).
3. Your agent conversation continues uninterrupted.

---

## 🤖 Telegram Remote Control Bridge

To start the interactive Telegram bot bridge:

```text
archangel.main> start telegram
```
*(or `/start telegram` from any chat mode)*

- **Single Instance Guard**: If the Telegram bridge is already running in another window, launching `start telegram` alerts you that it is already running.
- **Detailed Help**: Run `start telegram --help` or `--help detailed` in `archangel.main>` for full CLI options and bot directives.
