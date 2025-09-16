"""Display and UI utilities"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.table import Table
from rich.box import ROUNDED
from rich.progress import Progress, SpinnerColumn, TextColumn


class TerminalDisplay:
    """Handles terminal display operations"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        
    def enter_alternate_screen(self) -> None:
        """Enter alternate screen buffer"""
        sys.stdout.write("\033[?1049h")  # Enable alternate screen buffer
        sys.stdout.write("\033[H")       # Move cursor to home position
        sys.stdout.flush()
        self.console.clear()
        
    def exit_alternate_screen(self) -> None:
        """Exit alternate screen buffer"""
        sys.stdout.write("\033[?1049l")  # Disable alternate screen buffer
        sys.stdout.flush()
        
    def display_header(self) -> None:
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
        self.console.print(header)
        self.console.print()
        
    def display_step_header(self, step_text: str) -> None:
        """Display step header"""
        self.console.print(Panel(f"[bold cyan]{step_text}[/]", expand=False))
        
    def display_success(self, message: str) -> None:
        """Display success message"""
        self.console.print(f"[green]✓[/] {message}")
        
    def display_warning(self, message: str) -> None:
        """Display warning message"""
        self.console.print(f"[yellow]{message}[/]")
        
    def display_error(self, message: str) -> None:
        """Display error message"""
        self.console.print(f"[red]{message}[/]")
        
    def display_info(self, message: str) -> None:
        """Display info message"""
        self.console.print(f"[cyan]{message}[/]")
        
    def display_separator(self) -> None:
        """Display separator line"""
        self.console.print("\n" + "="*50)


class ConfigurationSummary:
    """Handles configuration summary display"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        
    def create_summary_table(self, mappings: dict) -> Table:
        """Create LED mapping configuration summary table"""
        table = Table(title="LED Mapping Configuration", box=ROUNDED)
        table.add_column("LED", style="cyan", width=15)
        table.add_column("Action", style="magenta")
        table.add_column("Sources/Frames", style="yellow", width=50)
        
        for i in range(1, 4):
            mapping = mappings[i]  # This is a LEDMappingResult object
            
            if mapping.is_keep:
                table.add_row(f"Custom LED {i}", "Keep Base", "-")
            elif mapping.is_combined:
                sources = mapping.data.get('sources', [])
                sources_str = "\n".join(sources[:3])
                if len(sources) > 3:
                    sources_str += f"\n... and {len(sources) - 3} more"
                frame_count = mapping.data.get('frame_count', 0)
                table.add_row(
                    f"Custom LED {i}", 
                    "Combined", 
                    f"{sources_str}\n({frame_count} frames)"
                )
            else:
                # Legacy replace action or other actions
                source_file = mapping.data.get('source_file', 'Unknown')
                source_led = mapping.data.get('source_led', 0)
                source = f"{source_file} → LED {source_led}"
                table.add_row(f"Custom LED {i}", "Replace", source)
                
        return table
    
    def display_current_configuration(self, sources: list, current_frames: int, max_frames: int) -> None:
        """Display current configuration status"""
        if sources:
            self.console.print(f"\n[green]Current configuration:[/]")
            for src in sources:
                self.console.print(f"  • {src}")
        self.console.print(f"[yellow]Current frames: {current_frames}/{max_frames}[/]")
        self.console.print(f"[cyan]Remaining capacity: {max_frames - current_frames} frames[/]\n")


class ProgressDisplay:
    """Handles progress display operations"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        
    def show_merge_progress(self, total_tasks: int = 3):
        """Show merge progress with context manager"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        )
        
    def display_directory_creation(self, created_dirs: list) -> None:
        """Display created directories information"""
        if created_dirs:
            dirs_str = ", ".join(f"'{d}'" for d in created_dirs)
            self.console.print(f"[green]✓[/] Created directories: {dirs_str}")
            if any('source' in d.lower() for d in created_dirs):
                self.console.print(f"[dim]Add CYBERBOARD R4 JSON files to get started.[/]")