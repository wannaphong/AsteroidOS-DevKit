import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from asteroidos.cli import build_parser, main


class TestCLI(unittest.TestCase):
    def test_parser_new_arguments(self):
        parser = build_parser()
        args = parser.parse_args(["new", "my-app", "--title", "My Watch App", "--template", "python"])
        self.assertEqual(args.name, "my-app")
        self.assertEqual(args.title, "My Watch App")
        self.assertEqual(args.template, "python")

    def test_cli_new_command(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target_dir = Path(tmp_dir) / "test-cli-app"
            code = main(["new", "test-cli-app", "--dest", str(target_dir), "--template", "qml_cpp"])
            self.assertEqual(code, 0)
            self.assertTrue((target_dir / "CMakeLists.txt").exists())
            self.assertTrue((target_dir / "src" / "main.qml").exists())

    def test_cli_templates_command(self):
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = main(["templates"])
            self.assertEqual(code, 0)
            self.assertIn("qml_cpp", fake_out.getvalue())
            self.assertIn("python", fake_out.getvalue())

    def test_cli_doctor_command(self):
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            code = main(["doctor"])
            self.assertEqual(code, 0)
            self.assertIn("DevKit", fake_out.getvalue())

    def test_parser_pip_arguments(self):
        parser = build_parser()
        args_build = parser.parse_args(["build", "my-app", "--pip-package", "numpy", "--pip-package", "requests"])
        self.assertEqual(args_build.pip_packages, ["numpy", "requests"])

        args_pkg = parser.parse_args(["package", "my-app", "--pip-package", "markupsafe", "--no-pip"])
        self.assertEqual(args_pkg.pip_packages, ["markupsafe"])
        self.assertTrue(args_pkg.no_pip)

    def test_cli_pip_list_command(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target_dir = Path(tmp_dir) / "test-py-app"
            code_new = main(["new", "test-py-app", "--dest", str(target_dir), "--template", "python"])
            self.assertEqual(code_new, 0)

            # Add requirements.txt
            (target_dir / "requirements.txt").write_text("numpy\nscipy\n", encoding="utf-8")

            with patch("sys.stdout", new=io.StringIO()) as fake_out:
                code_list = main(["pip", "list", str(target_dir)])
                self.assertEqual(code_list, 0)
                out = fake_out.getvalue()
                self.assertIn("numpy", out)
                self.assertIn("scipy", out)


if __name__ == "__main__":
    unittest.main()

