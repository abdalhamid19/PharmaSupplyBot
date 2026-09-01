# PharmaSupplyBot

أداة محلية لإدارة مطابقة أصناف المخزون مع منتجات Tawreed، وتجهيز الطلبات،
ومراجعة الحالات التي تحتاج قرارًا بشريًا. يدعم المطابقة على Tawreed مباشرة
وعلى Excel target catalogs (مثل vendor pricelists) باستخدام نفس خوارزمية
المطابقة ونفس المراجعة اليدوية.

## المتطلبات

- Python 3.11 أو أحدث
- متصفح Chromium عند تشغيل تدفقات المتصفح
- بيانات الدخول وإعدادات Tawreed في ملف البيئة المحلي

## التثبيت

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item config.example.yaml state/config.yaml
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
cp config.example.yaml state/config.yaml
```

## الإعداد

راجع `state/config.yaml` واضبط:

- أعمدة ملف Excel تحت `excel`.
- الصيدليات تحت `profiles`.
- محددات الواجهة تحت `selectors` عند تغير موقع Tawreed.
- سياسة اختيار المخازن unter `warehouse_strategy`.
- حدود المطابقة المحلية وخيارات حفظ المراجعة اليدوية unter `matching`.
- كاتالوجات Excel targets (موردين/صيدليات بديلة) unter `excel_targets`.

ضع بيانات الاتصال المحلية المطلوبة في `.env`. لا تضع أسرارًا في ملفات YAML أو في المستودع.

### Excel Target Source

قسم `excel_targets` يعرّف كاتالوجات Excel تعمل كمصدر مطابقة بديل أو مكمّل
لـ Tawreed. كل entry هو ملف XLSX بصيغة vendor/pharmacy pricelist
(اسم الصنف، السعر، الخصم) ويوضع افتراضيًا في `data/input/excel target/<key>.xlsx`.
خوارزمية المطابقة واحدة في الحالتين: نفس الـ queries، نفس الـ scoring،
ونفس قواعد المراجعة اليدوية. الفرق الوحيد أن سطح البحث يكون in-memory
catalog بدل HTTP/API/Playwright.

```yaml
excel_targets:
  alnasr:
    display_name: "صيدلية النصر"
    name_col: "صنف"
    price_col: "سعر"
    discount_col: "الخصم"
    sheet: ""
    header_row: 0
    enabled: true
```

## أوامر الطرفية

```bash
# تسجيل الدخول وحفظ الجلسة
py run.py auth --profile wardany

# تصدير كتالوج المنتجات
py run.py export-products --profile wardany

# تنفيذ المطابقة فقط، من دون إضافة أصناف إلى السلة
py run.py order --profile wardany --excel data/input/order.xlsx --match-only

# إنشاء طلب
py run.py order --profile wardany --excel data/input/order.xlsx

# مطابقة على Tawreed profile + Excel target catalog في نفس التشغيل
py run.py order --profile wardany --excel-target alnasr --excel data/input/order.xlsx --match-only

# مطابقة على كل الـ Excel targets المعرّفة
py run.py order --all-excel-targets --excel data/input/order.xlsx --match-only

# تجاوز مسار الكاتالوج لـ Excel target معيّن
py run.py order --excel-target alnasr \
    --excel-target-path alnasr=data/input/excel target/alnasr.xlsx \
    --excel data/input/order.xlsx --match-only

# حذف أصناف محددة من السلة
py run.py remove-cart --profile wardany --excel data/input/items.xlsx
```

استخدم `--help` مع أي أمر لعرض خياراته. مثال:

```bash
py run.py order --help
```

## المراجعة اليدوية والمخرجات

الحالات غير المحسومة أو منخفضة النتيجة تبقى للمراجعة اليدوية؛ لا تُضاف تلقائيًا إلى السلة ضمن السياسة الآمنة. ينشئ كل تشغيل ملفات مخرجات تشمل عادةً:

- `order_item_summary_*.csv`: نتيجة كل صنف.
- `manual_review_*.csv` و`manual_review_candidates_*.jsonl`: الحالات والبدائل المقترحة محليًا.
- `order_matching_trace_*.csv`: أثر قرار المطابقة المحلي.
- `excel_target_summary_<key>.csv`: نتيجة المطابقة لكل Excel target (نفس بنية `order_item_summary`).

النتائج من Tawreed ومن Excel targets تُكتب في نفس قواعد البيانات
(`state/order_runs.db` و `state/manual_review_decisions.db`)، فتعمل أدوات
Manual Review و Run DB على المصدرين بدون أي تمييز.

يمكن تشغيل الواجهة الرسومية لمراجعة هذه النتائج:

```bash
py -m streamlit run streamlit_app.py
```

في تبويب "Run Order"، استبدل "Run target" القديم بمتعدد اختيار (multiselect)
يجمع Tawreed profiles و Excel targets في مكان واحد؛ يمكن اختيار أي توليفة
(profile فقط، Excel target فقط، أو الاتنين معًا) في نفس التشغيل.

## التحقق محليًا

```bash
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m compileall -q src tests run.py streamlit_app.py
```

على Linux/macOS استبدل مسار مفسر Windows بـ `.venv/bin/python`.

## هيكل مختصر

- `src/core/drug_matching/`: الفهرسة، التطبيع، والتسجيل المحلي للمطابقة.
- `src/core/excel_target/`: تحميل ومطابقة كاتالوجات Excel targets.
- `src/tawreed/`: التكامل مع Tawreed وتدفق الطلبات.
- `src/core/manual_review/`: قواعد وملفات المراجعة اليدوية.
- `src/ui/`: واجهة Streamlit.
- `tests/`: اختبارات الوحدة والتكامل_local.
