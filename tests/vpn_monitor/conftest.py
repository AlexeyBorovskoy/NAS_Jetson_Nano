import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SVC = os.path.join(ROOT, "services", "vpn_monitor")
if SVC not in sys.path:
    sys.path.insert(0, SVC)
