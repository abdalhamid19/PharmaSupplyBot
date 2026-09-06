# تحقيق مطابقة «البركة شركات»

هذا المجلد يوثق التحقيق فقط. لا يحتوي على إصلاح لخوارزمية الإنتاج، ولا يغيّر نتيجة الطلب أو السلة.

## النتيجة المختصرة

الادعاء صحيح ومؤكد: مسار Excel target يقبل تطابقات دوائية خاطئة، بينما تشغيل Tawreed API في الأثر المتاح طابق 46 من أول 50 عنصرًا. السبب الأساسي ليس ملف Excel تالفًا ولا المتصفح ولا Cohere؛ بوابة قبول matcher المحلية تقبل أي candidate لا يملك أرقامًا زائدة، دون تطبيق حدود الثقة الموجودة في الإعدادات. ويتضاعف الخطر لأن حارس هوية العلامة التجارية معطّل لكل `excelTarget`، مع أن «البركة شركات» Arabic-only.

ابدأ من [01_reproduction_and_evidence.md](01_reproduction_and_evidence.md)، ثم [02_hypotheses_and_scores.md](02_hypotheses_and_scores.md). التنفيذ المقترح، الذي ينتظر الموافقة، في [04_execution_plan.md](04_execution_plan.md).

## ملفات الاختبار

- `tests/diagnostics/test_baraka_matching_hypotheses.py`: اختبارات سبب المشكلة؛ النتيجة الحالية: 2 فشل مقصود + 4 نجاح.
- `tests/diagnostics/test_baraka_solution_scorecard.py`: عقد اختيار الحل؛ النتيجة الحالية: 1 فشل مقصود + 2 نجاح.

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\diagnostics\test_baraka_matching_hypotheses.py tests\diagnostics\test_baraka_solution_scorecard.py
```

بعد الإصلاح لا يجوز تحويل هذه الاختبارات إلى `xfail` أو حذفها؛ نجاحها هو تعريف حل المشكلة.

