from __future__ import annotations

import asyncio

import typer

from kimi_cli.constant import VERSION

from .info import cli as info_cli
from .mcp import cli as mcp_cli
from .web import cli as web_cli

cli = typer.Typer(
    epilog="""\b\
Documentation:        https://moonshotai.github.io/kimi-cli/\n
LLM friendly version: https://moonshotai.github.io/kimi-cli/llms.txt""",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Kimi Web, focused on browser UI and backend.",
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"kimi, version {VERSION}")
        raise typer.Exit()


@cli.callback(invoke_without_command=True)
def kimi(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
):
    """Launch the web interface by default."""
    del version
    if ctx.invoked_subcommand is not None:
        return

    from kimi_cli.web.app import run_web_server

    run_web_server(open_browser=True)


cli.add_typer(info_cli, name="info")


@cli.command()
def login(
    json: bool = typer.Option(
        False,
        "--json",
        help="Emit OAuth events as JSON lines.",
    ),
) -> None:
    """Login to your Kimi account."""
    from rich.console import Console
    from rich.status import Status

    from kimi_cli.auth.oauth import login_kimi_code
    from kimi_cli.config import load_config

    async def _run() -> bool:
        if json:
            ok = True
            async for event in login_kimi_code(load_config()):
                typer.echo(event.json)
                if event.type == "error":
                    ok = False
            return ok

        console = Console()
        ok = True
        status: Status | None = None
        try:
            async for event in login_kimi_code(load_config()):
                if event.type == "waiting":
                    if status is None:
                        status = console.status("Waiting for user authorization...")
                        status.start()
                    continue
                if status is not None:
                    status.stop()
                    status = None
                if event.type == "error":
                    style = "red"
                elif event.type == "success":
                    style = "green"
                else:
                    style = None
                console.print(event.message, markup=False, style=style)
                if event.type == "error":
                    ok = False
        finally:
            if status is not None:
                status.stop()
        return ok

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@cli.command()
def logout(
    json: bool = typer.Option(
        False,
        "--json",
        help="Emit OAuth events as JSON lines.",
    ),
) -> None:
    """Logout from your Kimi account."""
    from rich.console import Console

    from kimi_cli.auth.oauth import logout_kimi_code
    from kimi_cli.config import load_config

    async def _run() -> bool:
        ok = True
        if json:
            async for event in logout_kimi_code(load_config()):
                typer.echo(event.json)
                if event.type == "error":
                    ok = False
            return ok

        console = Console()
        async for event in logout_kimi_code(load_config()):
            if event.type == "error":
                style = "red"
            elif event.type == "success":
                style = "green"
            else:
                style = None
            console.print(event.message, markup=False, style=style)
            if event.type == "error":
                ok = False
        return ok

    ok = asyncio.run(_run())
    if not ok:
        raise typer.Exit(code=1)


@cli.command(name="__web-worker", hidden=True)
def web_worker(session_id: str) -> None:
    """Run web worker subprocess (internal)."""
    from uuid import UUID

    from kimi_cli.app import enable_logging
    from kimi_cli.web.runner.worker import run_worker

    try:
        parsed_session_id = UUID(session_id)
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid session ID: {session_id}") from exc

    enable_logging(debug=False)
    asyncio.run(run_worker(parsed_session_id))


cli.add_typer(mcp_cli, name="mcp")
cli.add_typer(web_cli, name="web")
