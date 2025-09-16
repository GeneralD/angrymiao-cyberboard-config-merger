"""Main application entry point"""

import sys
from rich.console import Console

from .config.settings import AppConfig
from .core.merger import ConfigurationMerger
from .ui.display import TerminalDisplay


class CyberboardMergerApp:
    """Main application class"""
    
    def __init__(self):
        self.console = Console()
        self.config = AppConfig()
        self.display = TerminalDisplay(self.console)
        self.merger = ConfigurationMerger(self.config, self.console)
        
    def run(self) -> bool:
        """Main application workflow"""
        from .models.user_choices import UserChoice
        
        try:
            # Enter alternate screen for better UI
            self.display.enter_alternate_screen()
            self.display.display_header()
            
            # Initialize directories
            self.merger.initialize_directories()
            
            # Main workflow loop
            while True:
                # Step 1: Select base file
                if not self.merger.select_base_configuration():
                    return False
                    
                # Step 2: Configure LED mappings with navigation support
                led_config_completed = False
                while True:
                    self.display.display_info("[DEBUG] Starting configure_all_mappings")
                    if not self.merger.configure_all_mappings():
                        self.display.display_info("[DEBUG] configure_all_mappings returned False")
                        break  # Go back to base file selection
                    
                    self.display.display_info("[DEBUG] configure_all_mappings completed successfully")
                        
                    # Step 3: Show summary and get confirmation
                    self.display.display_info("[DEBUG] Starting show_summary")
                    summary_result = self.merger.show_summary()
                    self.display.display_info(f"[DEBUG] show_summary returned: {summary_result}")
                    
                    # Type-safe choice handling
                    if summary_result == UserChoice.CANCELLED:
                        self.display.display_info("[DEBUG] User cancelled, going back")
                        break  # User cancelled, go back to base file selection
                    elif summary_result == UserChoice.BACK_TO_MAPPING:
                        self.display.display_info("[DEBUG] User chose Back to mapping")
                        self.merger.mappings = {}  # Clear mappings
                        continue  # Go back to LED mapping
                    elif summary_result == UserChoice.RESTART:
                        self.display.display_info("[DEBUG] User chose restart")
                        self.display.display_warning("Restarting configuration...")
                        return False
                    elif summary_result == UserChoice.PROCEED:
                        self.display.display_info("[DEBUG] User chose proceed")
                        led_config_completed = True
                        break
                    else:
                        # Fallback for unexpected result
                        self.display.display_warning(f"[DEBUG] Unexpected result: {summary_result}")
                        break
                        
                # Exit main loop if LED configuration completed
                if led_config_completed:
                    self.display.display_info("[DEBUG] LED configuration completed, proceeding to save")
                    break
                    
            # Step 4 & 5: Save and merge
            while True:
                # Perform merge
                merged_config = self.merger.perform_merge()
                
                # Save configuration
                base_filename = "merged_config.json"  # Could be extracted from base config
                if self.merger.save_configuration(merged_config, base_filename):
                    self.display.display_success("✓ Configuration merge completed successfully!")
                    return True
                else:
                    # Retry save process
                    retry = input("Retry save process? (y/n): ").strip().lower()
                    if retry != 'y':
                        return False
                        
        except KeyboardInterrupt:
            self.display.display_info("\nOperation cancelled by user.")
            return False
        except Exception as e:
            self.display.display_error(f"Unexpected error: {e}")
            return False
        finally:
            self.display.exit_alternate_screen()


def main():
    """Application entry point"""
    app = CyberboardMergerApp()
    
    try:
        success = app.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()