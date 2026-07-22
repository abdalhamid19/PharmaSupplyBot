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

### 5. تشغيل كل الصيدليات المعرفة في `config.yaml`

Windows PowerShell:
```powershell
py run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --all-profiles
```

Linux / macOS (bash):
```bash
python3 run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --all-profiles
```

### 6. فتح المتصفح أثناء التشغيل للتشخيص

Windows PowerShell:
```powershell
py run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --debug-browser
```

Linux / macOS (bash):
```bash
python3 run.py order --excel "data/input/order_items/shortage_report_total_20260422.xlsx" --profile wardany --debug-browser
```

### 7. تشغيل أكثر من worker للأصناف داخل نفس الصيدلية

استخدم `--item-workers N` لتقسيم ملف Excel الواحد على أكثر من عملية Chromium معزولة لنفس الـ profile. القيمة الافتراضية `1`، ويمكن ضبطها أيضًا من `runtime.item_workers` داخل `config.yaml`. ابدأ بقيمة صغيرة مثل `2`، ولا ترفعها كثيرًا لأن كل worker يفتح Chromium مستقل ويستخدم نفس جلسة `state/<profile>.json` للقراءة فقط.

Windows PowerShell:
```powershell
py run.py order --excel "data/input/order_items/shortage_report_total_20260502.xlsx" --profile wardany --limit 10 --item-workers 2 --debug-browser
```

Linux / macOS (bash):
```bash
python3 run.py remove-cart --excel "data/input/remove_items/remove.xlsx" --profile wardany --item-workers 2
```

### 8. حذف أصناف من سلة المشتريات

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

### 9. تشغيل واجهة Streamlit

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
- استخدم `--fast-search` لتقليل زمن البحث عن الصنف؛ يتوقف عند أول نتيجة مطابقة مقبولة بدل تجربة صيغ إضافية.
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

## Logging

كل أمر CLI يستخدم نظام تسجيل موحّد قائم على stdlib
`logging`. تُكتب السجلات إلى:

- **stderr**: سجلات بمستوى `INFO+` افتراضياً (أو `WARNING+` مع `--quiet`).
- `logs/app.log`: كل شيء من مستوى `DEBUG+`، تدوير يومي، 14 نسخة احتياطية.
- `logs/errors.log`: `ERROR+` فقط (مفصل للمراقبة).

### خيارات CLI للـ logging

```bash
# زيادة مستوى التفاصيل
py run.py auth --log-level DEBUG --profile wardany

# كتم ما دون التحذيرات على stderr (الملفات تبقى تكتب كل شيء)
py run.py --quiet auth --profile wardany

# إخراج JSON صالح للتحليل الآلي (مفيد لـ CI و log aggregators)
py run.py --json-logs auth --profile wardany

# قيمة غير معروفة تُرفض من argparse
py run.py --log-level BOGUS auth --help
# exit 2
```

### كتابة logging في module جديد

```python
import logging

logger = logging.getLogger(__name__)


def do_thing(profile: str) -> None:
    logger.info("starting work", extra={"profile": profile})
    try:
        ...
    except SomeError:
        logger.exception("work failed for profile")
```

القواعد (مُتحقَّقة بـ CI guards في `tests/core/test_logging_audit.py`):

- ❌ لا `print(...)` في `src/`
- ❌ لا `logging.basicConfig(...)` خارج `src/cli/logging_setup.py`
- ❌ لا أسماء logger حرفية (استخدم `__name__`)
- ❌ لا معالجة يدوية لـ handlers
- ❌ لا `_console_safe(...)` — كان workaround قديم

### فحص الـ logging

```bash
py scripts/audit_logging.py
```

يُولّد تقرير markdown في `docs/audit_logging.md` بأعداد كل الانتهاكات.
اليوم كل الأرقام صفر. انظر `docs/logging_system.md` للتفاصيل الكاملة.

## تحسينات واجهة الـCLI (Stage 1)

مجموعة تحسينات على تجربة الاستخدام اليومية للأوامر، كلها backward compatible:

### 1. ملف إعدادات شخصي + `--preset`

بدل تكرار `--profile wardany --config state/config.yaml` في كل أمر، احفظ defaults + presets في `~/.pharmabotrc`:

```yaml
# ~/.pharmabotrc (أو ./.pharmabotrc لتجاوز محلي)
default:
  --profile: wardany
  --config: state/config.yaml

presets:
  # تشغيل سريع: 20 صنف، بدون إضافة للسلة
  quick-dry-run:
    --limit: 20
    --match-only: true
    --execution-mode: auto
    --item-workers: 4

  # طلب كامل بمساعدة AI مع سياسة صارمة
  ai-strict:
    --ai: true
    --execution-mode: auto
    --ai-verify-policy: score
    --ai-search-policy: safe
    --ai-accept-confidence: 0.95
```

**Precedence** (من الأعلى للأقل):
```
CLI args > --preset > ./.pharmabotrc > ~/.pharmabotrc > built-in defaults
```

أي flag تكتبه على الـcommand line يفوز على الـpreset والـfile.

**الاستخدام:**

```powershell
# بدل كده (144 حرف)
py run.py order --profile wardany --config state/config.yaml --excel data/inv.xlsx --limit 20 --match-only --execution-mode auto --item-workers 4

# كده (76 حرف — نقص 47%)
py run.py order -e data/inv.xlsx --preset quick-dry-run
```

### 2. اختصارات للأعلام المتكررة

| Shortcut | Long form | Subcommands |
|---|---|---|
| `-p` | `--profile` | كل الأوامر الخمسة |
| `-c` | `--config` | كل الأوامر الخمسة |
| `-x` | `--excel` | `order`, `remove-cart`, `match-products` |
| `-n` | `--limit` | `order`, `match-products`, `export-products` |

الشكل الكامل بيشتغل زي الأول — مفيش breaking changes.

### 3. إكمال تلقائي للـShell (Tab completion)

بعد تثبيت واحد لكل shell:

```bash
# bash
eval "$(py run.py --show-completion bash)"

# zsh
eval "$(py run.py --show-completion zsh)"

# fish
py run.py --show-completion fish | source
```

بعدها الـTab بيكمّل:
- أسماء الـsubcommands الخمسة
- flags الـsubcommand الحالي (طويلة وقصيرة)
- القيم المسموحة للـenum flags (مثلاً `--execution-mode` → `auto api browser`)

مصدر الحقيقة واحد: `build_parser()`. أي subcommand أو flag جديد بيظهر تلقائياً في الـcompletion.

### 4. ملخص موحّد في نهاية كل أمر

كل أمر بيطبع block ثابت بعد ما يخلص:

```text
✅ order completed
   - processed    20
   - matched      14
   - flagged      1
   - duration     25s
   - summary      artifacts\order\wardany\20260722_1411
```

- **stdout** مع `✅` عند النجاح، **stderr** مع `❌` عند الفشل (عشان يبان حتى لو الـoutput بيتـpipe)
- مخفي تحت `--quiet` (cron-friendly)
- الـfields بتختلف حسب الأمر (الـorder بيعرض processed/matched/flagged، الـauth بيعرض profiles، إلخ)

## ملاحظات إضافية

- محددات العناصر `selectors` قابلة للتعديل من `config.yaml` إذا تغيّرت واجهة Tawreed.
- المطابقة تعتمد على خوارزميات نصية مرنة (Fuzzy matching) يمكن ضبط معاملاتها من الإعدادات.
- البرنامج يدعم الاستكمال (Resume) حيث يتخطى الأصناف التي تم طلبها بنجاح في نفس اليوم.

