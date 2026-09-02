"""Verify the redesigned Excel target source panel using AppTest."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from streamlit.testing.v1 import AppTest


def main() -> int:
    script_path = Path(__file__).parent / "order_tab_fixture.py"
    at = AppTest.from_file(script_path, default_timeout=30)
    at.run()

    checkboxes = list(at.main.checkbox)
    radios = list(at.main.radio)
    file_uploaders = list(at.main.file_uploader)

    print("=== Initial render ===")
    print(f"  checkboxes: {len(checkboxes)}")
    for c in checkboxes:
        print(f"    label={c.label!r}  value={c.value}")
    print(f"  radios: {len(radios)}")
    for r in radios:
        print(f"    label={r.label!r}  options={[str(o) for o in r.options]}  value={r.value}")
    print(f"  file_uploaders: {len(file_uploaders)}")

    alnasr_box = next(
        (c for c in checkboxes if c.label and "alnasr" in str(c.label)), None
    )
    if alnasr_box is None:
        print("FAIL: alnasr checkbox not rendered")
        return 1

    print(f"\n=== Ticking alnasr checkbox ===")
    alnasr_box.set_value(True).run()
    at.run()

    checkboxes2 = list(at.main.checkbox)
    radios2 = list(at.main.radio)
    file_uploaders2 = list(at.main.file_uploader)
    print(f"  checkboxes: {len(checkboxes2)}")
    print(f"  radios: {len(radios2)}")
    for r in radios2:
        print(f"    label={r.label!r}  options={[str(o) for o in r.options]}  value={r.value}")
    print(f"  file_uploaders: {len(file_uploaders2)}")

    source_radio = next(
        (r for r in radios2 if r.label == "Source" and "Existing file" in r.options), None
    )
    if source_radio is None:
        print("FAIL: source radio for alnasr not rendered")
        return 1

    if "Existing file" not in source_radio.options:
        print("FAIL: Existing file mode missing")
        return 1
    if "Upload file" not in source_radio.options:
        print("FAIL: Upload file mode missing")
        return 1

    print(f"\n=== Switching to Upload file mode ===")
    source_radio.set_value("Upload file").run()
    at.run()

    file_uploaders3 = list(at.main.file_uploader)
    print(f"  file_uploaders after Upload file: {len(file_uploaders3)}")
    for f in file_uploaders3:
        print(f"    label={f.label!r}")

    if not any(f.label == "Upload catalog" for f in file_uploaders3):
        print("FAIL: file_uploader for alnasr did not appear in Upload file mode")
        return 1

    if at.exception:
        print("\nEXCEPTIONS:")
        for exc in at.exception:
            print(" ", exc.value)
        return 1

    print("\nALL UPLOAD WIDGETS RENDERED CORRECTLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())