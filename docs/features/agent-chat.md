# 💬 Agent Chat — Direct Subsystem Communication

Why talk to a generic AI bot that tries to do everything when you can speak directly to the specialized agent running that part of Archangel?

Agent Chat gives every core subsystem in Archangel—from the Web Collector to the Database Storage engine—its own dedicated AI persona and interactive chat session.

---

## ⚡ How to Chat with Agents

You can talk to any of Archangel's 7 core agents either in **Interactive Multi-Turn Mode** or via **Quick One-Shot Queries**.

### 1. Interactive Chat Mode
Type `<agent> chat` or `archangel.<agent> chat` in the terminal or REPL to drop into a dedicated sub-shell for that agent:

```bash
# In your terminal or inside archangel.main>
archangel.main> collector chat
```

This opens a dedicated prompt (`archangel.collector> `) where you can have a continuous back-and-forth conversation.

| Command | Target Agent | Best Used For |
| :--- | :--- | :--- |
| `collector chat` | `archangel.collector` | Web scraping, RSS feeds, Reddit search, X/Twitter filters |
| `commander chat` | `archangel.commander` | Platform orchestration, agent tasks, workflow status |
| `intelligence chat` | `archangel.intelligence` | Lead classification rules, buyer intent, complaint phrases |
| `scoring chat` | `archangel.scoring` | Urgency formulas, lead ranking metrics, budget confidence |
| `guardian chat` | `archangel.guardian` | System health checks, diagnostic errors, error logs |
| `storage chat` | `archangel.storage` | SQLite WAL database stats, lead export formats, schema |
| `notification chat` | `archangel.notification` | Telegram bot alerts, Discord webhooks, message formatting |

> 💡 **To Exit:** Type `exit`, `quit`, or `back` at any time to return to `archangel.main>`.

### 2. Quick One-Shot Queries
If you just want a fast answer without leaving your main workflow, pass your question directly on the command line:

```text
archangel.main> collector "how do I add a custom RSS feed?"
archangel.main> intelligence "evaluate: looking to hire python dev for scraping script"
archangel.main> guardian "what is the current status of all background tasks?"
```

---

## ⚙️ How It Works Under the Hood

When you start an Agent Chat:

1. **System Persona Injection**: Archangel instantly equips the LLM with a specialized system prompt tailored specifically to that agent's exact domain rules and responsibilities.
2. **Dedicated Command History**: Every agent maintains its own persistent history file in your user home directory (`~/.archangel_<agent>_history`), so tab-completion and prompt history remember your previous agent conversations.
3. **Real-time Tool Access**: Agents can execute PowerShell commands (`<execute>`) or perform live web lookups (`<search>`) to inspect system states or gather facts for you while you chat.

---

## 🔥 Why This Matters (The Benefits)

- **Domain-Specific Answers**: The Collector agent talks like a web scraping specialist; the Storage agent talks like a database administrator. You get accurate, focused answers.
- **Instant System Diagnostics**: Instead of reading raw log files, you can simply ask `guardian chat` why a task failed or ask `storage chat` how many leads were saved today.
- **Fast Rule Tuning**: Want to tweak how Archangel identifies leads? Jump into `intelligence chat` to discuss complaint language patterns and refine your detection strategy.
- **Clean Sub-REPL Workflow**: The custom prompt (`archangel.collector>`) keeps your workspace organized so you always know which component you are instructing.
