# Repo Notes for AI Sessions

- Interactive Python TUI tool that merges Custom LED pages (page_index 5–7) between CYBERBOARD R4 (Angry Miao keyboard) JSON config files.
- Stack: Python >=3.8, `rich` (terminal UI), `questionary` (prompts), `toml`. Packaged with setuptools via `pyproject.toml`; `mise.toml` pins `uv`.
- Status: active personal utility. Note: the root `CLAUDE.md` is partially outdated — it describes a single-file `cyberboard_merger.py` and bundled JSON themes; the code now lives as a package under `src/cyberboard_merger/` and no JSON files are committed (gitignored; runtime dirs `sources/` and `outputs/` per `config.toml`).
- Key directories:
  - `src/cyberboard_merger/main.py` — entry point (`cyberboard-merger` script)
  - `src/cyberboard_merger/core/` — merge logic + file handling
  - `src/cyberboard_merger/ui/` — rich display, prompts, LED animator (40x5 grid preview)
  - `src/cyberboard_merger/models/`, `utils/`, `config/` — data models, validators, settings loader
- Run: `uvx --from . cyberboard-merger` (use `uvx --refresh --from .` after code changes) or `pip install -e . && cyberboard-merger`.
- No tests, no CI, no LICENSE file.
