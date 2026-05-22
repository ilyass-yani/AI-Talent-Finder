"""Compatibility alias for legacy imports under `app.ai_module`.

This package forwards lookups to the top-level `ai_module` package so existing
patch paths like `app.ai_module.nlp.cv_cleaner` keep working.
"""

from importlib import import_module

_real_pkg = import_module("ai_module")
__path__ = _real_pkg.__path__