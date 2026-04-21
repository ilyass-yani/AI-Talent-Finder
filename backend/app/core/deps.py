"""
Convenience alias for `app.core.dependencies`.

The development guide and recent code refer to `app.core.deps`; existing routes
import from `app.core.dependencies`. Both must keep working — this module just
re-exports the public surface.
"""

from app.core.dependencies import (  # noqa: F401
    get_current_active_user,
    get_current_admin,
    get_current_candidate,
    get_current_recruiter,
    get_current_user,
    get_db,
    require_role,
)

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "get_current_admin",
    "get_current_recruiter",
    "get_current_candidate",
    "require_role",
]
