# Design Specification: Telegram Remote Bridge

## 1. Overview
The Telegram Remote Bridge plugin adds a Telegram bot integration to Archangel, providing full remote control to whitelisted users. Authorized users can chat with the AI, run system commands, and trigger scans remotely.

## 2. Architecture & File Structure
A new plugin is added under `archangel/plugins/telegram_bridge/`:

* `manifest.yaml`: Describes the plugin name, version, description, category, author, and required permissions.
* `__init__.py`: Plugin entry point, manages background thread for the telegram-bot application lifecycle (start, run, stop).
* `auth.py`: Checks user ID authorization dynamically against `configs/notifications.yaml`.
* `bridge.py`: Manages LLMClient and CommandExecutor instances, maintains user history, and runs the tool-execution loop.
* `bot.py`: Configures python-telegram-bot application, sets up handlers (`/start`, `/status`, `/clear`, `/help`, `/scan`, and text messages).

## 3. Dynamic Configuration
Instead of a hardcoded list, the allowed user IDs are dynamically read from `configs/notifications.yaml` (uncommented and updated during setup):
```yaml
channels:
  telegram:
    enabled: true
    bot_token: "${TELEGRAM_BOT_TOKEN}"
    allowed_user_ids: [8741237853]
```
If `configs/notifications.yaml` is missing or the allowed user IDs are not set, it will fallback to a default safe list or logging a warning.

## 4. Message Flow & Execution (Approach A)
1. **Telegram Handler**: When a message/command is received, check auth via `is_authorized(user_id)`.
2. **Offload to Worker Thread**: Call the bridge message processor using `asyncio.to_thread` to prevent blocking the async polling event loop.
3. **Tool Execution Loop**:
   * Append query to the user's history list.
   * Call `llm.chat(history)`.
   * Parse results for `<execute>` and `<search>` tags.
   * Execute found tools, append outputs (e.g. `<output>...`, `<search_results>...`), and loop (maximum 5 iterations).
4. **Message Splitting**: Split responses longer than 4096 characters to comply with Telegram API constraints.
5. **Response Sending**: Send the final generated response back to the user.
