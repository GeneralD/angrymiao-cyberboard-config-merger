"""User input prompts and interactions"""

from typing import List, Optional, Dict, Any
import questionary
from questionary import Style
from rich.console import Console

# Custom style for questionary prompts
CUSTOM_STYLE = Style([
    ('question', 'fg:#00ffff bold'),
    ('answer', 'fg:#44ff00 bold'),
    ('pointer', 'fg:#ff00ff bold'),
    ('highlighted', 'fg:#ff00ff bold'),
    ('selected', 'fg:#44ff00'),
    ('separator', 'fg:#888888'),
    ('instruction', 'fg:#888888'),
])


class UserPrompts:
    """Handles all user input prompts"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        
    def select_from_list(
        self, 
        message: str, 
        choices: List[str], 
        include_back: bool = True,
        include_quit: bool = False
    ) -> Optional[str]:
        """Generic selection from list with optional back/quit options"""
        full_choices = choices.copy()
        
        if include_back:
            full_choices.append("← Back")
        if include_quit:
            full_choices.append("← Quit")
            
        result = questionary.select(
            message,
            choices=full_choices,
            style=CUSTOM_STYLE,
            use_shortcuts=True
        ).ask()
        
        if result in ["← Back", "← Quit"] or result is None:
            return None
            
        return result
    
    def select_base_file(self, files: List[str]) -> Optional[str]:
        """Select base configuration file"""
        return self.select_from_list(
            "Choose base file (use arrows or number keys):",
            files,
            include_back=False,
            include_quit=True
        )
    
    def select_led_action(self, led_num: int) -> Optional['LEDAction']:
        """Select action for LED configuration"""
        from ..models.user_choices import LEDAction
        
        choices = ["Keep Base", "Replace", "Combine with Base"]
        choice_map = {
            "Keep Base": LEDAction.KEEP_BASE,
            "Replace": LEDAction.REPLACE,
            "Combine with Base": LEDAction.COMBINE
        }
        
        result = self.select_from_list(
            f"Action for Custom LED {led_num}:",
            choices
        )
        
        if result is None:
            return LEDAction.BACK
        
        return choice_map.get(result, LEDAction.BACK)
    
    def select_next_action(self) -> Optional['NextAction']:
        """Select next action after configuration"""
        from ..models.user_choices import NextAction
        
        choices = ["Add another LED", "Finish"]
        choice_map = {
            "Add another LED": NextAction.ADD_ANOTHER,
            "Finish": NextAction.FINISH
        }
        
        result = self.select_from_list(
            "What would you like to do next?",
            choices
        )
        
        if result is None:
            return NextAction.BACK
            
        return choice_map.get(result, NextAction.BACK)
    
    def select_source_file(self, files: List[str]) -> Optional[str]:
        """Select source file for LED configuration"""
        return self.select_from_list(
            "Select source file:",
            files
        )
    
    def select_source_led(self, choices: List[str], max_frames: int) -> Optional[str]:
        """Select source LED with frame validation"""
        return self.select_from_list(
            f"Select source LED (max {max_frames} frames):",
            choices
        )
    
    def confirm_proceed(self) -> Optional['UserChoice']:
        """Confirm to proceed with merge"""
        from ..models.user_choices import UserChoice
        
        choices = ["Yes, proceed", "No, restart", "← Back to LED mapping"]
        choice_map = {
            "Yes, proceed": UserChoice.PROCEED,
            "No, restart": UserChoice.RESTART,
            "← Back to LED mapping": UserChoice.BACK_TO_MAPPING
        }
        
        result = self.select_from_list(
            "Proceed with merge?",
            choices,
            include_back=False
        )
        
        if result is None:
            return UserChoice.CANCELLED
            
        return choice_map.get(result, UserChoice.CANCELLED)
    
    def select_save_method(self) -> Optional[str]:
        """Select save method"""
        choices = ["Save as new file", "Overwrite base file"]
        return self.select_from_list(
            "Save method:",
            choices
        )
    
    def confirm_overwrite(self, filename: str) -> Optional[str]:
        """Confirm file overwrite"""
        choices = ["① Yes, overwrite", "② No, go back"]
        return self.select_from_list(
            f"⚠ This will overwrite {filename}. Continue?",
            choices,
            include_back=False
        )
    
    def get_filename(self, default: str) -> str:
        """Get filename input from user"""
        from rich.prompt import Prompt
        
        filename = Prompt.ask(
            "Enter filename",
            default=default,
            console=self.console
        )
        
        if not filename.endswith('.json'):
            filename += '.json'
            
        return filename
    
    def handle_no_files_action(self) -> Optional[str]:
        """Handle action when no JSON files found"""
        choices = [
            "Retry after adding JSON files",
            "Reload config.toml and retry", 
            "Exit application"
        ]
        return self.select_from_list(
            "What would you like to do?",
            choices,
            include_back=False
        )