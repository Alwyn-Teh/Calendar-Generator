#!/usr/bin/env python3
"""Check Calendar Generator prerequisites and source syntax (no PDF generated)."""
from pathlib import Path
import ast
import importlib.metadata
import sys
import tokenize

ROOT = Path(__file__).resolve().parents[1]
print(f"Python: {sys.version.split()[0]}")
if sys.version_info < (3, 9):
    raise SystemExit("Python 3.9 or newer is required for the current script")
for package in ("reportlab", "holidays"):
    try:
        print(f"{package}: {importlib.metadata.version(package)}")
    except importlib.metadata.PackageNotFoundError:
        raise SystemExit(f"Missing package: {package}. Run: python -m pip install -r requirements.txt")
files = [ROOT / "make_calendar.py", *sorted((ROOT / "versions").glob("*.py"))]
for file in files:
    
    with tokenize.open(file) as source:
        ast.parse(source.read(), filename=str(file))
print(f"Source syntax OK: {len(files)} Python files")
