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
py run.py order --excel "input/order_items/shortage_report_total_20260422.xlsx" --profile wardany
```

Linux / macOS (bash):
```bash
python3 run.py order --excel "input/order_items/shortage_report_total_20260422.xlsx" --profile wardany
```

### 3. تشغيل عدد محدود من الأصناف

Windows PowerShell:
```powershell
py run.py order --excel "input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --limit 5
```

Linux / macOS (bash):
```bash
python3 run.py order --excel "input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --limit 5
```

### 4. تشغيل كل الصيدليات المعرفة في `config.yaml`

Windows PowerShell:
```powershell
py run.py order --excel "input/order_items/shortage_report_total_20260422.xlsx" --all-profiles
```

Linux / macOS (bash):
```bash
python3 run.py order --excel "input/order_items/shortage_report_total_20260422.xlsx" --all-profiles
```

### 5. فتح المتصفح أثناء التشغيل للتشخيص

Windows PowerShell:
```powershell
py run.py order --excel "input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --debug-browser
```

Linux / macOS (bash):
```bash
python3 run.py order --excel "input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --debug-browser
```

### 6. حذف أصناف من سلة المشتريات

ضع ملف الحذف داخل `input/remove_items/` ويجب أن يحتوي على الأعمدة:
`كود` و`إسم الصنف`.

Linux / macOS (bash):
```bash
python3 run.py remove-cart --excel "input/remove_items/remove.xlsx" --profile wardany
```

Windows PowerShell:
```powershell
py run.py remove-cart --excel "input/remove_items/remove.xlsx" --profile wardany
```

### 7. تشغيل واجهة Streamlit

الرابط الأونلاين:
```text
https://mahrouspharmacies-pharmasupplybot.streamlit.app/
```

لتشغيلها محليًا:

Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python -m streamlit run streamlit_app.py
```

Linux / macOS (bash):
```bash
source .venv/bin/activate
python3 -m streamlit run streamlit_app.py
```

## فحص الكود محليًا

تشغيل فحص القواعد المحلي:

Windows PowerShell:
```powershell
.\.venv\Scripts\python tools\rule_audit.py
```

Linux / macOS (bash):
```bash
python3 tools/rule_audit.py
```

إذا كان كل شيء سليمًا فسيظهر:

```text
rule_audit_ok
```

قبل كل `push` نفّذ:

```bash
.venv/bin/python -m unittest discover -s tests -q
.venv/bin/python tools/rule_audit.py
```

ملاحظة:
- `rule_audit.py` يمنع المخالفات الجديدة، ويسمح بخفض المخالفات القديمة تدريجيًا أثناء refactor.
- GitHub Actions يشغل نفس الفحوصات تلقائيًا بعد كل `push` و`pull request`.

## سلوك التنفيذ الحالي

- افتراضيًا البوت يضيف الأصناف إلى السلة فقط.
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
- `input/order_items/`
  ملفات Excel التي تحتوي الأصناف المطلوب رفعها/طلبها على موقع توريد
- `input/prevented_items/`
  ملفات Excel الخاصة بالأصناف الممنوعة من الطلب، والافتراضي `drugprevented.xlsx`
- `input/remove_items/`
  ملفات Excel التي تحتوي الأصناف المطلوب حذفها من سلة مشتريات توريد
- `artifacts/<profile>/`
  صور وHTML وlogs تشخيصية عند الفشل
- `artifacts/<profile>/match_log_all.txt`
  سجل نصي لكل مرشحي المطابقة
- `artifacts/<profile>/match_log_all.csv`
  سجل CSV لكل مرشحي المطابقة
- `artifacts/<profile>/order_result_summary.csv`
  الملخص الأساسي لنتائج التشغيل، وهو المصدر الأحدث المعتمد للتحليل
- `artifacts/<profile>/order_result_summary.xlsx`
  نسخة Excel من ملخص النتائج إذا كانت موجودة
- `streamlit_app.py`
  واجهة Streamlit لتشغيل `auth` و`order` ومراجعة النتائج

## ملاحظات

- محددات العناصر `selectors` قابلة للتعديل من `config.yaml` إذا تغيّرت واجهة Tawreed.
- المطابقة بين اسم Excel ونتائج Tawreed تعتمد على الاسم فقط، وليس على كود الصنف الداخلي للصيدلية.
- عند فشل صنف تقنيًا، تُحفظ artifacts داخل `artifacts/<profile>/`.


في تبويب `Results`:
- يتم عرض `CSV` و`XLSX` في تبويبين منفصلين
- إذا كان `order_result_summary.xlsx` أقدم من `order_result_summary.csv` ستظهر ملاحظة بذلك داخل الواجهة

عند استخدام النسخة الأونلاين:
- شغّل `py run.py auth --profile <profile>` محليًا مرة واحدة
- ثم ارفع ملف `state/<profile>.json` داخل تبويب `Order`
- إذا لم ترفع الملف، فستستخدم الواجهة أي default state مهيأ على الخادم لنفس الـ profile إذا كان موجودًا

## سلوك التنفيذ الحالي

- افتراضيًا البوت يضيف الأصناف إلى السلة فقط.
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
- `artifacts/<profile>/`
  صور وHTML وlogs تشخيصية عند الفشل
- `artifacts/<profile>/match_log_all.txt`
  سجل نصي لكل مرشحي المطابقة
- `artifacts/<profile>/match_log_all.csv`
  سجل CSV لكل مرشحي المطابقة
- `artifacts/<profile>/order_result_summary.csv`
  الملخص الأساسي لنتائج التشغيل، وهو المصدر الأحدث المعتمد للتحليل
- `artifacts/<profile>/order_result_summary.xlsx`
  نسخة Excel من ملخص النتائج إذا كانت موجودة
- `streamlit_app.py`
  واجهة Streamlit لتشغيل `auth` و`order` ومراجعة النتائج

## فحص الكود محليًا

تشغيل فحص القواعد المحلي:

```powershell
.\.venv\Scripts\python tools\rule_audit.py
```

إذا كان كل شيء سليمًا فسيظهر:

```text
rule_audit_ok
```

## ملاحظات

- محددات العناصر `selectors` قابلة للتعديل من `config.yaml` إذا تغيّرت واجهة Tawreed.
- المطابقة بين اسم Excel ونتائج Tawreed تعتمد على الاسم فقط، وليس على كود الصنف الداخلي للصيدلية.
- عند فشل صنف تقنيًا، تُحفظ artifacts داخل `artifacts/<profile>/`.
