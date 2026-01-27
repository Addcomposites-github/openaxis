"""
OpenAxis Backend Module

HTTP API server for communication between Electron frontend and Python backend.
"""

from .server import run_server

__all__ = ['run_server']
