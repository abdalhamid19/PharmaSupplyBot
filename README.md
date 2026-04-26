# PharmaSupplyBot

بوت لأتمتة إدخال أصناف من Excel على `seller.tawreed.io` وإنشاء الطلبيات لكل صيدلية بدون تدخل بشري بعد إعداد جلسة تسجيل الدخول مرة واحدة.

## المتطلبات

- Python 3.10+ (عندك 3.13 شغال)

## التثبيت

```bash
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py -m playwright install
```

## الإعداد

1) انسخ ملف الإعدادات:

```bash
copy config.example.yaml config.yaml
```

2) (اختياري) ضع بيانات الدخول في `.env`:

```bash
copy .env.example .env
```

## تسجيل الدخول (مرة واحدة لكل صيدلية)

يفتح متصفح مرئي لتسجل دخول يدويًا، ثم يحفظ الجلسة في `state/<profile>.json`:

```bash
py run.py auth --profile wardany
```

## تشغيل الأتمتة (بدون تدخل بشري)

```bash
py run.py order --excel "input/shortage_report_total_20260422.xlsx" --profile wardany
```

بشكل افتراضي البوت يضيف الأصناف ويترك اعتماد الطلبية للمراجعة البشرية. لو أردت الإرسال التلقائي لاحقًا غيّر `runtime.submit_order` إلى `true` في `config.yaml`.

لإظهار المتصفح أثناء تشخيص التنفيذ:

```bash
py run.py order --excel "input/shortage_report_total_20260422.xlsx" --profile wardany --debug-browser
```

أو تشغيل كل الصيدليات المعرفة في `config.yaml`:

```bash
py run.py order --excel "input/shortage_report_total_20260422.xlsx" --all-profiles
```

## ملاحظات مهمة

- واجهة الموقع قد تتغير؛ لذلك كل محددات العناصر (selectors) قابلة للتعديل من `config.yaml`.
- لو الموقع فيه CAPTCHA أو تحقق إضافي، هتحتاج تعمل `auth` يدويًا من وقت لآخر لتجديد الجلسة.

