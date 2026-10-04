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
    import xml.etree.ElementTree as ET
    ET.parse(layout)
    print("CERTIFICATE_LAYOUT_XML_VALID")
    fragment_files = list(root.glob("smali_classes*/kz/mobile/mgov/features/eds/presentation/my_eds/CertificateInfoFragment.smali"))
    model_files = list(root.glob("smali_classes*/kz/mobile/mgov/core/model/Certificate.smali"))
    if len(fragment_files) != 1 or len(model_files) != 1:
        raise SystemExit("expected unique certificate fragment and model")
    fragment = fragment_files[0].read_text(encoding="utf-8")
    model = model_files[0].read_text(encoding="utf-8")
    if ".method public onViewCreated(" not in fragment or "setData()V" not in fragment:
        raise SystemExit("certificate screen lifecycle anchors missing")
    if "getPem()Ljava/lang/String;" not in model:
        raise SystemExit("public PEM accessor missing")
    print("CERTIFICATE_PUBLIC_PEM_ANCHORS_OK")

if __name__ == "__main__":
    main()
