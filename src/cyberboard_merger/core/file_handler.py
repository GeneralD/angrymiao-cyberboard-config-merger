"""File operations and JSON handling"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.led_data import LEDConfiguration


class FileHandler:
    """Handles file operations for configuration files"""
    
    def __init__(self, source_dir: str, output_dir: str):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        
    def get_json_files(self) -> List[str]:
        """Get list of JSON files in source directory"""
        try:
            return [
                f.name for f in self.source_dir.iterdir() 
                if f.is_file() and f.suffix.lower() == '.json'
            ]
        except FileNotFoundError:
            raise FileNotFoundError(f"Source directory '{self.source_dir}' not found")
            
    def load_configuration(self, filename: str) -> LEDConfiguration:
        """Load LED configuration from JSON file"""
        file_path = self.source_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file '{filename}' not found")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return LEDConfiguration(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file '{filename}': {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration '{filename}': {e}")
            
    def save_configuration(
        self, 
        config: LEDConfiguration, 
        filename: str, 
        overwrite: bool = False
    ) -> str:
        """Save LED configuration to JSON file
        
        Returns:
            Full path to saved file
        """
        # Determine save location
        if overwrite:
            # Overwrite uses source directory
            save_path = self.source_dir / filename
        else:
            # New files use output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)
            save_path = self.output_dir / filename
            
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(config.config_data, f, ensure_ascii=False, indent=2)
            return str(save_path)
        except Exception as e:
            raise RuntimeError(f"Failed to save configuration to '{save_path}': {e}")
            
    def generate_default_filename(self) -> str:
        """Generate default filename with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"merged_{timestamp}.json"
        
    def validate_json_file(self, filename: str) -> bool:
        """Validate if file contains valid JSON"""
        try:
            self.load_configuration(filename)
            return True
        except:
            return False


class ConfigurationLoader:
    """Handles loading and validation of configuration files"""
    
    def __init__(self, file_handler: FileHandler):
        self.file_handler = file_handler
        
    def load_and_validate_files(self) -> List[str]:
        """Load and validate all JSON files in source directory"""
        all_files = self.file_handler.get_json_files()
        valid_files = []
        
        for filename in all_files:
            if self.file_handler.validate_json_file(filename):
                valid_files.append(filename)
                
        return valid_files
        
    def get_file_info(self, filename: str) -> Dict[str, Any]:
        """Get basic information about a configuration file"""
        try:
            config = self.file_handler.load_configuration(filename)
            custom_pages = config.get_custom_led_pages()
            
            return {
                'filename': filename,
                'valid': True,
                'product_info': config.product_info,
                'page_count': config.page_count,
                'custom_led_frames': [page.get_frame_count() for page in custom_pages],
                'total_custom_frames': sum(page.get_frame_count() for page in custom_pages)
            }
        except Exception as e:
            return {
                'filename': filename,
                'valid': False,
                'error': str(e)
            }