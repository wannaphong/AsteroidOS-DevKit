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

    def test_pip_dependencies_in_metadata_and_app(self):
        meta = AppMetadata(
            name="py-numpy-app",
            pip_dependencies=["numpy", "requests>=2.28"],
        )
        self.assertIn("numpy", meta.pip_dependencies)
        self.assertIn("requests>=2.28", meta.pip_dependencies)

        meta_dict = meta.to_dict()
        self.assertIn("pip_dependencies", meta_dict)

        loaded_meta = AppMetadata.from_dict(meta_dict)
        self.assertEqual(loaded_meta.pip_dependencies, ["numpy", "requests>=2.28"])

        app = App("asteroid-math-app", app_type=AppType.PYTHON_QML)
        app.add_pip_package("numpy")
        app.add_pip_dependency("scipy")
        self.assertEqual(app.pip_dependencies, ["numpy", "scipy"])

    def test_requirements_txt_loading_and_generation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            proj_dir = Path(tmp_dir) / "asteroid-req-app"
            app = App(
                name="asteroid-req-app",
                app_type=AppType.PYTHON_QML,
                pip_dependencies=["markupsafe", "urllib3"],
            )
            app.generate_project(proj_dir)

            # Check requirements.txt was written
            req_file = proj_dir / "requirements.txt"
            self.assertTrue(req_file.exists())
            req_content = req_file.read_text()
            self.assertIn("markupsafe", req_content)
            self.assertIn("urllib3", req_content)

            # Check loading loads requirements.txt
            loaded = App.load(proj_dir)
            self.assertIn("markupsafe", loaded.pip_dependencies)
            self.assertIn("urllib3", loaded.pip_dependencies)


if __name__ == "__main__":
    unittest.main()
