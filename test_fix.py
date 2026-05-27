"""
Test suite for aoh2_diplomacy_fix.py

Run with:
  python test_fix.py
  python test_fix.py -v
"""

import os
import re
import sys
import math
import time
import shutil
import struct
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import aoh2_diplomacy_fix as fix


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_relation_data(nan_count: int, total_floats: int = 100) -> bytes:
    data = bytearray()
    for i in range(total_floats):
        data += fix.NAN_BYTES if i < nan_count else fix.PLUS10_BYTES
    return bytes(data)


def make_fake_save(tmp_dir: Path, save_name: str, file_specs: dict) -> Path:
    save_dir = tmp_dir / "games" / "Earth" / save_name
    save_dir.mkdir(parents=True)
    for suffix, nan_count in file_specs.items():
        (save_dir / f"{save_name}{suffix}").write_bytes(make_relation_data(nan_count))
    return save_dir


# ---------------------------------------------------------------------------
# Original tests
# ---------------------------------------------------------------------------

class TestScanFile(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_counts_nan_correctly(self):
        f = self.tmp / "test_2X"
        f.write_bytes(make_relation_data(nan_count=7, total_floats=20))
        self.assertEqual(fix.scan_file(f), 7)

    def test_zero_nan(self):
        f = self.tmp / "test_2X"
        f.write_bytes(make_relation_data(nan_count=0, total_floats=20))
        self.assertEqual(fix.scan_file(f), 0)

    def test_all_nan(self):
        f = self.tmp / "test_2X"
        f.write_bytes(make_relation_data(nan_count=50, total_floats=50))
        self.assertEqual(fix.scan_file(f), 50)

    def test_does_not_modify_file(self):
        f = self.tmp / "test_2X"
        original = make_relation_data(nan_count=5)
        f.write_bytes(original)
        fix.scan_file(f)
        self.assertEqual(f.read_bytes(), original)


class TestFixFile(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_replaces_nan_with_plus10(self):
        f = self.tmp / "test_2X"
        f.write_bytes(make_relation_data(nan_count=10, total_floats=20))
        count = fix.fix_file(f, fix.PLUS10_BYTES)
        self.assertEqual(count, 10)
        self.assertEqual(f.read_bytes().count(fix.NAN_BYTES), 0)

    def test_replaces_nan_with_zero(self):
        f = self.tmp / "test_2X"
        f.write_bytes(make_relation_data(nan_count=5, total_floats=10))
        fix.fix_file(f, fix.ZERO_BYTES)
        self.assertEqual(f.read_bytes().count(fix.NAN_BYTES), 0)

    def test_returns_correct_count(self):
        f = self.tmp / "test_2X"
        f.write_bytes(make_relation_data(nan_count=13, total_floats=50))
        self.assertEqual(fix.fix_file(f, fix.PLUS10_BYTES), 13)

    def test_does_not_touch_clean_file(self):
        f = self.tmp / "test_2X"
        original = make_relation_data(nan_count=0, total_floats=20)
        f.write_bytes(original)
        self.assertEqual(fix.fix_file(f, fix.PLUS10_BYTES), 0)
        self.assertEqual(f.read_bytes(), original)

    def test_does_not_corrupt_valid_values(self):
        """Valid +10.0 values must survive the fix unchanged."""
        f = self.tmp / "test_2X"
        data = fix.NAN_BYTES + fix.PLUS10_BYTES + fix.NAN_BYTES
        f.write_bytes(data)
        fix.fix_file(f, fix.PLUS10_BYTES)
        result = f.read_bytes()
        self.assertEqual(result.count(fix.PLUS10_BYTES), 3)
        self.assertEqual(result.count(fix.NAN_BYTES), 0)


class TestBackupFiles(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_backup_created(self):
        f = self.tmp / "save_2X"
        f.write_bytes(b"\x00" * 16)
        backup_dir = fix.backup_files([f], self.tmp)
        self.assertTrue(backup_dir.exists())
        self.assertTrue((backup_dir / "save_2X").exists())

    def test_backup_content_matches_original(self):
        original = make_relation_data(nan_count=5)
        f = self.tmp / "save_2X"
        f.write_bytes(original)
        backup_dir = fix.backup_files([f], self.tmp)
        self.assertEqual((backup_dir / "save_2X").read_bytes(), original)

    def test_backup_name_has_timestamp(self):
        f = self.tmp / "save_2X"
        f.write_bytes(b"\x00" * 4)
        backup_dir = fix.backup_files([f], self.tmp)
        self.assertTrue(backup_dir.name.startswith("BACKUP_"))

    def test_original_not_modified_by_backup(self):
        original = make_relation_data(nan_count=3)
        f = self.tmp / "save_2X"
        f.write_bytes(original)
        fix.backup_files([f], self.tmp)
        self.assertEqual(f.read_bytes(), original)


class TestFindRelationFiles(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _make_file(self, name):
        p = self.tmp / name
        p.write_bytes(b"\x00" * 4)
        return p

    def test_finds_2x_files(self):
        for name in ["save_2X", "save_2X1", "save_2X2", "save_2X10"]:
            self._make_file(name)
        self.assertEqual(len(fix.find_relation_files(self.tmp)), 4)

    def test_ignores_other_files(self):
        self._make_file("save_2X")
        self._make_file("save.json")
        self._make_file("save_1")
        self._make_file("unrelated.txt")
        found = fix.find_relation_files(self.tmp)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].name, "save_2X")

    def test_case_insensitive(self):
        self._make_file("save_2x")
        self._make_file("save_2X1")
        self.assertEqual(len(fix.find_relation_files(self.tmp)), 2)

    def test_ignores_backup_folder(self):
        self._make_file("save_2X")
        backup = self.tmp / "BACKUP_20260527"
        backup.mkdir()
        (backup / "save_2X").write_bytes(b"\x00" * 4)
        self.assertEqual(len(fix.find_relation_files(self.tmp)), 1)


class TestEndToEnd(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.save_dir = make_fake_save(
            self.tmp, "TestSave123",
            {"_2X": 50, "_2X1": 30, "_2X2": 0}
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_scan_detects_nan(self):
        rel_files = fix.find_relation_files(self.save_dir)
        self.assertEqual(sum(fix.scan_file(f) for f in rel_files), 80)

    def test_scan_does_not_modify(self):
        rel_files = fix.find_relation_files(self.save_dir)
        original = {f: f.read_bytes() for f in rel_files}
        for f in rel_files:
            fix.scan_file(f)
        for f in rel_files:
            self.assertEqual(f.read_bytes(), original[f])

    def test_full_fix_workflow(self):
        rel_files = fix.find_relation_files(self.save_dir)
        backup_dir = fix.backup_files(rel_files, self.save_dir)
        self.assertTrue(backup_dir.exists())
        total = sum(fix.fix_file(f, fix.PLUS10_BYTES) for f in rel_files)
        self.assertEqual(total, 80)
        self.assertEqual(sum(fix.scan_file(f) for f in rel_files), 0)
        backed = (backup_dir / "TestSave123_2X").read_bytes()
        self.assertEqual(backed.count(fix.NAN_BYTES), 50)

    def test_clean_file_untouched_after_fix(self):
        rel_files = fix.find_relation_files(self.save_dir)
        clean = next(f for f in rel_files if f.name.endswith("_2X2"))
        original = clean.read_bytes()
        fix.fix_file(clean, fix.PLUS10_BYTES)
        self.assertEqual(clean.read_bytes(), original)


# ---------------------------------------------------------------------------
# Negative / edge case tests
# ---------------------------------------------------------------------------

class TestBadData(unittest.TestCase):
    """Feed the script broken, weird, or unexpected input."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_empty_file(self):
        """Empty file — should not crash, return 0."""
        f = self.tmp / "save_2X"
        f.write_bytes(b"")
        self.assertEqual(fix.fix_file(f, fix.PLUS10_BYTES), 0)
        self.assertEqual(f.read_bytes(), b"")

    def test_random_bytes_no_nan(self):
        """Random binary data without NaN — untouched."""
        f = self.tmp / "save_2X"
        original = os.urandom(256).replace(fix.NAN_BYTES, b"\x00\x00\x00\x00")
        f.write_bytes(original)
        self.assertEqual(fix.fix_file(f, fix.PLUS10_BYTES), 0)
        self.assertEqual(f.read_bytes(), original)

    def test_partial_nan_bytes_not_replaced(self):
        """Only 3 of the 4 NaN bytes — must NOT be replaced."""
        f = self.tmp / "save_2X"
        partial = bytes([0x7F, 0xC0, 0x00])  # missing last 0x00
        f.write_bytes(partial)
        fix.fix_file(f, fix.PLUS10_BYTES)
        self.assertEqual(f.read_bytes(), partial)

    def test_nan_at_start_of_file(self):
        """NaN at very beginning of file."""
        f = self.tmp / "save_2X"
        f.write_bytes(fix.NAN_BYTES + fix.PLUS10_BYTES * 10)
        self.assertEqual(fix.fix_file(f, fix.PLUS10_BYTES), 1)
        self.assertEqual(f.read_bytes().count(fix.NAN_BYTES), 0)

    def test_nan_at_end_of_file(self):
        """NaN at very end of file."""
        f = self.tmp / "save_2X"
        f.write_bytes(fix.PLUS10_BYTES * 10 + fix.NAN_BYTES)
        self.assertEqual(fix.fix_file(f, fix.PLUS10_BYTES), 1)
        self.assertEqual(f.read_bytes().count(fix.NAN_BYTES), 0)

    def test_entire_file_is_nan(self):
        """Worst case — every single value is NaN."""
        f = self.tmp / "save_2X"
        f.write_bytes(fix.NAN_BYTES * 1000)
        self.assertEqual(fix.fix_file(f, fix.PLUS10_BYTES), 1000)
        self.assertEqual(f.read_bytes().count(fix.NAN_BYTES), 0)

    def test_large_file(self):
        """~3.5 MB file — same size as real _2X save file."""
        f = self.tmp / "save_2X"
        data = (fix.NAN_BYTES * 500 + fix.PLUS10_BYTES * 500) * 400
        f.write_bytes(data)
        count = fix.fix_file(f, fix.PLUS10_BYTES)
        self.assertEqual(count, 200000)
        self.assertEqual(f.read_bytes().count(fix.NAN_BYTES), 0)

    def test_backup_survives_after_fix(self):
        """Backup must keep original NaN data after fix is applied."""
        f = self.tmp / "save_2X"
        f.write_bytes(fix.NAN_BYTES * 10 + fix.PLUS10_BYTES * 10)
        backup_dir = fix.backup_files([f], self.tmp)
        fix.fix_file(f, fix.PLUS10_BYTES)
        self.assertEqual(f.read_bytes().count(fix.NAN_BYTES), 0)
        self.assertEqual((backup_dir / "save_2X").read_bytes().count(fix.NAN_BYTES), 10)

    def test_two_backups_dont_overwrite(self):
        """Running fix twice creates two separate backup folders."""
        f = self.tmp / "save_2X"
        f.write_bytes(fix.NAN_BYTES * 5)
        b1 = fix.backup_files([f], self.tmp)
        time.sleep(1.1)
        b2 = fix.backup_files([f], self.tmp)
        self.assertNotEqual(b1, b2)
        self.assertTrue(b1.exists())
        self.assertTrue(b2.exists())

    def test_empty_save_folder(self):
        """Folder with no _2X files — return empty list, no crash."""
        empty = self.tmp / "empty"
        empty.mkdir()
        self.assertEqual(fix.find_relation_files(empty), [])

    def test_folder_with_no_matching_files(self):
        """Save folder exists but contains only json/numbered files."""
        (self.tmp / "save.json").write_bytes(b"{}")
        (self.tmp / "save_1").write_bytes(b"\x00" * 4)
        (self.tmp / "save_3").write_bytes(b"\x00" * 4)
        self.assertEqual(fix.find_relation_files(self.tmp), [])


class TestByteConstants(unittest.TestCase):
    """Verify our byte constants are what we claim they are."""

    def test_nan_bytes_are_ieee754_nan(self):
        value = struct.unpack(">f", fix.NAN_BYTES)[0]
        self.assertTrue(math.isnan(value), f"Expected NaN, got {value}")

    def test_plus10_bytes_are_10(self):
        value = struct.unpack(">f", fix.PLUS10_BYTES)[0]
        self.assertAlmostEqual(value, 10.0, places=5)

    def test_zero_bytes_are_zero(self):
        value = struct.unpack(">f", fix.ZERO_BYTES)[0]
        self.assertEqual(value, 0.0)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    verbosity = 2 if "-v" in sys.argv else 1
    print("=" * 58)
    print("   AoH2 Diplomacy Fix — Test Suite")
    print("=" * 58)
    print()
    suite = unittest.TestSuite()
    for cls in [
        TestScanFile,
        TestFixFile,
        TestBackupFiles,
        TestFindRelationFiles,
        TestEndToEnd,
        TestBadData,
        TestByteConstants,
    ]:
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(cls))
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
