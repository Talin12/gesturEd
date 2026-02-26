# backend/reactions/opencv_handler.py

import sys
from pathlib import Path

_OPENCV_MODULES = Path(__file__).resolve().parent.parent / 'opencv_modules'
if str(_OPENCV_MODULES) not in sys.path:
    sys.path.insert(0, str(_OPENCV_MODULES))

from .stream_state import state


def start_lab():
    """No-op: frame capture handled per-WebSocket in consumers.py."""
    state["running"] = True


def stop_lab():
    state["running"] = False
    state["reaction_complete_flag"] = False