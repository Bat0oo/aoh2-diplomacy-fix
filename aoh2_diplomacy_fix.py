"""
AoH2 Diplomacy Fix - NaN Relations Bug

Run directly (double-click .exe or python script) for interactive mode.
Or use command-line arguments for scripting:

  python aoh2_diplomacy_fix.py --save-path "D:\\Steam\\...\\YOUR_SAVE"
  python aoh2_diplomacy_fix.py --save-path "D:\\Steam\\...\\YOUR_SAVE" --scan
  python aoh2_diplomacy_fix.py --save-path "D:\\Steam\\...\\YOUR_SAVE" --dry-run
  python aoh2_diplomacy_fix.py --value 0
"""

import os
import re
import sys
import shutil
import argparse
from datetime import datetime
from pathlib import Path

NAN_BYTES    = bytes([0x7F, 0xC0, 0x00, 0x00])  # NaN in IEEE 754 float
PLUS10_BYTES = bytes([0x41, 0x20, 0x00, 0x00])  # +10.0
ZERO_BYTES   = bytes([0x00, 0x00, 0x00, 0x00])  # 0.0

PATTERN = re.compile(r"_2X\d*$", re.IGNORECASE)

# True when running as a bundled .exe or double-clicked script (no CLI args)
IS_INTERACTIVE = len(sys.argv) == 1


# ---------------------------------------------------------------------------
# Save folder detection
# ---------------------------------------------------------------------------

def find_steam_path_from_registry() -> Path | None:
    """
    Ask Windows registry where Steam is installed.
    This works regardless of which drive or folder Steam is on.
    Returns the Steam root path (e.g. D:\\Steam), or None if not found.
    """
    try:
        import winreg
        # Steam writes its install path here on every Windows install
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "InstallPath")
        winreg.CloseKey(key)
        return Path(steam_path)
    except Exception:
        try:
            # Fallback: 32-bit registry path
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam")
            steam_path, _ = winreg.QueryValueEx(key, "InstallPath")
            winreg.CloseKey(key)
            return Path(steam_path)
        except Exception:
            return None


def find_all_steam_libraries(steam_root: Path) -> list[Path]:
    """
    Steam lets you install games across multiple drives (Steam Libraries).
    This reads libraryfolders.vdf to find all of them.
    Returns a list of all Steam library root paths.
    """
    libraries = [steam_root]

    vdf_path = steam_root / "steamapps" / "libraryfolders.vdf"
    if not vdf_path.exists():
        return libraries

    try:
        content = vdf_path.read_text(encoding="utf-8")
        # libraryfolders.vdf contains lines like:  "path"  "D:\\Games\\Steam"
        for match in re.finditer(r'"path"\s+"([^"]+)"', content):
            p = Path(match.group(1))
            if p.exists() and p not in libraries:
                libraries.append(p)
    except Exception:
        pass

    return libraries


def find_aoh2_saves(steam_libraries: list[Path]) -> list[Path]:
    """
    Search every Steam library for the AoH2 saves folder.
    AoH2 (Age of Civilizations II) has Steam App ID 598610.
    Returns all found saves/games paths.
    """
    # All known folder names AoH2 might be installed under
    aoh2_folder_names = [
        "AoCII",
        "Age of History II",
        "Age of Civilizations II",
    ]

    found = []
    for library in steam_libraries:
        for folder_name in aoh2_folder_names:
            saves = library / "steamapps" / "common" / folder_name / "saves" / "games"
            if saves.exists():
                found.append(saves)

    return found


def find_saves_non_steam() -> list[Path]:
    """
    Check non-Steam install locations (AppData, GOG, etc).
    """
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Age of History II" / "saves",
        Path(os.environ.get("APPDATA", "")) / "Age of History II" / "saves",
        Path(os.environ.get("LOCALAPPDATA", "")) / "AoCII" / "saves",
    ]
    return [p for p in candidates if p.exists()]


def find_all_saves_roots() -> list[Path]:
    """
    Master function: find every possible AoH2 saves location on this PC.
    1. Read Steam install path from Windows registry
    2. Find all Steam library folders (multi-drive setups)
    3. Search each library for AoH2
    4. Also check non-Steam locations
    """
    results = []

    steam_root = find_steam_path_from_registry()
    if steam_root:
        libraries = find_all_steam_libraries(steam_root)
        results.extend(find_aoh2_saves(libraries))

    results.extend(find_saves_non_steam())

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for p in results:
        if p not in seen:
            seen.add(p)
            unique.append(p)

    return unique


# ---------------------------------------------------------------------------
# Core file operations
# ---------------------------------------------------------------------------

def find_relation_files(save_dir: Path) -> list[Path]:
    return [f for f in save_dir.iterdir() if f.is_file() and PATTERN.search(f.stem)]


def backup_files(files: list[Path], save_dir: Path) -> Path:
    """Always called before any file is modified."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = save_dir / f"BACKUP_{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.copy2(f, backup_dir / f.name)
    return backup_dir


def scan_file(path: Path) -> int:
    """Count NaN occurrences without modifying the file."""
    return path.read_bytes().count(NAN_BYTES)


def fix_file(path: Path, replace_with: bytes) -> int:
    """Replace all NaN bytes. Returns number of replacements."""
    data = path.read_bytes()
    count = data.count(NAN_BYTES)
    if count > 0:
        path.write_bytes(data.replace(NAN_BYTES, replace_with))
    return count


# ---------------------------------------------------------------------------
# Save directory picker
# ---------------------------------------------------------------------------

def pick_save_dir_from_root(saves_root: Path) -> Path | None:
    candidates = []
    for item in sorted(saves_root.iterdir()):
        if item.is_dir():
            subs = [s for s in item.iterdir() if s.is_dir()]
            candidates.extend(subs if subs else [item])

    if not candidates:
        return None

    print("\nFound saves:")
    for i, d in enumerate(candidates):
        print(f"  [{i+1}] {d.relative_to(saves_root)}")

    choice = input("\nWhich save? (number): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(candidates):
        return candidates[int(choice) - 1]
    return None


def resolve_save_dir(save_path: Path | None, saves_root: Path | None) -> Path | None:
    """Resolve save directory — from arg, auto-detect, or ask user."""

    # 1. Direct path provided via --save-path
    if save_path:
        if not save_path.exists():
            print(f"\n[ERROR] Folder not found: {save_path}")
            return None
        return save_path

    # 2. --saves-root provided explicitly
    if saves_root:
        if not saves_root.exists():
            print(f"\n[ERROR] Folder not found: {saves_root}")
            return None
        print(f"\nSaves folder: {saves_root}")
        return pick_save_dir_from_root(saves_root)

    # 3. Auto-detect via registry + library scan
    print("\nSearching for AoH2 saves...")
    found_roots = find_all_saves_roots()

    if len(found_roots) == 1:
        print(f"Found: {found_roots[0]}")
        return pick_save_dir_from_root(found_roots[0])

    if len(found_roots) > 1:
        # Multiple installs (e.g. Steam + non-Steam)
        print(f"Found {len(found_roots)} AoH2 install location(s):")
        for i, r in enumerate(found_roots):
            print(f"  [{i+1}] {r}")
        choice = input("\nWhich location? (number): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(found_roots):
            root = found_roots[int(choice) - 1]
            return pick_save_dir_from_root(root)
        return None

    # 4. Nothing found — ask user to paste path manually
    if IS_INTERACTIVE:
        print("\n[!] Could not find AoH2 automatically.")
        print("    Please paste the path to your saves/games folder.")
        print(r"    Example: D:\Steam\steamapps\common\AoCII\saves\games")
        print()
        raw = input("Path: ").strip().strip('"')
        p = Path(raw)
        if not p.exists():
            print(f"\n[ERROR] Folder not found: {p}")
            return None
        return pick_save_dir_from_root(p)
    else:
        print("\n[ERROR] Could not auto-detect saves folder.")
        print(r'Use: --saves-root "D:\Steam\steamapps\common\AoCII\saves\games"')
        return None


# ---------------------------------------------------------------------------
# Run modes
# ---------------------------------------------------------------------------

def run_scan(rel_files: list[Path]):
    print("\n[SCAN] Checking for NaN values — no files will be modified.\n")
    total = 0
    for f in sorted(rel_files):
        count = scan_file(f)
        tag = f"[AFFECTED]  {count:>6} NaN" if count > 0 else "[CLEAN]          0 NaN"
        print(f"  {tag}    {f.name}")
        total += count

    print("\n" + "=" * 58)
    if total > 0:
        affected = sum(1 for f in rel_files if scan_file(f) > 0)
        print(f"Save IS affected. {total} NaN values in {affected}/{len(rel_files)} files.")
        print("Choose option [2] or [3] from the menu to fix it.")
    else:
        print("Save is NOT affected. All relation values look valid.")
    print("=" * 58)


def run_dry_run(rel_files: list[Path], replace_label: str):
    print("\n[DRY RUN] Simulating fix — no files will be modified.\n")
    total = 0
    for f in sorted(rel_files):
        count = scan_file(f)
        tag = f"[WOULD FIX]  {count} NaN -> {replace_label}" if count > 0 else "[SKIP]       no NaN found"
        print(f"  {tag:<38} {f.name}")
        total += count

    print("\n" + "=" * 58)
    if total > 0:
        print(f"Would replace {total} NaN values.")
        print("A backup would be created automatically before any changes.")
        print("Choose option [3] from the menu to apply the fix.")
    else:
        print("Nothing to fix — no NaN values found.")
    print("=" * 58)


def run_fix(save_dir: Path, rel_files: list[Path], replace_bytes: bytes, replace_label: str):
    backup_dir = backup_files(rel_files, save_dir)
    print(f"\nBackup saved to: {backup_dir.name}")
    print("\nFixing files:")
    total = 0
    for f in sorted(rel_files):
        count = fix_file(f, replace_bytes)
        tag = f"[FIXED]  {count} NaN -> {replace_label}" if count > 0 else "[OK]     no NaN found"
        print(f"  {tag:<35} {f.name}")
        total += count

    print("\n" + "=" * 58)
    if total > 0:
        print(f"Done! Replaced {total} NaN values.")
        print("Launch AoH2 and load your save — relations should be fixed.")
    else:
        print("No NaN values found. Save may not be affected by this bug.")
    print(f"Backup kept at: {backup_dir.name}")
    print("=" * 58)


# ---------------------------------------------------------------------------
# Interactive menu (shown when double-clicking .exe)
# ---------------------------------------------------------------------------

def interactive_menu(save_dir: Path, rel_files: list[Path]):
    while True:
        print(f"\nSave: {save_dir.name}")
        print(f"Relation files found: {len(rel_files)}")
        print()
        print("  [1] Scan    — check if save is affected (read-only)")
        print("  [2] Dry run — preview what would change (read-only)")
        print("  [3] Fix     — apply the fix (backup created first)")
        print("  [4] Exit")
        print()
        choice = input("Choose an option (1-4): ").strip()

        if choice == "1":
            run_scan(rel_files)
        elif choice == "2":
            print("\nReplace NaN with: [1] +10.0 (recommended)  [2] 0.0 (neutral)")
            v = input("Choice (1/2, default 1): ").strip()
            label = "0.0" if v == "2" else "+10.0"
            run_dry_run(rel_files, label)
        elif choice == "3":
            print("\nReplace NaN with: [1] +10.0 (recommended)  [2] 0.0 (neutral)")
            v = input("Choice (1/2, default 1): ").strip()
            rb = ZERO_BYTES if v == "2" else PLUS10_BYTES
            label = "0.0" if v == "2" else "+10.0"
            print()
            confirm = input("This will modify your save files (backup created first). Continue? (y/n): ").strip().lower()
            if confirm == "y":
                run_fix(save_dir, rel_files, rb, label)
            else:
                print("Cancelled.")
        elif choice == "4":
            break
        else:
            print("Invalid choice, try again.")

        if choice in ("1", "2", "3"):
            input("\nPress Enter to return to menu...")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def pause_exit(code: int = 0):
    if IS_INTERACTIVE:
        print("\nPress Enter to exit...")
        input()
    sys.exit(code)


def main():
    parser = argparse.ArgumentParser(description="AoH2 Diplomacy NaN Fix")
    parser.add_argument("--save-path", type=Path, default=None)
    parser.add_argument("--saves-root", type=Path, default=None)
    parser.add_argument("--value", choices=["10", "0"], default="10")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--scan", action="store_true")
    args = parser.parse_args()

    replace_bytes = PLUS10_BYTES if args.value == "10" else ZERO_BYTES
    replace_label = "+10.0" if args.value == "10" else "0.0"

    print("=" * 58)
    print("   AoH2 Diplomacy Fix — NaN Relations Bug")
    print("   github.com/Bat0oo/aoh2-diplomacy-fix")
    print("=" * 58)

    save_dir = resolve_save_dir(args.save_path, args.saves_root)
    if not save_dir:
        pause_exit(1)

    print(f"\nSave: {save_dir.name}")
    rel_files = find_relation_files(save_dir)

    if not rel_files:
        print(f"\n[INFO] No _2X relation files found in: {save_dir}")
        print("Make sure you selected the correct save folder.")
        pause_exit(1)

    print(f"Relation files: {len(rel_files)} found.")

    if IS_INTERACTIVE:
        interactive_menu(save_dir, rel_files)
    elif args.scan:
        run_scan(rel_files)
    elif args.dry_run:
        run_dry_run(rel_files, replace_label)
    else:
        run_fix(save_dir, rel_files, replace_bytes, replace_label)

    pause_exit(0)


if __name__ == "__main__":
    main()
