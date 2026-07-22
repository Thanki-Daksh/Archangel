# 💬 Agent Chat — Direct Subsystem Communication & Groupchat

Why talk to a generic AI bot that tries to do everything when you can speak directly to the specialized agents running Archangel?

Agent Chat gives every core subsystem in Archangel—from the Web Collector to the Database Storage engine—its own dedicated AI persona, topic-routing hub, and multi-agent groupchat room.

---

## ⚡ How to Chat with Agents

You can interact with Archangel's 7 core agents in 4 flexible ways:

### 1. Interactive Single-Agent Chat Mode
Type `<agent> chat` or `archangel.agents.<agent>` in the terminal or REPL to drop into a dedicated sub-shell for that agent:

```bash
archangel.main> collector chat
```

This opens prompt `archangel.agents.collector>` for continuous back-and-forth conversation.

| Command | Prompt | Target Subsystem |
| :--- | :--- | :--- |
| `collector chat` | `archangel.agents.collector>` | Web scraping, RSS feeds, Reddit JSON API, X/Twitter search |
| `commander chat` | `archangel.agents.commander>` | Platform orchestration, agent tasks, workflow status |
| `intelligence chat` | `archangel.agents.intelligence>` | Lead classification rules, buyer intent, complaint phrases |
| `scoring chat` | `archangel.scoring>` | Urgency formulas, lead ranking metrics, budget rating |
| `guardian chat` | `archangel.guardian>` | System health checks, diagnostic errors, error logs |
| `storage chat` | `archangel.storage>` | SQLite WAL database stats, lead export formats, schema |
| `notification chat` | `archangel.notification>` | Telegram bot alerts, Discord webhooks, message formatting |

---

### 2. Central Agent Topic-Routing Hub (`agents`)
Type `agents` or `archangel.agents` to enter the central agent hub (`archangel.agents>`).

In this hub, **all 7 agents are active**. Type any question without specifying an agent name, and the Hub automatically routes your message to the matching domain expert agent.

---

### 3. Multi-Agent Groupchat Room (`groupchat`)
Type `groupchat` or `archangel.agents.groupchat` to enter the multi-agent collaboration room (`archangel.agents.groupchat>`).

Throw a high-level goal into the room:
> *"Find 5 Python scraping leads on Reddit, score them, save to storage, and alert Telegram"*

All 7 agents take turns conversing, delegating, and executing the objective collaboratively in sequence:

```text
archangel.agents.groupchat> Find 5 Python scraping leads and notify Telegram

archangel.agents.commander>
  Initiating group workflow. Assigning data discovery to Collector.

archangel.agents.collector>
  Found 5 Reddit posts matching 'Python scraping'. Passing to Intelligence for classification.

archangel.agents.intelligence>
  Analyzed 5 posts: 3 verified demand-side leads. Passing to Scoring.

archangel.agents.scoring>
  Lead 1 (9.2/10), Lead 2 (8.5/10), Lead 3 (7.8/10). Passing to Storage.

archangel.agents.storage>
  Saved 3 leads into SQLite WAL database. Passing to Notification.

archangel.agents.notification>
  Dispatched Telegram alert for 3 top leads. Task complete.
```

---

## ⚙️ How It Works Under the Hood

1. **System Persona Injection**: Each agent receives a specialized domain system prompt defining its expertise.
2. **Dedicated Command History**: History files are persisted (`~/.archangel_<agent>_history`, `~/.archangel_groupchat_history`) for seamless tab completion.
3. **Structured Agent Handoffs**: In groupchat mode, the Commander agent moderates turn-taking and passes data outputs between sibling agents.
