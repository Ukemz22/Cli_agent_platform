import typer

app = typer.Typer(help="CLI Agent Platform — developer command line")


@app.command()
def hello():
    """Sanity-check command."""
    typer.echo("platform CLI is alive")


if __name__ == "__main__":
    app()
