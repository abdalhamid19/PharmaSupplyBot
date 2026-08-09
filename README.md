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

### 9. فحص نماذج الذكاء الاصطناعي (test-models)

يبعت طلبًا حقيقيًا واحدًا لكل `(provider, model)` معرّف في إعدادات `ai.providers.*` ويطبع تقريرًا فيه:
حالة كل نموذج (OK/FAIL)، تصنيف الصحة (working / quota-limited / permission-failed / model-not-accessible / degraded)،
زمن الاستجابة (latency) بالثواني، كود HTTP، وسبب الفشل بالضبط (نوع الخطأ + رسالة الـ API).
كما يحفظ التقرير الكامل في `output/api_model_tests/ai_models_test_<timestamp>.csv` و`.json`.

قائمة النماذج المفحوصة تُقرأ من أول ملف موجود بالترتيب:
`state/config.yaml` (الملف النشط وقت التشغيل) ثم `config.yaml` ثم `config.example.yaml`.
مزوّد مكتوب فيه `models: []` (قائمة فارغة) يُتخطّى تمامًا — فلو فضّيت مزوّدًا من `state/config.yaml` لن يدخل في الفحص.
مزوّد بدون مفاتيح API صالحة في `.env` يُتخطّى أيضًا.

Windows PowerShell:
```powershell
py run.py test-models
```

Linux / macOS (bash):
```bash
python3 run.py test-models
```

خيارات مفيدة:
- `--provider google,mistral` — فحص مزوّدات محددة فقط (افتراضيًا: الكل).
- `--all-keys` — فحص كل مفتاح API × كل نموذج (افتراضيًا: أول مفتاح لكل نموذج).
- `--timeout 30` / `--concurrency 6` / `--max-tokens 64` — ضبط مهلة الطلب والتوازي وحجم الرد.
- `--format json|plain` — إخراج آلي بدل الجدول.
- الخروج بكود `0` لو في نموذج واحد على الأقل شغال، و`1` لو كله فاشل.

> ملاحظة: الفحص يستهلك quota — طلب واحد لكل نموذج.

### 10. تشغيل واجهة Streamlit

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

## إعدادات الذكاء الاصطناعي (`ai:` في `config.yaml`)

كل إعدادات الـ AI (الموديلات، الـ rotation pools، مفاتيح الـ providers)
تعيش تحت مفتاح `ai:` واحد في `config.yaml`. هذا يحل محل ثلاثة
مصادر متناثرة كانت موجودة قبل ذلك:

  1. متغيرات بيئية (`AI_MODEL`, `FALLBACK_MODELS`, `REVIEW_MODEL`,
     `AI_REVIEW_THRESHOLD`, `{PROVIDER}_MODELS`) — كانت الإعدادات
     الأساسية في `.env`.
  2. tuples الـ rotation (`GROQ_MODELS`, `OPENCODE_MODELS`, ...) في
     `src/core/drug_matching/ai/ai_rotation_config.py`.
  3. dict الـ `PROVIDERS` (base_url / env_keys / account_id_env) في
     `src/core/drug_matching/config/config_providers.py`.

كل المصادر الثلاثة بقت declarative في الـ YAML تحت `ai:`، مع
الحفاظ على `.env` كـ override per-run فقط.

### الـ precedence chain

كل قيمة `ai.*` تتحلّل بهذا الترتيب (الأعلى يفوز):

```
1. CLI flag / explicit constructor argument
   (مثل: --model openai/gpt-4o-mini)
2. Environment variable override
   (AI_MODEL / FALLBACK_MODELS / REVIEW_MODEL / AI_REVIEW_THRESHOLD)
3. ai: block في config.yaml
4. Hardcoded default في الـ dataclass
```

ولـ per-provider model pool (اللي بيستخدمه `ai_rotation` و `config_helpers.resolve_api_config`):

```
1. {PROVIDER}_MODELS env var (CSV)       ← override per-run، بيكسب لو مش فاضي
2. ai.providers.{name}.models من YAML    ← الـ rotation pool الكامل
3. ai.providers.{name}.default_model     ← موديل واحد بس (بيرجع لأول عنصر في models لو مش مكتوب)
4. _FALLBACK_PROVIDER_METADATA في الكود  ← آخر معقل، alias قديم للـ tests
```

#### الـ `default_model` (الموديل المبدئي لكل provider)

ده الموديل اللي بيُستخدم لما `--model` flag مش متحدد. بيتحلّل بالترتيب:

| المصدر | الشرط | النتيجة |
|---|---|---|
| `ai.providers.{name}.default_model` في YAML | مكتوب صراحةً كـ string | يستخدم القيمة دي |
| `ai.providers.{name}.models[0]` | الـ YAML فيه `models:` لكن مفيش `default_model:` | أول عنصر في القائمة |
| (مفيش pool) | مفيش models خالص | الـ provider بيـ skip — الـ consumer يرجع لـ `_FALLBACK_PROVIDER_METADATA` |

**مثال:**

```yaml
ai:
  providers:
    groq:
      default_model: "openai/gpt-oss-120b"   # ← meta.default_model (case A)
      models:
        - "openai/gpt-oss-120b"
        - "meta-llama/llama-4-scout-17b-16e-instruct"
        - "llama-3.3-70b-versatile"
```

لما `--provider groq` بدون `--model` → يستخدم `openai/gpt-oss-120b`.
لما `--provider rotation` → يجرّب الـ models بالترتيب: GPT-OSS → Llama-4 → Llama-3.3.

#### الـ `models` (الـ rotation pool)

ده **قائمة الموديلات** اللي `ai_rotation._provider_models` بيمشي عليها لو واحد فشل. بيتحلّل:

1. `{PROVIDER}_MODELS` env var (CSV، مثل `GROQ_MODELS="llama-3.3-70b,llama-3.1-8b"`) — لو فاضي اتخطاه
2. `ai.providers.{name}.models` من YAML (list أو string CSV)
3. لو الاتنين فاضيين → الـ provider بيـ skip بالكامل

#### الـ `meta` في الـ hardcoded fallback

الـ `_FALLBACK_PROVIDER_METADATA` في `src/core/drug_matching/config/config_models.py:342` فيه 8 providers (groq, cloudflare, openrouter, cerebras, google, mistral, github, opencode) — ده الـ layer الأخير اللي بيضمن إن في default حتى لو الـ YAML فاضي. الـ `PROVIDERS` dict في `config_providers.py` مجرد alias قديم ليه.

### الهيكل

```yaml
ai:
  # الـ verification model الأساسي (OpenRouter)
  primary_model: "minimax-m2.5-free"
  # قائمة الـ fallback لما الـ primary يفشل
  fallback_models:
    - "nemotron-3-super-free"
    - "hy3-preview-free"
    - "trinity-large-preview-free"
  # الـ model اللي بيعمل cross-check لو الـ verdict أقل من review_threshold
  review_model: "big-pickle"
  # الـ confidence threshold — أي verdict أقل من ده بيروح manual review
  review_threshold: 0.95

  # كل provider (8 مدعومين): base_url + env_keys + account_id_env + models
  providers:
    groq:
      default_model: "openai/gpt-oss-120b"
      base_url: "https://api.groq.com/openai/v1"
      env_keys: ["GROQ_API_KEY_1", "GROQ_API_KEY"]
      models:
        - "openai/gpt-oss-120b"
        - "meta-llama/llama-4-scout-17b-16e-instruct"
        - ...
    cloudflare:
      default_model: "@cf/openai/gpt-oss-120b"
      base_url: ""     # مش مستخدم — الـ URL مشتق من account_id
      env_keys:
        - "CLOUDFLARE_API_TOKEN_1"
        - "CLOUDFLARE_API_TOKEN_2"
        - ...
        - "CLOUDFLARE_API_TOKEN"   # legacy single-key
      account_id_env: "CLOUDFLARE_ACCOUNT_ID"
      models:
        - "@cf/openai/gpt-oss-120b"
        - ...
    openrouter:  # providers مشابهين لـ cerebras / google / mistral / github / opencode
      default_model: "..."
      base_url: "https://openrouter.ai/api/v1"
      env_keys: ["OPENROUTER_API_KEY_1", "OPENROUTER_API_KEY"]
      models: [...]
```

### كيف تضيف provider جديد

1. ضيف block جديد تحت `ai.providers.<name>` في `config.yaml`
   (base_url / env_keys / default_model / models).
2. ضيف الـ env vars في `.env`.
3. لو الـ provider جديد على `PROVIDER_ORDER` (rotation policy):
   عدّل `src/core/drug_matching/ai/ai_rotation_config.py`.

### الـ API اللي بيستهلك الـ `ai:` block

في `src/core/drug_matching/config/`:

  * `AIConfig.from_sources(...)` → resolved `AIConfig` dataclass
    مع `providers: tuple[ProviderPool, ...]`.
  * `AIConfig.provider(name)` → `ProviderPool | None`
    (case-insensitive lookup).
  * `get_provider_metadata(name)` → `ProviderMetadata | None`
    (base_url / env_keys / account_id_env).
  * `ProviderPool(name, default_model, models)` و
    `ProviderMetadata(name, base_url, env_keys, account_id_env)`
    هم الـ frozen dataclasses المعروضة.

### Override per-run

```bash
# جرّب model مختلف على Tawreed:
GROQ_MODELS="llama-3.3-70b-versatile,llama-3.1-8b-instant" \
  py run.py order --profile wardany --provider groq

# أو فعّل rotation كامل مع override للـ primary:
AI_MODEL=openai/gpt-5 \
  py run.py order --provider rotation --review-model gemini-2.5-pro
```

### الـ backwards compatibility

`PROVIDERS` dict في `config_providers.py` لسه موجود (alias for legacy
tests)، لكن لا تضيف عليه — استخدم `ai.providers.<name>` في الـ YAML.

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

# إخراج JSON صالح للتحليل الآلي (مفيد لـ CI و log aggregators).
# الـ flag اتغير من --json-logs لـ --json-log-records للوضوح بين logs و data.
py run.py --json-log-records auth --profile wardany

# تلوين الـ console output بـ Rich (الـ files تبقى plain text للـ aggregators)
py run.py --rich-logs auth --profile wardany

# قيمة غير معروفة تُرفض قبل الـ command (Typer callback → exit 2)
py run.py --log-level BOGUS auth --help
# exit 2
```

### Output formats (--format)

كل subcommand بيطلّع بيانات (export-products, match-products, remove-cart, order)
يدعم ثلاث صيغ:

```bash
# human (default): Rich-rendered table على TTY، plain TSV لو piped
py run.py export-products --profile wardany

# json: envelope {"ok": true, "data": [...]} على stdout، stderr للـ diagnostics
py run.py export-products --profile wardany --format json | jq .

# plain: TSV rows على stdout (grep-friendly، بدون ألوان)
py run.py export-products --profile wardany --format plain | head
```

الـ `--format` flag موجود حتى على `auth` (no-op هناك) عشان يبقى الـ UX ثابت.

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

