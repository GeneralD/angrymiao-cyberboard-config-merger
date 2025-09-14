# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains JSON configuration files for an RGB LED display system (CYBERBOARD R4). The files define animation pages, frames, and lighting configurations for a customizable LED keyboard product (product_id: "CB_XX").

## Project Structure

The repository consists of:
- **JSON configuration files**: Animation theme files (1_boom.json, 1_rainbow_circle.json, 2_gengar.json, 3_cyberpunk.json, 3_kuromi.json)
- **Layout configuration**: mac_layout.json (large file, >2.5MB)
- **Python CLI tool**: cyberboard_merger.py - Interactive merger for LED configurations
- **Modern dependencies**: pyproject.toml - Modern Python packaging with uvx support
- **Configuration**: config.toml - Directory settings for source and output
- **Documentation**: README.md - Comprehensive usage guide

## Configuration File Schema

Each animation configuration file contains:
- **product_info**: Product identification and addressing
- **page_num**: Total number of display pages (typically 8)
- **page_data**: Array of page configurations, each containing:
  - **valid**: Page enabled flag (0/1)
  - **page_index**: Page number (0-7)
  - **lightness**: Brightness level (0-100)
  - **speed_ms**: Animation speed in milliseconds
  - **color**: Default colors and RGB values
  - **word_page**: Text/unicode display configuration
  - **frames**: Standard animation frame data
  - **keyframes**: Keyframe animation data with RGB arrays

### Page Types (Based on Chinese Comments)
1. Page 0: Battery interface (电池界面)
2. Page 1: Mosaic interface (马赛克界面)
3. Page 2: Time interface (时间界面)
4. Page 3: Custom text interface (自定义文字界面)
5. Page 4: Animation interface (动画界面)
6. Page 5: Custom LED 1 (自定义界面1) - **Merger tool target**
7. Page 6: Custom LED 2 (自定义界面2) - **Merger tool target**
8. Page 7: Custom LED 3 (自定义界面3) - **Merger tool target**

## Working with Configuration Files

### Key Considerations
- Files can be very large (mac_layout.json exceeds 2.5MB)
- RGB values are stored as hex strings (e.g., "#FF0000")
- Frame data contains arrays of RGB values for pixel-by-pixel control
- Chinese comments indicate interface types and functionality

### Common Tasks
- To modify animations: Edit the `frame_data` arrays within the appropriate page's `frames` or `keyframes` section
- To adjust timing: Modify the `speed_ms` value for animation speed
- To change brightness: Adjust the `lightness` value (0-100)
- To enable/disable pages: Toggle the `valid` field (0/1)

## CLI Merger Tool

### cyberboard_merger.py
A comprehensive Python CLI tool for merging LED configurations between different theme files:

**Key Features:**
- Rich terminal UI with alternate screen buffer (vim-like experience)
- Interactive navigation with number keys and back functionality
- Real-time LED animation preview (40x5 grid, 3-second animations)
- Selective merging of Custom LED pages (5-7) between files
- Safe file operations (overwrite or new file)
- Automatic directory creation and configuration management

**Dependencies:**
- `rich>=13.0.0` - Terminal UI framework
- `questionary>=2.0.0` - Interactive prompts
- `toml>=0.10.2` - Configuration file support

**Modern Usage (Recommended):**
```bash
# Using uvx (no installation required)
uvx --from . cyberboard-merger

# Development/testing with cache refresh
uvx --refresh --from . cyberboard-merger
```

**Traditional Usage:**
```bash
# Direct execution
python3 cyberboard_merger.py

# Or install and use
pip install -e .
cyberboard-merger
```

### Configuration (config.toml)

The tool supports directory configuration via `config.toml`:

```toml
[directories]
source = "./sources"    # JSON files directory
output = "./outputs"    # Merged files output directory
```

**Features:**
- Automatic directory creation on first run
- Configurable source and output directories
- Fallback to current directory if config missing
- Runtime configuration reload capability

## Development Notes

- **Modern Python packaging**: Uses pyproject.toml instead of requirements.txt
- **uvx compatibility**: Supports instant execution without local installation
- **Configuration-focused**: Repository for CYBERBOARD R4 LED keyboard configurations
- **Large file handling**: mac_layout.json (>2.5MB) should be read with offset/limit parameters
- **Safe merging**: CLI tool provides safe LED configuration merging without manual JSON editing
- **Schema validation**: Ensure JSON validity and maintain existing schema structure
- **LED specifications**: All LED frame data uses 40x5 pixel arrays with hex color values (#RRGGBB)

### Development Workflow
1. **Code changes**: Use `uvx --refresh --from . cyberboard-merger` to bypass cache
2. **Configuration**: Modify `config.toml` for directory settings  
3. **Testing**: Tool automatically creates missing directories on first run
4. **Installation**: `pip install -e .` for development mode if needed