import os
from pathlib import Path

import httpx
import typer

app = typer.Typer(help="CLI Agent Platform — developer command line")

CREDENTIALS_PATH = Path.home() / ".platform" / "credentials"
API_BASE_URL = os.environ.get("PLATFORM_API_URL", "http://localhost:8000")
BUSINESS_ROOT = Path("businesses")


@app.command()
def hello():
    """Sanity-check command."""
    typer.echo("platform CLI is alive")


@app.command()
def login(token: str = typer.Option(..., "--token", help="Long-lived developer token issued by admin")):
    """Save a developer token locally for CLI use."""
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_PATH.write_text(token.strip() + "\n")
    os.chmod(CREDENTIALS_PATH, 0o600)
    typer.echo(f"Token saved to {CREDENTIALS_PATH}")


def load_token() -> str:
    """Used by every other CLI command to read the saved token."""
    if not CREDENTIALS_PATH.exists():
        typer.echo("Not logged in. Run: platform login --token <your-token>")
        raise typer.Exit(code=1)
    return CREDENTIALS_PATH.read_text().strip()


def api_headers() -> dict:
    return {"Authorization": f"Bearer {load_token()}"}


agent_app = typer.Typer(help="Manage a business's AI agent")
app.add_typer(agent_app, name="agent")


@agent_app.command("create")
def agent_create(business_name: str):
    """Create a new business: scaffolds local folder + creates it via the API."""
    resp = httpx.post(
        f"{API_BASE_URL}/businesses",
        json={"name": business_name},
        headers=api_headers(),
    )
    if resp.status_code != 200:
        typer.echo(f"API error: {resp.status_code} {resp.text}")
        raise typer.Exit(code=1)

    business = resp.json()

    business_dir = BUSINESS_ROOT / business_name
    (business_dir / "knowledge").mkdir(parents=True, exist_ok=True)
    (business_dir / "tools").mkdir(parents=True, exist_ok=True)
    (business_dir / "memory").mkdir(parents=True, exist_ok=True)
    (business_dir / "skills").mkdir(parents=True, exist_ok=True)

    (business_dir / "prompt.md").write_text("You are a helpful assistant.\n")
    (business_dir / "config.yml").write_text(
        f"business_id: {business['id']}\nname: {business_name}\nstatus: draft\n"
    )
    (business_dir / "memory" / "corrections.md").write_text("")

    typer.echo(f"Created business '{business_name}' (id: {business['id']})")
    typer.echo(f"Local folder: {business_dir}/")


@agent_app.command("edit")
def agent_edit(business_name: str):
    """Open the business's prompt.md — tries $EDITOR, falls back to a file-path hint (mobile/Replit friendly)."""
    business_dir = BUSINESS_ROOT / business_name
    prompt_path = business_dir / "prompt.md"

    if not prompt_path.exists():
        typer.echo(f"No such business locally: {prompt_path}")
        typer.echo("Run 'platform agent create' first, or check you're in the right folder.")
        raise typer.Exit(code=1)

    editor = os.environ.get("EDITOR")
    if editor and os.system(f'which {editor} > /dev/null 2>&1') == 0:
        os.system(f'{editor} "{prompt_path}"')
        typer.echo(f"Saved. Run 'platform agent test {business_name}' to try it, or 'publish' to go live.")
    else:
        typer.echo("No terminal editor found. Open this file in Replit's Files tab instead:")
        typer.echo(f"  {prompt_path}")
        typer.echo(f"After saving, run 'platform agent test {business_name}' to try it.")


@agent_app.command("test")
def agent_test(business_name: str, message: str = typer.Argument(..., help="Message to send to the agent")):
    """Test the agent locally using draft files (prompt.md + knowledge/*.md) — no publish needed."""
    business_dir = BUSINESS_ROOT / business_name
    prompt_path = business_dir / "prompt.md"

    if not prompt_path.exists():
        typer.echo(f"No such business locally: {prompt_path}")
        raise typer.Exit(code=1)

    system_prompt = prompt_path.read_text().strip()

    knowledge_dir = business_dir / "knowledge"
    knowledge_snippets = []
    if knowledge_dir.exists():
        for f in knowledge_dir.glob("*.md"):
            file_content = f.read_text().strip()
            if any(w in file_content.lower() for w in message.lower().split()):
                knowledge_snippets.append(file_content)

    typer.echo("[NOTE: using a fake/mock LLM response — no real LLM key wired yet]")
    typer.echo(f"System prompt used: {system_prompt}")
    if knowledge_snippets:
        typer.echo(f"Knowledge matched: {knowledge_snippets}")
    else:
        typer.echo("Knowledge matched: (none)")

    fake_reply = f"[draft-mode fake reply] I received: '{message}'"
    typer.echo("")
    typer.echo(f"Agent: {fake_reply}")


if __name__ == "__main__":
    app()
