# PharmaSupplyBot

بوت لأتمتة إدخال أصناف من ملف Excel على `seller.tawreed.io` وإنشاء الطلبيات لكل صيدلية بعد حفظ جلسة تسجيل الدخول مرة واحدة.

## المتطلبات

- Python 3.10 أو أحدث
- Bash (Linux/macOS) أو Windows PowerShell

## التثبيت

### Windows PowerShell
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m playwright install
```

### Linux / macOS (bash)
```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m playwright install
```

## الإعداد

انسخ ملف الإعدادات:

### Windows PowerShell
```powershell
Copy-Item config.example.yaml config.yaml
```

### Linux / macOS (bash)
```bash
cp config.example.yaml config.yaml
```

إذا أردت استخدام البريد وكلمة المرور من البيئة:

### Windows PowerShell
```powershell
Copy-Item .env.example .env
```

### Linux / macOS (bash)
```bash
cp .env.example .env
```

## أوامر الطرفية

### 1. تسجيل الدخول وحفظ الجلسة
يفتح المتصفح بشكل مرئي، وبعد تسجيل الدخول تُحفظ الجلسة في `state/<profile>.json`.

Windows PowerShell:
```powershell
py run.py auth --profile wardany
```

Linux / macOS (bash):
```bash
python3 run.py auth --profile wardany
```

### 2. تشغيل الطلب من ملف Excel

Windows PowerShell:
```powershell
py run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --profile wardany
```

Linux / macOS (bash):
```bash
python3 run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --profile wardany
```

### 3. تشغيل عدد محدود من الأصناف

Windows PowerShell:
```powershell
py run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --limit 5
```

Linux / macOS (bash):
```bash
python3 run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --limit 5
```

### 4. تشغيل البحث السريع

يستخدم `--fast-search` أول مطابقة مقبولة بدل تجربة صيغ بحث إضافية، وهذا يقلل زمن إضافة الصنف عندما تكون نتائج Tawreed واضحة.

Windows PowerShell:
```powershell
py run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --fast-search
```

Linux / macOS (bash):
```bash
python3 run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --fast-search
```

### 5. تشغيل مطابقة الأصناف فقط بدون إضافة للسلة

استخدم `--match-only` لتشغيل خوارزمية المطابقة وتسجيل النتائج داخل
`artifacts/order/<profile>/<run_id>/` بدون الضغط على زر السلة أو إضافة أي صنف.
هذا الوضع مفيد لمراجعة وتحسين خوارزمية التطابق بأمان.

ملف `match_only_summary.csv` يحتوي صفًا لكل مرشح تم تقييمه، ويتضمن بيانات Tawreed/API المهمة مثل `productId` و`storeProductId` و`productNameEn` و`productName` و`availableQuantity` و`productsCount` و`storeName` و`discountPercent` و`salePrice` و`retailPrice`، بالإضافة إلى درجات التطابق وسبب القبول/الرفض ونسخة JSON مضغوطة من المرشح داخل `api_raw_candidate_json`.

كل تشغيل order يضيف أيضًا ملفات مراجعة سهلة داخل نفس مجلد التشغيل:
`order_item_summary_<run_id>.csv/.txt` كسطر مختصر لكل صنف،
`order_ai_trace_<run_id>.csv/.txt` كتتبع تفصيلي لقرارات AI ونتائج API،
و`manual_review_<run_id>.csv/.txt` للأصناف التي تحتاج مراجعة يدوية.

Windows PowerShell:
```powershell
py run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --match-only
```

Linux / macOS (bash):
```bash
python3 run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --match-only
```

يمكن تفعيل AI Matching داخل order اختيارياً. عند القبول بثقة كافية يمكن للـ AI
تأكيد أو اختيار match نشط، أما الثقة المنخفضة أو رفض review فيذهب إلى
`manual_review` ولا يدخل السلة:

```bash
python3 run.py order --profile wardany \
  --excel "data/input/order_items/shortage_report_total_20260502.xlsx" \
  --limit 1 --match-only --ai --provider rotation --review-model rotation
```

### 6. تشغيل كل الصيدليات المعرفة في `config.yaml`

Windows PowerShell:
```powershell
py run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --all-profiles
```

Linux / macOS (bash):
```bash
python3 run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --all-profiles
```

### 7. فتح المتصفح أثناء التشغيل للتشخيص

Windows PowerShell:
```powershell
py run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --debug-browser
```

Linux / macOS (bash):
```bash
python3 run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --debug-browser
```

### 8. تشغيل أكثر من worker للأصناف داخل نفس الصيدلية

استخدم `--item-workers N` لتقسيم ملف Excel الواحد على أكثر من عملية Chromium معزولة لنفس الـ profile. القيمة الافتراضية `1`، ويمكن ضبطها أيضًا من `runtime.item_workers` داخل `config.yaml`. ابدأ بقيمة صغيرة مثل `2`، ولا ترفعها كثيرًا لأن كل worker يفتح Chromium مستقل ويستخدم نفس جلسة `state/<profile>.json` للقراءة فقط.

Windows PowerShell:
```powershell
py run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --limit 10 --item-workers 2
```

Linux / macOS (bash):
```bash
python3 run.py remove-cart --excel "data/input/remove_items/remove.xlsx" --profile wardany --item-workers 2
```

### 9. حذف أصناف من سلة المشتريات

ضع ملف الحذف داخل `data/input/remove_items/` ويجب أن يحتوي على الأعمدة:
`كود` و`إسم الصنف`.

Linux / macOS (bash):
```bash
python3 run.py remove-cart --excel "data/input/remove_items/remove.xlsx" --profile wardany
```

Windows PowerShell:
```powershell
py run.py remove-cart --excel "data/input/remove_items/remove.xlsx" --profile wardany
```

### 10. تصدير كل أصناف Tawreed

استخدم `export-products` لسحب كتالوج أصناف Tawreed المتاح للحساب المحفوظ في
`state/<profile>.json`. ينشئ الأمر ثلاثة ملفات بنفس البيانات داخل مجلد تشغيل:

- `artifacts/export-products/<profile>/<run_id>/tawreed_products_<run_id>.csv`
- `artifacts/export-products/<profile>/<run_id>/tawreed_products_<run_id>.xlsx`
- `artifacts/export-products/<profile>/<run_id>/tawreed_products_<run_id>.txt`

الأعمدة الناتجة ثابتة: `product_name_ar` و`product_name_en` و`store_product_id`.
يمكن استخدام `--limit` لاختبار عدد صغير أولًا، واتركه `0` لتصدير كل الأصناف.

Windows PowerShell:
```powershell
py run.py export-products --profile wardany --output-dir "artifacts/{profile}" --limit 10
```

Linux / macOS (bash):
```bash
python3 run.py export-products --profile wardany --output-dir "artifacts/{profile}" --limit 10
```

### 11. مطابقة ملف أصناف مع كتالوج Tawreed المصدر

استخدم `match-products` لمطابقة ملف مخزون/نواقص مع أحدث Tawreed catalog في
`artifacts/export-products/<profile>/...` أو legacy fallback. يعمل الأمر بالخوارزمية فقط عند
استخدام `--no-ai`، أو يحاول مراحل AI عند توفر مفاتيح API في `.env`.

Linux / macOS (bash):
```bash
python3 run.py match-products --profile wardany \
  --excel "data/input/order_items/shortage_report_total_20260502.xlsx" \
  --limit 5 --no-ai --trace
```

Windows PowerShell:
```powershell
py run.py match-products --profile wardany `
  --excel "data/input/order_items/shortage_report_total_20260502.xlsx" `
  --limit 5 --no-ai --trace
```

ينشئ الأمر ملف نتائج CSV وملف manual review، وعند تفعيل `--trace` يكتب trace
تفصيليًا داخل `artifacts/match-products/<profile>/<run_id>/`.

## تنظيم artifacts

كل أمر جديد يكتب داخل مجلد تشغيل مستقل:

- `artifacts/order/<profile>/<run_id>/`
- `artifacts/match-products/<profile>/<run_id>/`
- `artifacts/export-products/<profile>/<run_id>/`
- `artifacts/remove-cart/<profile>/<run_id>/`
- `artifacts/run-control/<command>/`

داخل `artifacts/order/<profile>/<run_id>/` تظهر الملفات التالية عند توفر بياناتها:

- `order_item_summary_<run_id>.csv/.txt`: صف واحد مختصر لكل صنف يوضح هل تم
  العثور على match، اسم المنتج المختار، هل تم AI verify/search/review، درجات
  الثقة، والحركة النهائية.
- `order_ai_trace_<run_id>.csv/.txt`: تتبع تفصيلي لكل صنف مع تركيز على AI،
  ويشمل مراحل verify/search/review ومحاولات provider/model عندما تكون متاحة.
- `manual_review_<run_id>.csv/.txt`: الأصناف المرفوضة أو منخفضة الثقة أو غير
  المتاحة، مع حقول جاهزة لقرار المراجعة اليدوية.

الملفات القديمة نُقلت إلى `artifacts/legacy/...` بدل حذفها.

### 12. تشغيل واجهة Streamlit

الرابط الأونلاين:
```text
https://mahrouspharmacies-pharmasupplybot.streamlit.app/
```

لتشغيلها محليًا:

Windows PowerShell:
```powershell
cd PharmaSupplyBot
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python -m streamlit run streamlit_app.py
```

Linux / macOS (bash):
```bash
cd PharmaSupplyBot
source .venv/bin/activate
python3 -m streamlit run streamlit_app.py
```

## فحص الكود محليًا

تشغيل فحص القواعد المحلي:

Windows PowerShell:
```powershell
cd PharmaSupplyBot
.\.venv\Scripts\python tools\rule_audit.py
```

Linux / macOS (bash):
```bash
cd PharmaSupplyBot
python3 tools/rule_audit.py
```

إذا كان كل شيء سليمًا فسيظهر:

```text
rule_audit_ok
```

قبل كل `push` نفّذ:

```bash
cd PharmaSupplyBot
.venv/bin/python -m unittest discover -s tests -q
.venv/bin/python tools/rule_audit.py
```

ملاحظة:
- `rule_audit.py` يمنع المخالفات الجديدة، ويسمح بخفض المخالفات القديمة تدريجيًا أثناء refactor.
- GitHub Actions يشغل نفس الفحوصات تلقائيًا بعد كل `push` و`pull request`.

## سلوك التنفيذ الحالي

- افتراضيًا البوت يضيف الأصناف إلى السلة فقط.
- استخدم `--fast-search` لتقليل زمن البحث عن الصنف؛ يتوقف عند أول نتيجة مطابقة مقبولة بدل تجربة صيغ إضافية.
- استخدم `--match-only` لتسجيل نتائج المطابقة فقط في `match_only_summary.csv` بدون إضافة أي صنف إلى السلة.
- استخدم `--item-workers N` لتشغيل order/remove-cart بالتوازي داخل profile واحد. عند التوازي تُكتب ملخصات مؤقتة بصيغة `*.worker_<id>.*` ثم تُدمج في الملخص الأساسي بعد انتهاء workers.
- اعتماد الطلبية النهائي لا يتم تلقائيًا إلا إذا كان:
  - `runtime.submit_order: true` داخل `config.yaml`
- إذا كانت الجلسة منتهية أو غير صالحة، سيطلب منك البرنامج إعادة تنفيذ:

```powershell
py run.py auth --profile wardany
```

## ملفات مهمة

- `config.yaml`
  إعدادات التشغيل الفعلية
- `config.example.yaml`
  مثال جاهز لهيكل الإعدادات
- `state/<profile>.json`
  جلسة Playwright المحفوظة لكل صيدلية
- `data/input/order_items/`
  ملفات Excel التي تحتوي الأصناف المطلوب رفعها/طلبها على موقع توريد
- `data/input/prevented_items/`
  ملفات Excel الخاصة بالأصناف الممنوعة من الطلب، والافتراضي `drugprevented.xlsx`
- `data/input/remove_items/`
  ملفات Excel التي تحتوي الأصناف المطلوب حذفها من سلة مشتريات توريد
- `artifacts/<command>/<profile>/<run_id>/`
  مجلدات تشغيل مستقلة لكل أمر مع أسماء ملفات موقّتة.
- `artifacts/order/<profile>/<run_id>/order_item_summary_*.csv`
  الملخص الأساسي لنتائج تشغيل الطلبات أو `--match-only`.
- `artifacts/order/<profile>/<run_id>/order_ai_trace_*.csv`
  سجل تفصيلي لكل مراحل المطابقة وAI الخاصة بالـ order.
- `artifacts/order/<profile>/<run_id>/manual_review_*.csv`
  قائمة الأصناف التي تحتاج قرارًا يدويًا قبل الطلب.
- `artifacts/legacy/`
  مخرجات البنية القديمة بعد الترحيل.
- `streamlit_app.py`
  واجهة Streamlit لتشغيل `auth` و`order` ومراجعة النتائج

## ملاحظات

- محددات العناصر `selectors` قابلة للتعديل من `config.yaml` إذا تغيّرت واجهة Tawreed.
- المطابقة بين اسم Excel ونتائج Tawreed تعتمد على الاسم فقط، وليس على كود الصنف الداخلي للصيدلية.
- عند فشل صنف تقنيًا، تُحفظ artifacts داخل مجلد تشغيل الأمر الحالي.


في تبويب `Results`:
- يتم عرض `CSV` و`XLSX` في تبويبين منفصلين
- إذا كان `order_result_summary.xlsx` أقدم من `order_result_summary.csv` ستظهر ملاحظة بذلك داخل الواجهة

عند استخدام النسخة الأونلاين:
- شغّل `py run.py auth --profile <profile>` محليًا مرة واحدة
- ثم ارفع ملف `state/<profile>.json` داخل تبويب `Order`
- إذا لم ترفع الملف، فستستخدم الواجهة أي default state مهيأ على الخادم لنفس الـ profile إذا كان موجودًا

## هيكل المشروع (للتحسين والصيانة)

تم تنظيم الكود البرمجي في حزم منفصلة لزيادة الوضوح:
- `src/tawreed/`: منطق العمل الخاص بموقع توريد (تسجيل الدخول، الطلب، الحذف).
- `src/ui/`: منطق واجهة Streamlit.
- `src/cli/`: منطق أوامر الطرفية (CLI).
- `src/core/`: النماذج (Models) والأدوات الأساسية المشتركة.
  - `src/core/config/`: معالجة ملفات الإعدادات.
  - `src/core/utils/`: أدوات معالجة Excel والمتصفح.

## ملفات مهمة

- `config.yaml`: إعدادات التشغيل الفعلية (معدلات المطابقة، الروابط، الحسابات).
- `config.example.yaml`: مثال مرجعي للإعدادات.
- `streamlit_app.py`: نقطة انطلاق واجهة الويب.
- `run.py`: نقطة انطلاق أوامر الطرفية.
- `data/input/`: المجلد الرئيسي لملفات Excel المدخلة.
- `state/<profile>.json`: ملفات حفظ الجلسة.
- `artifacts/<profile>/`: نتائج التشغيل (Summaries, Screenshots, Logs).

## ملاحظات إضافية

- محددات العناصر `selectors` قابلة للتعديل من `config.yaml` إذا تغيّرت واجهة Tawreed.
- المطابقة تعتمد على خوارزميات نصية مرنة (Fuzzy matching) يمكن ضبط معاملاتها من الإعدادات.
- البرنامج يدعم الاستكمال (Resume) حيث يتخطى الأصناف التي تم طلبها بنجاح في نفس اليوم.
