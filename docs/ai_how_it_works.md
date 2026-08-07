# كيف يعمل الـ AI داخل PharmaSupplyBot؟

> **الجمهور**: مطوّرون جدد على المشروع، أو أي شخص يريد فهم "طبقة الذكاء الاصطناعي" بدون قراءة 40 ملفًا موزعين على `src/core/drug_matching/ai/` و `verification/`.
>
> **الإصدار المرجعي**: فرع `logging_system`، الـ commit `6a18d67` (HEAD الحالي).

---

## 1. الصورة الكبيرة في 30 ثانية

PharmaSupplyBot أتمتة لـ **صيدلية الورداني** على بوابة **Tawreed**. الـ workflow اليومي:

```
Excel بالأصناف الناقصة
       │
       ▼
Phase 1 ── Fuzzy index match (محلي، بدون AI)
       │
       ▼
Phase 2 ── AI Verify  ←── أول نموذج AI يتأكد من الترشيحات "المشكوك فيها"
       │
       ▼
Phase 3 ── AI Search  ←── ثانياً، الـ AI يبحث عن أدوية ما لقتش لها match محلي
       │
       ▼
Phase 4 ── AI Review  ←── نموذج ثالث مستقل يراجع قرارات الـ AI متدنية الثقة
       │
       ▼
Phase 5 ── Order placement عبر Playwright (مفيش AI هنا)
```

كل ما يخص "الـ AI" موجود في **3 طبقات فقط**:

| الطبقة | الملف الرئيسي | المسؤولية |
|---|---|---|
| الإعدادات | `src/core/drug_matching/config/config_models.py` | يقرأ `ai:` من `state/config.yaml` ويعمل 4-layer resolution |
| الـ Rotation | `src/core/drug_matching/ai/ai_rotation.py` | يولّد قائمة `(provider, key, model)` للتجربة |
| الـ HTTP client | `src/core/drug_matching/verification/verifier.py` + `verifier_request.py` | يبعت request لـ OpenAI-compatible API ويجرب كل attempt |

**٣ مراحل AI منطقية** (`ai_verify`, `ai_search`, `ai_review`) كلها بتستخدم نفس الـ HTTP client، وبتختلف بس في الـ prompt والـ schema المتوقع في الـ JSON response.

---

## 2. من أين تأتي الـ Configuration؟ (4-layer resolution)

**File**: `src/core/drug_matching/config/config_models.py:20-113`

الكود بيقرأ `state/config.yaml` (الـ runtime-active) — ولو مش موجود يجرب `config.yaml` ثم `config.example.yaml`. كل قيمة تتحل بـ 4 طبقات من الأعلى للأقل أولوية:

```
┌─────────────────────────────────────────────┐
│ 1. CLI flag / explicit constructor arg      │  ← أعلى أولوية
├─────────────────────────────────────────────┤
│ 2. Environment variables                    │
│    AI_MODEL, FALLBACK_MODELS, REVIEW_MODEL, │
│    AI_REVIEW_THRESHOLD, {PROVIDER}_MODELS   │
├─────────────────────────────────────────────┤
│ 3. ai: block in state/config.yaml           │
├─────────────────────────────────────────────┤
│ 4. Hardcoded defaults in AIConfig dataclass │  ← أقل أولوية
└─────────────────────────────────────────────┘
```

### الـ Providers المسجّلة في YAML

في `state/config.yaml` السطور 85-292، عندك **8 providers** تحت `ai.providers.*`:

```
groq       opencode       openrouter      cerebras
google     mistral        cloudflare      github
```

كل provider فيه:

| Field | المعنى | مثال |
|---|---|---|
| `default_model` | الموديل اللي بيبدأ بيه لو مفيش `--model` flag | `groq/openai/gpt-oss-120b` |
| `models` | قائمة الـ rotation (المحاولة بالترتيب) | 9 موديلات لـ `groq`، 53 لـ `cloudflare` |
| `base_url` | رابط الـ OpenAI-compatible endpoint | `https://api.groq.com/openai/v1` |
| `env_keys` | أسماء env-vars للـ API keys (بالتوالي) | `[GROQ_API_KEY_1, GROQ_API_KEY]` |
| `account_id_env` | (Cloudflare بس) الـ account ID المرتبط | `CLOUDFLARE_ACCOUNT_ID` |

### الـ Resolution function

```python
# config_models.py:248-307
def _resolve_providers(yaml_block):
    for name in sorted(raw_providers):           # ❶ iterate alphabetically
        env_models = _split_csv(os.getenv(f"{name.upper()}_MODELS", ""))
        if env_models:                           # ❷ env wins
            models = env_models
        elif yaml_models is list:                # ❸ fall back to YAML
            models = tuple(m.strip() for m in yaml_models)
        else:
            continue                             # ❹ skip provider
        pools.append(ProviderPool(name, default, models))
```

`ProviderPool` frozen dataclass (`config_models.py:222-245`) يحمل `(name, default_model, models tuple)` ودي الـ immutable shape اللي بيشتغل بيها كل الكود downstream.

---

## 3. الـ Rotation: من provider واحد لـ "plan كامل" من المحاولات

**File**: `src/core/drug_matching/ai/ai_rotation.py`

### 3.1 الـ `AIModelAttempt` (line 20-45)

كل محاولة = tuple من:

```python
@dataclass(frozen=True, slots=True)
class AIModelAttempt:
    provider: str        # "groq"
    base_url: str        # "https://api.groq.com/openai/v1"
    key_name: str        # "GROQ_API_KEY_1"
    api_key: str         # "gsk_xxx..."  (مخفية من repr)
    model: str           # "openai/gpt-oss-120b"
    quality_rank: int    # ترتيب الجودة
    latency: float       # 9999.0 افتراضياً
    quota_remaining: float  # 0.0 افتراضياً
    eligible: bool       # هل ينفع نجرّبه؟
    disabled_until: str  # ISO timestamp لو اتعطّل مؤقتاً
    rotation_tier: int   # 1/2/3 (حسب جودة الموديل في القائمة)
```

### 3.2 بناء الـ Attempts (`_provider_attempts`)

```python
# ai_rotation.py:184+
def _provider_attempts(provider):
    meta = _resolve_meta(provider)       # ❶ ProviderMetadata
    keys = _provider_keys(meta)          # ❷ كل الـ API keys المضبوطة
    models = _provider_models(provider)  # ❸ قائمة الموديلات من YAML/env
    for key_name, key_value in keys:
        for rank, model in enumerate(models):
            attempts.append(AIModelAttempt(...))
    return attempts
```

### 3.3 الـ Tiering (`_model_tier`)

الـ models بتقسّم لـ 3 tiers بالتساوي (line 120-129):

```
9 models:
  tier-1 = models[0:3]      # الأقوى
  tier-2 = models[3:6]      # وسط
  tier-3 = models[6:9]      # الأضعف
```

### 3.4 الـ Plan الكامل (`build_request_plan`)

في `verifier_request.py:44`:

```python
plan = self._planner.build_request_plan(model)
```

الـ plan = **قائمة مسطّحة من كل الـ (key, model) combos** لكل providers اللي عندهم keys مضبوطة. مفيش هنا "primary model قبل الـ fallbacks" — **كل الـ combos بتُجرَّب بالتوازي حسب الـ semaphore** (`ai_max_concurrent: 5`).

> **مهم**: الترتيب اللي بتشوفه في الـ logs يعتمد على:
> 1. ترتيب الـ providers أبجدياً
> 2. ترتيب الـ keys داخل كل provider
> 3. ترتيب الـ models داخل كل pool
>
> مش عشوائي — لكن كمان مش "primary-first".

---

## 4. الـ HTTP Client: كيف بنبعت request وبنقرأ response

**File**: `src/core/drug_matching/verification/verifier.py` + `verifier_request.py`

### 4.1 `AIVerifier`

```python
# verifier.py:37-87
async with AIVerifier(api_cfg, max_concurrent=5) as verifier:
    await verifier.search_batch(items)
```

الـ class بتفتح `aiohttp.ClientSession` مع headers ثابتين:

```python
{
    "Content-Type": "application/json",
    "HTTP-Referer": "https://pharmasupplybot.local",
    "X-Title": "MediCompare Drug Matcher",
}
timeout = aiohttp.ClientTimeout(total=30)
```

### 4.2 تنفيذ attempt واحد (`_try_plan_item`)

```python
# verifier_request.py:83-112
async def _try_plan_item(self, item, payload, session, ...):
    key, mdl, base_url, provider = (
        item["key"], item["model"], item["base_url"], item["provider"]
    )
    combo_key = self.combo_key(key, mdl, provider)

    if combo_key in self._failed_combos:    # ❶ تخطّي الـ combos الميتة
        return last_unparseable

    payload["model"] = mdl
    headers["Authorization"] = f"Bearer {key}"

    for attempt in range(max_retries + 1):  # ❷ max_retries = 2 (default)
        async with self._semaphore:         # ❸ rate-limit
            if combo_key in self._failed_combos:
                break
            result = await self._make_single_request(...)
            if result is not None:
                if result.get("parse_failed"):
                    last_unparseable = (content, mdl)
                    break
                self.record_rotation_used(item)
                return None                  # ❹ نجاح — بنرجع فوراً
```

### 4.3 الـ Failure Tracking

كل failure (HTTP 4xx/5xx, exception, parse error) بيتمرّر على `_failure_tracker` (`verifier_request_validate.py`):

- **combo عطبان**: يتحط في `self._planner._failed_combos` — الـ attempts الجاية بتتخطاه فوراً.
- **combo عطبان permanent**: الـ `disabled_until` يتحط لـ TTL معين (`ai_provider_cooldown.py`).
- **Logging**: `log_combo_failure(...)` بيكتب سبب العطل + الـ stack excerpt.

> **النتيجة**: attempt فاشل = تتحط في الـ blacklist، الـ attempts الباقية بتكمّل. لو كلهم فشلوا → بيرجع `None` والـ Phase الـ AI بيعمل skip مع `trace.log_ai_skip(...)`.

---

## 5. الـ 3 مراحل AI بالتفصيل

كل مرحلة = prompt مختلف + schema مختلف + action مختلف على الـ DataFrame.

### 5.1 `ai_verify.py` — Phase 2: تأكيد الترشيحات

**الهدف**: الموديل المحلي رشح منتج للـ query. الـ AI يتأكد "أيّاء فعلاً نفس الدواء؟"

**متى بنبعت؟** لما الـ fuzzy match score بين `ai_verify_threshold: 80.0` و `ai_verify_threshold + 20` (الـ "fuzzy gray zone"). الـ items الواضحة (score > 95 أو exact match) ما بتبعتش للـ AI.

**الـ Schema المتوقع في الـ response**:

```json
{
  "is_correct": true,
  "confidence": 0.92,
  "reason": "same active ingredient, same strength, different brand prefix",
  "component_conflicts": []
}
```

**الـ Action على الـ DataFrame**:

```python
# ai_verify_handlers.py:_handle_rejected
if not is_correct and confidence >= 0.8:
    _clear_match(row)                          # ❶ match فاسد → unmatched
elif is_correct and confidence < ai_review_threshold:
    row["verified"] = "ai_confirmed_low_conf"   # ❷ مقبول لكن مشكل ثقة
```

**حالات الـ `verified` column**:
- `ai_confirmed` — AI وافق
- `ai_corrected` — AI غيّر الـ match لبديل أفضل
- `ai_found` — AI لقى match في الـ search phase
- `ai_rejected` — AI رفض الـ match
- `ai_confirmed_low_conf` — وافق بثقة منخفضة (رح يروح لـ Phase 4)

### 5.2 `ai_search.py` — Phase 3: البحث في الـ unmatched

**الهدف**: في الـ index مش لقى match. الـ AI يقترح اسم منتج من الذاكرة بتاعته (أو يرجّع "لا يوجد").

**متى بنبعت؟** كل صف في `results` فيه `matched_product_name_en` فاضي.

**الـ Schema**:

```json
{
  "found": true,
  "product_name_en": "PANTHENOL CREAM 5% 30G",
  "manufacturer": "Egyptian Co.",
  "confidence": 0.78
}
```

**الـ Constraint**: محدود بـ `ai_search_limit` (لو محدد) + `ai_search_candidate_limit: 5` مرشحين كحد أقصى من الـ index.

### 5.3 `ai_review.py` — Phase 4: المراجعة المستقلة

**الهدف**: موديل **مختلف** يراجع قرارات Phase 2 اللي الثقة فيها < `ai_review_threshold: 0.8`.

**الشرط**:

```python
# ai_review.py:42-51
if not api_cfg.api_key or not api_cfg.review_model:
    return results                            # skip
if api_cfg.review_model == "rotation" and not api_cfg.review_attempt_plan:
    return results
```

يعني **لو `review_model: rotation`**، الـ rotation بيختار أحسن موديل متاح (tier 1 أولاً). ده الـ default في `config.yaml` السطر 83: `review_model: big-pickle` (يعني موديل ثابت في `opencode` provider).

**الـ Action**: لو الـ reviewer رفض قرار الـ verifier → `overridden++` والـ match بيتغيّر أو يتمسح.

---

## 6. مثال عملي كامل 🚀

### الـ Setup

```yaml
# state/config.yaml
ai:
  primary_model: minimax-m2.5-free           # مفيش provider محدد — "rotation"
  fallback_models:
    - nemotron-3-super-free
    - hy3-preview-free
    - trinity-large-preview-free
  review_model: big-pickle                   # موديل ثابت في opencode
  review_threshold: 0.95
  providers:
    groq:
      default_model: openai/gpt-oss-120b
      models: [openai/gpt-oss-120b, ...9 models]
      env_keys: [GROQ_API_KEY_1, GROQ_API_KEY]
    opencode:
      default_model: big-pickle
      models: [big-pickle, ...7 models]
      env_keys: [OPENCODE_API_KEY_1, OPENCODE_API_KEY]
```

```bash
# env vars (اللي على الجهاز بتاعك)
export GROQ_API_KEY_1="gsk_xxxxx"
export OPENCODE_API_KEY_1="oc_xxxxx"
```

### الـ Excel input (3 صفوف)

| code | drug_name | كمية النقص |
|------|-----------|------------|
| 1001 | PANTHENOL CREAM 5% 30GM URICH | 5 |
| 1002 | كتافلام ٥٠ مجم اقراص | 3 |
| 1003 | سيفترياكسون 1جم حقن وريدي | 2 |

### مثال: كود 1001 — PANTHENOL

#### Phase 1 (محلي — بدون AI)

```python
parse_drug("PANTHENOL CREAM 5% 30GM URICH")
# → DrugParse(
#     normalized="panthenol cream",
#     brand="urich",
#     strength="5%",
#     form="cream",
#     modifiers=["gm"]
#   )
```

الـ index بيرجّع top 5:

| rank | matched_product_name_en | score | decision |
|------|-------------------------|-------|----------|
| 1 | URICH PANTHENOL 5% CREAM 30G | 92.5 | ✅ gray zone (80–95) |
| 2 | PANTHENOL EURAX 5% 30G | 78.3 | ❌ skip |
| 3 | PANTHENOL BEPANTHEN 5% 30G | 71.1 | ❌ skip |

> الـ score 92.5 داخل الـ AI verify range → هيتبعت للـ AI.

#### Phase 2 (AI Verify) — الـ attempt plan

```
plan = [
  # opencode (provider أبجدياً أولاً)
  (OPENCODE_API_KEY_1, "big-pickle",         "https://opencode.ai/zen/v1"),
  (OPENCODE_API_KEY_1, "nemotron-3-super-free", ...),
  (OPENCODE_API_KEY_1, "minimax-m2.5-free",  ...),
  ... (7 models × 1 key = 7 attempts)

  # groq
  (GROQ_API_KEY_1, "openai/gpt-oss-120b",  "https://api.groq.com/openai/v1"),
  (GROQ_API_KEY_1, "meta-llama/llama-4-scout-17b-16e-instruct", ...),
  ... (9 models × 1 key = 9 attempts)

  # المجموع: 16 attempts متاحة
]
```

> الـ semaphore=5 بيخلّي 5 attempts بس يـ run بالتوازي.

#### الـ Prompt اللي بيتبعت

```text
You are a pharmaceutical expert verifying whether a candidate product
is the correct match for a query drug.

QUERY: PANTHENOL CREAM 5% 30GM URICH
CANDIDATE: URICH PANTHENOL 5% CREAM 30G
PRICE QUERY: 45.00 EGP   PRICE CANDIDATE: 47.00 EGP

Check:
1. Active ingredient match
2. Strength match
3. Form match (cream/tablet/injection)
4. Manufacturer/brand plausibility

Respond ONLY with this JSON:
{"is_correct": bool, "confidence": 0.0-1.0,
 "reason": "short explanation",
 "component_conflicts": []}
```

#### الـ Successful response (مثلاً من Groq)

```json
{
  "is_correct": true,
  "confidence": 0.96,
  "reason": "Same active ingredient (panthenol), same strength (5%), same form (cream), same brand (urich)",
  "component_conflicts": []
}
```

#### تطبيق القرار على الـ DataFrame

```python
# ai_verify_handlers.py
if is_correct and confidence >= 0.8:
    row["verified"] = "ai_confirmed"
    row["ai_confidence"] = 0.96
    row["ai_reason"] = "Same active ingredient..."

# Phase 4 (Review) ما بتشتغلش — الـ confidence 0.96 > review_threshold 0.95
```

#### الـ Output النهائي

| code | drug_name | matched_product_name_en | verified | ai_confidence |
|------|-----------|-------------------------|----------|---------------|
| 1001 | PANTHENOL CREAM 5% 30GM URICH | URICH PANTHENOL 5% CREAM 30G | ai_confirmed | 0.96 |

### مثال: كود 1003 — سيفترياكسون (low confidence)

```text
QUERY: سيفترياكسون 1جم حقن وريدي
parsed: { active="ceftriaxone", strength="1g", form="injection",
          modifiers=["وريدي"] }

INDEX top-5: لا يوجود match (الـ active ingredient صحيح لكن
              الـ modifiers "وريدي" ضايعة الـ fuzzy scorer)
```

#### Phase 3 (AI Search) — مفيش match في الـ index

الـ prompt:

```text
You are a pharmaceutical expert. The local database did not find a match
for this query. Suggest a candidate if you know it.

QUERY: سيفترياكسون 1جم حقن وريدي

Respond ONLY with:
{"found": bool, "product_name_en": "...",
 "manufacturer": "...", "confidence": 0.0-1.0}
```

الـ response:

```json
{
  "found": true,
  "product_name_en": "CEFTRIAXONE 1G IV INJECTION",
  "manufacturer": "Egyptian Pharmaceutical Co.",
  "confidence": 0.82
}
```

الـ action: الصف ده بيتحدّث ومبيروحش للـ unmatched.

---

## 7. الـ Failure modes والـ Recovery

| المشكلة | الـ Symptom | الـ Recovery |
|---------|-----------|-------------|
| كل الـ keys لـ provider فولت rate limit | الـ plan كله `failed_combos` | الـ rotation يجرّب الـ provider التالي |
| مفيش env var لأي provider | `_provider_keys([])` → مفيش attempts | AI يتخطّى المرحلة، الـ trace يكتب `no_api_key` |
| YAML فيه `models` فاضية | `_resolve_providers` يـ skip الـ provider ده | بيـ fallback لـ `meta.default_model` أو بيُتجاهَل |
| Response مش JSON | `parse_failed=True` | الـ آخر unparseable يتـ fallback عبر `fallback_from_unparseable_response` |
| مفيش `review_model` مضبوط | `ai_review.py:42` → skip Phase 4 | الـ rows `ai_confirmed_low_conf` بتفضل كما هي |
| Cloudflare account_id مش مضبوط | `_provider_base_url` يرجع `""` | الـ attempt بيتـ skip من الـ plan |

> **ملاحظة عملية**: `state/config.yaml` الحالي (السطر 236-244) بيسجّل `CLOUDFLARE_API_TOKEN_1..6` مع `account_id_env: CLOUDFLARE_ACCOUNT_ID` **اللي بيربط CLOUDFLARE_API_TOKEN بـ CLOUDFLARE_ACCOUNT_ID_2 مش _1** — ده bug معروف (موجود في memory). الـ fix: استخدم `CLOUDFLARE_API_TOKEN` (singular) مع `CLOUDFLARE_ACCOUNT_ID`، أو زاوج الـ indices يدوي.

---

## 8. الـ Tracing والـ Observability

كل attempt فاشل أو ناجح بيتسجل في الـ DataFrame بالـ columns دي:

| column | متى بتتملي |
|---|---|
| `verified` | بعد كل phase AI |
| `ai_confidence` | Phase 2/3 |
| `ai_reason` | Phase 2 |
| `ai_provider` | آخر provider نجح |
| `ai_model` | آخر model نجح |
| `ai_attempts` (في trace) | كل المحاولات في الـ JSON للـ rotation |

الـ trace الكامل بيـ render في الـ Streamlit UI عبر `src/ui/views/streamlit_product_matching.py` + `src/core/drug_matching/tracing/`.

---

## 9. ملخّص — الـ Mental model في جملة واحدة

> **`AIConfig` تقرأ 4 layers → `ProviderPool` تجمّد الـ models → `ai_rotation` تولّد attempt plan مسطّح من كل (provider × key × model) → `verifier_request` يـ fan-out مع semaphore=5 وبيلغي الـ combos الميتة → الـ 3 phases (`verify/search/review`) بتاخد الـ plan ده وبتعيد توزيعه على الـ DataFrame.**

كل اللي محتاج تعرفه عشان تعدّل أو debug:

1. **الـ config**: `state/config.yaml` → `ai:` block فقط.
2. **الـ flow**: `src/core/drug_matching/ai/ai_steps.py` (3 imports) → `ai_verify.py` / `ai_search.py` / `ai_review.py`.
3. **الـ HTTP**: `verifier.py:37` + `verifier_request.py:24` (`APICaller.call_api`).
4. **الـ rotation**: `ai_rotation.py:184` (`_provider_attempts`).