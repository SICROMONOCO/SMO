#!/usr/bin/env python3
"""
SMO Control Panel Launcher
--------------------------
Quick launcher for the SMO GUI Control Panel.

This is a simple wrapper that starts the GUI dashboard on port 8000
and automatically opens it in your default browser.
"""

import sys
import webbrowser
import time
import threading
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def open_browser():
    """Open browser after a short delay."""
    time.sleep(2)  # Wait for server to start
    print("\n🌐 Opening browser...")
    webbrowser.open('http://localhost:8000')


def main():
    """Launch the GUI dashboard."""
    print("=" * 70)
    print("🚀 SMO Control Panel Launcher")
    print("=" * 70)
    print()
    print("Starting the GUI Control Panel...")
    print()
    print("📍 Control Panel URL: http://localhost:8000")
    print()
    print("Features:")
    print("  ✅ Start/Stop services with one click")
    print("  ✅ Monitor system metrics in real-time")
    print("  ✅ View logs and edit configuration")
    print("  ✅ Clean, XAMPP-like interface")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 70)
    print()
    
    # Start browser opener in background
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Import and run the GUI dashboard
    from gui_dashboard import main as run_gui
    run_gui()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Control Panel stopped successfully!")
        sys.exit(0)
