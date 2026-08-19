# PharmaSupplyBot

أداة محلية لإدارة مطابقة أصناف المخزون مع منتجات Tawreed، وتجهيز الطلبات،
ومراجعة الحالات التي تحتاج قرارًا بشريًا.

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
- سياسة اختيار المخازن تحت `warehouse_strategy`.
- حدود المطابقة المحلية وخيارات حفظ المراجعة اليدوية تحت `matching`.

ضع بيانات الاتصال المحلية المطلوبة في `.env`. لا تضع أسرارًا في ملفات YAML أو في المستودع.

## أوامر الطرفية

```bash
# تسجيل الدخول وحفظ الجلسة
py run.py auth --profile wardany

# تصدير كتالوج المنتجات
py run.py export-products --profile wardany

# مطابقة ملف مخزون محليًا
py run.py match-products --profile wardany --excel data/input/inventory.xlsx \
  --tawreed-csv artifacts/wardany/tawreed_products.csv --trace

# تنفيذ المطابقة فقط، من دون إضافة أصناف إلى السلة
py run.py order --profile wardany --excel data/input/order.xlsx --match-only

# إنشاء طلب
py run.py order --profile wardany --excel data/input/order.xlsx

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

يمكن تشغيل الواجهة الرسومية لمراجعة هذه النتائج:

```bash
py -m streamlit run streamlit_app.py
```

## التحقق محليًا

```bash
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m compileall -q src tests run.py streamlit_app.py
```

على Linux/macOS استبدل مسار مفسر Windows بـ `.venv/bin/python`.

## هيكل مختصر

- `src/core/drug_matching/`: الفهرسة، التطبيع، والتسجيل المحلي للمطابقة.
- `src/tawreed/`: التكامل مع Tawreed وتدفق الطلبات.
- `src/core/manual_review/`: قواعد وملفات المراجعة اليدوية.
- `src/ui/`: واجهة Streamlit.
- `tests/`: اختبارات الوحدة والتكامل المحلي.
