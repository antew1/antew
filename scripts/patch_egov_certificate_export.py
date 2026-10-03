from pathlib import Path
import sys

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_egov_certificate_export.py <decoded-apk-dir>")

    root = Path(sys.argv[1])
    if not root.is_dir():
        raise SystemExit(f"decoded APK directory not found: {root}")

    layout = root / "res" / "layout" / "fragment_certificate_info.xml"
    if not layout.is_file():
        raise SystemExit(f"certificate info layout not found: {layout}")

    text = layout.read_text(encoding="utf-8")
    if '@id/revoke' not in text or '@id/certificate_date' not in text:
        raise SystemExit("expected certificate info layout anchors not found")

    print(f"PATCH_TARGET_OK:{layout}")

if __name__ == "__main__":
    main()
