# PharmaSupplyBot

بوت لأتمتة إدخال أصناف من ملف Excel على `seller.tawreed.io` وإنشاء الطلبيات لكل صيدلية بعد حفظ جلسة تسجيل الدخول مرة واحدة.

## المتطلبات

- Python 3.10 أو أحدث
- Windows PowerShell

## التثبيت

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m playwright install
```

## الإعداد

انسخ ملف الإعدادات:

```powershell
Copy-Item config.example.yaml config.yaml
```

إذا أردت استخدام البريد وكلمة المرور من البيئة:

```powershell
Copy-Item .env.example .env
```

## أوامر الطرفية

### 1. تسجيل الدخول وحفظ الجلسة

يفتح المتصفح بشكل مرئي، وبعد تسجيل الدخول تُحفظ الجلسة في `state/<profile>.json`:

```powershell
py run.py auth --profile wardany
```

يمكن زيادة وقت الانتظار قبل إغلاق نافذة تسجيل الدخول:

```powershell
py run.py auth --profile wardany --wait-seconds 900
```

### 2. تشغيل الطلب من ملف Excel

```powershell
py run.py order --excel "input/shortage_report_total_20260422.xlsx" --profile wardany
```

### 3. تشغيل عدد محدود من الأصناف

```powershell
py run.py order --excel "input/shortage_report_total_20260422.xlsx" --profile wardany --limit 5
```

### 4. تشغيل كل الصيدليات المعرفة في `config.yaml`

```powershell
py run.py order --excel "input/shortage_report_total_20260422.xlsx" --all-profiles
```

### 5. فتح المتصفح أثناء التشغيل للتشخيص

```powershell
py run.py order --excel "input/shortage_report_total_20260422.xlsx" --profile wardany --debug-browser
```

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
