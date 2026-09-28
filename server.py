"""Launcher for registrations that run `python <repo>/server.py`.

The server lives in grok/server.py (console script: grok-mcp).
"""

import sys

from grok.server import main

if __name__ == "__main__":
    sys.exit(main())
