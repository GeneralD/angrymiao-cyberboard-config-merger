"""LED data models and operations"""

from typing import Dict, List, Any, Optional
import copy


class LEDFrame:
    """Represents a single LED frame"""
    
    def __init__(self, frame_data: Dict[str, Any]):
        self.frame_data = frame_data
        
    @property
    def rgb_values(self) -> List[str]:
        """Get RGB values for this frame"""
        return self.frame_data.get('frame_RGB', [])
    
    @property
    def frame_index(self) -> int:
        """Get frame index"""
        return self.frame_data.get('frame_index', 0)
    
    def set_frame_index(self, index: int) -> None:
        """Set frame index"""
        self.frame_data['frame_index'] = index


class LEDPage:
    """Represents an LED page configuration"""
    
    def __init__(self, page_data: Dict[str, Any]):
        self.page_data = copy.deepcopy(page_data)
        
    @property
    def is_valid(self) -> bool:
        """Check if page is valid"""
        return self.page_data.get('valid', 0) == 1
    
    @property
    def page_index(self) -> int:
        """Get page index"""
        return self.page_data.get('page_index', 0)
    
    def set_page_index(self, index: int) -> None:
        """Set page index"""
        self.page_data['page_index'] = index
    
    def get_frames(self) -> List[LEDFrame]:
        """Get LED frames from page data"""
        frames_data = self.page_data.get('frames', {})
        if frames_data.get('valid', 0) == 0:
            frames_data = self.page_data.get('keyframes', {})
            
        frame_list = frames_data.get('frame_data', [])
        return [LEDFrame(frame_data) for frame_data in frame_list]
    
    def get_frame_count(self) -> int:
        """Get number of frames"""
        return len(self.get_frames())
    
    def get_rgb_data(self) -> List[List[str]]:
        """Get all RGB frame data"""
        frames = self.get_frames()
        return [frame.rgb_values for frame in frames if len(frame.rgb_values) == 200]  # 40x5 LED grid


class LEDConfiguration:
    """Represents complete LED configuration data"""
    
    def __init__(self, config_data: Dict[str, Any]):
        self.config_data = copy.deepcopy(config_data)
        
    @property
    def product_info(self) -> Dict[str, Any]:
        """Get product information"""
        return self.config_data.get('product_info', {})
    
    @property
    def page_count(self) -> int:
        """Get total number of pages"""
        return self.config_data.get('page_num', 8)
    
    def get_page(self, index: int) -> Optional[LEDPage]:
        """Get page by index"""
        page_data_list = self.config_data.get('page_data', [])
        if 0 <= index < len(page_data_list):
            return LEDPage(page_data_list[index])
        return None
    
    def get_custom_led_pages(self) -> List[LEDPage]:
        """Get custom LED pages (indices 5, 6, 7)"""
        pages = []
        for i in range(5, 8):  # Custom LED pages 1, 2, 3
            page = self.get_page(i)
            if page:
                pages.append(page)
        return pages
    
    def set_page(self, index: int, page: LEDPage) -> None:
        """Set page at specific index"""
        if 0 <= index < len(self.config_data.get('page_data', [])):
            page.set_page_index(index)
            self.config_data['page_data'][index] = page.page_data


class LEDMerger:
    """Handles LED frame merging operations"""
    
    @staticmethod
    def combine_pages(pages: List[LEDPage]) -> LEDPage:
        """Combine multiple LED pages into one"""
        if not pages:
            raise ValueError("No pages provided for combination")
        
        # Start with the first page as base
        combined = copy.deepcopy(pages[0])
        
        # Determine which frame structure to use
        frames_key = 'frames' if combined.page_data.get('frames', {}).get('valid', 0) == 1 else 'keyframes'
        combined_frames = combined.page_data.get(frames_key, {})
        combined_frame_list = list(combined_frames.get('frame_data', []))
        
        # Add frames from remaining pages
        for page in pages[1:]:
            frames_data = page.page_data.get('frames', {})
            if frames_data.get('valid', 0) == 0:
                frames_data = page.page_data.get('keyframes', {})
            
            frame_list = frames_data.get('frame_data', [])
            combined_frame_list.extend(frame_list)
        
        # Renumber frame indices
        for idx, frame in enumerate(combined_frame_list):
            frame['frame_index'] = idx
        
        # Update the combined frame data
        combined_frames['frame_data'] = combined_frame_list
        combined_frames['frame_num'] = len(combined_frame_list)
        combined.page_data[frames_key] = combined_frames
        
        return combined