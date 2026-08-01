"""
Chapter 7 Part 1: interactive TUI menu.
Wraps the existing agent/keys/login commands from cli.main —
no duplicated logic, just a friendlier way to trigger them.
"""
import questionary
import typer
from rich.console import Console
from rich.panel import Panel

from cli.main import (
    agent_create,
    agent_edit,
    agent_test,
    agent_publish,
    agent_rollback,
    agent_correct,
    keys_set,
    login,
)

console = Console()

MENU_OPTIONS = [
    "Create new agent",
    "Edit an agent",
    "Test an agent",
    "Publish an agent",
    "Roll back an agent",
    "Teach a correction",
    "Set BYOK key",
    "Log in / update token",
    "Exit",
]

BACK = object()  # sentinel: means "cancel this action, return to menu"


def _ask(prompt_fn, *args, **kwargs):
    """Wraps a questionary prompt: empty input, 'back', or Ctrl+C all return BACK."""
    try:
        answer = prompt_fn(*args, **kwargs).ask()
    except KeyboardInterrupt:
        return BACK
    if answer is None or answer.strip().lower() == "back" or answer.strip() == "":
        return BACK
    return answer


def _ask_business_name():
    return _ask(questionary.text, "Business name:")


def run_menu():
    console.print(Panel.fit("[bold cyan]CLI Agent Platform[/bold cyan]", border_style="cyan"))
    console.print("[dim]At any prompt: type 'back' or leave blank to return to the menu.[/dim]")

    while True:
        choice = questionary.select("What do you want to do?", choices=MENU_OPTIONS, use_shortcuts=True).ask()

        if choice is None or choice == "Exit":
            console.print("[dim]Goodbye.[/dim]")
            break

        try:
            if choice == "Create new agent":
                name = _ask_business_name()
                if name is BACK:
                    continue
                agent_create(name)

            elif choice == "Edit an agent":
                name = _ask_business_name()
                if name is BACK:
                    continue
                agent_edit(name)

            elif choice == "Test an agent":
                name = _ask_business_name()
                if name is BACK:
                    continue
                message = _ask(questionary.text, "Message to send:")
                if message is BACK:
                    continue
                agent_test(name, message)

            elif choice == "Publish an agent":
                name = _ask_business_name()
                if name is BACK:
                    continue
                agent_publish(name)

            elif choice == "Roll back an agent":
                name = _ask_business_name()
                if name is BACK:
                    continue
                agent_rollback(name)

            elif choice == "Teach a correction":
                name = _ask_business_name()
                if name is BACK:
                    continue
                correction = _ask(questionary.text, "What should the agent remember?")
                if correction is BACK:
                    continue
                agent_correct(name, correction)

            elif choice == "Set BYOK key":
                name = _ask_business_name()
                if name is BACK:
                    continue
                provider = _ask(questionary.text, "Provider (e.g. openai, groq):")
                if provider is BACK:
                    continue
                key = _ask(questionary.password, "API key:")
                if key is BACK:
                    continue
                keys_set(name, provider=provider, key=key)

            elif choice == "Log in / update token":
                token = _ask(questionary.password, "Paste your token:")
                if token is BACK:
                    continue
                login(token=token)

        except typer.Exit:
            pass
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")

        console.print()
