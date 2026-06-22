#!/usr/bin/env python3
"""Pre-deployment sanity check.

Verifies that critical fixes are present in source files before pushing to the
HF Space. Run this script from the backend/ directory (or the deployment repo
root) before any `git push`.

Usage:
    python check_before_deploy.py
"""

import sys
import py_compile
import pathlib

ROOT = pathlib.Path(__file__).parent

CHECKS = [
    # (description, file_relative_to_ROOT, required_substring)
    (
        "_can_access_profile guard in candidates.py",
        "app/api/candidates.py",
        "_can_access_profile",
    ),
    (
        "recruiter_id column in Candidate model",
        "app/models/models.py",
        "recruiter_id",
    ),
    (
        "cascade delete in Candidate model",
        "app/models/models.py",
        "cascade",
    ),
    (
        "HF_TOKEN alias at startup",
        "app/main.py",
        "HF_TOKEN_CHATBOT",
    ),
    (
        "DATABASE_URL override in alembic/env.py",
        "alembic/env.py",
        "DATABASE_URL",
    ),
    (
        "GLiNER extractor present",
        "ai_module/nlp/gliner_extractor.py",
        "GLiNERExtractor",
    ),
]

COMPILE_TARGETS = [
    "app/main.py",
    "app/api/candidates.py",
    "app/models/models.py",
    "app/core/capabilities.py",
    "ai_module/nlp/gliner_extractor.py",
]

errors: list[str] = []

print("=" * 60)
print("AI-Talent-Finder — pre-deploy check")
print("=" * 60)

for description, rel_path, needle in CHECKS:
    path = ROOT / rel_path
    if not path.exists():
        errors.append(f"MISSING FILE  : {rel_path}")
        print(f"  [FAIL] {description}\n         File not found: {rel_path}")
        continue
    content = path.read_text(encoding="utf-8", errors="replace")
    if needle not in content:
        errors.append(f"MISSING FIX   : {description} (needle: {needle!r})")
        print(f"  [FAIL] {description}\n         '{needle}' not found in {rel_path}")
    else:
        print(f"  [OK]   {description}")

print()
print("Syntax check:")
for rel_path in COMPILE_TARGETS:
    path = ROOT / rel_path
    if not path.exists():
        print(f"  [SKIP] {rel_path} (not found)")
        continue
    try:
        py_compile.compile(str(path), doraise=True)
        print(f"  [OK]   {rel_path}")
    except py_compile.PyCompileError as exc:
        errors.append(f"SYNTAX ERROR  : {rel_path} — {exc}")
        print(f"  [FAIL] {rel_path}\n         {exc}")

print()
if errors:
    print(f"DEPLOY BLOCKED — {len(errors)} issue(s) found:")
    for e in errors:
        print(f"  • {e}")
    sys.exit(1)
else:
    print("All checks passed — safe to deploy.")
    sys.exit(0)
