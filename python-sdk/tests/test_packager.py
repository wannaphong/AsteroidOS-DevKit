import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

from asteroidos.packager import ArArchive, IpkPackager


class TestPackager(unittest.TestCase):
    def test_ar_archive_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            archive_path = Path(tmp_dir) / "test.a"
            entries = [
                ("debian-binary", b"2.0\n", 0o100644),
                ("control.tar.gz", b"fake control content", 0o100644),
                ("data.tar.gz", b"fake data content with odd length!", 0o100644),
            ]

            ArArchive.create(archive_path, entries)
            self.assertTrue(archive_path.exists())

            # Verify with pure-python reader
            members = ArArchive.read(archive_path)
            self.assertEqual(members["debian-binary"], b"2.0\n")
            self.assertEqual(members["control.tar.gz"], b"fake control content")
            self.assertEqual(members["data.tar.gz"], b"fake data content with odd length!")

            # Verify with system GNU ar
            res = subprocess.run(["ar", "-t", str(archive_path)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)
            names = res.stdout.strip().splitlines()
            self.assertIn("debian-binary", names)
            self.assertIn("control.tar.gz", names)
            self.assertIn("data.tar.gz", names)

    def test_create_and_extract_ipk(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            ipk_path = Path(tmp_dir) / "sample-app-1.0.0.ipk"
            control = {
                "Package": "sample-app",
                "Version": "1.0.0",
                "Architecture": "core2-32",
                "Description": "Test application",
                "Maintainer": "dev@example.com",
            }
            files = [
                (b"#!/bin/sh\necho hello\n", "/usr/bin/sample-app", 0o755),
                (b"[Desktop Entry]\nName=Sample\n", "/usr/share/applications/sample-app.desktop", 0o644),
            ]

            IpkPackager.create_ipk(ipk_path, control, files)
            self.assertTrue(ipk_path.exists())

            # Read control
            read_ctrl = IpkPackager.read_control(ipk_path)
            self.assertEqual(read_ctrl["Package"], "sample-app")
            self.assertEqual(read_ctrl["Version"], "1.0.0")
            self.assertEqual(read_ctrl["Architecture"], "core2-32")

            # Extract IPK
            extract_dir = Path(tmp_dir) / "extracted"
            extracted_ctrl = IpkPackager.extract_ipk(ipk_path, extract_dir)
            self.assertEqual(extracted_ctrl["Package"], "sample-app")

            bin_file = extract_dir / "usr" / "bin" / "sample-app"
            desktop_file = extract_dir / "usr" / "share" / "applications" / "sample-app.desktop"

            self.assertTrue(bin_file.exists())
            self.assertTrue(desktop_file.exists())
            self.assertEqual(bin_file.read_text(), "#!/bin/sh\necho hello\n")


if __name__ == "__main__":
    unittest.main()

