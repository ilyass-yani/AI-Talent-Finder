#!/usr/bin/env python3
"""
Check IA environment: optional deps and API keys.
Run: PYTHONPATH=. python3 scripts/check_ia_environment.py
"""
import os
import importlib
import sys

checks = []

def check_import(name):
    try:
        importlib.import_module(name)
        return True, None
    except Exception as e:
        return False, str(e)

# Packages to check
packages = [
    ('transformers', 'transformers'),
    ('tika', 'tika'),
    ('pytesseract', 'pytesseract'),
    ('PIL', 'PIL'),
    ('torch', 'torch'),
    ('sentence_transformers', 'sentence_transformers'),
    ('faiss', 'faiss'),
]

print('\nIA environment quick-check')
print('================================')

for label, pkg in packages:
    ok, err = check_import(pkg)
    print(f"Package {pkg}: {'OK' if ok else 'MISSING'}")
    if not ok:
        print(f"  -> {err}")

# Environment variables of interest
env_vars = [
    'OPENAI_API_KEY',
    'HUGGINGFACE_API_KEY',
    'TESSERACT_CMD',
    'ELASTICSEARCH_URL',
    'DATABASE_URL',
]

print('\nEnvironment variables')
for var in env_vars:
    val = os.getenv(var)
    print(f"{var}: {'SET' if val else 'NOT SET'}")

# Check tesseract availability if pytesseract exists
ok, _ = check_import('pytesseract')
if ok:
    try:
        import pytesseract
        tcmd = os.getenv('TESSERACT_CMD')
        try:
            from shutil import which
            found = which(tcmd) if tcmd else None
            if found:
                print('\nTesseract binary: FOUND at ' + found)
            else:
                print('\nTesseract binary: NOT FOUND (set TESSERACT_CMD if installed)')
        except Exception:
            print('\nTesseract binary: check path manually')
    except Exception:
        pass

# High-level fallback guidance
print('\nFallback modes detected in code:')
print('- LLM/Embeddings: when API keys missing, code should fallback to local models or disable features')
print('- NER/OCR: when native libraries missing, extraction will be partial or rely on heuristics')
print('- Provide environment variable flags to force fallback in production')

print('\nQuick recommendations:')
print('- Install optional packages with `pip install -r requirements-faiss-optional.txt`')
print('- Set OpenAI/HuggingFace keys if using hosted LLMs')
print('- Install Tesseract system binary for OCR on scanned PDFs')

print('\nDone.')
