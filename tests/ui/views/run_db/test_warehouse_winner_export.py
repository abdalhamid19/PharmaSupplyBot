"""Export contents agree with UI rows, including Arabic and hostile names."""

from io import BytesIO
from zipfile import ZipFile

from openpyxl import load_workbook

from src.ui.views.run_db.warehouse_winner_export import COLUMNS, build_warehouse_zip, warehouse_groups


def test_zip_has_independent_safe_workbooks_and_literal_codes():
    rows = [dict(source_kind=source, store_key=key, store_name="../البركة.xlsx",
                 item_code="=1+1", item_name="صنف", product_name="Supplier",
                 requested_qty=10, available_qty=2, public_price=10,
                 discount_percent=20, purchase_price=8, currency="EGP")
            for source, key in [("tawreed", "1"), ("tawreed", "2"), ("excel-target", "1")]]
    assert len(warehouse_groups(rows)) == 3
    with ZipFile(BytesIO(build_warehouse_zip(rows))) as archive:
        assert len(set(archive.namelist())) == 3
        for name in archive.namelist():
            assert "/" not in name and "\\" not in name
            book = load_workbook(BytesIO(archive.read(name)))
            sheet = book.active
            assert [c.value for c in sheet[1]] == list(COLUMNS.values())
            assert [c.value for c in sheet[2]] == [rows[0][key] for key in COLUMNS]
            assert sheet["A2"].data_type == "s"
            assert sheet.sheet_view.rightToLeft
            book.close()
