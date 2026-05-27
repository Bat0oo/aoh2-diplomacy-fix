# Code Explanation — aoh2_diplomacy_fix.py

This document explains every part of the script in plain English.  
No programming knowledge required. If anything seems suspicious or unclear, this is your reference.

**Short summary of what the script does:**
1. Finds your AoH2 save folder
2. Makes a full backup of the relation files
3. Opens each file as raw bytes and replaces `NaN` values with `+10.0`
4. Reports what it changed

The script does **not** connect to the internet, does **not** collect any data, and does **not** touch anything outside the save folder you point it to.

---

## Imports (lines 12–17)

```python
import os
import re
import shutil
import argparse
from datetime import datetime
from pathlib import Path
```

These are all **standard Python libraries** — they ship with Python itself, nothing is downloaded.

| Library | What it's used for |
|---|---|
| `os` | Read Windows environment variables (e.g. `LOCALAPPDATA`) to find Steam |
| `re` | Match filenames using a pattern (e.g. `_2X`, `_2X1`, `_2X10`) |
| `shutil` | Copy files to the backup folder |
| `argparse` | Handle command-line arguments like `--save-path`, `--dry-run`, `--scan` |
| `datetime` | Generate a timestamp for the backup folder name |
| `pathlib.Path` | Work with file and folder paths in a safe, cross-platform way |

---

## Byte constants (lines 19–21)

```python
NAN_BYTES    = bytes([0x7F, 0xC0, 0x00, 0x00])  # NaN in IEEE 754 float
PLUS10_BYTES = bytes([0x41, 0x20, 0x00, 0x00])  # +10.0
ZERO_BYTES   = bytes([0x00, 0x00, 0x00, 0x00])  # 0.0
```

AoH2 stores relation values as **4-byte floating point numbers** (IEEE 754 standard).  
These are the raw byte representations of three specific values:

- `7F C0 00 00` — what `NaN` looks like in memory. NaN means "Not a Number" — an invalid value that breaks math operations. This is the bug.
- `41 20 00 00` — this is `+10.0`. A slightly positive starting relation. Safe default.
- `00 00 00 00` — this is `0.0`. Strict neutral. Use `--value 0` if you prefer this.

You can verify these yourself with any [IEEE 754 converter](https://www.h-schmidt.net/FloatConverter/IEEE754.html):
- Enter `NaN` → hex = `7FC00000`
- Enter `10` → hex = `41200000`

---

## File pattern (line 24)

```python
PATTERN = re.compile(r"_2X\d*$", re.IGNORECASE)
```

This defines which files the script will touch.  
It matches filenames that **end with** `_2X` followed by zero or more digits — so `_2X`, `_2X1`, `_2X2` ... `_2X10`, etc.

These are AoH2's **relation files** — they store the diplomatic values between every pair of civilizations. No other files are matched.

`re.IGNORECASE` means it also matches `_2x` (lowercase), just in case.

---

## Known save paths (lines 27–32)

```python
KNOWN_PATHS = [
    Path("D:/Steam/steamapps/common/AoCII/saves/games"),
    Path("C:/Steam/steamapps/common/AoCII/saves/games"),
    Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Steam/steamapps/common/AoCII/saves/games",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Age of History II/saves",
]
```

A list of common locations where AoH2 saves are stored. The script tries each one in order and uses the first that exists.

`os.environ.get(...)` reads Windows environment variables — built-in system variables that point to your user folders. No personal data is collected; they are only used to build a folder path.

---

## `find_default_saves()` (lines 35–39)

```python
def find_default_saves() -> Path | None:
    for p in KNOWN_PATHS:
        if p.exists():
            return p
    return None
```

Loops through `KNOWN_PATHS` and returns the first folder that actually exists on your system. If none are found, returns `None` and the script will ask you to provide the path manually.

---

## `find_relation_files()` (lines 42–43)

```python
def find_relation_files(save_dir: Path) -> list[Path]:
    return [f for f in save_dir.iterdir() if f.is_file() and PATTERN.search(f.stem)]
```

Lists every file inside your save folder and keeps only the ones whose name matches the `_2X` pattern.

`f.stem` is the filename without extension. `f.is_file()` ensures folders are skipped.  
**Only these specific files are ever read or written.**

---

## `backup_files()` (lines 46–53)

```python
def backup_files(files: list[Path], save_dir: Path) -> Path:
    """Always called before any file is modified."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = save_dir / f"BACKUP_{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.copy2(f, backup_dir / f.name)
    return backup_dir
```

**This function is always called before `fix_file()` — no file is ever modified without a backup existing first.**

- `ts` — current timestamp, e.g. `20260527_014200`
- `backup_dir` — creates a folder called `BACKUP_20260527_014200` inside your save folder
- `shutil.copy2(f, ...)` — copies each relation file into that backup folder, preserving metadata
- Returns the backup folder path so it can be displayed to you

---

## `scan_file()` (lines 56–58)

```python
def scan_file(path: Path) -> int:
    """Count NaN occurrences in a file without modifying it."""
    data = path.read_bytes()
    return data.count(NAN_BYTES)
```

**Read-only.** Reads the file as raw bytes and counts how many times the NaN byte sequence appears. Used by both `--scan` and `--dry-run` modes. The file is never written to.

---

## `fix_file()` (lines 61–67)

```python
def fix_file(path: Path, replace_with: bytes) -> int:
    """Replace all NaN bytes in file. Returns number of replacements."""
    data = path.read_bytes()
    count = data.count(NAN_BYTES)
    if count > 0:
        path.write_bytes(data.replace(NAN_BYTES, replace_with))
    return count
```

This is the core fix. Here's exactly what happens:

1. `path.read_bytes()` — reads the entire file as raw bytes into memory. Nothing is executed.
2. `data.count(NAN_BYTES)` — counts how many times `7F C0 00 00` appears
3. `if count > 0` — only writes back to disk if there's actually something to fix
4. `data.replace(NAN_BYTES, replace_with)` — replaces every `7F C0 00 00` with `41 20 00 00`
5. `path.write_bytes(...)` — writes the fixed data back to the same file
6. Returns the count so it can be shown in the output

If no NaN bytes are found, **the file is not touched at all.**

---

## `pick_save_dir()` (lines 70–86)

Used when you don't provide `--save-path` directly. Walks the saves folder and builds a numbered list for you to choose from. Only reads folder names — no file contents are accessed here.

---

## `run_scan()` (lines 89–107)

```python
def run_scan(save_dir: Path, rel_files: list[Path]):
```

Called when you pass `--scan`. Loops through all relation files using `scan_file()` (read-only) and reports which ones contain NaN values and how many. **Nothing is written. No backup is created.** Pure diagnostic mode.

---

## `run_dry_run()` (lines 110–125)

```python
def run_dry_run(save_dir: Path, rel_files: list[Path], replace_label: str):
```

Called when you pass `--dry-run`. Same as scan, but formats output as "would fix X NaN values" to simulate what the actual fix would do. **Nothing is written. No backup is created.** Lets you verify the script's behaviour before committing.

---

## `run_fix()` (lines 128–147)

```python
def run_fix(save_dir: Path, rel_files: list[Path], replace_bytes: bytes, replace_label: str):
```

The actual fix mode (default, no flags). Order of operations:

1. `backup_files()` — backup created first, no exceptions
2. Loop through each relation file with `fix_file()`
3. Print summary

---

## `main()` — argument parsing (lines 150–185)

Sets up five command-line options:

| Argument | Type | What it does |
|---|---|---|
| `--save-path` | Path | Skip the save picker, use this folder directly |
| `--saves-root` | Path | Override auto-detection |
| `--value` | `"10"` or `"0"` | Pick replacement value |
| `--dry-run` | flag (on/off) | Simulate without writing |
| `--scan` | flag (on/off) | Diagnose without writing |

`action="store_true"` for `--dry-run` and `--scan` means they're boolean switches — just adding the flag sets them to `True`. No value needed.

---

## `main()` — mode routing (lines 200–207)

```python
if args.scan:
    run_scan(save_dir, rel_files)
elif args.dry_run:
    run_dry_run(save_dir, rel_files, replace_label)
else:
    run_fix(save_dir, rel_files, replace_bytes, replace_label)
```

Simple decision tree: scan → dry-run → fix. If both `--scan` and `--dry-run` are passed, `--scan` takes priority.

---

## Entry point (last 2 lines)

```python
if __name__ == "__main__":
    main()
```

Standard Python pattern. `main()` only runs when you execute the script directly. It won't run if the file is imported as a module by something else.

---

## What the script does NOT do

- ❌ Does not connect to the internet
- ❌ Does not send or collect any data
- ❌ Does not touch any file outside your specified save folder
- ❌ Does not modify `.json` files, game executables, or any other save data
- ❌ Does not run any system commands
- ✅ Only reads and writes `_2X*` files inside the save folder you provide
- ✅ Always creates a backup before writing anything (`run_fix` only)
- ✅ `--scan` and `--dry-run` are fully read-only — zero writes, zero backups needed
