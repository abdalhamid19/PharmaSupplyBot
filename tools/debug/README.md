# Debug Tools

أدوات تشخيص وفحص لمشاكل موقع Tawreed.

## الملفات

### debug_login_page.py
يفتح صفحة تسجيل الدخول ويحلل محتواها:
- يحفظ HTML الكامل
- يأخذ screenshot
- يبحث عن حقول البريد وكلمة المرور

```bash
python3 tools/debug/debug_login_page.py
```

### test_login_headless.py
اختبار تسجيل دخول headless سريع:
```bash
python3 tools/debug/test_login_headless.py
```

### test_login_proper.py
اختبار تسجيل دخول مع form validation:
```bash
python3 tools/debug/test_login_proper.py
```

## النتائج

النتائج تُحفظ في `artifacts/debug/`:
- `login_page.html` - HTML الخام
- `login_page.png` - صورة للصفحة
- `login_test_result.txt` - نتيجة الاختبار
