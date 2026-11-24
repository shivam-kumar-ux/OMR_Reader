"""
Bundle Size Validator for Vercel Serverless Deployment (< 500 MB).
Simulates excluded directories from .vercelignore and computes total deployable payload size.
"""

import os
import sys

MAX_ALLOWED_BYTES = 500 * 1024 * 1024  # 500 MB

IGNORE_DIRS = {
    ".venv", ".git", ".github", "tests", "samples/filled",
    "scans_input", "storage", "node_modules", ".pytest_cache", "__pycache__"
}


def get_deployable_bundle_size(root_dir="."):
    total_bytes = 0
    file_count = 0

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Normalize relative path
        rel_dir = os.path.relpath(dirpath, root_dir).replace("\\", "/")

        # Prune ignored directories
        dirnames[:] = [d for d in dirnames if not any(
            rel_dir == ign or rel_dir.startswith(ign + "/") or d == ign for ign in IGNORE_DIRS
        )]

        if any(rel_dir == ign or rel_dir.startswith(ign + "/") for ign in IGNORE_DIRS):
            continue

        for f in filenames:
            if f.endswith((".pyc", ".log", ".sqlite")):
                continue
            fpath = os.path.join(dirpath, f)
            try:
                sz = os.path.getsize(fpath)
                total_bytes += sz
                file_count += 1
            except OSError:
                pass

    return total_bytes, file_count


def main():
    total_bytes, file_count = get_deployable_bundle_size()
    total_mb = total_bytes / (1024 * 1024)

    print("=" * 60)
    print("      VERCEL SERVERLESS BUNDLE SIZE AUDIT")
    print("=" * 60)
    print(f"Deployable Files Count:  {file_count}")
    print(f"Deployable Bundle Size:  {total_mb:.2f} MB")
    print(f"Vercel Maximum Limit:    500.00 MB")
    print(f"Headroom Remaining:      {(500.0 - total_mb):.2f} MB")
    print("-" * 60)

    if total_bytes > MAX_ALLOWED_BYTES:
        print(f"❌ FAIL: Deployable bundle ({total_mb:.2f} MB) exceeds 500 MB limit!")
        sys.exit(1)
    else:
        print(f"✅ PASS: Bundle size is well within limits ({total_mb:.2f} MB < 500 MB)")
        print("=" * 60)
        sys.exit(0)


if __name__ == "__main__":
    main()
