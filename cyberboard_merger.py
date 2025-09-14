#!/usr/bin/env python3
"""
CYBERBOARD R4 Configuration Merger Tool
Merge custom LED configurations from multiple JSON files
"""

import json
import os
import sys
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Union
import copy
import toml

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED
from rich.prompt import Prompt, Confirm
from rich.columns import Columns
import questionary
from questionary import Style

console = Console()

custom_style = Style([
    ('question', 'fg:#00ffff bold'),
    ('answer', 'fg:#44ff00 bold'),
    ('pointer', 'fg:#ff00ff bold'),
    ('highlighted', 'fg:#ff00ff bold'),
    ('selected', 'fg:#44ff00'),
    ('separator', 'fg:#888888'),
    ('instruction', 'fg:#888888'),
])

class LEDPreviewAnimator:
    """Handles LED animation preview in terminal"""
    
    def __init__(self, width=40, height=5):
        self.width = width
        self.height = height
        self.frames = []
        self.current_frame = 0
        self.running = False
        self.thread = None
        
    def load_frames(self, page_data: Dict):
        """Load frames from page data"""
        self.frames = []
        if not page_data:
            return
            
        frames_data = page_data.get('frames', {})
        if frames_data.get('valid', 0) == 0:
            frames_data = page_data.get('keyframes', {})
            
        frame_list = frames_data.get('frame_data', [])
        
        for frame in frame_list:
            rgb_values = frame.get('frame_RGB', [])
            if rgb_values and len(rgb_values) == self.width * self.height:
                self.frames.append(rgb_values)
                
    def get_frame_display(self, frame_index: Optional[int] = None) -> str:
        """Generate terminal display for a single frame"""
        if not self.frames:
            return self._generate_empty_display()
            
        if frame_index is None:
            frame_index = self.current_frame % len(self.frames)
            
        frame = self.frames[frame_index]
        display = []
        
        for y in range(self.height):
            row = []
            for x in range(self.width):
                idx = y * self.width + x
                if idx < len(frame):
                    color = frame[idx]
                    if color.startswith('#'):
                        r = int(color[1:3], 16)
                        g = int(color[3:5], 16)
                        b = int(color[5:7], 16)
                        row.append(f"[rgb({r},{g},{b})]█[/]")
                    else:
                        row.append("█")
                else:
                    row.append(" ")
            display.append("".join(row))
            
        return "\n".join(display)
        
    def _generate_empty_display(self) -> str:
        """Generate empty display grid"""
        return "\n".join(["░" * self.width for _ in range(self.height)])
        
    def start_animation(self, callback=None):
        """Start animation in background thread"""
        self.running = True
        self.current_frame = 0
        
        def animate():
            while self.running:
                if callback:
                    callback(self.get_frame_display())
                self.current_frame = (self.current_frame + 1) % max(len(self.frames), 1)
                time.sleep(0.2)
                
        self.thread = threading.Thread(target=animate, daemon=True)
        self.thread.start()
        
    def stop_animation(self):
        """Stop animation"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.5)

class CyberboardMerger:
    """Main application class"""
    
    def __init__(self):
        self.base_file = None
        self.base_data = None
        self.mappings = {}
        self.output_file = None
        self.config = self.load_config()
        self.source_dir = self.config.get('directories', {}).get('source', '.')
        self.output_dir = self.config.get('directories', {}).get('output', '.')
        self.ensure_directories()
        
    def load_config(self) -> Dict:
        """Load configuration from config.toml"""
        config_path = Path('config.toml')
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return toml.load(f)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load config.toml: {e}[/]")
                console.print(f"[yellow]Using default settings[/]")
        
        # Default configuration
        return {
            'directories': {
                'source': '.',
                'output': '.'
            }
        }
        
    def ensure_directories(self):
        """Ensure source and output directories exist"""
        created_dirs = []
        
        # Check and create source directory
        if not os.path.exists(self.source_dir):
            try:
                os.makedirs(self.source_dir, exist_ok=True)
                created_dirs.append(self.source_dir)
            except Exception as e:
                console.print(f"[red]Error creating source directory '{self.source_dir}': {e}[/]")
                
        # Check and create output directory (only if different from source)
        if self.output_dir != self.source_dir and not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir, exist_ok=True)
                created_dirs.append(self.output_dir)
            except Exception as e:
                console.print(f"[red]Error creating output directory '{self.output_dir}': {e}[/]")
        
        # Notify user of created directories
        if created_dirs:
            dirs_str = ", ".join(f"'{d}'" for d in created_dirs)
            console.print(f"[green]✓[/] Created directories: {dirs_str}")
            if self.source_dir in created_dirs:
                console.print(f"[dim]Add CYBERBOARD R4 JSON files to '{self.source_dir}' to get started.[/]")
        
    def enter_alternate_screen(self):
        """Enter alternate screen buffer"""
        sys.stdout.write("\033[?1049h")  # Enable alternate screen buffer
        sys.stdout.write("\033[H")       # Move cursor to home position
        sys.stdout.flush()
        console.clear()
        
    def exit_alternate_screen(self):
        """Exit alternate screen buffer"""
        sys.stdout.write("\033[?1049l")  # Disable alternate screen buffer
        sys.stdout.flush()
        
    def display_header(self):
        """Display application header"""
        header = Panel(
            Align.center(
                Text("CYBERBOARD R4 Configuration Merger Tool", style="bold cyan"),
                vertical="middle"
            ),
            box=ROUNDED,
            border_style="bright_blue",
            padding=(1, 2)
        )
        console.print(header)
        console.print()
        
    def get_json_files(self) -> List[str]:
        """Get list of JSON files in source directory"""
        try:
            return [f for f in os.listdir(self.source_dir) if f.endswith('.json')]
        except FileNotFoundError:
            console.print(f"[red]Error: Source directory '{self.source_dir}' not found![/]")
            return []
        
    def select_base_file(self) -> Optional[str]:
        """Select base configuration file"""
        while True:
            files = self.get_json_files()
            if not files:
                console.print(f"[yellow]No JSON files found in source directory: '{self.source_dir}'[/]")
                console.print(f"[dim]Please add CYBERBOARD R4 JSON configuration files to '{self.source_dir}' and try again.[/]")
                
                choice = questionary.select(
                    "What would you like to do?",
                    choices=[
                        "1. Retry after adding JSON files",
                        "2. Reload config.toml and retry",
                        "3. Exit application"
                    ],
                    style=custom_style,
                    use_shortcuts=True
                ).ask()
                
                if choice and "Retry after adding" in choice:
                    # Check for files again
                    console.print("[cyan]Checking for JSON files...[/]")
                    continue
                elif choice and "Reload config" in choice:
                    # Reload configuration
                    console.print("[cyan]Reloading configuration...[/]")
                    self.config = self.load_config()
                    self.source_dir = self.config.get('directories', {}).get('source', '.')
                    self.output_dir = self.config.get('directories', {}).get('output', '.')
                    self.ensure_directories()
                    continue
                else:
                    return None
            else:
                break
            
        console.print(Panel("[bold cyan]Step 1: Select Base Configuration File[/]", expand=False))
        
        # Add number prefixes for keyboard shortcuts
        numbered_choices = [f"{i+1}. {file}" for i, file in enumerate(files)]
        
        choice = questionary.select(
            "Choose base file (use arrows or number keys):",
            choices=numbered_choices + ["← Back to Main Menu"],
            style=custom_style,
            use_shortcuts=True
        ).ask()
        
        if choice == "← Back to Main Menu" or choice is None:
            return None
            
        # Extract filename from numbered choice
        if choice:
            file_name = choice.split('. ', 1)[1] if '. ' in choice else choice
            self.base_file = file_name
            full_path = os.path.join(self.source_dir, file_name)
            with open(full_path, 'r', encoding='utf-8') as f:
                self.base_data = json.load(f)
                
            console.print(f"\n[green]✓[/] Base file selected: [bold]{file_name}[/]")
            self.preview_base_leds_animated()
            return file_name
            
        return None
        
    def preview_base_leds(self):
        """Preview base file's custom LED configurations"""
        console.print("\n[bold]Current Custom LED Configurations:[/]\n")
        
        for i in range(3):
            page_idx = 5 + i
            page_data = self.base_data['page_data'][page_idx]
            
            animator = LEDPreviewAnimator()
            animator.load_frames(page_data)
            
            panel = Panel(
                animator.get_frame_display(0),
                title=f"[bold]Custom LED {i+1} (Page {page_idx})[/]",
                border_style="blue"
            )
            console.print(panel)
            
    def preview_base_leds_animated(self):
        """Preview base file's custom LED configurations with animation"""
        console.print("\n[bold]Current Custom LED Configurations (3 seconds):[/]\n")
        
        animators = []
        max_frames = 0
        for i in range(3):
            page_idx = 5 + i
            page_data = self.base_data['page_data'][page_idx]
            
            animator = LEDPreviewAnimator()
            animator.load_frames(page_data)
            animators.append(animator)
            max_frames = max(max_frames, len(animator.frames))
        
        # Calculate frame delay to fit animation in 3 seconds
        if max_frames > 0:
            frame_delay = 3.0 / max_frames
        else:
            frame_delay = 0.2
        
        # Show animated preview for 3 seconds
        with Live(refresh_per_second=10, console=console) as live:
            start_time = time.time()
            while time.time() - start_time < 3:
                previews = []
                for i, animator in enumerate(animators):
                    panel = Panel(
                        animator.get_frame_display(),
                        title=f"[bold]Custom LED {i+1}[/]",
                        border_style="blue"
                    )
                    previews.append(panel)
                    animator.current_frame = (animator.current_frame + 1) % max(len(animator.frames), 1)
                
                columns = Columns(previews, equal=True, expand=True)
                live.update(columns)
                time.sleep(frame_delay)
    
            
    def configure_led_mapping(self, led_num: int) -> Dict:
        """Configure mapping for a single LED"""
        console.print(f"\n[bold cyan]Configure Custom LED {led_num}[/]")
        
        page_idx = 4 + led_num
        current_page = self.base_data['page_data'][page_idx]
        
        animator = LEDPreviewAnimator()
        animator.load_frames(current_page)
        
        # Calculate frame delay for 3 seconds animation
        if len(animator.frames) > 0:
            frame_delay = 3.0 / len(animator.frames)
        else:
            frame_delay = 0.2
        
        # Show animated preview of current base LED
        console.print(f"\n[bold]Current Base LED {led_num} (3 seconds):[/]")
        with Live(refresh_per_second=10, console=console) as live:
            start_time = time.time()
            while time.time() - start_time < 3:
                panel = Panel(
                    animator.get_frame_display(),
                    title=f"[bold]Current Base LED {led_num}[/]",
                    border_style="green"
                )
                live.update(panel)
                animator.current_frame = (animator.current_frame + 1) % max(len(animator.frames), 1)
                time.sleep(frame_delay)
        
        action = questionary.select(
            f"Action for Custom LED {led_num}:",
            choices=["1. Keep Base", "2. Replace", "← Back"],
            style=custom_style,
            use_shortcuts=True
        ).ask()
        
        if action == "← Back" or action is None:
            return {"action": "back"}
        elif "Keep Base" in action:
            return {"action": "keep"}
        elif "Replace" in action:
            files = self.get_json_files()
            numbered_files = [f"{i+1}. {file}" for i, file in enumerate(files)]
            
            source_choice = questionary.select(
                "Select source file:",
                choices=numbered_files + ["← Back"],
                style=custom_style,
                use_shortcuts=True
            ).ask()
            
            if source_choice == "← Back" or source_choice is None:
                return self.configure_led_mapping(led_num)  # Retry this LED config
            
            source_file = source_choice.split('. ', 1)[1] if '. ' in source_choice else source_choice
            
            if source_file:
                full_path = os.path.join(self.source_dir, source_file)
                with open(full_path, 'r', encoding='utf-8') as f:
                    source_data = json.load(f)
                    
                console.print(f"\n[bold]Preview LED configurations from {source_file} (3 seconds):[/]\n")
                
                # Animate source LEDs
                animators = []
                max_frames = 0
                for i in range(3):
                    source_page = source_data['page_data'][5 + i]
                    animator = LEDPreviewAnimator()
                    animator.load_frames(source_page)
                    animators.append(animator)
                    max_frames = max(max_frames, len(animator.frames))
                
                # Calculate frame delay to fit animation in 3 seconds
                if max_frames > 0:
                    frame_delay = 3.0 / max_frames
                else:
                    frame_delay = 0.2
                
                with Live(refresh_per_second=10, console=console) as live:
                    start_time = time.time()
                    while time.time() - start_time < 3:
                        previews = []
                        for i, animator in enumerate(animators):
                            panel = Panel(
                                animator.get_frame_display(),
                                title=f"[bold]LED {i+1}[/]",
                                border_style="yellow"
                            )
                            previews.append(panel)
                            animator.current_frame = (animator.current_frame + 1) % max(len(animator.frames), 1)
                        
                        columns = Columns(previews, equal=True, expand=True)
                        live.update(columns)
                        time.sleep(frame_delay)
                
                source_led = questionary.select(
                    "Select source LED:",
                    choices=["1. LED 1", "2. LED 2", "3. LED 3", "← Back"],
                    style=custom_style,
                    use_shortcuts=True
                ).ask()
                
                if source_led == "← Back" or source_led is None:
                    return self.configure_led_mapping(led_num)  # Retry this LED config
                
                # Extract LED number safely
                if "LED 1" in source_led:
                    led_idx = 1
                elif "LED 2" in source_led:
                    led_idx = 2
                elif "LED 3" in source_led:
                    led_idx = 3
                else:
                    led_idx = 1  # Default fallback
                
                return {
                    "action": "replace",
                    "source_file": source_file,
                    "source_led": led_idx,
                    "source_data": source_data
                }
                
        return {"action": "keep"}
        
    def configure_all_mappings(self) -> bool:
        """Configure mappings for all 3 custom LEDs"""
        console.print(Panel("[bold cyan]Step 2: Configure LED Mappings[/]", expand=False))
        
        i = 1
        while i <= 3:
            result = self.configure_led_mapping(i)
            if result.get("action") == "back":
                if i > 1:
                    i -= 1  # Go back to previous LED
                else:
                    return False  # Go back to base file selection
            else:
                self.mappings[i] = result
                i += 1  # Move to next LED
        
        return True
            
    def show_summary(self) -> Optional[str]:
        """Show configuration summary and confirm"""
        console.print("\n" + "="*50)
        console.print(Panel("[bold cyan]Step 3: Configuration Summary[/]", expand=False))
        
        table = Table(title="LED Mapping Configuration", box=ROUNDED)
        table.add_column("LED", style="cyan", width=12)
        table.add_column("Action", style="magenta")
        table.add_column("Source", style="yellow")
        
        for i in range(1, 4):
            mapping = self.mappings[i]
            if mapping["action"] == "keep":
                table.add_row(f"Custom LED {i}", "Keep Base", "-")
            else:
                source = f"{mapping['source_file']} → LED {mapping['source_led']}"
                table.add_row(f"Custom LED {i}", "Replace", source)
                
        console.print(table)
        
        # Animate final preview
        console.print("\n[bold]Final LED Configuration Preview (3 seconds):[/]\n")
        
        animators = []
        max_frames = 0
        for i in range(1, 4):
            mapping = self.mappings[i]
            animator = LEDPreviewAnimator()
            
            if mapping["action"] == "keep":
                page_data = self.base_data['page_data'][4 + i]
            else:
                page_data = mapping['source_data']['page_data'][4 + mapping['source_led']]
                
            animator.load_frames(page_data)
            animators.append(animator)
            max_frames = max(max_frames, len(animator.frames))
        
        # Calculate frame delay to fit animation in 3 seconds
        if max_frames > 0:
            frame_delay = 3.0 / max_frames
        else:
            frame_delay = 0.2
        
        with Live(refresh_per_second=10, console=console) as live:
            start_time = time.time()
            while time.time() - start_time < 3:
                previews = []
                for i, animator in enumerate(animators):
                    panel = Panel(
                        animator.get_frame_display(),
                        title=f"[bold]Final LED {i+1}[/]",
                        border_style="green"
                    )
                    previews.append(panel)
                    animator.current_frame = (animator.current_frame + 1) % max(len(animator.frames), 1)
                
                columns = Columns(previews, equal=True, expand=True)
                live.update(columns)
                time.sleep(frame_delay)
        
        choice = questionary.select(
            "\nProceed with merge?",
            choices=["1. Yes, proceed", "2. No, restart", "← Back to LED mapping"],
            style=custom_style,
            use_shortcuts=True
        ).ask()
        
        if "Yes" in choice:
            return "proceed"
        elif "Back" in choice:
            return "back"
        else:
            return "restart"
        
    def select_save_method(self) -> Optional[Tuple[str, str]]:
        """Select save method and filename"""
        console.print(Panel("[bold cyan]Step 4: Save Configuration[/]", expand=False))
        
        save_method = questionary.select(
            "Save method:",
            choices=["1. Save as new file", "2. Overwrite base file", "← Back"],
            style=custom_style,
            use_shortcuts=True
        ).ask()
        
        if save_method == "← Back" or save_method is None:
            return None
        elif "Overwrite" in save_method:
            confirm = questionary.select(
                f"\n⚠ This will overwrite {self.base_file}. Continue?",
                choices=["1. Yes, overwrite", "2. No, go back"],
                style=custom_style,
                use_shortcuts=True
            ).ask()
            
            if "Yes" in confirm:
                return "overwrite", self.base_file
            else:
                return self.select_save_method()
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"merged_{timestamp}.json"
            
            filename = Prompt.ask(
                "Enter filename",
                default=default_name
            )
            
            if not filename.endswith('.json'):
                filename += '.json'
                
            return "new", filename
            
    def perform_merge(self):
        """Perform the actual merge operation"""
        console.print(Panel("[bold cyan]Step 5: Merging Configuration[/]", expand=False))
        
        merged_data = copy.deepcopy(self.base_data)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Merging configurations...", total=3)
            
            for i in range(1, 4):
                mapping = self.mappings[i]
                if mapping["action"] == "replace":
                    source_idx = 4 + mapping['source_led']
                    target_idx = 4 + i
                    merged_data['page_data'][target_idx] = copy.deepcopy(
                        mapping['source_data']['page_data'][source_idx]
                    )
                    merged_data['page_data'][target_idx]['page_index'] = target_idx
                    
                progress.update(task, advance=1)
                time.sleep(0.2)
                
        return merged_data
        
    def save_result(self, data: Dict, method: str, filename: str):
        """Save merged configuration"""
        if method == "overwrite":
            # Overwrite uses source directory
            full_path = os.path.join(self.source_dir, filename)
        else:
            # New files use output directory
            os.makedirs(self.output_dir, exist_ok=True)
            full_path = os.path.join(self.output_dir, filename)
            
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        if method == "overwrite":
            console.print(f"\n[green]✓[/] Configuration overwritten: [bold]{full_path}[/]")
        else:
            console.print(f"\n[green]✓[/] Configuration saved: [bold]{full_path}[/]")
            
    def run(self):
        """Main application flow"""
        try:
            self.enter_alternate_screen()
            self.display_header()
            
            # Step 1: Select base file
            while True:
                if not self.select_base_file():
                    return False
                break
            
            # Step 2: Configure LED mappings with back support
            while True:
                if not self.configure_all_mappings():
                    continue  # Go back to base file selection
                    
                # Step 3: Show summary
                summary_result = self.show_summary()
                if summary_result == "back":
                    self.mappings = {}  # Clear mappings
                    continue  # Go back to LED mapping
                elif summary_result == "restart":
                    console.print("\n[yellow]Restarting configuration...[/]")
                    return False
                elif summary_result == "proceed":
                    break
            
            # Step 4: Select save method
            while True:
                save_result = self.select_save_method()
                if save_result is None:
                    # Go back to summary
                    summary_result = self.show_summary()
                    if summary_result == "back":
                        self.mappings = {}
                        continue
                    elif summary_result == "restart":
                        return False
                    elif summary_result != "proceed":
                        continue
                else:
                    save_method, filename = save_result
                    break
            
            # Step 5: Perform merge and save
            merged_data = self.perform_merge()
            self.save_result(merged_data, save_method, filename)
            
            console.print("\n[bold green]✨ Merge completed successfully![/]")
            return True
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/]")
            return False
        finally:
            self.exit_alternate_screen()

def main():
    """Main entry point"""
    try:
        while True:
            merger = CyberboardMerger()
            success = merger.run()
            
            if success:
                # Use regular console for continuation prompt (outside alternate screen)
                if not Confirm.ask("\nContinue with another merge?", default=False):
                    break
            else:
                break
            
        console.print("\n[bold cyan]Thank you for using CYBERBOARD R4 Configuration Merger![/]")
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Operation cancelled by user.[/]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/]")
        sys.exit(1)

if __name__ == "__main__":
    main()