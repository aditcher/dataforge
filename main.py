#!/usr/bin/env python3
"""
DataForge - Main Application Entry Point

Launches the unified data intake and visualization platform.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app import DataForgeApp


def main():
    """Initialize and launch the DataForge application."""
    app = DataForgeApp()
    app.run()


if __name__ == "__main__":
    main()
