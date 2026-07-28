import os
from pathlib import Path

import typer

app = typer.Typer(help="CLI Agent Platform — developer command line")

CREDENTIALS_PATH = Path.home() / ".platform" / "credentials"


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


if __name__ == "__main__":
    app()
