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


if __name__ == "__main__":
    app()
