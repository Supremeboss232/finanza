#!/usr/bin/env python3
import py_compile
import sys

files_to_check = [
    'rate_limiter.py',
    'routers/fund_v1_api.py', 
    'ws_manager.py'
]

all_ok = True
for filepath in files_to_check:
    try:
        py_compile.compile(filepath, doraise=True)
        print(f"✓ {filepath}: Syntax OK")
    except py_compile.PyCompileError as e:
        print(f"✗ {filepath}: {e}")
        all_ok = False

if all_ok:
    print("\n✓ All files compiled successfully!")
    sys.exit(0)
else:
    print("\n✗ Some files have syntax errors")
    sys.exit(1)
