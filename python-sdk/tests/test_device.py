import unittest
from asteroidos.app import Target
from asteroidos.device import Device


class TestDevice(unittest.TestCase):
    def test_for_target_defaults(self):
        emu_dev = Device.for_target(Target.EMULATOR)
        self.assertEqual(emu_dev.host, "localhost")
        self.assertEqual(emu_dev.port, 2222)
        self.assertEqual(emu_dev.user, "ceres")

        watch_dev = Device.for_target(Target.ARM)
        # ARM defaults
        self.assertEqual(watch_dev.host, "localhost") # unless 'watch' target passed

        watch_dev_explicit = Device.for_target("watch")
        self.assertEqual(watch_dev_explicit.host, "192.168.2.15")
        self.assertEqual(watch_dev_explicit.port, 22)
        self.assertEqual(watch_dev_explicit.user, "root")

    def test_ssh_command_formatting(self):
        dev = Device(host="10.0.0.5", port=2222, user="testuser")
        cmd_base = dev._ssh_cmd_base()
        self.assertIn("testuser@10.0.0.5", cmd_base)
        self.assertIn("2222", cmd_base)


if __name__ == "__main__":
    unittest.main()

