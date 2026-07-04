"""Test prevented items filtering for safety and correctness.

اختبارات حماية الأصناف للتحقق من وظيفة منع الأصناف.
هذه الاختبارات توثق السلوك الجديد للتطبيع القوي باستخدام
normalize_prevented_compare_name().

ملاحظة مهمة: التطبيع الجديد يزيل النقطة في نهاية اسم الصنف، مما يجعل
المطابقة أقوى وأكثر دقة في منع الأصناف الممنوعة.

Note: These tests document the new behavior where normalization DOES remove
trailing dots from item names using normalize_prevented_compare_name().
This provides stronger matching for prevented items.
"""

import unittest

from src.core.ordering.prevented_items import (
    PreventedItem,
    filter_prevented_order_items,
)
from src.core.utils.excel import Item


class PreventedItemsSafetyTests(unittest.TestCase):
    """اختبارات حماية الأصناف - Prevented Items Safety Tests."""

    def test_blocked_item_with_trailing_dot_blocks_without_dot(self) -> None:
        """اختبار أن الصنف المنتهي بنقطة يمنع الصنف بدون نقطة (السلوك الجديد).

        Test that a blocked item ending with a dot DOES block without a dot
        (new behavior - strong normalization).
        BREVY 5 MG 10 F.C. TABS. (منع) vs BREVY 5 MG 10 F.C. TABS (طلب)
        السلوك الجديد: يُمنَع (لأن التطبيع الجديد يزيل النقطة).
        """
        items = [
            Item(code="1", name="BREVY 5 MG 10 F.C. TABS", qty=1),
            Item(code="2", name="Allowed Item", qty=2),
        ]
        prevented_items = [
            PreventedItem(code="", name="BREVY 5 MG 10 F.C. TABS.")
        ]

        allowed_items = list(filter_prevented_order_items(items, prevented_items))

        # New behavior: trailing dot is removed, so item IS blocked
        self.assertEqual(len(allowed_items), 1)
        self.assertEqual(allowed_items, [items[1]])

    def test_nine_dot_ending_items_blocked_without_dot(self) -> None:
        """اختبار أن الأصناف التسعة المنتهية بنقطة تمنع بدون نقطة (السلوك الجديد).

        Test that nine items ending with a dot DO block without dot
        (new behavior - strong normalization).
        الأصناف المنتهية بنقطة:
        - DIXVIT 10.000 I.U. 20 TABS.
        - IMATINIB  400 MG 30 F.C. TABS.
        - INJECTMOL 1 GM/100ML VIAL FOR I.V. INF.
        - MICA 20 F.C. TABS.
        - ROTADANSETRON 4MG/2ML 5 I.M./I.V./INF. AMP.
        - ROTADANSETRON 8MG/2ML 5 I.M./I.V./INF. AMP.
        - CIPROFLOXMET 500/500MG 20 F.C.TABS.
        - BABY RELIEF 25 MG 10 SUPP.
        - BREVY 5 MG 10 F.C. TABS.
        السلوك الجديد: تُمنَع جميعها (لأن التطبيع الجديد يزيل النقطة).
        """
        items = [
            Item(code="1", name="DIXVIT 10.000 I.U. 20 TABS", qty=1),
            Item(code="2", name="IMATINIB  400 MG 30 F.C. TABS", qty=1),
            Item(code="3", name="INJECTMOL 1 GM/100ML VIAL FOR I.V. INF", qty=1),
            Item(code="4", name="MICA 20 F.C. TABS", qty=1),
            Item(code="5", name="ROTADANSETRON 4MG/2ML 5 I.M./I.V./INF. AMP", qty=1),
            Item(code="6", name="ROTADANSETRON 8MG/2ML 5 I.M./I.V./INF. AMP", qty=1),
            Item(code="7", name="CIPROFLOXMET 500/500MG 20 F.C.TABS", qty=1),
            Item(code="8", name="BABY RELIEF 25 MG 10 SUPP", qty=1),
            Item(code="9", name="BREVY 5 MG 10 F.C. TABS", qty=1),
            Item(code="10", name="Allowed Item", qty=2),
        ]
        prevented_items = [
            PreventedItem(code="", name="DIXVIT 10.000 I.U. 20 TABS."),
            PreventedItem(code="", name="IMATINIB  400 MG 30 F.C. TABS."),
            PreventedItem(code="", name="INJECTMOL 1 GM/100ML VIAL FOR I.V. INF."),
            PreventedItem(code="", name="MICA 20 F.C. TABS."),
            PreventedItem(code="", name="ROTADANSETRON 4MG/2ML 5 I.M./I.V./INF. AMP."),
            PreventedItem(code="", name="ROTADANSETRON 8MG/2ML 5 I.M./I.V./INF. AMP."),
            PreventedItem(code="", name="CIPROFLOXMET 500/500MG 20 F.C.TABS."),
            PreventedItem(code="", name="BABY RELIEF 25 MG 10 SUPP."),
            PreventedItem(code="", name="BREVY 5 MG 10 F.C. TABS."),
        ]

        allowed_items = list(filter_prevented_order_items(items, prevented_items))

        # New behavior: all nine are blocked due to strong normalization
        self.assertEqual(len(allowed_items), 1)
        self.assertEqual(allowed_items, [items[9]])

    def test_decimal_point_in_dose_preserved(self) -> None:
        """اختبار أن النقطة العشرية في الجرعة محفوظة (السلوك الجديد).

        Test that decimal point in dose is preserved (new behavior).
        DIXVIT 10.000 I.U. 20 TABS vs DIXVIT 5.000 I.U. 20 TABS
        النقطة العشرية محفوظة (لأنها في منتصف النص، ليست في النهاية).
        التطبيع الجديد لا يؤثر على النقطة العشرية في الجرعة.
        """
        items = [
            Item(code="1", name="DIXVIT 10.000 I.U. 20 TABS", qty=1),
            Item(code="2", name="DIXVIT 5.000 I.U. 20 TABS", qty=1),
            Item(code="3", name="Allowed Item", qty=2),
        ]
        prevented_items = [
            PreventedItem(code="", name="DIXVIT 10.000 I.U. 20 TABS")
        ]

        allowed_items = list(filter_prevented_order_items(items, prevented_items))

        # New behavior: exact match is blocked, different dose is not blocked
        # Decimal point in dose is preserved (not affected by normalization)
        self.assertEqual(allowed_items, [items[1], items[2]])

    def test_non_prevented_item_is_not_blocked(self) -> None:
        """اختبار أن الصنف غير الممنوع لا يُمنَع (لا false block).
        
        Test that a non-prevented item is not blocked (no false block).
        """
        items = [
            Item(code="1", name="Panadol Extra", qty=1),
            Item(code="2", name="Aspirin 500 MG", qty=2),
            Item(code="3", name="Vitamin C 1000 MG", qty=3),
        ]
        prevented_items = [
            PreventedItem(code="", name="BREVY 5 MG 10 F.C. TABS."),
            PreventedItem(code="", name="DIXVIT 10.000 I.U. 20 TABS."),
        ]

        allowed_items = list(filter_prevented_order_items(items, prevented_items))

        self.assertEqual(len(allowed_items), 3)
        self.assertEqual(allowed_items, items)

    def test_exact_match_with_trailing_dot_blocks(self) -> None:
        """اختبار التطابق التام مع النقطة في النهاية يمنع الصنف.
        
        Test that exact match with trailing dot blocks the item.
        """
        items = [
            Item(code="1", name="BREVY 5 MG 10 F.C. TABS.", qty=1),
            Item(code="2", name="Allowed Item", qty=2),
        ]
        prevented_items = [
            PreventedItem(code="", name="BREVY 5 MG 10 F.C. TABS.")
        ]

        allowed_items = list(filter_prevented_order_items(items, prevented_items))

        self.assertEqual(allowed_items, [items[1]])

    def test_normalization_handles_multiple_spaces(self) -> None:
        """اختبار أن التطبيع يتعامل مع المسافات المتعددة.

        Test that normalization handles multiple spaces.
        """
        items = [
            Item(code="1", name="BREVY  5  MG  10  F.C.  TABS", qty=1),
            Item(code="2", name="Allowed Item", qty=2),
        ]
        prevented_items = [
            PreventedItem(code="", name="BREVY 5 MG 10 F.C. TABS")
        ]

        allowed_items = list(filter_prevented_order_items(items, prevented_items))

        # Normalization handles multiple spaces correctly
        self.assertEqual(allowed_items, [items[1]])

    def test_brevy_with_trailing_dot_blocks_without_dot(self) -> None:
        """اختبار محدد لـ BREVY مع النقطة في النهاية يمنع بدون نقطة.

        Specific test for BREVY with trailing dot blocking without dot.
        BREVY 5 MG 10 F.C. TABS. (منع) vs BREVY 5 MG 10 F.C. TABS (طلب)
        السلوك الجديد: يُمنَع (التطبيع القوي يزيل النقطة).
        """
        items = [
            Item(code="1", name="BREVY 5 MG 10 F.C. TABS", qty=1),
            Item(code="2", name="Other Item", qty=2),
        ]
        prevented_items = [
            PreventedItem(code="", name="BREVY 5 MG 10 F.C. TABS.")
        ]

        allowed_items = list(filter_prevented_order_items(items, prevented_items))

        # BREVY is blocked due to strong normalization
        self.assertEqual(len(allowed_items), 1)
        self.assertEqual(allowed_items, [items[1]])

    def test_decimal_point_not_affected(self) -> None:
        """اختبار أن النقطة العشرية في الجرعة لا تتأثر بالتطبيع.

        Test that decimal point in dose is not affected by normalization.
        DIXVIT 10.000 I.U. 20 TABS - النقطة العشرية محفوظة.
        لا يوجد منع خاطئ لصنف مختلف الجرعة.
        """
        items = [
            Item(code="1", name="DIXVIT 10.000 I.U. 20 TABS", qty=1),
            Item(code="2", name="DIXVIT 5.000 I.U. 20 TABS", qty=1),
            Item(code="3", name="DIXVIT 20.000 I.U. 20 TABS", qty=1),
        ]
        prevented_items = [
            PreventedItem(code="", name="DIXVIT 10.000 I.U. 20 TABS")
        ]

        allowed_items = list(filter_prevented_order_items(items, prevented_items))

        # Only 10.000 is blocked, other doses are not (decimal preserved)
        self.assertEqual(len(allowed_items), 2)
        self.assertEqual(allowed_items[0].name, "DIXVIT 5.000 I.U. 20 TABS")
        self.assertEqual(allowed_items[1].name, "DIXVIT 20.000 I.U. 20 TABS")

    def test_all_nine_dot_ending_items_blocked(self) -> None:
        """اختبار شامل أن كل الأصناف الـ9 المنتهية بنقطة تُمنَع.

        Comprehensive test that all 9 dot-ending items are blocked.
        التطبيع القوي يضمن منع جميع الأصناف المنتهية بنقطة.
        """
        items = [
            Item(code="1", name="DIXVIT 10.000 I.U. 20 TABS", qty=1),
            Item(code="2", name="IMATINIB  400 MG 30 F.C. TABS", qty=1),
            Item(code="3", name="INJECTMOL 1 GM/100ML VIAL FOR I.V. INF", qty=1),
            Item(code="4", name="MICA 20 F.C. TABS", qty=1),
            Item(code="5", name="ROTADANSETRON 4MG/2ML 5 I.M./I.V./INF. AMP", qty=1),
            Item(code="6", name="ROTADANSETRON 8MG/2ML 5 I.M./I.V./INF. AMP", qty=1),
            Item(code="7", name="CIPROFLOXMET 500/500MG 20 F.C.TABS", qty=1),
            Item(code="8", name="BABY RELIEF 25 MG 10 SUPP", qty=1),
            Item(code="9", name="BREVY 5 MG 10 F.C. TABS", qty=1),
        ]
        prevented_items = [
            PreventedItem(code="", name="DIXVIT 10.000 I.U. 20 TABS."),
            PreventedItem(code="", name="IMATINIB  400 MG 30 F.C. TABS."),
            PreventedItem(code="", name="INJECTMOL 1 GM/100ML VIAL FOR I.V. INF."),
            PreventedItem(code="", name="MICA 20 F.C. TABS."),
            PreventedItem(code="", name="ROTADANSETRON 4MG/2ML 5 I.M./I.V./INF. AMP."),
            PreventedItem(code="", name="ROTADANSETRON 8MG/2ML 5 I.M./I.V./INF. AMP."),
            PreventedItem(code="", name="CIPROFLOXMET 500/500MG 20 F.C.TABS."),
            PreventedItem(code="", name="BABY RELIEF 25 MG 10 SUPP."),
            PreventedItem(code="", name="BREVY 5 MG 10 F.C. TABS."),
        ]

        allowed_items = list(filter_prevented_order_items(items, prevented_items))

        # All 9 items should be blocked
        self.assertEqual(len(allowed_items), 0)

    def test_non_prevented_item_no_false_block(self) -> None:
        """اختبار أن صنف غير ممنوع لا يُمنَع (لا false block).

        Test that a non-prevented item is not blocked (no false block).
        التطبيع القوي لا يسبب منع خاطئ للأصناف غير الممنوعة.
        """
        items = [
            Item(code="1", name="Panadol Extra", qty=1),
            Item(code="2", name="Aspirin 500 MG", qty=2),
            Item(code="3", name="Vitamin C 1000 MG", qty=3),
        ]
        prevented_items = [
            PreventedItem(code="", name="BREVY 5 MG 10 F.C. TABS."),
            PreventedItem(code="", name="DIXVIT 10.000 I.U. 20 TABS."),
        ]

        allowed_items = list(filter_prevented_order_items(items, prevented_items))

        # All non-prevented items should pass through
        self.assertEqual(len(allowed_items), 3)
        self.assertEqual(allowed_items, items)


if __name__ == "__main__":
    unittest.main()
