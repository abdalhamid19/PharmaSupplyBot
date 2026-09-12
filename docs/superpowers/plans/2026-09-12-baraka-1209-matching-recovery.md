# خطة استعادة المطابقة الآمنة لكتالوج البركة 1209

> **For agentic workers:** استخدم مهارة `executing-plans` ونفّذ المهام بالترتيب، مع مراجعة نتيجة كل بوابة قبل الانتقال.

**Goal:** تسجيل ملف `البركه 1209.xlsx` كهدف مستقل، ثم استعادة المطابقات التي تثبت هويتها وخصائصها، مع إبقاء المنتجات الملتبسة أو الناقصة للمراجعة.

**Architecture:** يفصل التنفيذ بين اختيار ملف الكتالوج، وإثبات الهوية بين الاسم الإنجليزي والصف العربي، والتحقق من التركيز والشكل والعبوة، ثم اختيار العرض/تنفيذ الطلب. تُضاف أسماء ثنائية اللغة موثقة ومحددة بالهدف؛ ولا تُستخدم زيادة درجات التشابه لتجاوز بوابات التوافق.

**Tech Stack:** Python، openpyxl، YAML، pytest، ومخرجات CSV/JSONL لوضع المطابقة فقط.

**Spec:** طلب المستخدم الحالي وقائمة الأصناف الاثني عشر؛ خط الأساس في `artifacts/excel-target/البركة شركات/20260912_1730/match_only_summary_البركة شركات.csv`؛ والكتالوج المقصود `data/input/excel target/البركه 1209.xlsx`.

## الأدلة الحالية

- تقرير 17:30 شغّل هدف `البركة شركات`، ومصدر الصفوف الناجحة فيه `البركة شركات.xlsx`؛ الملف `البركه 1209.xlsx` ليس هدفاً مسجلاً في `state/config.yaml`.
- في ذلك التقرير، طابق `SYNOBAR-S` بالفعل، وظهر لـ`DURJOY` مرشح مراجعة رُفض لنقص دليل العبوة، بينما غابت الهوية عن ثمانية أصناف، ومنعت موافقتان قديمتان بلا row key `LEVOFLOXACIN-EVA` و`OMEGAL ULTRA` من متابعة البحث الاعتيادي. هذه نتيجة هدف `البركة شركات`، وليست نتيجة ملف 1209.
- ملف 1209 عربيّ الأسماء، فلا تظهر فيه أي من الأسماء الإنجليزية الاثني عشر حرفياً. إعادة تشغيل المطابق على هذا الملف تعرّفت تلقائياً على `LEVOFLOXACIN-EVA` و`OMEGAL ULTRA`، ووجدت لـ`DURJOY` مرشحاً رفضه لأن عدد الأقراص غير مثبت؛ الأصناف التسعة الأخرى لم تملك دليلاً آلياً للهوية.
- توجد أسماء عربية محتملة في الصفوف المذكورة أدناه، لكن وجود الاسم القريب لا يثبت دائماً القوة أو الشكل أو حجم العبوة. `LIMITLESS MILGA MAX` تحديداً لا يملك صفاً مثبتاً له في الكتالوج؛ توجد منتجات LIMITLESS أخرى منفصلة.
- تشغيل الطلب عبر Tawreed مسار آخر: في تشغيل 11:25 أضيفت عشرة أصناف، وتخطى Levofloxacin وSynobar بسبب مقارنة السعر، وكان Pencitard مطلوباً بكمية 14 ونُفذ منه 1؛ كما طابق Limitless بديلاً خاطئاً هو `LIMITLESS MAN MAX`. لا تُحسب تلك النتائج دليلاً على أن ملف 1209 استُخدم.

## القيود العامة

- اربط المفتاح `البركه 1209` بالملف ذي الاسم نفسه؛ لا تغيّر افتراضياً هدف `البركة شركات` ولا تخلط نتائج الكتالوجين.
- لا تقبل صفاً عربياً بلا دليل هوية معروف أو alias معتمد ومحدد للهدف.
- يجب أن تبقى بوابات التركيز والشكل والعبوة قائمة؛ المعلومة غير الموجودة في الصف تعني مراجعة أو رفضاً، لا قبولاً تلقائياً.
- يجب أن تكون مطابقة Excel المحلية حتمية ودون استدعاء ترجمة مباشرة؛ أي ترجمة جماعية تبقى في خطوة pre-translation الصريحة.
- لا تطابق `LIMITLESS MILGA MAX` مع `LIMITLESS MAN MAX`، ولا تنشئ صفاً بديلاً من قاموس Tawreed.
- افصل في التقارير بين `matched-only` واختيار المورد والسعر والكمية التي أضيفت فعلياً.
- اختبر قرارات المراجعة على قاعدة بيانات مؤقتة؛ لا تعدّل قرارات المستخدم المحفوظة أو بقية تغييرات مساحة العمل.

---

## خريطة الملفات

- `state/config.yaml`: تعريف مفتاح الكتالوج الجديد وظهوره في قائمة الأهداف.
- `src/core/excel_target/excel_target_matching.py`: مسار تجاوز المطابقة الاعتيادية عند وجود قرار قديم غير قابل لإعادة الربط.
- `src/cli/commands/cli_order_excel_target.py`: تشغيل Excel-target عبر CLI يجب أن يستخدم الفهارس المحلية/المخزنة فقط.
- `src/core/excel_target/excel_target_identity.py` و`src/core/excel_target/excel_target_aliases.py`: مصادر الهوية والـaliases المحددة بهدف البركة.
- `src/core/normalization/normalizer_parsing_normalize.py` وملفات تحليل خصائص المنتج في `src/core/normalization/` و`src/core/excel_target/product_attributes.py`: اختصارات الاسم والعبوة/التركيز.
- `tests/cli/commands/test_excel_target_e2e.py`: اختيار الهدف والملف في مسار CLI.
- `tests/core/excel_target/test_baraka_safe_matching.py` و`tests/core/excel_target/test_excel_target_aliases.py` و`tests/core/excel_target/test_product_attributes.py`: اختبارات الأمان والهوية والخصائص.
- `tests/core/excel_target/fixtures/`: سجل ذهبي صغير يربط أسماء الطلب بصفوف الكتالوج وتوقع المطابقة أو المراجعة.

## Task 1: سجّل الملف باسم هدف مستقل واختبر اختيار المصدر

**Files:**
- Modify: `state/config.yaml`
- Test: `tests/cli/commands/test_excel_target_e2e.py`
- Test fixture: `tests/cli/commands/fixtures/excel_target_with_target.yaml`

- [ ] أضف `البركه 1209` إلى `excel_targets` و`user_added_targets` في `state/config.yaml`، مع `name_col: الصنف` و`price_col: سعر ج` و`discount_col: شركات` و`header_row: 0`، واترك اختيار أول sheet أو سمِّ sheet الموجودة `محروس ص` صراحةً. طابق هجاء المفتاح مع اسم الملف كي يحل المسار الافتراضي إلى `data/input/excel target/البركه 1209.xlsx`.
- [ ] أضف fixture مصغّراً بثلاثة أعمدة وبـsheet/header مماثلين، واختبر أن `selected_excel_target_configs` يختار الهدف الجديد ويحمل ملفه، وأن هدف `البركة شركات` يبقى مرتبطاً بملفه القديم.
- [ ] شغّل بوابة الاختبار: `.\.venv\Scripts\python.exe -m pytest -q tests\core\excel_target\test_excel_target.py tests\cli\commands\test_excel_target_e2e.py`.

**Expected:** يستقبل مفتاح `البركه 1209` ملفه، ولا تتغير مسارات الأهداف الحالية الأخرى.

## Task 2: أصلح رجوع المطابقة بعد قرار محفوظ قديم

**Files:**
- Modify: `src/core/excel_target/excel_target_matching.py`
- Test: `tests/core/excel_target/test_baraka_safe_matching.py`

- [ ] أضف اختباراً يحاكي موافقة محفوظة بلا `excel_target_row_key`، ويجعل المنتج المسجل غائباً عن الكتالوج الحالي، مع وجود هوية حالية صالحة لنفس عنصر الطلب. أثبت أن فشل إعادة الربط يُسجل ثم تستمر المطابقة الاعتيادية، بدلاً من إرجاع `Saved product is absent from current Excel file` وإخفاء المرشح الحالي.
- [ ] أضف اختباراً مقابلاً يثبت أن قرارات `not_matching` و`needs_correction` الصريحة تظل مانعة للمطابقة التلقائية.
- [ ] عدّل `_scoped_manual_review`/`ExcelTargetMatcher.match` بحيث يكون فشل إعادة ربط موافقة قديمة غير مانع للبحث الحالي، مع الإبقاء على تحقق target/row key والتوافق قبل تطبيق أي موافقة محفوظة.
- [ ] شغّل: `.\.venv\Scripts\python.exe -m pytest -q tests\core\excel_target\test_baraka_safe_matching.py`.

**Expected:** عند إعادة استخدام هدف `البركة شركات`، لا تعيد موافقة قديمة بلا row key وحُذف صفها قرار رفض نهائي قبل البحث الاعتيادي؛ يستمر البحث ويصدر نتيجة أو مراجعة حسب أدلة الكتالوج الحالي. موافقات الصفوف المحددة تُطبق فقط عند تطابق المفتاح والمصدر والصف. هذا الإصلاح وحده لا يضمن استعادة `LEVOFLOXACIN-EVA` أو`OMEGAL ULTRA`؛ يتطلب ذلك أيضاً هوية صالحة وتوافق الخصائص. الهدف الجديد `البركه 1209` لا يرث تلقائياً قرارات الهدف القديم.

## Task 3: ثبّت سجل الصفوف الاثني عشر ونتيجة كل حالة

**Files:**
- Create: `tests/core/excel_target/fixtures/baraka_1209_gold_labels.csv`
- Test: `tests/core/excel_target/test_baraka_safe_matching.py`

- [ ] أضف سجلاً لكل item code/اسم، ورقم صف المصدر، والاسم العربي الخام، والحالة المتوقعة (`auto_match`, `review`, `no_match`) وسببها. ابدأ بمراجعة هذه الصفوف المؤكدة في الملف؛ الأسماء العربية مرشحة للربط فقط إلى أن يثبت صاحب الكتالوج خصائصها:

| Item code | الاسم في الطلب | صف/اسم الكتالوج المحتمل | نقطة التحقق |
|---|---|---|---|
| 23031 | `ELBAVIT SYP 60 ML` | 353 `البافيت بالحديد 60مل شراب`؛ 354 `البافيت كالسيوم 60مل شراب` | مكوّن الحديد/الكالسيوم يترك الحالة ملتبسة |
| 64430 | `DURJOY 60 MG 3 TAB` | 2115 `ديورجوى 60 مجم اقراص` | عدد الأقراص 3 غير مذكور |
| 73151 | `PENCITARD 1200000 i.u vial` | 1229 `بنسيتارد فيال` | قوة 1,200,000 IU غير مثبتة |
| 74209 | `PROTOFIX 40MG 14 TAB` | 1073 `بروتوفكس40مجم اقراص س ج` | حجم عبوة 14 غير مذكور |
| 74659 | `ZOLADEX DEPOT 3.6 MG AM` | 2311 `زولاديكس 3.6مجم 1سرنجة` | معنى `AM` وتوافق الشكل يحتاجان توثيقاً |
| 80532 | `LOGUSGYN 10 SUPPOSITORIES` | 3725 `لوجس جين لبوس مهبلي` | عبوة 10 غير مذكورة |
| 81148 | `SYNOBAR-S SOAP 100GM` | 2796 `سينوبار اس صابونة` | الوزن 100 جم غير مذكور |
| 87486 | `CONVENTIN XR 300 MG 30 TABS` | 3546 `كونفينتين 300 اكس ار ممتد المفعول ق` | عبوة 30 غير مذكورة |
| 88189 | `LEVOFLOXACIN-EVA 500 MG 10 F.C.TABS.` | 3808 `ليفوفلوكساسين ايفا 500مجم 10اقراص` | تحقّق أن التطبيع يستخرج عبوة 10 أقراص |
| 90893 | `quadriderm cream 15g` | 3431 `كوادريدرم كريم س ج` | حجم 15 جم غير مذكور |
| 90993 | `OMEGAL ULTRA 30CAP` | 791 `اوميجال الترا 30كبسولة` | تحقّق من تطابق الاسم والعبوة |
| 92558 | `LIMITLESS MILGA MAX 30 TABS` | لا يوجد صف يثبت نسخة `MILGA MAX` | لا تستخدم منتج LIMITLESS آخر كبديل |
- [ ] لا تصنّف المرشح كـ`auto_match` اعتماداً على التشابه وحده. أبقِ ELBAVIT للمراجعة لوجود الحديد والكالسيوم كصفين؛ وابقِ pack/strength/form غير المثبت في DURJOY وPENCITARD وPROTOFIX وZOLADEX وLOGUSGYN وSYNOBAR-S وCONVENTIN وQUADRIDERM للمراجعة أو الرفض.
- [ ] سجّل LEVOFLOXACIN-EVA وOMEGAL ULTRA كحالتَي قبول فقط إذا بقي row name والعبوة متوافقين بعد إصلاح التحليل. سجّل LIMITLESS كـ`no_match` ما لم يظهر صف مستقل موثق لـ`MILGA MAX`؛ لا تستخدم `ليمتلس باور ماكس` أو`ميلجا ادفانس` كبديل.
- [ ] اكتب اختباراً يقرأ الـfixture ويقارن كل قرار بالمطابقة الفعلية على بيانات عربية مصطنعة مكافئة، حتى لا يعتمد الاختبار الآلي على ملف المستخدم المحلي غير المتعقب.

**Expected:** كل واحدة من الاثنتي عشرة لها نتيجة معللة قابلة للمراجعة، ولا يتحول نقص بيانات العبوة إلى قبول صامت.

## Task 4: أضف aliases محددة بالهدف وطبّع الاختصارات المثبتة

**Files:**
- Modify: `src/core/excel_target/excel_target_aliases.py`
- Modify: `src/core/excel_target/excel_target_identity.py`
- Modify: `src/core/excel_target/excel_target_matching.py`
- Modify: `src/cli/commands/cli_order_excel_target.py`
- Modify: `src/core/normalization/normalizer_parsing_normalize.py` وأداة تحليل الخصائص ذات الصلة
- Test: `tests/core/excel_target/test_excel_target_aliases.py`
- Test: `tests/core/excel_target/test_product_attributes.py`

- [ ] أضف مساراً لتمرير aliases معتمدة ومحددة بـ`target_key=البركه 1209` إلى فهرس الهوية، مع مصدر/مرجع صف لكل alias. لا تضع أسماء هذا الكتالوج في قاموس عام يؤثر على أهداف أخرى. حافظ على حد alias الحالي (درجة 96 وهامش 4) وعلى تحقق التوافق بعد اكتشاف الهوية.
- [ ] أضف فقط aliases التي يثبتها سجل الصفوف أو قاموس موثوق: الاسم الإنجليزي، النص العربي المطابق للصف، والخصائص المتاحة. إذا لم تثبت خاصية لازمة، يجب أن ينتج المرشح مراجعة لا قبولاً.
- [ ] أضف اختبارات تطبيع مستقلة على الإدخالات الحرفية `ELBAVIT SYP` و`PENCITARD 1200000 i.u vial` و`LEVOFLOXACIN-EVA 500 MG 10 F.C.TABS.`؛ يجب أن تتعرف على شراب، و`1200000 IU`، وعبوة 10 أقراص مغلفة. لا تعرّف `AM` كـampoule عاماً؛ لا تضف هذا التفسير لـZOLADEX إلا إذا وثّق مرجع المنتج أنه المقصود.
- [ ] اجعل `run_excel_target_match_only_multi` يستخدم `allow_live_translation=False` افتراضياً؛ أضف اختباراً يثبت أن مسار المطابقة لا يستدعي مزوّد ترجمة. تبقى ترجمة الكتالوج خطوة منفصلة وصريحة عبر أداة pre-translation.
- [ ] أضف حواجز سلبية: اختلاف نسخة ELBAVIT (حديد/كالسيوم)، غياب قوة PENCITARD، غياب عدد الأقراص/الوزن، ورفض `LIMITLESS MAN MAX` أمام `LIMITLESS MILGA MAX`.
- [ ] شغّل: `.\.venv\Scripts\python.exe -m pytest -q tests\core\excel_target\test_excel_target_aliases.py tests\core\excel_target\test_product_attributes.py tests\core\excel_target\test_baraka_safe_matching.py`.

**Expected:** يمكن توليد مرشحين للتهجئات الثنائية اللغة الموثقة، لكن المطابقة التلقائية تظل مشروطة بتوافق الجرعة والشكل والعبوة وعدم وجود التباس.

## Task 5: أعد تشغيل الهدف الصحيح وافصل المطابقة عن التوريد

**Files:**
- Test: `tests/cli/commands/test_excel_target_e2e.py`
- Test: `tests/core/excel_target/test_baraka_safe_matching.py`
- Output: ملف CSV/JSONL مؤقت للمقارنة، بلا تعديل لكتالوج المستخدم

- [ ] شغّل تقرير التغطية على الطلب الفعلي والهدف الجديد:

```powershell
.\.venv\Scripts\python.exe scripts\baraka_coverage_report.py `
  --config state\config.yaml `
  --excel data\input\order_items\12092026.xlsx `
  --target-key "البركه 1209" `
  --target-path "data\input\excel target\البركه 1209.xlsx" `
  --limit 2000 `
  --output-prefix "$env:TEMP\baraka-1209-after"
```

- [ ] راجع صفوف الأكواد الاثني عشر في التقرير؛ يجب أن يرتبط التقرير بمفتاح `البركه 1209` وحجم كتالوجه، وأن تطابق كل نتيجة تصنيف السجل الذهبي. لا تشترط وجود `source_file` في الصفوف التي لم تنتج مرشحاً؛ تحقّق من اسم المصدر عند وجود مرشح أو منتج فقط. سجّل منفصلةً عدد المطابقات التلقائية، المرشحين للمراجعة، والرفض مع السبب.
- [ ] شغّل بوابة Excel Target وCLI: `.\.venv\Scripts\python.exe -m pytest -q tests\core\excel_target tests\cli\commands\test_excel_target_e2e.py`.
- [ ] أنشئ نسخة مؤقتة من الإعداد تجعل `database.order_runs_path` في `%TEMP%`، ثم اختبر المسار كاملاً. أنشئ النسخة دون تعديل إعداد المستخدم هكذا:

```powershell
@'
from pathlib import Path
import os
import yaml

config = yaml.safe_load(Path("state/config.yaml").read_text(encoding="utf-8"))
temp_dir = Path(os.environ["TEMP"])
config.setdefault("database", {})["order_runs_path"] = str(temp_dir / "baraka-1209-order-runs.db")
target = temp_dir / "baraka-1209-test-config.yaml"
target.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
print(target)
'@ | .\.venv\Scripts\python.exe -
```

ثم نفّذ:

```powershell
.\.venv\Scripts\python.exe run.py order `
  --config "$env:TEMP\baraka-1209-test-config.yaml" `
  --excel data\input\order_items\12092026.xlsx `
  --excel-target "البركه 1209" `
  --excel-target-only `
  --match-only `
  --limit 2000 `
  --execution-mode api `
  --item-workers 1
```

تحقق أن سجل الهدف يحمل `matching_source=excel-target` و`matching_source_label=excel-target:البركه 1209@البركه 1209.xlsx`، وأنه لم يضف للسلة.
- [ ] قارن مع تشغيل `20260912_1125`: سجّل أن Levofloxacin وSynobar تم تخطيهما وقتها بسبب مقارنة السعر، وأن PENCITARD طلب 14 لكن المنفذ كان 1، وأن نتيجة LIMITLESS MAN MAX غير صحيحة ولا تُحسب كاستعادة ناجحة لمطابقة `MILGA MAX`.

**Expected:** يصبح ممكناً تمييز عدم تحميل الملف من فقدان الهوية، وفشل التوافق، أو اختيار السعر/الكمية. لا يُعلن نجاح الحالة إلا إذا تطابق اسم المنتج وخصائصه ومصدر الصف.
