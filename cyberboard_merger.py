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
import select
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
from rich.console import Group
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
        self.width = width  # LED grid width (40)
        self.height = height  # LED grid height (5)
        self.display_width = width * 2  # Display width (80 chars for square appearance)
        self.frames = []
        self.current_frame = 0
        self.running = False
        self.thread = None
        self.fps = 10  # 10 frames per second
        self.frame_delay = 1.0 / self.fps  # 0.1 seconds per frame
        
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
                        # Use two characters to make square appearance
                        row.append(f"[rgb({r},{g},{b})]██[/]")
                    else:
                        row.append("██")
                else:
                    row.append("  ")
            display.append("".join(row))
            
        return "\n".join(display)
        
    def _generate_empty_display(self) -> str:
        """Generate empty display grid"""
        return "\n".join(["░░" * self.width for _ in range(self.height)])
    
    def get_synchronized_frame(self, target_frame_count: int, current_position: int) -> int:
        """Get frame index for synchronized animation with looping
        
        Args:
            target_frame_count: Total frames in the longest animation
            current_position: Current position (0 to target_frame_count-1)
        
        Returns:
            Frame index for this animation with looping
        """
        if not self.frames or target_frame_count <= 0:
            return 0
        
        animation_length = len(self.frames)
        if animation_length == 0:
            return 0
        
        # Calculate which frame to show based on current position
        return current_position % animation_length
    
    def wait_for_any_key(self) -> bool:
        """Check if Enter key was pressed (non-blocking)
        
        Returns:
            True if Enter key was pressed, False otherwise
        """
        if sys.stdin.isatty():
            # Use select for non-blocking input check (Unix/Linux/macOS)
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                # Read any input and clear the buffer
                try:
                    line = sys.stdin.readline()
                    # Clear any remaining input buffer
                    while select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                        try:
                            sys.stdin.readline()
                        except:
                            break
                    return True
                except:
                    return False
        return False
        
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
    
    @staticmethod
    def show_animations(animators, titles, border_styles=None, instruction: str = "Press Enter to continue...") -> None:
        """Show LED animations with unified layout (supports single or multiple)
        
        Args:
            animators: Single LEDPreviewAnimator or List of LEDPreviewAnimators
            titles: Single title string or List of title strings
            border_styles: Single border style string or List of border style strings (optional)
            instruction: Instruction text
        """
        # Convert single items to lists for unified processing
        if not isinstance(animators, list):
            animators = [animators]
        if not isinstance(titles, list):
            titles = [titles]
        if border_styles is not None and not isinstance(border_styles, list):
            border_styles = [border_styles]
            
        if not animators or not titles:
            return
            
        # Default border styles if not provided
        if border_styles is None:
            border_styles = ["blue"] * len(animators)
        elif len(border_styles) < len(animators):
            # Extend border_styles to match animators length
            border_styles.extend(["blue"] * (len(animators) - len(border_styles)))
            
        # Filter animators with frames
        valid_animators = [(a, t, b) for a, t, b in zip(animators, titles, border_styles) if len(a.frames) > 0]
        if not valid_animators:
            return
            
        animators, titles, border_styles = zip(*valid_animators)
        animators, titles, border_styles = list(animators), list(titles), list(border_styles)
        
        max_frames = max(len(a.frames) for a in animators)
        with Live(refresh_per_second=10, console=console) as live:
            frame_position = 0
            frame_delay = animators[0].frame_delay if animators else 0.1
            
            while True:
                previews = []
                for animator, title, border_style in zip(animators, titles, border_styles):
                    # Use synchronized frame logic for consistent looping
                    frame_index = animator.get_synchronized_frame(max_frames, frame_position)
                    
                    # Set expand=False for single panel to fit content
                    is_single = len(animators) == 1
                    panel = Panel(
                        animator.get_frame_display(frame_index),
                        title=f"[bold]{title}[/]",
                        border_style=border_style,
                        expand=not is_single
                    )
                    previews.append(panel)
                
                # Use single panel or columns layout based on count
                if len(previews) == 1:
                    display_content = previews[0]
                else:
                    display_content = Columns(previews, equal=True, expand=True)
                
                instruction_text = Text(instruction, style="dim")
                content = Group(display_content, "", instruction_text)
                
                # Clear the live display before updating to prevent overlap
                live.update(content)
                frame_position = (frame_position + 1) % max_frames
                time.sleep(frame_delay)
                
                # Check for Enter key
                if animators[0].wait_for_any_key():
                    # Small delay to allow final render to complete
                    time.sleep(0.05)
                    break

class CyberboardMerger:
    """Main application class"""
    
    MAX_FRAMES = 300  # Maximum frames per LED
    
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
                        "Retry after adding JSON files",
                        "Reload config.toml and retry",
                        "Exit application"
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
        
        choice = questionary.select(
            "Choose base file (use arrows or number keys):",
            choices=files + ["← Quit"],
            style=custom_style,
            use_shortcuts=True
        ).ask()
        
        if choice == "← Quit" or choice is None:
            return None
            
        # Extract filename from choice
        if choice:
            self.base_file = choice
            full_path = os.path.join(self.source_dir, choice)
            with open(full_path, 'r', encoding='utf-8') as f:
                self.base_data = json.load(f)
                
            console.print(f"\n[green]✓[/] Base file selected: [bold]{choice}[/]")
            self.preview_base_leds_animated()
            return choice
            
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
        console.print("\n[bold]Base LED Configuration Preview:[/]")
        
        animators = []
        titles = []
        for i in range(3):
            page_idx = 5 + i
            page_data = self.base_data['page_data'][page_idx]
            
            animator = LEDPreviewAnimator()
            animator.load_frames(page_data)
            animators.append(animator)
            titles.append(f"Custom LED {i+1}")
        
        LEDPreviewAnimator.show_animations(animators, titles, "blue")
    
    def get_frame_count(self, page_data: Dict) -> int:
        """Get the number of frames in a page data"""
        if not page_data:
            return 0
            
        frames_data = page_data.get('frames', {})
        if frames_data.get('valid', 0) == 0:
            frames_data = page_data.get('keyframes', {})
            
        return len(frames_data.get('frame_data', []))
    
    def combine_led_frames(self, page_data_list: List[Dict]) -> Dict:
        """Combine multiple LED page data into one"""
        if not page_data_list:
            return {}
        
        # Start with the first page's data as base
        combined = copy.deepcopy(page_data_list[0])
        
        # Determine which frame structure to use
        frames_key = 'frames' if combined.get('frames', {}).get('valid', 0) == 1 else 'keyframes'
        combined_frames = combined.get(frames_key, {})
        combined_frame_list = list(combined_frames.get('frame_data', []))
        
        # Add frames from remaining pages
        for page_data in page_data_list[1:]:
            frames_data = page_data.get('frames', {})
            if frames_data.get('valid', 0) == 0:
                frames_data = page_data.get('keyframes', {})
            
            frame_list = frames_data.get('frame_data', [])
            combined_frame_list.extend(frame_list)
        
        # Renumber frame_index for all frames
        for idx, frame in enumerate(combined_frame_list):
            frame['frame_index'] = idx
        
        # Update the combined frame data with correct frame_num
        combined_frames['frame_data'] = combined_frame_list
        combined_frames['frame_num'] = len(combined_frame_list)
        combined[frames_key] = combined_frames
        
        return combined
            
    def configure_led_mapping(self, led_num: int) -> Dict:
        """Configure mapping for a single LED with continuous addition support"""
        console.print(f"\n[bold cyan]Configure Custom LED {led_num}[/]")
        
        page_idx = 4 + led_num
        current_page_data = copy.deepcopy(self.base_data['page_data'][page_idx])
        current_frames = self.get_frame_count(current_page_data)
        combined_sources = []  # Track all combined sources
        
        while True:
            # Show current status
            if combined_sources:
                console.print(f"\n[green]Current configuration:[/]")
                for src in combined_sources:
                    console.print(f"  • {src}")
            console.print(f"[yellow]Current frames: {current_frames}/{self.MAX_FRAMES}[/]")
            console.print(f"[cyan]Remaining capacity: {self.MAX_FRAMES - current_frames} frames[/]\n")
            
            # Show animated preview of current configuration
            console.print(f"[bold]Current LED {led_num} Preview:[/]")
            animator = LEDPreviewAnimator()
            animator.load_frames(current_page_data)
            LEDPreviewAnimator.show_animations(
                animator, 
                f"LED {led_num} ({current_frames} frames)", 
                "green"
            )
            
            # First action or continue adding
            if not combined_sources:
                action = questionary.select(
                    f"Action for Custom LED {led_num}:",
                    choices=["Keep Base", "Replace", "Combine with Base", "← Back"],
                    style=custom_style,
                    use_shortcuts=True
                ).ask()
                
                if action == "← Back" or action is None:
                    return {"action": "back"}
                elif "Keep Base" in action:
                    # Just keep base, no combining
                    return {"action": "keep"}
                elif "Replace" in action:
                    # Replace with a source LED
                    source_result = self.select_source_led(current_frames, self.MAX_FRAMES)
                    if source_result is None:
                        continue
                    
                    current_page_data = copy.deepcopy(source_result['page_data'])
                    current_frames = source_result['frame_count']
                    combined_sources = [f"{source_result['file']} → LED {source_result['led']}"]
                elif "Combine" in action:
                    # Keep base and prepare to add more
                    combined_sources.append(f"Base LED {led_num}")
            
            # Ask if want to add another LED
            if current_frames < self.MAX_FRAMES:
                add_more = questionary.select(
                    "\nWhat would you like to do next?",
                    choices=["Add another LED", "Finish", "← Back"],
                    style=custom_style,
                    use_shortcuts=True
                ).ask()
                
                if add_more == "← Back" or add_more is None:
                    # Go back to the initial action selection
                    current_page_data = copy.deepcopy(self.base_data['page_data'][page_idx])
                    current_frames = self.get_frame_count(current_page_data)
                    combined_sources = []
                    continue
                elif "Add another" in add_more:
                    # Select another LED to combine
                    source_result = self.select_source_led(current_frames, self.MAX_FRAMES - current_frames)
                    if source_result is None:
                        continue
                    
                    # Combine the frames
                    combined = self.combine_led_frames([current_page_data, source_result['page_data']])
                    current_page_data = combined
                    current_frames += source_result['frame_count']
                    combined_sources.append(f"{source_result['file']} → LED {source_result['led']}")
                else:
                    # Finish
                    break
            else:
                console.print(f"[yellow]Maximum frame limit ({self.MAX_FRAMES}) reached![/]")
                break
        
        # Return the final configuration
        return {
            "action": "combined",
            "page_data": current_page_data,
            "sources": combined_sources,
            "frame_count": current_frames
        }
    
    def select_source_led(self, current_frames: int, max_additional_frames: int) -> Optional[Dict]:
        """Select a source LED with frame count validation"""
        files = self.get_json_files()
        
        source_choice = questionary.select(
            "Select source file:",
            choices=files + ["← Back"],
            style=custom_style,
            use_shortcuts=True
        ).ask()
        
        if source_choice == "← Back" or source_choice is None:
            return None
        
        source_file = source_choice
        
        if not source_file:
            return None
            
        full_path = os.path.join(self.source_dir, source_file)
        with open(full_path, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
        
        # Preview all LEDs with frame counts
        console.print(f"\n[bold]LED configurations from {source_file}:[/]\n")
        
        animators = []
        frame_counts = []
        choices = []
        titles = []
        border_styles = []
        
        for i in range(3):
            source_page = source_data['page_data'][5 + i]
            animator = LEDPreviewAnimator()
            animator.load_frames(source_page)
            animators.append(animator)
            
            frame_count = self.get_frame_count(source_page)
            frame_counts.append(frame_count)
            
            # Build choice text and styling
            if frame_count <= max_additional_frames:
                choice_text = f"LED {i+1} ({frame_count} frames) ✓"
                choices.append(choice_text)
                titles.append(f"LED {i+1} - ✓ {frame_count} frames")
                border_styles.append("green")
            else:
                choice_text = f"LED {i+1} ({frame_count} frames) ❌ Exceeds limit"
                titles.append(f"LED {i+1} - ❌ {frame_count} frames (exceeds)")
                border_styles.append("red")
        
        # Show animation preview using unified function
        console.print("[bold]LED Preview:[/]")
        LEDPreviewAnimator.show_animations(animators, titles, border_styles)
        
        if not choices:
            console.print("[red]No LEDs fit within the remaining frame limit![/]")
            return None
        
        source_led = questionary.select(
            f"Select source LED (max {max_additional_frames} frames):",
            choices=choices + ["← Back"],
            style=custom_style,
            use_shortcuts=True
        ).ask()
        
        if source_led == "← Back" or source_led is None:
            return None
        
        # Extract LED number
        if "LED 1" in source_led:
            led_idx = 1
        elif "LED 2" in source_led:
            led_idx = 2
        elif "LED 3" in source_led:
            led_idx = 3
        else:
            led_idx = 1
        
        return {
            "file": source_file,
            "led": led_idx,
            "page_data": source_data['page_data'][4 + led_idx],
            "source_data": source_data,
            "frame_count": frame_counts[led_idx - 1]
        }
        
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
        table.add_column("LED", style="cyan", width=15)
        table.add_column("Action", style="magenta")
        table.add_column("Sources/Frames", style="yellow", width=50)
        
        for i in range(1, 4):
            mapping = self.mappings[i]
            if mapping["action"] == "keep":
                table.add_row(f"Custom LED {i}", "Keep Base", "-")
            elif mapping["action"] == "combined":
                sources_str = "\n".join(mapping['sources'][:3])
                if len(mapping['sources']) > 3:
                    sources_str += f"\n... and {len(mapping['sources']) - 3} more"
                table.add_row(f"Custom LED {i}", "Combined", f"{sources_str}\n({mapping['frame_count']} frames)")
            else:
                # Legacy replace action
                source = f"{mapping['source_file']} → LED {mapping['source_led']}"
                table.add_row(f"Custom LED {i}", "Replace", source)
                
        console.print(table)
        
        # Prepare animators and titles for final preview
        console.print("\n[bold]Final LED Configuration Preview:[/]\n")
        
        animators = []
        titles = []
        for i in range(1, 4):
            mapping = self.mappings[i]
            animator = LEDPreviewAnimator()
            
            if mapping["action"] == "keep":
                page_data = self.base_data['page_data'][4 + i]
            elif mapping["action"] == "combined":
                page_data = mapping['page_data']
            else:
                # Legacy replace action
                page_data = mapping['source_data']['page_data'][4 + mapping['source_led']]
                
            animator.load_frames(page_data)
            animators.append(animator)
            titles.append(f"Final LED {i} ({len(animator.frames)} frames)")
        
        # Show final preview using unified function
        LEDPreviewAnimator.show_animations(animators, titles, "green")
        
        choice = questionary.select(
            "\nProceed with merge?",
            choices=["Yes, proceed", "No, restart", "← Back to LED mapping"],
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
            choices=["Save as new file", "Overwrite base file", "← Back"],
            style=custom_style,
            use_shortcuts=True
        ).ask()
        
        if save_method == "← Back" or save_method is None:
            return None
        elif "Overwrite" in save_method:
            confirm = questionary.select(
                f"\n⚠ This will overwrite {self.base_file}. Continue?",
                choices=["①  Yes, overwrite", "②  No, go back"],
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
                target_idx = 4 + i
                
                if mapping["action"] == "combined":
                    # Use the combined page data
                    merged_data['page_data'][target_idx] = copy.deepcopy(mapping['page_data'])
                    merged_data['page_data'][target_idx]['page_index'] = target_idx
                elif mapping["action"] == "replace":
                    # Legacy replace action
                    source_idx = 4 + mapping['source_led']
                    merged_data['page_data'][target_idx] = copy.deepcopy(
                        mapping['source_data']['page_data'][source_idx]
                    )
                    merged_data['page_data'][target_idx]['page_index'] = target_idx
                # "keep" action doesn't require any changes
                    
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
            
            # Main workflow loop
            while True:
                # Step 1: Select base file
                if not self.select_base_file():
                    return False
                
                # Step 2: Configure LED mappings with back support
                led_config_completed = False
                while True:
                    if not self.configure_all_mappings():
                        break  # Go back to base file selection
                        
                    # Step 3: Show summary
                    summary_result = self.show_summary()
                    if summary_result == "back":
                        self.mappings = {}  # Clear mappings
                        continue  # Go back to LED mapping
                    elif summary_result == "restart":
                        console.print("\n[yellow]Restarting configuration...[/]")
                        return False
                    elif summary_result == "proceed":
                        led_config_completed = True
                        break
                
                # If LED configuration was completed, exit the main loop
                if led_config_completed:
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