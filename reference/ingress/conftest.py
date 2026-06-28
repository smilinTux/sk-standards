"""Make ``capauth_gate`` importable when pytest is invoked from any CWD."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
