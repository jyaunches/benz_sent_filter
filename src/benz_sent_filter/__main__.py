"""Entry point for benz_sent_filter service."""

import typer

app = typer.Typer()


@app.command()
def main(
    port: int = typer.Option(8002, help="Port to run the server on"),
    host: str = typer.Option("0.0.0.0", help="Host to bind the server to"),
    reload: bool = typer.Option(False, help="Enable auto-reload for development"),
):
    """Start the Benz Sent Filter API server."""
    import uvicorn

    typer.echo(f"Starting Benz Sent Filter on {host}:{port}")

    uvicorn.run(
        "benz_sent_filter.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
