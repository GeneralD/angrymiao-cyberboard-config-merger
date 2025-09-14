# CYBERBOARD R4 Configuration Merger Tool

A command-line tool for merging custom LED configurations from multiple CYBERBOARD R4 JSON configuration files.

## Features

- **Rich Terminal UI**: Beautiful interface with boxes, colors, and animations
- **Alternate Screen Buffer**: Full-screen application experience like vim/htop - preserves your console history
- **LED Preview**: Real-time 40x5 LED animations (3 seconds each, synchronized with max frame count)
- **Interactive Navigation**: 
  - Number key shortcuts (1-9) for quick selection
  - Arrow keys for menu navigation
  - Back functionality (← Back) at every step
- **Flexible Mapping**: Choose which LED configurations to keep or replace
- **Safe Operations**: Option to save as new file or overwrite existing
- **Visual Feedback**: See before/after animated previews of your LED configurations

## Usage

**Recommended**: Use `uvx` for instant execution:

```bash
uvx --from . cyberboard-merger
```

### Development

When developing or after making code changes, use the `--refresh` flag to bypass uvx cache:

```bash
# Force refresh to apply code changes
uvx --refresh --from . cyberboard-merger

# Alternative: Clear all uv cache
uv cache clean

# Development mode (recommended for frequent changes)
pip install -e .
cyberboard-merger
```

**Note**: uvx caches builds for performance. Use `--refresh` when testing code modifications.

## Workflow

1. **Select Base File**: Choose your base configuration file
   - Animated preview of all Custom LEDs (3 seconds)
2. **Configure LED Mappings**: For each Custom LED (1-3):
   - View current base LED animation (3 seconds)
   - Choose to Keep Base or Replace
   - If replacing, select source file and view LED previews (3 seconds)
   - Use ← Back to navigate between steps
3. **Review Summary**: See mapping table and final animated preview (3 seconds)
4. **Save Configuration**: Choose to overwrite or save as new file
5. **Continue or Exit**: Option to perform another merge

## Controls

- **Number Keys (1-9)**: Quick selection of menu items
- **Arrow Keys**: Navigate menu options
- **Enter**: Confirm selection
- **← Back**: Return to previous step
- **Ctrl+C**: Exit application

## File Structure

The tool works with CYBERBOARD R4 JSON files containing:
- Page 0-4: System pages (battery, mosaic, time, etc.)
- Page 5-7: Custom LED configurations (Custom LED 1-3)

## LED Preview

The tool displays LED animations as a 40x5 grid using colored blocks (█) in your terminal:
- **3-second animations**: Each preview runs for exactly 3 seconds
- **Adaptive frame rate**: Speed automatically adjusts based on the animation with the most frames
- **True color support**: RGB values from JSON are displayed as actual colors
- **Multiple animations**: Up to 3 LEDs shown side-by-side

## User Experience

- **Full-screen mode**: Application runs in alternate screen buffer (like vim/htop)
- **Console preservation**: Your terminal history is completely preserved
- **Seamless navigation**: Back/forward through all configuration steps
- **Visual feedback**: Every selection shows immediate animated preview

## Requirements

- Python 3.6+
- Terminal with 256-color or TrueColor support
- CYBERBOARD R4 JSON configuration files

## Dependencies

- `rich>=13.0.0` - Rich terminal UI components
- `questionary>=2.0.0` - Interactive command line user interfaces  
- `toml>=0.10.2` - TOML configuration file support

## File Organization

- **Source files**: JSON configurations are read from the `source` directory
- **Output files**: New merged files are saved to the `output` directory
- **Overwrite**: When overwriting, files are updated in the `source` directory
- **Auto-creation**: Output directory is automatically created if it doesn't exist