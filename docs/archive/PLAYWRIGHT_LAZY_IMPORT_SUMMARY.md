# ملخص تأجيل استيراد Playwright (Lazy Import Strategy)

## التاريخ
29 يونيو 2026

## الهدف
فصل طبقي صحيح بين core و tawreed + اختبارات نقية لا تنهار بغياب المتصفح

## الاستراتيجية المستخدمة

### النوع 1: تلميحات الأنواع فقط (Type Hints Only)
**الملفات (17 ملفاً):**
- tawreed_dialogs.py
- tawreed_products_flow.py
- tawreed_ui.py
- tawreed_product_search.py
- tawreed_login_detection.py
- tawreed_auth.py
- tawreed_session.py
- product_export_headers.py
- product_export_api.py
- tawreed_cart_removal.py
- tawreed_order_processing.py
- tawreed_navigation.py
- tawreed_timing.py
- tawreed_checkout.py
- tawreed_search_logic.py
- tawreed_artifacts.py

**التعديل:**
- إضافة `from __future__ import annotations` في أعلى الملف
- إضافة `from typing import TYPE_CHECKING`
- نقل استيرادات Playwright إلى كتلة `if TYPE_CHECKING:`
- المثال:
```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page, Locator
```

### النوع 2: استخدام فعلي (Actual Usage)
**الملفات (6 ملفات):**
- tawreed_order_placement.py
- tawreed_cart_flow.py
- tawreed_order_match.py
- tawreed_headless_auth_refresh.py
- tawreed.py
- tawreed_api_client.py

**التعديل:**
- حذف الاستيراد من مستوى الوحدة
- إضافة الاستيراد داخل الدالة التي تستخدمه فعلياً (lazy import)
- المثال:
```python
def place_order_from_items(...):
    from playwright.sync_api import sync_playwright
    # استخدام sync_playwright هنا
```

## النتيجة النهائية
- ✅ صفر استيرادات Playwright على مستوى الوحدة خارج TYPE_CHECKING
- ✅ يمكن استيراد أي وحدة tawreed دون تثبيت playwright
- ✅ الاختبارات النقية لا تنهار بغياب المتصفح
- ✅ الفصل الصحيح بين طبقات core و tawreed محقق
- ✅ **المجموع الكلي: 23 ملفاً (17 TYPE_CHECKING + 6 lazy imports)**

## التحقق
```bash
grep -rn "^from playwright\|^import playwright" src/tawreed/
# النتيجة: صفر استيرادات على مستوى الوحدة
```

## معيار النجاح
`python -m pytest --co -q` ⇒ 0 أخطاء جمع عند غياب playwright
