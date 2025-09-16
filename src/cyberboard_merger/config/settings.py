"""Application configuration and constants"""

import os
from pathlib import Path
from typing import Dict, Any
import toml


class AppConfig:
    """Application configuration manager"""
    
    # Default configuration constants
    DEFAULT_SOURCE_DIR = "."
    DEFAULT_OUTPUT_DIR = "."
    MAX_FRAMES = 300
    LED_WIDTH = 40
    LED_HEIGHT = 5
    ANIMATION_FPS = 10
    
    # LED page mappings
    BATTERY_PAGE = 0
    MOSAIC_PAGE = 1
    TIME_PAGE = 2
    CUSTOM_TEXT_PAGE = 3
    ANIMATION_PAGE = 4
    CUSTOM_LED_START_PAGE = 5
    
    def __init__(self, config_path: str = "config.toml"):
        self.config_path = Path(config_path)
        self._config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from config.toml"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return toml.load(f)
            except Exception:
                # Fall back to defaults if config is invalid
                pass
        
        # Default configuration
        return {
            'directories': {
                'source': self.DEFAULT_SOURCE_DIR,
                'output': self.DEFAULT_OUTPUT_DIR
            }
        }
    
    @property
    def source_dir(self) -> str:
        """Get source directory path"""
        return self._config.get('directories', {}).get('source', self.DEFAULT_SOURCE_DIR)
    
    @property
    def output_dir(self) -> str:
        """Get output directory path"""
        return self._config.get('directories', {}).get('output', self.DEFAULT_OUTPUT_DIR)
    
    def ensure_directories(self) -> list[str]:
        """Ensure source and output directories exist
        
        Returns:
            List of created directory paths
        """
        created_dirs = []
        
        # Check and create source directory
        if not os.path.exists(self.source_dir):
            try:
                os.makedirs(self.source_dir, exist_ok=True)
                created_dirs.append(self.source_dir)
            except Exception as e:
                raise RuntimeError(f"Failed to create source directory '{self.source_dir}': {e}")
                
        # Check and create output directory (only if different from source)
        if self.output_dir != self.source_dir and not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir, exist_ok=True)
                created_dirs.append(self.output_dir)
            except Exception as e:
                raise RuntimeError(f"Failed to create output directory '{self.output_dir}': {e}")
        
        return created_dirs