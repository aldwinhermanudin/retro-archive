#!/usr/bin/env python3
import sys

try:
    from retroarchive import verify
except ImportError:
    print("Error: Could not import retroarchive. Please ensure you are in the correct directory.", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    verify.main()
