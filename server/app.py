"""OpenEnv server entry point.

This module provides the FastAPI server for OpenEnv multi-mode deployment.
"""

import os
import sys
import uvicorn

# Add backend to path for imports
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend = os.path.join(_root, "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)
if _root not in sys.path:
    sys.path.insert(0, _root)

# Import the FastAPI app from backend
# Try different import paths for compatibility
try:
    from backend.app import app
except ImportError:
    sys.path.insert(0, _backend)
    from app import app

def main():
    """Entry point for the server script."""
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("server.app:app", host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
