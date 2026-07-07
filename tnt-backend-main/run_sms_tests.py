"""
Standalone runner for test_sms_dispatch.py that avoids the conftest import chain.

The project conftest at tests/ imports the full FastAPI app which in turn requires
numpy, scikit-learn etc.  Our tests are pure unit tests with mocks — they don't
need the conftest at all, so we run them directly via unittest.
"""
import os
import sys

# Ensure we're in the backend dir
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

# Fake Redis is already handled by app/core/redis.py auto-fallback

import unittest

from tests.test_sms_dispatch import *

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
