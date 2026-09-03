# 07 — انهيار مهلة الملاحة أثناء تشغيل match-only (Navigation Timeout Crash)

> عُثر عليه أثناء التحقق الميداني من إصلاح `auto_matched`: التشغيل الحقيقي انهار قبل الوصول لمنطق الحفظ.

---

## 1. الأعراض

```
2026-08-30T19:05:19 | INFO    | artifact run started
2026-08-30T19:05:20 | WARNING | headless login flow instructions
2026-08-30T19:05:23 | INFO    | login detected
2026-08-30T19:05:39 | ERROR   | unhandled exception in command order
...
playwright._impl._errors.TimeoutError: Page.goto: Timeout 15000ms exceeded.
Call log:
  - navigating to "https://seller.tawreed.io/#/catalog/store-products/dv/",
    waiting until "domcontentloaded"
```

الأمر انهار بـ traceback كامل — التشغيل بالكامل توقف، ولم تُنفَّذ أي مطابقة ولا حفظ.

## 2. مسار الاستدعاء (من الـ traceback)

```
run_order_command                         cli_order.py:87
 → execute_profiles                       cli_order.py:200
 → run_single_profile                     cli_order_execution.py:40
 → run_single_profile_items               cli_order_execution.py:66
 → run_profile_items                      cli_order_execution.py:74
 → run_profile_match_only                 cli_order_execution.py:96
 → bot.match_items_only                   tawreed_bot_methods.py:41
 → order_flow.match_items_only            tawreed_order_flow.py:51
 → _match_flow.match_items_only           tawreed_order_match.py:39
 → bot._ensure_valid_auth                 tawreed_bot_methods.py:21
 → auth_flow.ensure_valid_auth            tawreed_auth.py:155
 → auto_refresh_auth_if_needed            tawreed_auto_auth.py:33
 → _refresh_single_worker                 tawreed_auto_auth.py:40
 → run_headless_auth_refresh              tawreed_headless_auth_refresh.py:28
 → _run_auth_refresh_session              tawreed_headless_auth_refresh.py:44
 → _capture_and_validate_session          tawreed_headless_auth_refresh.py:68
 → validate_saved_session                 tawreed_session.py:137   ← نقطة الانهيار
 → page.goto(target_url, wait_until="domcontentloaded")            ← TimeoutError
```

**الترتيب المهم:** تسجيل الدخول **نجح** (`login detected` في 19:05:23). الانهيار حدث في خطوة **التحقق** بعده: فتح صفحة الكتالوج للتأكد من صلاحية الجلسة.

## 3. التشخيص بالأدلة

### 3.1 المهلة المستخدمة كانت 15 ثانية

```
state/config.yaml → runtime.timeout_ms: 15000
```
و `open_order_page` يضبط `page.set_default_timeout(runtime.timeout_ms)` فيصبح 15000ms هو سقف `page.goto` أيضاً — وهذا يطابق نص الخطأ `Timeout 15000ms exceeded`.

> ملاحظة: افتراضي الكود (`RuntimeConfig.timeout_ms = 45000` و `config_factory` نفس القيمة) أعلى بكثير؛ الملف الفعلي `state/config.yaml` كان يخفضه إلى 15000.

### 3.2 قياس الشبكة الفعلي أثبت ركوداً عابراً

```
TCP connect seller.tawreed.io:443
  attempt 1 (cold): 21.08 s     ← أطول من 15 s!
  attempt 2:         0.05 s
  ثم 4 قياسات متتالية: 0.06, 0.06, 0.04, 0.05 s
DNS: 0.01 s (سليم)
HTTPS GET /: 0.25 s (status 200, سليم)
```

**السبب المركّب:** مهلة 15s ضيقة + ركود عابر في أول اتصال TCP/TLS (21s) → تجاوز المهلة → استثناء غير مُعالَج → انهيار التشغيل بالكامل.
الموقع نفسه سليم (200 OK، DNS سريع، الاتصالات التالية أجزاء من الثانية).

### 3.3 حالة الجلسة المحفوظة سليمة

فحص `state/wardany.json`:
```
COOKIES: metabase.DEVICE (bi.tawreed.io) تنتهي 2027-10-04 → ok
LOCAL STORAGE (seller.tawreed.io): refresh-token(174), access-token(174),
                                   user-sessions(452), preferences(48)
```
لا مشكلة في الجلسة — تأكيد إضافي أن السبب شبكي/مهلة لا مصادقة.

## 4. لماذا كان الأثر كارثياً (انهيار كامل)

`page.goto` بدون مهلة صريحة يأخذ مهلة الصفحة الافتراضية (15s هنا)، وبدون أي إعادة محاولة. أي ركود عابر لثوانٍ = خسارة التشغيل بالكامل، حتى لو كان كل شيء آخر سليماً.

## 5. الحل المُطبَّق

### 5.1 دالة ملاحة صامدة

`src/tawreed/auth/tawreed_session.py`:

```python
# Navigations target a remote SPA over the public internet; the widget-level
# default timeout (state/config.yaml timeout_ms, commonly 15000) is too tight
# for cold TCP/TLS handshakes. A transient first-connection stall of 20+ s was
# observed in the field (TCP connect to seller.tawreed.io took 21 s once, then
# 0.05 s on retry), so navigations get a floor plus one retry on timeout.
NAVIGATION_TIMEOUT_FLOOR_MS = 60_000


def resilient_goto(page, url: str, timeout_ms: int | None = None) -> None:
    """Navigate with a navigation-grade timeout and one retry on timeout."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    effective = max(NAVIGATION_TIMEOUT_FLOOR_MS, timeout_ms or 0)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=effective)
    except PlaywrightTimeoutError:
        logger.warning(
            "navigation timed out; retrying once",
            extra={"url": url, "timeout_ms": effective},
        )
        page.goto(url, wait_until="domcontentloaded", timeout=effective)
```

**قرارات التصميم:**
- **حد أدنى 60s للملاحة** بدل الاعتماد على `timeout_ms` الخاص بانتظار العناصر — تحميل صفحة SPA عبر الإنترنت ليس نفس انتظار عنصر في DOM محمّل.
- **إعادة محاولة واحدة** — تكفي للركود العابر (القياس: المحاولة الثانية 0.05s)، ولا تخفي فشلاً دائماً.
- **مهلة فقط تُعاد** — أخطاء DNS/شبكة أخرى تُرفع فوراً بلا إعادة.
- **تسجيل تحذير** عند الإعادة لتبقى المشكلة مرئية.

### 5.2 استبدال كل نقاط الملاحة الحرجة

| الملف:السطر | الاستدعاء |
|---|---|
| `src/tawreed/auth/tawreed_session.py:74` | `open_auth_page` — تحميل صفحة تسجيل الدخول |
| `src/tawreed/auth/tawreed_session.py:167` | `validate_saved_session` — **نقطة الانهيار الأصلية** |
| `src/tawreed/cart/tawreed_cart_flow.py:69` | `_prepare_cart_page` |
| `src/tawreed/cart/tawreed_cart_flow.py:95` | `_prepare_order_page` |
| `src/tawreed/order/tawreed_order_processing.py:157` | `prepare_order_page` |

### 5.3 رفع المهلة المُهيأة

- `state/config.yaml`: `timeout_ms: 15000` → `45000` (مطابقة لافتراضي الكود).
- `config.example.yaml`: نفس الرفع + تعليق يشرح أن الملاحة لها حد أدنى أعلى.

## 6. الاختبارات

`tests/reproduction/test_resilient_goto_navigation.py` — 5 اختبارات:

| الاختبار | يثبت |
|---|---|
| `test_uses_navigation_floor_despite_small_default` | المهلة الفعلية ≥ 60s حتى لو مُرِّر 15000 |
| `test_transient_timeout_is_retried_once` | مهلة عابرة واحدة → إعادة واحدة → نجاح (استدعاءان بالضبط) |
| `test_persistent_timeout_still_raises` | فشل مستمر يرفع الاستثناء ولا يدور بلا نهاية |
| `test_non_timeout_error_propagates_without_retry` | خطأ DNS يُرفع فوراً (استدعاء واحد) |
| `test_no_timeout_argument_still_gets_floor` | بدون تمرير مهلة يبقى الحد الأدنى مُطبَّقاً |

```
5 passed
```

> **تصحيح موثق في بناء الاختبار:** النسخة الأولى من `_FakePage` كانت تبني الاستثناء الافتراضي بـ `error or PlaywrightTimeoutError(...)`، ومع `failures=0` الافتراضي لم تُرفع أي أخطاء — الاختبارات فشلت لسبب في الاختبار لا في الكود. صُحّح بفصل `failures` عن `error` وبناء الاستثناء الافتراضي داخل `goto`.

## 7. النتيجة النهائية

```
tests/reproduction + tests/solutions + tests/hypotheses  →  54 passed
الحزمة الكاملة (باستثناء tests/core/database غير المكتمل من عمل آخر) →  696 passed, 8 failed (baseline)
```

الإخفاقات الثمانية موروثة من الفرع (أُثبت بـ `git stash`) ولا صلة لها بهذا العمل.
