# Execution Scripts

Deterministic Python scripts that do the actual work.

## Rules

1. **Check here first** before writing a new script — one may already exist.
2. Scripts must be **self-contained**: load env vars from `.env`, accept CLI args, produce predictable output.
3. Comment generously — explain *why*, not just *what*.
4. Write to `.tmp/` for any intermediate files; never hardcode absolute paths.
5. After fixing a bug, update the corresponding directive with the lesson learned.

## Naming convention

`<verb>_<noun>.py` — mirrors the directive it belongs to.  
e.g. `scrape_single_site.py`, `generate_slides.py`

## Running a script

```bash
python execution/<script_name>.py [args]
```

Env vars are loaded via `python-dotenv`:

```python
from dotenv import load_dotenv
load_dotenv()
```
