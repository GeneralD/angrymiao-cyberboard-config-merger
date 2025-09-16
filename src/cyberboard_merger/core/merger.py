"""Core merging logic and business operations"""

from typing import Dict, List, Optional, Tuple
import time
from rich.console import Console

from ..models.led_data import LEDConfiguration, LEDPage, LEDMerger
from ..ui.animator import LEDAnimator, AnimationDisplay
from ..ui.prompts import UserPrompts
from ..ui.display import TerminalDisplay, ConfigurationSummary, ProgressDisplay
from ..core.file_handler import FileHandler, ConfigurationLoader
from ..config.settings import AppConfig


class LEDMappingResult:
    """Represents the result of LED mapping configuration"""
    
    def __init__(self, action: str, **kwargs):
        try:
            if not isinstance(action, str):
                raise ValueError(f"Action must be string, got {type(action)}")
            if action not in ["back", "keep", "combined"]:
                raise ValueError(f"Invalid action: {action}")
                
            self.action = action
            self.data = kwargs
            
        except Exception as e:
            # Fallback to safe defaults
            print(f"[ERROR] LEDMappingResult init failed: {e}")
            self.action = "keep"
            self.data = {}
        
    @property
    def is_back(self) -> bool:
        return self.action == "back"
    
    @property
    def is_keep(self) -> bool:
        return self.action == "keep"
    
    @property
    def is_combined(self) -> bool:
        return self.action == "combined"


class ConfigurationMerger:
    """Handles the main configuration merging workflow"""
    
    def __init__(self, config: AppConfig, console: Console = None):
        self.config = config
        self.console = console or Console()
        
        # Initialize components
        self.file_handler = FileHandler(config.source_dir, config.output_dir)
        self.config_loader = ConfigurationLoader(self.file_handler)
        self.prompts = UserPrompts(self.console)
        self.display = TerminalDisplay(self.console)
        self.summary_display = ConfigurationSummary(self.console)
        self.progress_display = ProgressDisplay(self.console)
        self.animation_display = AnimationDisplay(self.console)
        
        # Application state
        self.base_config: Optional[LEDConfiguration] = None
        self.mappings: Dict[int, LEDMappingResult] = {}
        
    def initialize_directories(self) -> None:
        """Initialize and create necessary directories"""
        created_dirs = self.config.ensure_directories()
        if created_dirs:
            self.progress_display.display_directory_creation(created_dirs)
            
    def get_available_files(self) -> List[str]:
        """Get list of available configuration files"""
        try:
            return self.config_loader.load_and_validate_files()
        except FileNotFoundError:
            return []
            
    def select_base_configuration(self) -> bool:
        """Select base configuration file"""
        while True:
            files = self.get_available_files()
            
            if not files:
                self.display.display_warning(
                    f"No JSON files found in source directory: '{self.config.source_dir}'"
                )
                self.display.display_info(
                    f"Please add CYBERBOARD R4 JSON configuration files to '{self.config.source_dir}' and try again."
                )
                
                action = self.prompts.handle_no_files_action()
                if action and "Retry after adding" in action:
                    continue
                elif action and "Reload config" in action:
                    self.config = AppConfig()  # Reload configuration
                    self.file_handler = FileHandler(self.config.source_dir, self.config.output_dir)
                    self.config_loader = ConfigurationLoader(self.file_handler)
                    self.initialize_directories()
                    continue
                else:
                    return False
            else:
                break
                
        self.display.display_step_header("Step 1: Select Base Configuration File")
        
        selected_file = self.prompts.select_base_file(files)
        if not selected_file:
            return False
            
        try:
            self.base_config = self.file_handler.load_configuration(selected_file)
            self.display.display_success(f"Base file selected: [bold]{selected_file}[/]")
            self._preview_base_configuration()
            return True
        except Exception as e:
            self.display.display_error(f"Failed to load base configuration: {e}")
            return False
            
    def _preview_base_configuration(self) -> None:
        """Preview base configuration LED animations"""
        if not self.base_config:
            return
            
        self.display.display_info("Base LED Configuration Preview:")
        
        animators = []
        titles = []
        
        for i, page in enumerate(self.base_config.get_custom_led_pages(), 1):
            animator = LEDAnimator()
            animator.load_frames(page.get_rgb_data())
            animators.append(animator)
            titles.append(f"Custom LED {i}")
            
        self.animation_display.show_animations(animators, titles, "blue")
        
    def configure_led_mapping(self, led_num: int) -> LEDMappingResult:
        """Configure mapping for a single LED"""
        from ..models.user_choices import LEDAction, NextAction
        
        page_idx = self.config.CUSTOM_LED_START_PAGE - 1 + led_num
        current_page = self.base_config.get_page(page_idx)
        current_frames = current_page.get_frame_count() if current_page else 0
        combined_sources = []
        
        while True:
            # Show current status
            if combined_sources:
                self.summary_display.display_current_configuration(
                    combined_sources, current_frames, self.config.MAX_FRAMES
                )
                
            # Show current LED preview
            if current_page:
                self._show_led_preview(led_num, current_page, current_frames)
                
            # Get user action
            if not combined_sources:
                action = self.prompts.select_led_action(led_num)
                
                if action == LEDAction.BACK:
                    return LEDMappingResult("back")
                elif action == LEDAction.KEEP_BASE:
                    return LEDMappingResult("keep")
                elif action == LEDAction.REPLACE:
                    result = self._handle_replace_action(current_frames)
                    if result:
                        current_page = result['page']
                        current_frames = result['frame_count']
                        combined_sources = [result['source_description']]
                    else:
                        continue
                elif action == LEDAction.COMBINE:
                    combined_sources.append(f"Base LED {led_num}")
                    
            # Ask for next action
            if current_frames < self.config.MAX_FRAMES:
                next_action = self.prompts.select_next_action()
                
                if next_action == NextAction.BACK:
                    # Reset to base
                    current_page = self.base_config.get_page(page_idx)
                    current_frames = current_page.get_frame_count() if current_page else 0
                    combined_sources = []
                    continue
                elif next_action == NextAction.ADD_ANOTHER:
                    result = self._handle_add_led_action(current_frames)
                    if result:
                        # Combine pages
                        combined_page = LEDMerger.combine_pages([current_page, result['page']])
                        current_page = combined_page
                        current_frames += result['frame_count']
                        combined_sources.append(result['source_description'])
                    else:
                        continue
                elif next_action == NextAction.FINISH:
                    break
            else:
                self.display.display_warning(f"Maximum frame limit ({self.config.MAX_FRAMES}) reached!")
                break
                
        return LEDMappingResult(
            "combined",
            page_data=current_page,
            sources=combined_sources,
            frame_count=current_frames
        )
        
    def _show_led_preview(self, led_num: int, page: LEDPage, frame_count: int) -> None:
        """Show preview of current LED configuration"""
        self.display.display_info(f"Current LED {led_num} Preview:")
        
        animator = LEDAnimator()
        animator.load_frames(page.get_rgb_data())
        
        self.animation_display.show_animations(
            animator,
            f"LED {led_num} ({frame_count} frames)",
            "green"
        )
        
    def _handle_replace_action(self, current_frames: int) -> Optional[Dict]:
        """Handle replace action selection"""
        return self._select_source_led(current_frames, self.config.MAX_FRAMES)
        
    def _handle_add_led_action(self, current_frames: int) -> Optional[Dict]:
        """Handle add LED action selection"""
        max_additional = self.config.MAX_FRAMES - current_frames
        return self._select_source_led(current_frames, max_additional)
        
    def _select_source_led(self, current_frames: int, max_additional_frames: int) -> Optional[Dict]:
        """Select source LED with frame count validation"""
        files = self.get_available_files()
        
        selected_file = self.prompts.select_source_file(files)
        if not selected_file:
            return None
            
        try:
            source_config = self.file_handler.load_configuration(selected_file)
        except Exception as e:
            self.display.display_error(f"Failed to load source configuration: {e}")
            return None
            
        # Show all LEDs from source file
        self.display.display_info(f"LED configurations from {selected_file}:")
        
        animators = []
        titles = []
        border_styles = []
        valid_choices = []
        
        for i, page in enumerate(source_config.get_custom_led_pages(), 1):
            animator = LEDAnimator()
            animator.load_frames(page.get_rgb_data())
            animators.append(animator)
            
            frame_count = page.get_frame_count()
            
            if frame_count <= max_additional_frames:
                titles.append(f"LED {i} - ✓ {frame_count} frames")
                border_styles.append("green")
                valid_choices.append(f"LED {i} ({frame_count} frames) ✓")
            else:
                titles.append(f"LED {i} - ❌ {frame_count} frames (exceeds)")
                border_styles.append("red")
                
        # Show preview
        self.animation_display.show_animations(animators, titles, border_styles)
        
        if not valid_choices:
            self.display.display_error("No LEDs fit within the remaining frame limit!")
            return None
            
        selected_led = self.prompts.select_source_led(valid_choices, max_additional_frames)
        if not selected_led:
            return None
            
        # Extract LED number
        led_idx = 1
        if "LED 1" in selected_led:
            led_idx = 1
        elif "LED 2" in selected_led:
            led_idx = 2
        elif "LED 3" in selected_led:
            led_idx = 3
            
        source_page = source_config.get_page(self.config.CUSTOM_LED_START_PAGE - 1 + led_idx)
        if not source_page:
            return None
            
        return {
            'page': source_page,
            'frame_count': source_page.get_frame_count(),
            'source_description': f"{selected_file} → LED {led_idx}"
        }
        
    def configure_all_mappings(self) -> bool:
        """Configure mappings for all 3 custom LEDs"""
        self.display.display_step_header("Step 2: Configure LED Mappings")
        
        led_num = 1
        while led_num <= 3:
            result = self.configure_led_mapping(led_num)
            
            if result.is_back:
                if led_num > 1:
                    led_num -= 1  # Go back to previous LED
                else:
                    return False  # Go back to base file selection
            else:
                self.mappings[led_num] = result
                led_num += 1  # Move to next LED
                
        return True
        
    def show_summary(self) -> Optional[str]:
        """Show configuration summary and get confirmation"""
        self.display.display_separator()
        self.display.display_step_header("Step 3: Configuration Summary")
        
        # Show summary table
        table = self.summary_display.create_summary_table(self.mappings)
        self.console.print(table)
        
        # Show final preview
        self.display.display_info("Final LED Configuration Preview:")
        self._show_final_preview()
        
        return self.prompts.confirm_proceed()
        
    def _show_final_preview(self) -> None:
        """Show final configuration preview"""
        animators = []
        titles = []
        
        for i in range(1, 4):
            mapping = self.mappings[i]
            animator = LEDAnimator()
            
            if mapping.is_keep:
                page = self.base_config.get_page(self.config.CUSTOM_LED_START_PAGE - 1 + i)
            elif mapping.is_combined:
                page = mapping.data['page_data']
            else:
                # Handle other cases if needed
                continue
                
            if page:
                animator.load_frames(page.get_rgb_data())
                animators.append(animator)
                titles.append(f"Final LED {i} ({len(animator.frames)} frames)")
                
        self.animation_display.show_animations(animators, titles, "green")
        
    def perform_merge(self) -> LEDConfiguration:
        """Perform the actual configuration merge"""
        self.display.display_step_header("Step 5: Merging Configuration")
        
        merged_config = LEDConfiguration(self.base_config.config_data)
        
        with self.progress_display.show_merge_progress() as progress:
            task = progress.add_task("[cyan]Merging configurations...", total=3)
            
            for i in range(1, 4):
                mapping = self.mappings[i]
                target_idx = self.config.CUSTOM_LED_START_PAGE - 1 + i
                
                if mapping.is_combined:
                    merged_config.set_page(target_idx, mapping.data['page_data'])
                # Keep action doesn't require changes
                    
                progress.update(task, advance=1)
                time.sleep(0.2)
                
        return merged_config
        
    def save_configuration(self, config: LEDConfiguration, base_filename: str) -> bool:
        """Handle configuration saving workflow"""
        self.display.display_step_header("Step 4: Save Configuration")
        
        save_method = self.prompts.select_save_method()
        if not save_method:
            return False
            
        if "Overwrite" in save_method:
            confirm = self.prompts.confirm_overwrite(base_filename)
            if confirm and "Yes" in confirm:
                try:
                    saved_path = self.file_handler.save_configuration(
                        config, base_filename, overwrite=True
                    )
                    self.display.display_success(f"Configuration overwritten: [bold]{saved_path}[/]")
                    return True
                except Exception as e:
                    self.display.display_error(f"Failed to overwrite file: {e}")
                    return False
            else:
                return self.save_configuration(config, base_filename)  # Retry
        else:
            default_name = self.file_handler.generate_default_filename()
            filename = self.prompts.get_filename(default_name)
            
            try:
                saved_path = self.file_handler.save_configuration(config, filename)
                self.display.display_success(f"Configuration saved: [bold]{saved_path}[/]")
                return True
            except Exception as e:
                self.display.display_error(f"Failed to save file: {e}")
                return False