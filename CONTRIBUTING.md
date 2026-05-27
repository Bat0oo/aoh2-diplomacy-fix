# Contributing to aoh2-diplomacy-fix

Thanks for wanting to help! This is a small focused tool, so contributions don't need to be big to be useful.

---

## Reporting a bug

Open an [issue](../../issues/new) and include:

1. Your OS and Python version (`python --version`)
2. The full command you ran
3. The full terminal output (copy-paste, don't screenshot)
4. What you expected to happen vs what actually happened

If your save is still broken after running the fix, also mention:
- How many turns into your campaign you are
- Which scenario (Earth, Europe, custom map, etc.)

---

## Suggesting a feature

Open an issue with the label `enhancement`. Describe what you want and why it would be useful. No need to write code first — discussion is welcome.

Good candidates:
- Android/iOS workflow improvements
- Support for other AoH2 save file quirks
- Better auto-detection for non-standard Steam install locations
- GUI version (tkinter or similar)

---

## Submitting a pull request

1. Fork the repo
2. Create a branch: `git checkout -b my-feature`
3. Make your changes
4. Test on at least one real save file
5. Submit a PR with a short description of what changed and why

Please keep PRs focused — one feature or fix per PR.

---

## Known areas that need work

- **iOS support** — save files require iTunes backup extraction. If you've done this manually and know the path, a doc update would be great.
- **Android 11+ restricted storage** — the `/Android/data/` path is locked on newer Android. Better instructions or a helper script would help.
- **`.exe` build automation** — currently manual via PyInstaller. A GitHub Actions workflow that builds and uploads to Releases on every tag would be ideal.
- **Re-occurrence detection** — the bug can come back after more turns. A mode that watches a save folder and alerts when NaN values appear again would be useful.

---

## Code style

- Standard Python, no external libraries
- Type hints on all function signatures
- Keep `scan_file()` and `fix_file()` strictly separated (read-only vs write)
- Any new mode should follow the `run_scan / run_dry_run / run_fix` pattern

---

## Questions?

Open an issue — no question is too small.
