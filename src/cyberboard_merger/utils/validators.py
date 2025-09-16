"""Validation utilities"""

from typing import Dict, Any, List
import re


class ConfigurationValidator:
    """Validates CYBERBOARD R4 configuration data"""
    
    # Expected structure constants
    REQUIRED_ROOT_KEYS = ['product_info', 'page_num', 'page_data']
    REQUIRED_PRODUCT_KEYS = ['product_id']
    EXPECTED_PAGE_COUNT = 8
    RGB_COLOR_PATTERN = re.compile(r'^#[0-9A-Fa-f]{6}$')
    
    @classmethod
    def validate_configuration(cls, config_data: Dict[str, Any]) -> List[str]:
        """Validate complete configuration data
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check root structure
        errors.extend(cls._validate_root_structure(config_data))
        
        if not errors:  # Only continue if basic structure is valid
            errors.extend(cls._validate_product_info(config_data.get('product_info', {})))
            errors.extend(cls._validate_page_data(config_data.get('page_data', [])))
            
        return errors
    
    @classmethod
    def _validate_root_structure(cls, config_data: Dict[str, Any]) -> List[str]:
        """Validate root level structure"""
        errors = []
        
        for required_key in cls.REQUIRED_ROOT_KEYS:
            if required_key not in config_data:
                errors.append(f"Missing required key: '{required_key}'")
                
        page_num = config_data.get('page_num')
        if page_num != cls.EXPECTED_PAGE_COUNT:
            errors.append(f"Expected {cls.EXPECTED_PAGE_COUNT} pages, got {page_num}")
            
        return errors
    
    @classmethod
    def _validate_product_info(cls, product_info: Dict[str, Any]) -> List[str]:
        """Validate product information"""
        errors = []
        
        for required_key in cls.REQUIRED_PRODUCT_KEYS:
            if required_key not in product_info:
                errors.append(f"Missing product info key: '{required_key}'")
                
        return errors
    
    @classmethod
    def _validate_page_data(cls, page_data: List[Dict[str, Any]]) -> List[str]:
        """Validate page data structure"""
        errors = []
        
        if len(page_data) != cls.EXPECTED_PAGE_COUNT:
            errors.append(f"Expected {cls.EXPECTED_PAGE_COUNT} page entries, got {len(page_data)}")
            return errors
            
        for i, page in enumerate(page_data):
            page_errors = cls._validate_single_page(page, i)
            errors.extend([f"Page {i}: {error}" for error in page_errors])
            
        return errors
    
    @classmethod
    def _validate_single_page(cls, page: Dict[str, Any], page_index: int) -> List[str]:
        """Validate a single page configuration"""
        errors = []
        
        # Check basic page structure
        if 'page_index' not in page:
            errors.append("Missing 'page_index'")
        elif page['page_index'] != page_index:
            errors.append(f"Page index mismatch: expected {page_index}, got {page['page_index']}")
            
        # Validate custom LED pages (5, 6, 7) more strictly
        if page_index >= 5:
            errors.extend(cls._validate_led_page(page))
            
        return errors
    
    @classmethod
    def _validate_led_page(cls, page: Dict[str, Any]) -> List[str]:
        """Validate LED page with frame data"""
        errors = []
        
        # Check for frame data
        frames_data = page.get('frames', {})
        keyframes_data = page.get('keyframes', {})
        
        if frames_data.get('valid', 0) == 1:
            errors.extend(cls._validate_frame_data(frames_data))
        elif keyframes_data.get('valid', 0) == 1:
            errors.extend(cls._validate_frame_data(keyframes_data))
        else:
            errors.append("No valid frame data found")
            
        return errors
    
    @classmethod
    def _validate_frame_data(cls, frame_data: Dict[str, Any]) -> List[str]:
        """Validate frame data structure"""
        errors = []
        
        frame_list = frame_data.get('frame_data', [])
        frame_num = frame_data.get('frame_num', 0)
        
        if len(frame_list) != frame_num:
            errors.append(f"Frame count mismatch: declared {frame_num}, found {len(frame_list)}")
            
        for i, frame in enumerate(frame_list):
            frame_errors = cls._validate_single_frame(frame, i)
            errors.extend([f"Frame {i}: {error}" for error in frame_errors])
            
        return errors
    
    @classmethod
    def _validate_single_frame(cls, frame: Dict[str, Any], frame_index: int) -> List[str]:
        """Validate a single frame"""
        errors = []
        
        if 'frame_index' not in frame:
            errors.append("Missing 'frame_index'")
        elif frame['frame_index'] != frame_index:
            errors.append(f"Frame index mismatch: expected {frame_index}, got {frame['frame_index']}")
            
        rgb_values = frame.get('frame_RGB', [])
        expected_rgb_count = 200  # 40x5 LED grid
        
        if len(rgb_values) != expected_rgb_count:
            errors.append(f"Expected {expected_rgb_count} RGB values, got {len(rgb_values)}")
            
        # Validate RGB color format (sample first few)
        for i, color in enumerate(rgb_values[:10]):  # Check first 10 colors
            if not isinstance(color, str) or not cls.RGB_COLOR_PATTERN.match(color):
                errors.append(f"Invalid RGB color format at index {i}: '{color}'")
                break  # Don't spam errors
                
        return errors
    
    @classmethod
    def is_valid_configuration(cls, config_data: Dict[str, Any]) -> bool:
        """Quick check if configuration is valid"""
        errors = cls.validate_configuration(config_data)
        return len(errors) == 0


class FrameValidator:
    """Validates LED frame data specifically"""
    
    LED_GRID_SIZE = 200  # 40x5
    
    @classmethod
    def validate_rgb_values(cls, rgb_values: List[str]) -> List[str]:
        """Validate RGB color values"""
        errors = []
        
        if len(rgb_values) != cls.LED_GRID_SIZE:
            errors.append(f"Expected {cls.LED_GRID_SIZE} RGB values, got {len(rgb_values)}")
            return errors
            
        for i, color in enumerate(rgb_values):
            if not isinstance(color, str):
                errors.append(f"RGB value at index {i} is not a string: {type(color)}")
            elif not ConfigurationValidator.RGB_COLOR_PATTERN.match(color):
                errors.append(f"Invalid RGB color format at index {i}: '{color}'")
                
        return errors
    
    @classmethod
    def are_valid_rgb_values(cls, rgb_values: List[str]) -> bool:
        """Quick check if RGB values are valid"""
        return len(cls.validate_rgb_values(rgb_values)) == 0