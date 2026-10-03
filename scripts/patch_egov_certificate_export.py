from pathlib import Path
import sys

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_egov_certificate_export.py <decoded-apk-dir>")
    root = Path(sys.argv[1])
    if not root.is_dir():
        raise SystemExit(f"decoded APK directory not found: {root}")
    print(f"PATCHER_READY:{root}")

if __name__ == "__main__":
    main()
