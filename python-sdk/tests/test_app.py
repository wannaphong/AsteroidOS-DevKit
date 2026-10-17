from pathlib import Path
import tempfile
import unittest

from asteroidos.app import App, AppMetadata, AppType, Target
from asteroidos.packager import IpkPackager


class TestApp(unittest.TestCase):
    def test_metadata_normalization(self):
        meta = AppMetadata(name="My Awesome_App!")
        self.assertEqual(meta.name, "my-awesome-app")
        self.assertEqual(meta.title, "My Awesome App")

        app = App("asteroid-stopwatch")
        self.assertEqual(app.title, "Stopwatch")

    def test_generate_and_package_python_app(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            proj_dir = Path(tmp_dir) / "asteroid-stepcounter"
            app = App(
                name="asteroid-stepcounter",
                title="Steps",
                version="1.0.0",
                app_type=AppType.PYTHON_QML,
            )

            # Custom QML
            custom_qml = "import QtQuick\nItem { id: root }\n"
            app.set_main_qml(custom_qml)

            # Generate project
            app.generate_project(proj_dir)
            self.assertTrue((proj_dir / "main.py").exists())
            self.assertTrue((proj_dir / "main.qml").exists())
            self.assertEqual((proj_dir / "main.qml").read_text(), custom_qml)
            self.assertTrue((proj_dir / "asteroid.json").exists())

            # Package directly
            ipk_path = app.package(target=Target.ALL)
            self.assertTrue(ipk_path.exists())

            # Inspect package
            ctrl = IpkPackager.read_control(ipk_path)
            self.assertEqual(ctrl["Package"], "asteroid-stepcounter")
            self.assertEqual(ctrl["Architecture"], "all")
            self.assertIn("python3-core", ctrl["Depends"])

    def test_load_existing_project(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            proj_dir = Path(tmp_dir) / "asteroid-myloader"
            app1 = App(
                name="asteroid-myloader",
                title="Loader",
                version="2.0.1",
                center_color="#aabbcc",
                app_type=AppType.NATIVE_QML,
            )
            app1.generate_project(proj_dir)

            # Reload
            app2 = App.load(proj_dir)
            self.assertEqual(app2.name, "asteroid-myloader")
            self.assertEqual(app2.title, "Loader")
            self.assertEqual(app2.version, "2.0.1")
            self.assertEqual(app2.metadata.center_color, "#aabbcc")


if __name__ == "__main__":
    unittest.main()
