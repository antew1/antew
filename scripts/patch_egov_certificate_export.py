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
    import re
    public_xml = root / "res" / "values" / "public.xml"
    if not public_xml.is_file():
        raise SystemExit("resource ID table missing")
    resources = ET.parse(public_xml).getroot()
    certificate_date_ids = [
        e.get("id") for e in resources
        if e.get("type") == "id" and e.get("name") == "certificate_date"
    ]
    if len(certificate_date_ids) != 1 or not re.fullmatch(r"0x[0-9a-fA-F]{8}", certificate_date_ids[0]):
        raise SystemExit("certificate_date resource ID not uniquely resolved")
    print("CERTIFICATE_RESOURCE_ID_RESOLVED:" + certificate_date_ids[0])
    if text.count('android:id="@+id/certificate_export"') != 1:
        raise SystemExit("export button missing or duplicated")
    if any(e.get("name") == "certificate_export" and e.get("type") == "id" for e in resources):
        raise SystemExit("export resource ID already exists")
    used = {
        int(e.get("id"), 16) for e in resources
        if e.get("type") == "id" and re.fullmatch(r"0x[0-9a-fA-F]{8}", e.get("id") or "")
    }
    prefix = int(certificate_date_ids[0], 16) & 0xffff0000
    candidates = [prefix | i for i in range(0xffff) if (prefix | i) not in used]
    if not candidates:
        raise SystemExit("no free ID resources")
    export_id = candidates[-1]
    ET.SubElement(resources, "public", {
        "type": "id", "name": "certificate_export", "id": f"0x{export_id:08x}"
    })
    ET.indent(resources)
    ET.ElementTree(resources).write(public_xml, encoding="utf-8", xml_declaration=True)
    layout.write_text(text.replace('android:id="@+id/certificate_export"', 'android:id="@id/certificate_export"'), encoding="utf-8")
    print(f"CERTIFICATE_EXPORT_RESOURCE_REGISTERED:0x{export_id:08x}")
    listener = fragment_files[0].with_name("CertificateExportClickListener.smali")
    if listener.exists():
        raise SystemExit("certificate export listener already exists")
    listener.write_text(""" .class public final Lkz/mobile/mgov/features/eds/presentation/my_eds/CertificateExportClickListener;
.super Ljava/lang/Object;
.implements Landroid/view/View$OnClickListener;

.field private final fragment:Lkz/mobile/mgov/features/eds/presentation/my_eds/CertificateInfoFragment;

.method public constructor <init>(Lkz/mobile/mgov/features/eds/presentation/my_eds/CertificateInfoFragment;)V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    iput-object p1, p0, Lkz/mobile/mgov/features/eds/presentation/my_eds/CertificateExportClickListener;->fragment:Lkz/mobile/mgov/features/eds/presentation/my_eds/CertificateInfoFragment;
    return-void
.end method

.method public onClick(Landroid/view/View;)V
    .locals 2
    iget-object v0, p0, Lkz/mobile/mgov/features/eds/presentation/my_eds/CertificateExportClickListener;->fragment:Lkz/mobile/mgov/features/eds/presentation/my_eds/CertificateInfoFragment;
    invoke-static {v0}, Lkz/mobile/mgov/features/eds/presentation/my_eds/CertificateInfoFragment;->access$getCertificate$p(Lkz/mobile/mgov/features/eds/presentation/my_eds/CertificateInfoFragment;)Lkz/mobile/mgov/core/model/Certificate;
    move-result-object v0
    if-eqz v0, :done
    invoke-virtual {v0}, Lkz/mobile/mgov/core/model/Certificate;->getPem()Ljava/lang/String;
    move-result-object v1
    if-eqz v1, :done
    invoke-virtual {v1}, Ljava/lang/String;->length()I
    move-result v0
    if-lez v0, :done
    :done
    return-void
.end method
""".lstrip(), encoding="utf-8")
    print("CERTIFICATE_EXPORT_LISTENER_SKELETON_CREATED")
    method_start = fragment.index(".method public onViewCreated(Landroid/view/View;Landroid/os/Bundle;)V")
    method_end = fragment.index(".end method", method_start)
    method = fragment[method_start:method_end]
    target = "    invoke-direct {p0}, Lkz/mobile/mgov/features/eds/presentation/my_eds/CertificateInfoFragment;->setData()V"
    if method.count(target) != 1 or ".locals 1" not in method:
        raise SystemExit("unexpected certificate view lifecycle structure")
    method = method.replace(".locals 1", ".locals 2", 1)
    instructions = (
        "\n    const v0, 0x%08x\n"
        "    invoke-virtual {p1, v0}, Landroid/view/View;->findViewById(I)Landroid/view/View;\n"
        "    move-result-object v0\n"
        "    new-instance v1, Lkz/mobile/mgov/features/eds/presentation/my_eds/CertificateExportClickListener;\n"
        "    invoke-direct {v1, p0}, Lkz/mobile/mgov/features/eds/presentation/my_eds/CertificateExportClickListener;-><init>(Lkz/mobile/mgov/features/eds/presentation/my_eds/CertificateInfoFragment;)V\n"
        "    invoke-virtual {v0, v1}, Landroid/view/View;->setOnClickListener(Landroid/view/View$OnClickListener;)V"
    ) % export_id
    method = method.replace(target, target + instructions, 1)
    patched = fragment[:method_start] + method + fragment[method_end:]
    fragment_files[0].write_text(patched, encoding="utf-8")
    print("CERTIFICATE_EXPORT_LISTENER_CONNECTED")

if __name__ == "__main__":
    main()
