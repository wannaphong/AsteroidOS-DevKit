from pathlib import Path
import tempfile
import unittest

from asteroidos.templates import TemplateManager, render_template_string


class TestTemplates(unittest.TestCase):
    def test_render_template_string(self):
        tmpl = "Hello {{ name }}, welcome to {{ place }}! Empty: {{ non_existent }}"
        res = render_template_string(tmpl, {"name": "Asteroid", "place": "Smartwatch"})
        self.assertEqual(res, "Hello Asteroid, welcome to Smartwatch! Empty: ")

    def test_render_qml_cpp_template(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = Path(tmp_dir) / "test-app"
            ctx = {
                "app_name": "asteroid-test",
                "title": "Test App",
                "version": "1.2.3",
                "description": "Test description",
                "author": "tester",
                "icon": "ios-pulse-outline",
                "center_color": "#112233",
                "outer_color": "#445566",
            }
            files = TemplateManager.render_template("qml_cpp", ctx, dest)
            self.assertTrue(len(files) >= 5)

            cmake_file = dest / "CMakeLists.txt"
            self.assertTrue(cmake_file.exists())
            cmake_text = cmake_file.read_text()
            self.assertIn("asteroid-test", cmake_text)
            self.assertIn("1.2.3", cmake_text)

            main_qml = dest / "src" / "main.qml"
            self.assertTrue(main_qml.exists())
            self.assertIn("#112233", main_qml.read_text())

    def test_render_python_template(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = Path(tmp_dir) / "test-pyapp"
            ctx = {
                "app_name": "asteroid-pytest",
                "title": "Python Test App",
                "version": "0.5.0",
                "description": "Python test",
                "author": "tester",
                "icon": "ios-stopwatch-outline",
                "center_color": "#abcdef",
                "outer_color": "#123456",
            }
            files = TemplateManager.render_template("python", ctx, dest)
            self.assertTrue(len(files) >= 4)

            main_py = dest / "main.py"
            self.assertTrue(main_py.exists())
            self.assertIn("asteroid-pytest", main_py.read_text())

            runscript = dest / "runscript.sh"
            self.assertTrue(runscript.exists())
            self.assertIn("/usr/share/asteroid-pytest", runscript.read_text())


if __name__ == "__main__":
    unittest.main()

