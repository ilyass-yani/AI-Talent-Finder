"""Application package bootstrap.

This alias keeps legacy absolute imports like `from app...` working when the
project is launched from repository root with module path `backend.app.main`.
"""

import sys


# If loaded as `backend.app`, expose the same module object under `app`.
# This preserves compatibility with existing imports across the codebase.
if __name__ == "backend.app" and "app" not in sys.modules:
	sys.modules["app"] = sys.modules[__name__]

