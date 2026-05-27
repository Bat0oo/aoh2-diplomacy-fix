# Changelog

---

## [1.1.0] - 2026-05-28

### Added
- `--scan` mode: check if save is affected without modifying anything
- `--dry-run` mode: preview what would change before applying the fix
- Interactive menu when running as `.exe` or without arguments
- `Press Enter to exit` so window doesn't close before you read output
- Smart Steam detection via Windows registry (works on any drive/install path)
- Multi-library support: finds AoH2 across multiple Steam library folders
- Manual path fallback: asks user to paste path if auto-detection fails
- `test_fix.py`: 35-test suite covering normal and bad data scenarios
- `build.bat`: one-click `.exe` build via PyInstaller
- `CODE_EXPLAINED.md`: line-by-line explanation for skeptical users
- `CONTRIBUTING.md`: bug reporting and contribution guidelines
- Android save file instructions in README

### Changed
- Fix logic split into `run_fix()`, `run_scan()`, `run_dry_run()` for clarity
- `scan_file()` separated from `fix_file()` — read-only vs write, explicit
- Confirmation prompt (`y/n`) before applying fix in interactive mode

---

## [1.0.0] - 2026-05-27

### Added
- Initial release
- Replaces all NaN (`7F C0 00 00`) in `_2X*` relation files with `+10.0`
- Auto-detection of common AoCII Steam install paths
- Interactive save picker
- Automatic timestamped backup before any modification
- `--value` option: `+10.0` or `0.0`
- `--save-path` and `--saves-root` arguments
