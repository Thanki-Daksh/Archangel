import os, sys, time
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from archangel.cli.repl import AGENT_SYSTEM_PROMPTS, _classify_agent_topic, create_prompt_session
from archangel.cli.commands import COMMANDS as _CHAT_COMMANDS, handle_slash_command
from archangel.cli.parser import _execute_repl_command
from archangel.cli import commands as _cli_commands
def _get_project_root(): from pathlib import Path; return Path(__file__).resolve().parents[2]

def _handle_slash_intercept(raw: str, console: Console, history: list) -> bool:
    cmd = raw[1:].strip().split()[0].lower() if raw[1:].strip() else ""
    if cmd in _CHAT_COMMANDS: return handle_slash_command(raw, console, history)
    _execute_repl_command(console, raw[1:].strip()); return False

def run_agents_hub_repl(console: Console) -> None:
    from dotenv import load_dotenv; load_dotenv(_get_project_root() / ".env", override=False)
    from archangel.agents.chat import LLMClient
    try: llm = LLMClient()
    except RuntimeError as e: console.print(f"[red]{e}[/]"); return
    console.print("\n", Panel.fit("[bold cyan]🤖 archangel.agents — Hub[/]\n[dim]All 7 active. Topic-based routing.[/]", border_style="cyan"), "\n")
    session = create_prompt_session("archangel.agents> ", ".archangel_agents_hub_history")
    while True:
        try: raw = (session.prompt() if session else input("archangel.agents> ")).strip()
        except (EOFError, KeyboardInterrupt): console.print(); break
        if not raw: continue
        if raw.lower() in ("exit", "quit", "back", "/exit", "/back"): console.print(); break
        if raw.startswith("/") and _handle_slash_intercept(raw, console, []): console.print(); break
        if raw.startswith("/"): continue
        tgt = _classify_agent_topic(raw); hist = [{"role":"system", "content":AGENT_SYSTEM_PROMPTS[tgt]}, {"role":"user", "content":raw}]
        try:
            console.print(f"[dim]Routing to {tgt}...[/dim]"); llm.switch_provider(_cli_commands._active_model_provider); resp = llm.chat(hist)
            console.print(f"\n[bold cyan]archangel.agents.{tgt}>[/]")
            for ln in resp.splitlines():
                if ln.strip(): console.print(f"  {ln}")
            console.print()
        except Exception as e: console.print(f"[red]Error from {tgt}: {e}[/]")

def _render_groupchat_header(console: Console, busy: Optional[str] = None) -> None:
    s = f"[bold green]🟢 Online: 7[/bold green]" + (f"   [bold red]⬢ Busy: {busy}[/bold red]" if busy else "")
    console.print(Panel(f"[bold cyan]👥 archangel.agents.groupchat[/] | {s}\n[dim]Collaborative Room[/]", border_style="cyan", expand=True))

def run_groupchat_repl(console: Console) -> None:
    from archangel.agents.groupchat import GroupChatEngine, AGENT_ROLES; eng = GroupChatEngine()
    console.print(); _render_groupchat_header(console); console.print()
    session = create_prompt_session("archangel.agents.groupchat> ", ".archangel_groupchat_history")
    while True:
        try: raw = (session.prompt() if session else input("archangel.agents.groupchat> ")).strip()
        except (EOFError, KeyboardInterrupt): console.print(); break
        if not raw: continue
        if raw.lower() in ("exit", "quit", "back", "/exit", "/back"): console.print(); break
        if raw.startswith("/") and _handle_slash_intercept(raw, console, getattr(eng, "history", [])): console.print(); break
        if raw.startswith("/"): continue
        if raw.lower() in ("status", "online", "busy", "list"):
            console.print("\n[bold green]🟢 Online Agents:[/bold green]")
            for n in AGENT_ROLES: console.print(f"  - [bold cyan]archangel.agents.{n}[/]")
            console.print("\n[bold red]⬢ Busy Agents:[/bold red]"); console.print(f"  - [bold red]archangel.agents.{eng.busy_agent}[/]" if eng.busy_agent else "  - [dim]None[/dim]\n"); continue
        with console.status("[bold cyan]typing...[/bold cyan]", spinner="dots"): turns = eng.process_user_goal(raw)
        console.print()
        for turn in turns:
            a = turn.get("agent", "commander"); t = turn.get("text", "")
            with console.status(f"[bold cyan]{a} typing...[/]", spinner="dots"): time.sleep(1.0)
            console.print(f"[bold cyan]archangel.agents.{a}>[/]")
            for ln in t.splitlines():
                if ln.strip(): console.print(f"  {ln}")
            console.print()

def run_agent_chat_repl(console: Console, agent_name: str) -> None:
    agt = agent_name.lower().replace("archangel.", "").replace("agents.", "")
    if agt not in AGENT_SYSTEM_PROMPTS: console.print(f"[yellow]Unknown agent: {agent_name}[/]"); return
    from dotenv import load_dotenv; load_dotenv(_get_project_root() / ".env", override=False)
    from archangel.agents.chat import LLMClient, CommandExecutor, WebSearch, EXECUTE_RE, SEARCH_RE, extract_execute_commands, extract_search_queries
    try: llm = LLMClient(); exc = CommandExecutor()
    except RuntimeError as e: console.print(f"[red]{e}[/]"); return
    sys_prompt = AGENT_SYSTEM_PROMPTS[agt] + "\n\nRUNTIME\nOS: Windows | Shell: PowerShell\nTOOLS\n1. <execute>cmd</execute>\n2. <search>q</search>\n"
    hist = [{"role": "system", "content": sys_prompt}]
    console.print("\n", Panel.fit(f"[bold cyan]🤖 archangel.agents.{agt}[/]", border_style="cyan"), "\n")
    session = create_prompt_session(f"archangel.agents.{agt}> ", f".archangel_{agt}_history")
    while True:
        try: raw = (session.prompt() if session else input(f"archangel.agents.{agt}> ")).strip()
        except (EOFError, KeyboardInterrupt): console.print(); break
        if not raw: continue
        if raw.lower() in ("exit", "quit", "back", "/exit", "/back"): console.print(); break
        if raw.startswith("/") and _handle_slash_intercept(raw, console, hist): console.print(); break
        if raw.startswith("/"): continue
        hist.append({"role": "user", "content": raw})
        iters = 0
        while True:
            try: llm.switch_provider(_cli_commands._active_model_provider); resp = llm.chat(hist)
            except Exception as e: console.print(f"[red]Error: {e}[/]"); break
            iters += 1
            if iters > 5: console.print(f"[yellow]Stopped.[/]"); break
            hist.append({"role": "assistant", "content": resp})
            disp = SEARCH_RE.sub("", EXECUTE_RE.sub("", resp))
            console.print(f"\n[bold cyan]archangel.agents.{agt}>[/]")
            for ln in disp.splitlines():
                if ln.strip(): console.print(f"  {ln}")
            console.print()
            queries = extract_search_queries(resp)
            if queries:
                for q in queries:
                    console.print(f"[bold cyan]archangel.agents.{agt}>[/] [dim]searching: {q}[/]"); out = WebSearch().search(q)
                    hist.append({"role": "user", "content": f"<search_results>\n{out}\n</search_results>"})
                continue
            cmds = extract_execute_commands(resp)
            if not cmds: break
            for cmd in cmds:
                console.print(f"[bold cyan]archangel.{agt}>[/] [dim]$ {cmd}[/]"); out = exc.execute(cmd)
                hist.append({"role": "user", "content": f"<output>\n{out}\n</output>"})

def _run_single_agent_query(console: Console, agent_name: str, query: str) -> bool:
    agt = agent_name.lower().replace("archangel.", "")
    if agt not in AGENT_SYSTEM_PROMPTS: console.print(f"[yellow]Unknown target: {agent_name}[/]"); return False
    from dotenv import load_dotenv; load_dotenv(_get_project_root() / ".env", override=False)
    from archangel.agents.chat import LLMClient
    try: llm = LLMClient()
    except RuntimeError as e: console.print(f"[red]{e}[/]"); return False
    try:
        console.print(f"[dim]Querying archangel.{agt}...[/dim]"); resp = llm.chat([{"role": "system", "content": AGENT_SYSTEM_PROMPTS[agt]}, {"role": "user", "content": query}])
        console.print(f"\n[bold cyan]archangel.{agt}>[/] {resp}\n"); return True
    except Exception as e: console.print(f"[red]Error: {e}[/]"); return False

def cmd_agent_dispatch(console: Console, agent_name: str, action: str = "status", payload: str = "") -> bool:
    agt = agent_name.lower().replace("archangel.", "")
    if action.lower() in ("chat", "interactive", "repl") or payload.lower() in ("chat", "interactive"): run_agent_chat_repl(console, agt); return True
    if payload and action not in ("scan", "collect", "status", "health"): return _run_single_agent_query(console, agt, f"{action} {payload}".strip())
    console.print(f"[bold cyan]🤖 Agent Target:[/] archangel.{agt}")
    if agt == "collector":
        from archangel.collectors import CollectorAgent; CollectorAgent(); console.print("[green]✓ Connected to archangel.collector[/]")
        from archangel.cli.handlers import cmd_scan
        if action in ("scan", "collect"): return cmd_scan(console)
        elif payload: return _run_single_agent_query(console, agt, payload)
        console.print("  [dim]Status:[/] Ready.\n  [dim]Tip:[/] Type [bold green]collector chat[/] to talk."); return True
    elif agt == "intelligence":
        from archangel.analysis import IntelligenceAgent; console.print("[green]✓ Connected to archangel.intelligence[/]")
        if payload:
            from archangel.models import RawPost; a = IntelligenceAgent().analyze(RawPost(source="cli", channel="manual", author="user", content=payload, url="local"))
            console.print(f"  [bold]Is Lead:[/] {a.is_lead}\n  [bold]Confidence:[/] {a.confidence:.2f}\n  [bold]Category:[/] {a.category}\n  [bold]Reasoning:[/] {a.reasoning}")
        else: console.print("  [dim]Status:[/] Active.\n  [dim]Tip:[/] Type [bold green]intelligence chat[/] to talk.")
        return True
    elif agt == "scoring":
        from archangel.scoring import ScoringAgent; ScoringAgent(); console.print("[green]✓ Connected to archangel.scoring[/]\n  [dim]Status:[/] Active.\n  [dim]Tip:[/] Type [bold green]scoring chat[/] to talk."); return True
    elif agt == "guardian":
        from archangel.events import EventBus, GuardianAgent; h = GuardianAgent(EventBus.get_instance()).get_system_health()
        t = Table(title="🛡 Guardian Health", border_style="cyan"); t.add_column("Component", style="cyan"); t.add_column("Status", style="bold")
        for k, v in h["components"].items(): t.add_row(k, f"[green]{v}[/]")
        console.print(t); console.print("  [dim]Tip:[/] Type [bold green]guardian chat[/] to talk."); return True
    elif agt == "commander":
        from archangel.events import CommanderAgent, EventBus; CommanderAgent(EventBus.get_instance())
        console.print("[green]✓ Connected to archangel.commander[/]\n  [dim]Status:[/] Active.\n  [dim]Tip:[/] Type [bold green]commander chat[/] to talk."); return True
    elif agt == "storage":
        from archangel.storage import StorageBackend; c = StorageBackend.get_instance().get_lead_count()
        console.print(f"[green]✓ Connected to archangel.storage[/]\n  [bold]Active Leads:[/] {c}\n  [dim]Tip:[/] Type [bold green]storage chat[/] to talk."); return True
    elif agt == "notification":
        console.print("[green]✓ Connected to archangel.notification[/]\n  [dim]Status:[/] Active.\n  [dim]Tip:[/] Type [bold green]notification chat[/] to talk."); return True
    console.print(f"[yellow]Unknown agent: archangel.{agt}[/]"); return False

def run_chat_repl(console: Console) -> None:
    from archangel.agents.chat import LLMClient, CommandExecutor, WebSearch, EXECUTE_RE, SEARCH_RE, extract_execute_commands, extract_search_queries
    if not any(k in os.environ for k in ["GROQ", "GEMINI", "OPENAI", "ANTHROPIC"]): console.print("[red]No API key configured.[/]"); return
    use_pt = False
    if sys.stdin.isatty():
        try: import msvcrt; use_pt = True # noqa
        except Exception: pass
    from archangel.cli.repl import _countdown_or_second_ctrl_c as cdown
    class _ChatCompleter:
        def get_completions(self, d, e): pass
    if use_pt: session = create_prompt_session("archangel.chat> ", ".archangel_chat_history", completer=_ChatCompleter(), complete_while_typing=True)
    try: llm = LLMClient(); exc = CommandExecutor()
    except RuntimeError as e: console.print(f"[red]{e}[/]"); return
    hist = [{"role": "system", "content": "# ARCHANGEL\nYou are casual, sharp, AI assistant.\nOS: Windows | Shell: PowerShell\nTOOLS: <execute>cmd</execute>, <search>url</search>, <automate>gui task</automate>, <screenshot></screenshot>"}]
    last_c, c_win = 0.0, 3.0
    while True:
        try: raw = (session.prompt() if use_pt else input("archangel.chat> ")).strip()
        except KeyboardInterrupt:
            if time.time() - last_c < c_win: console.print("\n[yellow]Returning...[/]"); return
            last_c = time.time(); 
            if cdown(console): console.print("\n[yellow]Returning...[/]"); return
            continue
        except EOFError: console.print("\n[yellow]Returning...[/]"); return
        if not raw: continue
        if raw.startswith("/") and _handle_slash_intercept(raw, console, hist): console.print(); return
        if raw.startswith("/"): continue
        if raw.lower() in ("exit", "quit"): console.print("[yellow]Returning...[/]"); return
        hist.append({"role": "user", "content": raw}); iters = 0
        while True:
            try: llm.switch_provider(_cli_commands._active_model_provider); resp = llm.chat(hist)
            except Exception as e: console.print(f"[red]Error: {e}[/]"); break
            iters += 1
            if iters > 5: console.print("[yellow]archangel> Stuck.[/]"); break
            hist.append({"role": "assistant", "content": resp}); disp = SEARCH_RE.sub("", EXECUTE_RE.sub("", resp))
            console.print()
            for ln in disp.splitlines():
                if ln.strip(): console.print(f"[bold]archangel>[/] {ln}")
            console.print()
            queries = extract_search_queries(resp)
            if queries:
                for q in queries: console.print(f"[bold]archangel>[/] [dim]searching: {q}[/]"); hist.append({"role": "user", "content": f"<search_results>\n{WebSearch().search(q)}\n</search_results>"})
                continue
            cmds = extract_execute_commands(resp)
            if not cmds: break
            for cmd in cmds: console.print(f"[bold]archangel>[/] [dim]$ {cmd}[/]"); hist.append({"role": "user", "content": f"<output>\n{exc.execute(cmd)}\n</output>"})
