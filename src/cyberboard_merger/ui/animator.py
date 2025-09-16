"""LED animation display functionality"""

import sys
import time
import select
from typing import List, Optional, Union
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.columns import Columns
from rich.console import Group

from ..config.settings import AppConfig


class LEDAnimator:
    """Handles LED animation display in terminal"""
    
    def __init__(self, width: int = None, height: int = None, console: Console = None):
        self.width = width or AppConfig.LED_WIDTH
        self.height = height or AppConfig.LED_HEIGHT
        self.display_width = self.width * 2  # Two characters per LED for square appearance
        self.console = console or Console()
        self.frames = []
        self.fps = AppConfig.ANIMATION_FPS
        self.frame_delay = 1.0 / self.fps
        
    def load_frames(self, rgb_data: List[List[str]]) -> None:
        """Load RGB frame data for animation"""
        self.frames = rgb_data
        
    def get_frame_display(self, frame_index: int = 0) -> str:
        """Generate terminal display for a single frame"""
        if not self.frames or frame_index >= len(self.frames):
            return self._generate_empty_display()
            
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
        """Get frame index for synchronized animation with looping"""
        if not self.frames or target_frame_count <= 0:
            return 0
        
        animation_length = len(self.frames)
        if animation_length == 0:
            return 0
        
        return current_position % animation_length
    
    def _wait_for_enter(self) -> bool:
        """Check if Enter key was pressed (non-blocking)"""
        if sys.stdin.isatty():
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
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


class AnimationDisplay:
    """Handles unified animation display for single or multiple LEDs"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
    
    def show_animations(
        self,
        animators: Union[LEDAnimator, List[LEDAnimator]],
        titles: Union[str, List[str]],
        border_styles: Optional[Union[str, List[str]]] = None,
        instruction: str = "Press Enter to continue..."
    ) -> None:
        """Show LED animations with unified layout"""
        
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
            border_styles.extend(["blue"] * (len(animators) - len(border_styles)))
            
        # Filter animators with frames
        valid_animators = [
            (a, t, b) for a, t, b in zip(animators, titles, border_styles) 
            if len(a.frames) > 0
        ]
        if not valid_animators:
            return
            
        animators, titles, border_styles = zip(*valid_animators)
        animators, titles, border_styles = list(animators), list(titles), list(border_styles)
        
        max_frames = max(len(a.frames) for a in animators)
        
        with Live(refresh_per_second=self.fps, console=self.console) as live:
            frame_position = 0
            
            while True:
                previews = []
                for animator, title, border_style in zip(animators, titles, border_styles):
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
                
                live.update(content)
                frame_position = (frame_position + 1) % max_frames
                time.sleep(animators[0].frame_delay)
                
                # Check for Enter key
                if animators[0]._wait_for_enter():
                    time.sleep(0.05)  # Small delay for render completion
                    break
    
    @property
    def fps(self) -> int:
        """Get animation FPS"""
        return AppConfig.ANIMATION_FPS