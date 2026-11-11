import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from environment import load_environment

class EnvironmentTests(unittest.TestCase):
    def test_dev_configuration(self):
        c = load_environment("development")
        self.assertEqual(c["apollo"]["adapter"], "simulated")
        self.assertFalse(c["validation"]["activation_enabled"])

    def test_prod_configuration_declared(self):
        c = load_environment("production")
        self.assertEqual(c["apollo"]["adapter"], "gcp_authenticated")

    def test_unknown_environment_rejected(self):
        with self.assertRaises(RuntimeError):
            load_environment("staging")

    def test_env_selection(self):
        with patch.dict(os.environ, {"MORPHEUS_ENV": "development"}):
            self.assertEqual(load_environment()["environment"], "development")
