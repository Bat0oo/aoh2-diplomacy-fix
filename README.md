# AoH2 Diplomacy Fix — Relations Stuck at 0 Bug

![Tests](https://img.shields.io/badge/tests-35%20passed-brightgreen) ![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

Fix for the **Age of History II diplomacy bug** where all country relations are permanently stuck at `0` and cannot be changed. Works on any campaign length and any scenario.

> ✅ Always backs up your save before making any changes.  
> ✅ Use `--scan` to check if you're affected before committing to anything.  
> ✅ Use `--dry-run` to preview exactly what would change.

---

## Download

### Option A — Python script (all platforms)
Requires Python 3.10+. No external libraries needed.

```bash
git clone https://github.com/Bat0oo/aoh2-diplomacy-fix.git
cd aoh2-diplomacy-fix
```

### Option B — Windows .exe (no Python needed)
Download the latest `.exe` from the [Releases page](../../releases/latest) and run it directly.

---

## What causes the bug?

After many turns, AoH2 sets diplomatic relation values to `NaN` (Not a Number) — an invalid IEEE 754 float. Because NaN has special mathematical properties, all relation values appear as `0` and no longer respond to diplomacy actions.

This is a **known, unpatched bug** in Age of History II.

---

## Usage

### Step 1 — Check if your save is affected

```bash
python aoh2_diplomacy_fix.py --save-path "D:\Steam\steamapps\common\AoCII\saves\games\Earth\YOUR_SAVE" --scan
```

Output:
```
[SCAN MODE] No files will be modified.

  [AFFECTED]    243 NaN values    ..._2X
  [AFFECTED]    231 NaN values    ..._2X1
  [CLEAN]         0 NaN values    ..._2X2

Save IS affected by the NaN bug.
  2/11 files contain NaN values
  474 total NaN values found
```

### Step 2 — Preview what would change (optional)

```bash
python aoh2_diplomacy_fix.py --save-path "D:\Steam\steamapps\common\AoCII\saves\games\Earth\YOUR_SAVE" --dry-run
```

```
[DRY RUN] No files will be modified. Showing what would happen:

  [WOULD FIX] 243 NaN -> +10.0    ..._2X
  [WOULD FIX] 231 NaN -> +10.0    ..._2X1
  [SKIP]      no NaN found         ..._2X2

Dry run complete. Would replace 474 NaN values.
A backup would be created before any changes.
```

### Step 3 — Apply the fix

```bash
python aoh2_diplomacy_fix.py --save-path "D:\Steam\steamapps\common\AoCII\saves\games\Earth\YOUR_SAVE"
```

```
Backup saved to: BACKUP_20260527_014200

  [FIXED] 243 NaN -> +10.0    ..._2X
  [FIXED] 231 NaN -> +10.0    ..._2X1
  [OK]    no NaN found         ..._2X2

Done! Replaced 474 NaN values across 11 files.
Launch AoH2 and load your save — relations should be fixed.
```

---

## All options

| Argument | Description | Default |
|---|---|---|
| `--save-path` | Direct path to one save folder | — |
| `--saves-root` | Path to `saves/games` to list all saves | Auto-detect |
| `--value` | Replace NaN with `10` (+10.0) or `0` (neutral) | `10` |
| `--scan` | Check if save is affected, no changes made | off |
| `--dry-run` | Preview what would change, no changes made | off |

---

## Where are my save files?

**Windows (Steam):**
```
D:\Steam\steamapps\common\AoCII\saves\games\<Scenario>\<SaveName>\
```

**Android:**
```
/storage/emulated/0/Android/data/age.of.civilizations2.lukasz.jakowski/files/saves/games/
```
> See [Android instructions](#android) below.

---

## Android

The fix works on Android saves — the file format is identical. You just need to transfer files to a PC first.

1. Connect your phone via USB and enable **File Transfer (MTP)** mode
2. Navigate to `/Android/data/age.of.civilizations2.lukasz.jakowski/files/saves/games/`
3. Copy your save folder to your PC
4. Run the script on the copied folder
5. Copy the fixed files back to your phone (replace the originals)

> **Note:** On Android 11+, the `/Android/data/` folder may be restricted. Use a file manager app like **MiXplorer** or **Total Commander** to access it, or enable USB debugging.

---

## Building the .exe yourself

If you don't trust the pre-built release, you can build it from source:

```bash
pip install pyinstaller
pyinstaller --onefile aoh2_diplomacy_fix.py
```

The `.exe` will be in the `dist/` folder. It contains only the script and the Python runtime — nothing else.

---

## FAQ

**Will this corrupt my save?**
No. A timestamped backup is always created before any file is touched. If something goes wrong, copy the files from the `BACKUP_` folder back to your save folder.

**My relations are fixed but go back to 0 after a few turns — why?**
The bug can re-occur in very long campaigns. Run the script again after saving.

**What does `+10` mean?**
It sets the base relation value to +10 (slightly positive). Use `--value 0` for strict neutral.

**Does it work on iOS?**
iOS save files are harder to access (require iTunes backup extraction or a jailbreak), but the fix logic is identical once you have the files.

**I don't have Python — is there an .exe?**
Yes — check the [Releases page](../../releases/latest).

---

## Technical details

AoH2 stores relation values as 4-byte IEEE 754 big-endian floats.

| Bytes | Value |
|---|---|
| `7F C0 00 00` | `NaN` (broken — this is the bug) |
| `41 20 00 00` | `+10.0` (default replacement) |
| `00 00 00 00` | `0.0` |

You can verify with any [IEEE 754 converter](https://www.h-schmidt.net/FloatConverter/IEEE754.html).

---

## Transparency

Not sure what the script does? Read the full [line-by-line code explanation](CODE_EXPLAINED.md).

---

## Contributing

Found a bug? Want to add a feature? See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Credits

Fix method originally documented in the [Steam Community guide](https://steamcommunity.com/sharedfiles/filedetails/?id=3264095824).

## License

MIT
