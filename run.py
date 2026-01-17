#!/usr/bin/env python
"""
Flight Sales Dashboard Application Entry Point
This script runs the Streamlit application from the correct location
"""

import subprocess
import sys

if __name__ == "__main__":
    # Run the Streamlit application
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "src/ui/dashboard.py"
    ])
