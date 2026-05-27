# Changelog

All notable changes to this project will be documented here.

---

## [1.1.0] - 2026-05-27

### Added
- `--scan` mode: check if a save is affected by the NaN bug without modifying any files
- `--dry-run` mode: preview exactly what would change before applying the fix
- Android save file instructions in README
- `CONTRIBUTING.md`
- `CODE_EXPLAINED.md` — full line-by-line explanation of the script for non-technical users
- Windows `.exe` build instructions via PyInstaller

### Changed
- Refactored fix logic into `run_fix()`, `run_scan()`, `run_dry_run()` for clarity
- Renamed internal `fix_file()` scan path to `scan_file()` (read-only, explicit)
- README restructured: scan → dry-run → fix workflow order

---

## [1.0.0] - 2026-05-27

### Added
- Initial release
- Replaces all NaN (`7F C0 00 00`) values in `_2X*` relation files with `+10.0` (`41 20 00 00`)
- Auto-detection of common AoCII Steam install paths
- Interactive save picker when `--save-path` is not provided
- Automatic timestamped backup before any modification
- `--value` option to choose between `+10.0` and `0.0` as replacement
- `--save-path` and `--saves-root` arguments
