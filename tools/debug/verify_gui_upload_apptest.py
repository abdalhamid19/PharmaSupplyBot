"""Verify the Excel target upload widgets render using AppTest on the fixture."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from streamlit.testing.v1 import AppTest


def main() -> int:
    script_path = Path(__file__).parent / "order_tab_fixture.py"
    at = AppTest.from_file(script_path, default_timeout=30)
    at.run()

    multiselects = list(at.main.multiselect)
    radios = list(at.main.radio)
    file_uploaders = list(at.main.file_uploader)

    print("=== Initial render ===")
    print(f"  multiselects: {len(multiselects)}")
    for m in multiselects:
        print(f"    label={m.label!r}  options={[str(o) for o in m.options]}  default={list(m.value)}")
    print(f"  radios: {len(radios)}")
    for r in radios:
        print(f"    label={r.label!r}  options={[str(o) for o in r.options]}  value={r.value}")
    print(f"  file_uploaders: {len(file_uploaders)}")
    for f in file_uploaders:
        print(f"    label={f.label!r}")

    run_target = next(
        (m for m in multiselects if m.label and "Run target" in m.label), None
    )
    if run_target is None:
        print("FAIL: 'Run target' multiselect not found")
        return 1
    excel_options = [str(o) for o in run_target.options if "Excel target" in str(o)]
    if not excel_options:
        print(f"FAIL: no Excel target options. options={[str(o) for o in run_target.options]}")
        return 1

    print(f"\n=== Selecting Excel target: {excel_options[0]} ===")
    run_target.set_value([excel_options[0]]).run()
    at.run()

    multiselects2 = list(at.main.multiselect)
    radios2 = list(at.main.radio)
    file_uploaders2 = list(at.main.file_uploader)
    print(f"  multiselects: {len(multiselects2)}")
    for m in multiselects2:
        print(f"    label={m.label!r}  value={list(m.value)}")
    print(f"  radios: {len(radios2)}")
    for r in radios2:
        print(f"    label={r.label!r}  options={[str(o) for o in r.options]}  value={r.value}")
    print(f"  file_uploaders: {len(file_uploaders2)}")
    for f in file_uploaders2:
        print(f"    label={f.label!r}")

    source_radio = next(
        (r for r in radios2 if r.label and "alnasr" in str(r.label)), None
    )
    upload_widget = next(
        (f for f in file_uploaders2 if f.label and "alnasr" in str(f.label)), None
    )

    if source_radio is None:
        print("FAIL: source radio for alnasr not rendered")
        return 1
    print(f"\n=== Source radio options for alnasr: {[str(o) for o in source_radio.options]} ===")
    if "Configured" not in source_radio.options:
        print("FAIL: Configured mode not present")
        return 1
    if "Existing file" not in source_radio.options:
        print("FAIL: Existing file mode not present")
        return 1
    if "Upload file" not in source_radio.options:
        print("FAIL: Upload file mode not present")
        return 1

    print(f"\n=== Switching to Upload file mode ===")
    source_radio.set_value("Upload file").run()
    at.run()

    file_uploaders3 = list(at.main.file_uploader)
    print(f"  file_uploaders after Upload file: {len(file_uploaders3)}")
    for f in file_uploaders3:
        print(f"    label={f.label!r}")

    if not any(f.label and "alnasr" in str(f.label) for f in file_uploaders3):
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