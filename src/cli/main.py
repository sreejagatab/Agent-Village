"""
CLI interface for Agent Village.

Provides commands for:
- Running goals
- Monitoring agents
- Querying memory
- System management
"""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config import get_settings

# Create Typer app
app = typer.Typer(
    name="village",
    help="Agent Village - Multi-agent orchestration system",
    add_completion=False,
)

console = Console()

# Sub-command groups
goal_app = typer.Typer(help="Goal management commands")
agent_app = typer.Typer(help="Agent management commands")
memory_app = typer.Typer(help="Memory query commands")
config_app = typer.Typer(help="Configuration commands")

app.add_typer(goal_app, name="goal")
app.add_typer(agent_app, name="agent")
app.add_typer(memory_app, name="memory")
app.add_typer(config_app, name="config")


# Helper functions
def run_async(coro):
    """Run an async coroutine."""
    return asyncio.get_event_loop().run_until_complete(coro)


async def get_client():
    """Get HTTP client for API calls."""
    import httpx

    settings = get_settings()
    base_url = f"http://{settings.api.host}:{settings.api.port}"
    return httpx.AsyncClient(base_url=base_url, timeout=300.0)


# Main commands
@app.command()
def status():
    """Show system status."""
    async def _status():
        try:
            async with await get_client() as client:
                response = await client.get("/health")
                data = response.json()

                table = Table(title="Agent Village Status")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="green")

                table.add_row("Status", data.get("status", "unknown"))
                table.add_row("Version", data.get("version", "unknown"))
                table.add_row("Active Agents", str(data.get("agents_active", 0)))
                table.add_row(
                    "Providers",
                    ", ".join(data.get("providers_available", [])) or "none",
                )

                console.print(table)

        except Exception as e:
            console.print(f"[red]Error connecting to API: {e}[/red]")
            console.print("Is the API server running? Start it with: python -m src.api.main")

    run_async(_status())


@app.command()
def version():
    """Show version information."""
    from src import __version__

    console.print(Panel(
        f"[bold blue]Agent Village[/bold blue] v{__version__}\n\n"
        "Production-grade multi-agent orchestration system",
        title="Version",
    ))


# Goal commands
@goal_app.command("run")
def goal_run(
    description: str = typer.Argument(..., help="Goal description"),
    sync: bool = typer.Option(False, "--sync", "-s", help="Wait for completion"),
    priority: int = typer.Option(2, "--priority", "-p", help="Priority (1-5)"),
):
    """Run a new goal."""
    async def _run():
        console.print(f"[bold]Creating goal:[/bold] {description}")

        try:
            async with await get_client() as client:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Executing goal...", total=None)

                    response = await client.post(
                        "/goals",
                        json={
                            "description": description,
                            "priority": priority,
                            "context": {},
                        },
                    )

                    progress.remove_task(task)

                if response.status_code == 200:
                    data = response.json()

                    console.print(Panel(
                        f"[green]Goal completed![/green]\n\n"
                        f"ID: {data.get('id')}\n"
                        f"Status: {data.get('status')}\n\n"
                        f"Result:\n{data.get('result')}",
                        title="Goal Result",
                    ))
                else:
                    console.print(f"[red]Error: {response.text}[/red]")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    run_async(_run())


@goal_app.command("status")
def goal_status(goal_id: str = typer.Argument(..., help="Goal ID")):
    """Check goal status."""
    async def _status():
        try:
            async with await get_client() as client:
                response = await client.get(f"/goals/{goal_id}")
                if response.status_code == 200:
                    data = response.json()
                    console.print(Panel(
                        f"ID: {data.get('id')}\n"
                        f"Status: {data.get('status')}\n"
                        f"Description: {data.get('description')}",
                        title="Goal Status",
                    ))
                else:
                    console.print(f"[red]Error: {response.text}[/red]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    run_async(_status())


@goal_app.command("cancel")
def goal_cancel(goal_id: str = typer.Argument(..., help="Goal ID to cancel")):
    """Cancel a running goal."""
    async def _cancel():
        try:
            async with await get_client() as client:
                response = await client.delete(f"/goals/{goal_id}")
                if response.status_code == 200:
                    console.print(f"[green]Goal {goal_id} cancelled[/green]")
                else:
                    console.print(f"[red]Error: {response.text}[/red]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    run_async(_cancel())


@goal_app.command("approve")
def goal_approve(goal_id: str = typer.Argument(..., help="Goal ID to approve")):
    """Approve a goal awaiting human approval."""
    async def _approve():
        try:
            async with await get_client() as client:
                response = await client.post(f"/goals/{goal_id}/approve")
                if response.status_code == 200:
                    console.print(f"[green]Goal {goal_id} approved[/green]")
                else:
                    console.print(f"[red]Error: {response.text}[/red]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    run_async(_approve())


# Agent commands
@agent_app.command("list")
def agent_list():
    """List all active agents."""
    async def _list():
        try:
            async with await get_client() as client:
                response = await client.get("/agents")
                agents = response.json()

                if not agents:
                    console.print("[yellow]No active agents[/yellow]")
                    return

                table = Table(title="Active Agents")
                table.add_column("ID", style="cyan", max_width=12)
                table.add_column("Type", style="blue")
                table.add_column("Name", style="green")
                table.add_column("State", style="yellow")
                table.add_column("Model", style="magenta")

                for agent in agents:
                    table.add_row(
                        agent["id"][:12],
                        agent["type"],
                        agent["name"],
                        agent["state"],
                        agent.get("model", "unknown"),
                    )

                console.print(table)

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    run_async(_list())


@agent_app.command("watch")
def agent_watch():
    """Watch agents in real-time."""
    console.print("[yellow]Real-time agent watching not implemented yet[/yellow]")
    console.print("Use 'village agent list' to see current agents")


@agent_app.command("logs")
def agent_logs(agent_id: str = typer.Argument(..., help="Agent ID")):
    """Show agent logs."""
    console.print(f"[yellow]Agent logs for {agent_id} not implemented yet[/yellow]")


# Memory commands
@memory_app.command("search")
def memory_search(
    query: str = typer.Argument(..., help="Search query"),
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Memory type filter"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results"),
):
    """Search memory."""
    async def _search():
        try:
            async with await get_client() as client:
                params = {"query": query, "limit": limit}
                if type:
                    params["memory_type"] = type

                response = await client.get("/memory/search", params=params)
                data = response.json()

                results = data.get("results", [])
                if not results:
                    console.print("[yellow]No results found[/yellow]")
                    return

                for result in results:
                    console.print(Panel(
                        f"Type: {result.get('type')}\n"
                        f"Content: {result.get('content')}",
                        title=f"Memory {result.get('id', 'unknown')[:8]}",
                    ))

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    run_async(_search())


@memory_app.command("show")
def memory_show(memory_id: str = typer.Argument(..., help="Memory ID")):
    """Show memory details."""
    console.print(f"[yellow]Memory show for {memory_id} not implemented yet[/yellow]")


# Config commands
@config_app.command("show")
def config_show():
    """Show current configuration."""
    settings = get_settings()

    table = Table(title="Current Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Environment", settings.environment)
    table.add_row("Debug", str(settings.debug))
    table.add_row("Log Level", settings.log_level)
    table.add_row("Default Provider", settings.llm.default_provider)
    table.add_row("API Host", f"{settings.api.host}:{settings.api.port}")
    table.add_row("Max Recursion", str(settings.safety.max_recursion_depth))
    table.add_row("Max Agents", str(settings.safety.max_agent_spawns))

    console.print(table)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key (e.g., provider.default)"),
    value: str = typer.Argument(..., help="New value"),
):
    """Set a configuration value."""
    console.print(f"[yellow]Config set not implemented yet[/yellow]")
    console.print("Edit .env file directly or set environment variables")


# Entry point
def main():
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
