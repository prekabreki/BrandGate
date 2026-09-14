import os
import sys

# The tests import `pipeline.*`, so the repo root has to be importable whether
# pytest is run from the root or from inside pipeline/tests.
sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
