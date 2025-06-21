import docker
from docker.errors import APIError, DockerException
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.prompt import Confirm
import time
import os
import json

from app.translations import t

console = Console()
client = None

def get_docker_client():
    """Initializes and returns the Docker client, handling potential errors."""
    global client
    if client is None:
        try:
            client = docker.from_env()
            client.ping()
        except (DockerException, APIError):
            console.print(f"[bold red]{t('docker_error_client')}[/bold red]")
            return None
    return client

def view_container_logs(container):
    """Shows logs for a specific container."""
    os.system('cls' if os.name == 'nt' else 'clear')
    log_driver = container.attrs.get('HostConfig', {}).get('LogConfig', {}).get('Type')
    
    if log_driver not in ['json-file', 'journald']:
        console.print(t('docker_log_driver_unsupported', driver=log_driver))
        questionary.press_any_key_to_continue().ask()
        return

    try:
        console.print(Panel(t('docker_logs_title', name=container.name),
                      border_style="cyan", expand=False))
        # Stream logs
        for line in container.logs(stream=True):
            console.print(line.decode('utf-8').strip())
    except KeyboardInterrupt:
        # This allows the user to press Ctrl+C to stop watching logs and return
        pass
    finally:
        questionary.press_any_key_to_continue(t('docker_logs_press_enter')).ask()

def get_container_stats(container):
    """Helper to retrieve live stats for a container."""
    # ... (Implementation of this function can be complex, for now we will stub it)
    try:
        stats = container.stats(stream=False)
        # Parsing logic...
        return {"CPU": "1.23%", "Memory": "123.4 MiB", "PIDs": "12"}
    except (APIError, KeyError):
        return {"CPU": "N/A", "Memory": "N/A", "PIDs": "N/A"}

def container_actions(container):
    """Actions for a single container."""
    while True:
        container.reload()
        status_color = "green" if container.status == "running" else "yellow"
        action_prompt = t('docker_action_prompt', name=container.name, status=container.status, color=status_color)
        
        choices = [
            t('docker_action_logs'), t('docker_action_inspect'),
            t('docker_action_start') if container.status != "running" else None,
            t('docker_action_stop') if container.status == "running" else None,
            t('docker_action_restart') if container.status == "running" else None,
            t('docker_action_remove'), t('docker_action_back')
        ]
        
        action = questionary.select(action_prompt, choices=[c for c in choices if c]).ask()

        if action is None or action == t('docker_action_back'):
            break

        try:
            if action == t('docker_action_start'):
                container.start()
                console.print(f"[green]{t('docker_container_started', name=container.name)}[/green]")
            elif action == t('docker_action_stop'):
                container.stop()
                console.print(f"[yellow]{t('docker_container_stopped', name=container.name)}[/yellow]")
            elif action == t('docker_action_restart'):
                container.restart()
                console.print(f"[green]{t('docker_container_restarted', name=container.name)}[/green]")
            elif action == t('docker_action_logs'):
                view_container_logs(container)
            elif action == t('docker_action_inspect'):
                console.print(Panel(json.dumps(container.attrs, indent=2), title=t('docker_inspect_title', name=container.name)))
                questionary.press_any_key(t('docker_press_enter')).ask()
            elif action == t('docker_action_remove'):
                if Confirm.ask(t('docker_container_remove_confirm', name=container.name)):
                    container.remove()
                    console.print(f"[red]{t('docker_container_removed', name=container.name)}[/red]")
                    return 
        except APIError as e:
            console.print(f"[bold red]{t('docker_error_api', error=e)}[/bold red]")
            questionary.press_any_key(t('docker_press_enter')).ask()

def manage_all_containers():
    """Menu to list and manage all containers."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        try:
            containers = get_docker_client().containers.list(all=True)
            choices = {f"{c.name} ({c.short_id}) [{c.status}]": c for c in containers}
            choices[t('docker_action_back')] = None
        except Exception as e:
            console.print(f"[bold red]{t('docker_containers_error_list', error=e)}[/bold red]")
            time.sleep(3)
            return

        choice_key = questionary.select(t('docker_containers_prompt'), choices=choices.keys()).ask()
        container = choices.get(choice_key)

        if container:
            container_actions(container)
        else:
            break

def manage_images(client):
    """Placeholder for image management."""
    # TODO: Implement image management (pull, remove, list, etc.)
    console.print(t('docker_images_not_implemented'))
    questionary.press_any_key_to_continue().ask()

def manage_volumes(client):
    """Placeholder for volume management."""
    # TODO: Implement volume management

def show_docker_manager():
    """Main function for the Docker manager."""
    if not get_docker_client():
        return
        
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        console.print(Panel(f"[bold blue]{t('docker_title')}[/bold blue]"))
        
        choices = [
            # t('docker_menu_stats'), # Live stats is complex, stub for now
            t('docker_menu_manage_containers'),
            t('docker_menu_manage_images'),
            # t('docker_menu_manage_volumes'), # Stub
            # t('docker_menu_manage_networks'), # Stub
            t('docker_menu_prune'),
            t('docker_menu_back')
        ]
        choice = questionary.select(t('docker_prompt_main'), choices=choices).ask()

        if choice == t('docker_menu_back') or choice is None:
            break
        elif choice == t('docker_menu_manage_containers'):
            manage_all_containers()
        elif choice == t('docker_menu_manage_images'):
            manage_images(get_docker_client())
        elif choice == t('docker_menu_prune'):
            if Confirm.ask(t('docker_prune_confirm')):
                try:
                    pruned_info = get_docker_client().images.prune()
                    space = pruned_info.get('SpaceReclaimed', 0)
                    console.print(f"[green]{t('docker_prune_success')}[/green]")
                    if space:
                        console.print(t('docker_prune_reclaimed', space=space//1024**2))
                except APIError as e:
                    console.print(f"[bold red]{t('docker_prune_error', error=e)}[/bold red]")
                questionary.press_any_key(t('docker_press_enter')).ask() 