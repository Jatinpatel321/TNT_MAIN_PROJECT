#!/usr/bin/env python3
"""Run test_sms_dispatch.py via unittest, bypassing conftest.py."""
import sys
import os
import types

# Monkey-patch conftest BEFORE any test imports
fake = types.ModuleType("conftest")
sys.modules["conftest"] = fake

from unittest import defaultTestLoader, TextTestRunner

suite = defaultTestLoader.discover(
    os.path.join(os.path.dirname(__file__), "tests"),
    pattern="test_sms_dispatch.py",
)
runner = TextTestRunner(verbosity=2)
result = runner.run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
