"""Entry point for benz_sent_filter service."""

import os

import typer

app = typer.Typer()


@app.command()
def main(
    port: int = typer.Option(8002, help="Port to run the server on"),
    host: str = typer.Option("0.0.0.0", help="Host to bind the server to"),
    reload: bool = typer.Option(False, help="Enable auto-reload for development"),
    workers: int = typer.Option(
        None,
        help="Number of worker processes (default: CPU count, incompatible with --reload)",
    ),
):
    """Start the Benz Sent Filter API server."""
    import uvicorn

    # Determine worker count
    if reload:
        # Reload mode requires single worker
        actual_workers = 1
        if workers is not None and workers > 1:
            typer.echo(
                "Warning: --reload is incompatible with multiple workers, using 1 worker"
            )
    else:
        # Use specified workers or default to CPU count
        actual_workers = workers if workers is not None else os.cpu_count()

    typer.echo(
        f"Starting Benz Sent Filter on {host}:{port} with {actual_workers} worker(s)"
    )

    uvicorn.run(
        "benz_sent_filter.api.app:app",
        host=host,
        port=port,
        reload=reload,
        workers=actual_workers,
    )


if __name__ == "__main__":
    app()
