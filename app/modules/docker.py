import sys
import time

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.prompt import Prompt, Confirm

try:
    import docker
    from docker.errors import DockerException
except ImportError:
    # This is a fallback for the case where the user hasn't installed requirements.
    # The main script should handle this more gracefully.
    console = Console()
    console.print("[bold red]The 'docker' library is not installed.[/bold red]")
    console.print("Please run [bold yellow]pip install -r requirements.txt[/bold yellow] to install it.")
    sys.exit(1)

console = Console()
client = docker.from_env()

def get_docker_client():
    """Establishes connection with the Docker daemon."""
    try:
        client = docker.from_env(timeout=5)
        client.ping()
        return client
    except DockerException:
        return None

def show_container_logs(container):
    """Shows live logs for a specific container."""
    console.print(Panel(f"Logs for [cyan]{container.name}[/cyan]. Press Ctrl+C to return.", title="Log Viewer"))
    try:
        # Check container's logging driver
        log_driver = container.attrs.get('HostConfig', {}).get('LogConfig', {}).get('Type')
        if log_driver not in ['json-file', 'journald']:
            console.print(f"[bold yellow]Warning:[/bold yellow] The container [cyan]{container.name}[/cyan] uses the '{log_driver}' logging driver.")
            console.print("This driver might not support reading logs via the Docker API.")
            console.print("If logs don't appear, check the driver's configuration (e.g., syslog, fluentd).")

        log_stream = container.logs(stream=True, tail=100, follow=True)
        for line in log_stream:
            console.print(line.decode('utf-8', errors='replace').strip())

    except docker.errors.APIError as e:
        if "configured logging driver does not support reading" in str(e):
            console.print(f"\n[bold red]Error:[/bold red] The logging driver for this container does not support reading logs.")
            console.print("You will need to check the logs via the configured logging system (e.g., syslog, journalctl, etc.).")
        else:
            console.print(f"\n[bold red]An API error occurred: {e}[/bold red]")
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Returning to Docker menu...[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]An unexpected error occurred: {e}[/bold red]")
    finally:
        console.print("\n[cyan]Press Enter to return to the menu.[/cyan]")
        input()


def get_container_stats(container):
    """Retrieves and displays statistics for a container."""
    try:
        stats = client.api.stats(container.id, stream=False)
        mem_usage = stats['memory_stats']['usage'] / 1024 / 1024
        mem_limit = stats['memory_stats'].get('limit', 0) / 1024 / 1024
        mem_percent = (mem_usage / mem_limit * 100) if mem_limit > 0 else 0
        return {
            "CPU": f"{stats['cpu_stats']['cpu_usage']['total_usage']}ms",
            "Memory": f"{mem_usage:.2f}MiB / {mem_limit:.2f}MiB ({mem_percent:.2f}%)",
            "PIDs": stats['pids_stats'].get('current', 'N/A')
        }
    except (docker.errors.APIError, KeyError):
        return {"CPU": "N/A", "Memory": "N/A", "PIDs": "N/A"}


def perform_container_action(action, container):
    """Executes a given action (start, stop, restart) on a container."""
    try:
        console.print(f"Executing '{action}' on container [cyan]{container.name}[/cyan]...")
        if action == 'start':
            container.start()
        elif action == 'stop':
            container.stop()
        elif action == 'restart':
            container.restart()
        console.print(f"[bold green]Action '{action}' completed successfully![/bold green]")
        time.sleep(2)
    except docker.errors.APIError as e:
        console.print(f"[bold red]Error: {e.explanation}[/bold red]")
        time.sleep(3)
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
        time.sleep(3)


def show_docker_manager():
    """Main function for the Docker Container Manager."""
    client = get_docker_client()

    if not client:
        console.print(Panel("[bold red]Docker daemon is not running or accessible.[/bold red]\nPlease ensure Docker is installed, running, and that you have the correct permissions.", title="Error", border_style="red"))
        questionary.press_any_key_to_continue("Press any key to return...").ask()
        return

    while True:
        console.clear()
        try:
            containers = client.containers.list(all=True)
        except Exception as e:
            console.print(f"[bold red]Failed to list containers: {e}[/bold red]")
            time.sleep(3)
            return

        table = Table(title="Docker Containers", border_style="blue")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("ID", style="magenta")
        table.add_column("Status", style="yellow")
        table.add_column("Image", style="green")
        table.add_column("Ports", style="blue")

        if not containers:
            console.print(Panel("No Docker containers found.", title="Info"))
        else:
            for c in containers:
                status = c.status.capitalize()
                color = "green" if status == "Running" else "red"
                
                # Safely get ports
                try:
                    ports_dict = c.attrs['NetworkSettings']['Ports']
                    ports_list = []
                    if ports_dict:
                        for container_port, host_bindings in ports_dict.items():
                            if host_bindings:
                                for binding in host_bindings:
                                    host_ip = binding.get('HostIp', '0.0.0.0')
                                    host_port = binding.get('HostPort', '')
                                    ports_list.append(f"{host_ip}:{host_port}->{container_port}")
                    ports_str = "\n".join(ports_list)
                except (KeyError, TypeError):
                    ports_str = "N/A"

                table.add_row(
                    c.name,
                    c.short_id,
                    f"[{color}]{status}[/{color}]",
                    c.image.tags[0] if c.image.tags else 'N/A',
                    ports_str
                )
            console.print(table)

        choices = {f"{c.name} ({c.short_id})": c for c in containers}
        
        selected_choice = questionary.select(
            "What would you like to do?",
            choices=choices.keys() + [questionary.Separator(), "Back to Main Menu"],
            pointer="👉"
        ).ask()

        if selected_choice is None or selected_choice == "Back to Main Menu":
            break
        elif selected_choice == "Live Container Stats":
            show_live_stats()
        elif selected_choice == "Manage All Containers":
            manage_all_containers()
        elif selected_choice == "Manage Images":
            manage_images()
        elif selected_choice == "Manage Volumes":
            manage_volumes()
        elif selected_choice == "Manage Networks":
            manage_networks()
        elif selected_choice == "Prune System":
            if Confirm.ask("[bold yellow]This will remove all unused containers, networks, images (both dangling and unreferenced), and build cache. Are you sure?"):
                try:
                    pruned_info = client.images.prune()
                    space_reclaimed = pruned_info.get('SpaceReclaimed', 0)
                    pruned_containers = client.containers.prune()
                    pruned_volumes = client.volumes.prune()
                    pruned_networks = client.networks.prune()
                    console.print(f"[green]Docker system pruned successfully.[/green]")
                    if space_reclaimed:
                        console.print(f"Space reclaimed from images: {space_reclaimed // 1024 // 1024} MB")
                except docker.errors.APIError as e:
                    console.print(f"[bold red]Error pruning system: {e}[/bold red]")
                console.print("\n[cyan]Press Enter to return.[/cyan]")
                input()


def manage_all_containers():
    """Interactive menu to manage a specific container."""
    while True:
        try:
            containers = client.containers.list(all=True)
        except Exception as e:
            console.print(f"[bold red]Failed to list containers: {e}[/bold red]")
            time.sleep(3)
            return

        container_choices = {f"{c.name} ({c.short_id})": c for c in containers}

        choice = questionary.select(
            "Select a container to manage:",
            choices=container_choices.keys() + [questionary.Separator(), "Back"],
            pointer="👉"
        ).ask()

        if choice is None or choice == "Back":
            return

        container_id = choice.split('(')[-1].strip(')')
        container = client.containers.get(container_id)

        container_actions(container)

def container_actions(container):
    """Actions for a single container."""
    while True:
        status_color = "green" if container.status == "running" else "yellow"
        action_prompt = (
            f"Action for [cyan]{container.name}[/cyan] "
            f"([bold {status_color}]{container.status}[/bold {status_color}])"
        )
        action = questionary.select(
            action_prompt,
            choices=[
                "View Logs",
                "Inspect",
                "Start",
                "Stop",
                "Restart",
                "Remove",
                "Back"
            ],
            pointer="👉"
        ).ask()

        if action is None or action == "Back":
            break

        try:
            if action == "View Logs":
                show_container_logs(container)
                # After logs, we need to re-fetch container status
                container.reload()
            elif action == "Inspect":
                import json
                console.clear()
                console.print(Panel(f"Details for [cyan]{container.name}[/cyan]", border_style="green"))
                console.print_json(json.dumps(container.attrs, indent=2))
                questionary.press_any_key_to_continue().ask()
            elif action == "Start":
                container.start()
                console.print(f"[green]Container {container.name} started.[/green]")
            elif action == "Stop":
                container.stop()
                console.print(f"[yellow]Container {container.name} stopped.[/yellow]")
            elif action == "Restart":
                container.restart()
                console.print(f"[green]Container {container.name} restarted.[/green]")
            elif action == "Remove":
                if Confirm.ask(f"[bold red]Are you sure you want to remove container {container.name}?"):
                    container.remove()
                    console.print(f"[red]Container {container.name} removed.[/red]")
                    return # Exit as container is gone
        except docker.errors.APIError as e:
            console.print(f"[bold red]Error: {e}[/bold red]")
        
        # Reload container state for next loop iteration
        container.reload()
        console.print("\n[cyan]Press Enter to continue.[/cyan]")
        input()
        
def show_live_stats():
    """Display a live-updating table of container stats."""
    console.clear()
    console.print(Panel("Live Container Stats", border_style="blue", title_align="left"))
    try:
        with Live(console=console, screen=False, auto_refresh=True) as live:
            while True:
                containers = client.containers.list(all=True)
                table = Table(title="Container Stats", border_style="blue")
                table.add_column("Name", style="cyan", no_wrap=True)
                table.add_column("ID", style="magenta")
                table.add_column("Status", style="yellow")
                table.add_column("CPU", style="green")
                table.add_column("Memory", style="blue")
                table.add_column("PIDs", style="magenta")

                for c in containers:
                    stats = get_container_stats(c)
                    status_color = "green" if c.status == "running" else "yellow"
                    table.add_row(
                        c.name,
                        c.short_id,
                        f"[{status_color}]{c.status}[/{status_color}]",
                        stats["CPU"],
                        stats["Memory"],
                        stats["PIDs"]
                    )
                live.update(table)
                time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Returning to Docker menu...[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]An unexpected error occurred: {e}[/bold red]")
    finally:
        console.print("\n[cyan]Press Enter to return to the menu.[/cyan]")
        input() 