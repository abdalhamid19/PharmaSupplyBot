# تصميم مراجعة مستقلة لقياس `C_display` الحقيقي في Streamlit

> هذه وثيقة تصميم وتنفيذ للمراجعة فقط. لا تنفذ تعديلًا في هذا الملف على كود الإنتاج أو `state` أو ملفات Excel.

**الهدف:** قياس عدد المرشحين الذي يصل فعليًا إلى بطاقة المراجعة في Streamlit بعد التحميل والدمج وإزالة التكرار وإخفاء المكتملين وحد العرض، مع إبقاء `C_saved` قيمة مقروءة ومتحققًا منها من JSONL فقط.

**القرار المقترح:** لا نضيف في المرحلة الأولى telemetry دائمًا ولا نعيد تشغيل `run.py`. نستخدم اختبارًا مستقلاً read-only يستدعي مسار `render_run_candidates` الحقيقي، ويراقب الحد الفاصل الموجود أصلًا عند استدعاء `_render_item_card`. لا يحتاج هذا إلى تعديل production code؛ وإذا احتجنا لاحقًا إلى واجهة مراقبة عامة، يكون أقل تعديل اختياري هو callback اختباري غير مفعّل افتراضيًا.

**النطاق:** artifacts مكتملة لـ Excel-target، وطبقة Streamlit الخاصة بالمراجعة اليدوية.

**خارج النطاق:** أي matching جديد، أو إعادة تشغيل ضد input workbook، أو تحديث SQLite، أو تغيير حد الحفظ/العرض، أو إثبات precision/recall.

## التعريفات التي يجب ألا تختلط

يُحسب كل مقياس لكل `item_key` ولكل target/source scope ثم يُجمع على مستوى التقرير:

| المقياس | التعريف القابل للتدقيق | المصدر المسموح | ما لا يجوز فعله |
|---|---|---|---|
| `C_generated` | قيمة `candidate_count_total` في summary/JSONL؛ وهي اتحاد المرشحين بعد discovery في وقت التشغيل | `match_only_summary_*.csv` وenvelope JSONL | لا نساويها بعدد صفوف catalog كله |
| `C_saved` | القيمة الصريحة `candidate_count_saved` لكل سجل JSONL، بعد التحقق من أنها تساوي عدد `options` في السجل | `manual_review_candidates_*.jsonl` فقط | لا نستخدم `len(options)` كبديل، ولا `candidate_count`، ولا `candidate_count_total` |
| `C_loaded_unique` | عدد الخيارات بعد `load_review_candidates` ثم `_load_group_candidates` وإزالة التكرارات حسب هوية الصف | مسار loader الفعلي | لا نعيد تسميته `C_saved` إذا أسقط dedup خيارات |
| `C_display(item, page)` | عدد `visible_options` الذي يصل إلى `_render_item_card` في Streamlit للبطاقة والصفحة المحددين | spy عند boundary الفعلي | لا نعد خيار `None (Leave Unmatched)`؛ فهو widget option وليس candidate |
| `C_display_run` | مجموع `C_display(item, page)` عبر كل الصفحات في جلسة قياس واحدة بنفس الإعدادات | مجموعة نداءات spy لكل الصفحات | لا نعتبر صفحة واحدة ممثلة لكل run |

إذا غاب `candidate_count_saved` أو كان غير صالح، تكون نتيجة `C_saved` هي `status=not_measured` ويُوقف التقرير؛ لا يوجد fallback صامت. وإذا اختلف `C_saved` الصريح عن عدد `options`، تكون النتيجة `inconsistent` ولا تستعمل للمقارنة.

## مسار التنفيذ الذي يجب قياسه

يجب أن يتبع الاختبار نفس التسلسل المستخدم في `src/ui/manual_review/streamlit_manual_review_page.py`:

```text
load_review_candidates(run_dir)
  -> _load_group_candidates(run_dirs)
  -> manual_review_store_or_stop().lookup_all(...)
  -> _filter_and_prepare_items(..., hide_completed)
  -> _paginate_candidates(..., 50 per page)
  -> _limit_candidates_by_source(options, display_limit)
  -> _render_item_card(item_key, item, visible_options, ...)
```

موضع القياس الصحيح هو آخر سطر. قبل ذلك يمكن أن تتغير القائمة بسبب merge أو dedup أو saved-decision filtering، وبعده تبدأ تفاصيل radio/selectors ولا يعود لدينا boundary موحد لعدد المرشحين.

## خطة مراجعة مستقلة read-only

### 1. تثبيت مدخلات المراجعة

نفّذ المراجعة على run مكتمل موجود، مثل `artifacts/order/wardany/20260910_1243`، وعلى المجموعة الكاملة من مجلدات target التابعة لنفس `run_id`. لا تنشئ run جديدًا ولا تشغل `run.py`.

سجّل قبل القياس:

- `run_id` وlist مرتبة من `run_dirs` التي سيستخدمها `_group_runs_by_id`.
- اسم كل `manual_review_candidates_*.jsonl` وchecksum SHA-256 له.
- اسم كل `match_only_summary_*.csv` وchecksum SHA-256 له.
- قيمة `manual_review_display_candidate_limit` المقروءة من config الحالي، وقيمة الزيادة في widget؛ يجب أن تكون الزيادة `0` في القياس الأساسي.
- `hide_completed=False` في القياس الأساسي حتى لا يعتمد القياس على قرارات SQLite الموجودة أو يخفي جزءًا من union.
- رقم الصفحة الجاري قياسها.

قراءة config أو hashing الملفات مسموحان، لكن لا يُحفظ أي تغيير فيها. لا تُفتح `state/manual_review_decisions.db` من خلال `ManualReviewStore()` في القياس الأساسي؛ استخدم store بديلًا read-only يعيد `[]` من `lookup_all` أو snapshot read-only معلنًا إذا كان المطلوب قياس أثر الإخفاء.

### 2. حساب `C_saved` من JSONL دون تخمين

يقرأ harness كل ملف مرشح مباشرة، وليس نتيجة loader، ثم يطبق هذه القواعد الصارمة:

```python
for record in jsonl_records:
    require isinstance(record["candidate_count_saved"], int)
    require record["candidate_count_saved"] >= 0
    require record["candidate_count_saved"] == len(record["options"])
    require unique(record["item_key"] within this file)
    c_saved += record["candidate_count_saved"]
```

يُحتفظ أيضًا بـ`c_saved_by_item_and_file` حتى لا تخفي عملية الدمج اختلاف targetين يحملان نفس `item_key`. ويُقارن `candidate_count_total` مع summary للتحقق فقط؛ لا يُستخدم كبديل لـ`C_saved`.

إذا كان السجل القديم لا يملك `candidate_count_saved`، يكتب harness:

```json
{"status":"not_measured","reason":"missing_explicit_candidate_count_saved"}
```

ولا يحول `len(options)` إلى قيمة محفوظة تقديرية.

### 3. التقاط `C_display` عند boundary Streamlit

استخدم test harness مستقلًا في الذاكرة، أو `unittest.mock.patch` داخل اختبار Streamlit، بحيث:

```python
captured = []

def capture_item_card(item_key, item, visible_options, run_dir, store):
    captured.append({
        "item_key": item_key,
        "run_dir": str(run_dir),
        "row_keys": [o.excel_target_row_key for o in visible_options],
        "candidate_methods": [o.candidate_method for o in visible_options],
        "count": len(visible_options),
    })

with patch.object(page, "manual_review_store_or_stop", return_value=ReadOnlyStore()):
    with patch.object(page, "_render_item_card", side_effect=capture_item_card):
        page.render_run_candidates(run_dirs, app_config)
```

هذا لا يغيّر ترتيب أو filtering أو limit؛ يستبدل فقط جسم البطاقة الذي يبدأ منه عرض widgets بمراقب لا يكتب. `capture_item_card` هو مصدر `C_display`، وليس `_build_radio_opts`؛ لأن الأخير يضيف خيارًا اصطناعيًا غير مرشح.

يجب تكرار الاستدعاء لكل صفحة فعلية:

1. اضبط `st.session_state["manual_review_page"] = 1`.
2. شغّل `render_run_candidates` وسجّل كل نداءات `capture_item_card`.
3. انتقل إلى الصفحة التالية، مع عدم تغيير `run_dirs` أو config أو store، وسجّل النداءات الجديدة.
4. توقف بعد `ceil(number_of_items_after_filter / 50)` صفحات.
5. ارفض أي `item_key` مكرر في صفحة واحدة أو عبر الصفحات.

في الاختبار الأساسي، استخدم store fake لا يعيد قرارات؛ وبذلك تكون `hide_completed=False` و`True` قابلة للمقارنة دون لمس SQLite. ولقياس السلوك الواقعي مع قرارات سابقة، أضف وضعًا ثانيًا يقرأ SQLite عبر URI `mode=ro` فقط ويمنع أي method كتابة، ولا تخلط نتيجته بنتيجة baseline.

### 4. مطابقة النتائج مع artifact دون تغييرها

لكل بطاقة ملتقطة، أنشئ مفتاحًا:

```text
(item_key, matching_source, matching_source_label, target_key, source_file,
 excel_target_row_key)
```

تحقق من الآتي:

- كل `excel_target_row_key` المعروض موجود في أحد options المحفوظة لنفس item/target/source.
- لا يظهر row key مختلفان كأنهما خيار واحد بسبب dedup.
- `C_display(item) <= C_loaded_unique(item)` دائمًا.
- `C_display_run <= C_loaded_unique_run <= C_saved_artifact_run`؛ إذا لم يتحقق الشرط، لا تُصلح الرقم حسابيًا، بل تفشل المراجعة مع diff.
- candidate method و`ranking_tier` وtarget/source provenance محفوظة في كل خيار ملتقط.
- لا تحتوي أي بطاقة على `best_match` أو تؤدي إلى callback حفظ أثناء القياس.

الفرق بين `C_saved_artifact` و`C_loaded_unique` مهم: إذا أسقط loader duplicate قانونيًا، يُسجل كـ`load_dedup_delta` مستقل، ولا يُعاد تعريف `C_saved` ليطابق UI.

### 5. إخراج المراجعة

ينتج harness JSON على stdout أو في مجلد مؤقت خارج `state`، ولا يكتب إلى input workbook أو SQLite. الشكل الأدنى:

```json
{
  "schema_version": 1,
  "read_only": true,
  "status": "measured",
  "run_id": "20260910_1243",
  "settings": {
    "hide_completed": false,
    "configured_display_limit": 5,
    "extra_display_limit": 0,
    "items_per_page": 50
  },
  "targets": [
    {
      "target_key": "البركة شركات",
      "c_saved_artifact": 221,
      "c_loaded_unique": 221,
      "c_display_run": 221,
      "c_display_pages": [221],
      "displayed_items": 108,
      "invariants": {"passed": true, "errors": []}
    }
  ]
}
```

القيم في المثال توضيحية لبنية التقرير وليست نتيجة قياس. لا يسجل التقرير `C_display=C_saved` إلا إذا التقط نداءات Streamlit وأثبت مساواتهما لكل target/item في نفس الإعدادات.

## الاختبارات المطلوبة قبل قبول القياس

### Acceptance 1 — لا كتابة في SQLite أو input workbook

- احسب SHA-256 قبل التشغيل لـ`state/manual_review_decisions.db` وملفات input workbook المشار إليها في runbook.
- شغّل harness مع `ReadOnlyStore` وmonkeypatch لأي `upsert`, `upsert_batch`, `execute_update`, `commit` ليُفشل الاختبار إذا استُدعي.
- احسب SHA-256 بعد التشغيل.
- PASS فقط إذا لم يُستدع أي مسار كتابة ولم تتغير hashes. إذا كان الملف غير موجود قبل الاختبار، لا تنشئه؛ سجّل `not_applicable` بدل إنشاء SQLite.

### Acceptance 2 — `C_saved` صريح وغير تقديري

أنشئ fixture JSONL مؤقتًا بسجلين:

- سجل `candidate_count_saved=2` و`options` فيهما خياران؛ يجب أن يظهر `C_saved=2`.
- سجل بلا `candidate_count_saved`؛ يجب أن تكون النتيجة `not_measured`، حتى لو كان `len(options)=2`.
- سجل `candidate_count_saved=3` مع خيارين؛ يجب أن تفشل المراجعة بتناقض، لا أن تصحح القيمة إلى 2.

### Acceptance 3 — التقاط العدد الحقيقي بعد source-limit

استخدم أربعة options في target واحد وحد عرض `3`. يجب أن تصل ثلاثة options إلى `capture_item_card`، وأن تكون row keys الثلاثة هي أول ثلاثة بعد ترتيب الإنتاج.

استخدم targetين، وحد عرض `3`، مع option واحد على الأقل لكل target. يجب أن يلتقط spy ثلاثة options، وأن يحتفظ بخيار من كل source وفق `_limit_candidates_by_source`.

### Acceptance 4 — pagination لا تفقد ولا تكرر بطاقات

استخدم 51 item records و`items_per_page=50`. يجب أن تكون نتيجة الصفحة الأولى 50 بطاقة والثانية بطاقة واحدة، ومجموع `C_display_run` مساويًا لمجموع البطاقتين دون تكرار `item_key`.

### Acceptance 5 — dedup لا يخفي صف Excel مختلفًا

ضع خيارين لهما نفس product identity لكن `excel_target_row_key=row-a` و`row-b`. يجب أن يبقيا في `C_loaded_unique` وفي `C_display`، وأن يظهر كل منهما في captured row keys.

### Acceptance 6 — hide-completed منفصل عن baseline

في baseline، fake store يعيد `[]` و`hide_completed=False`. في تجربة ثانية، fake store يعيد قرارًا لنطاق target واحد. يجب أن ينخفض `C_display` فقط في التجربة الثانية، مع بقاء `C_saved_artifact` ثابتًا تمامًا. لا يجوز تعديل artifact أو DB.

### Acceptance 7 — review-only لا يتحول إلى automatic

بعد القياس، افحص captured options التي تحمل `review_identity`, `review_identity_prefix`, `review_fuzzy` أو `english_fuzzy`. يجب أن تظهر كمرشحين فقط، وألا تستدعي أي automatic decision أو save callback. هذه المراجعة لا تعيد تشغيل matcher؛ فحصها artifact/UI فقط.

### Acceptance 8 — صفا الاختبار المعروفان

تحقق من أن row `3100` لـ`VOLTAREN 3AMP` وrow `2345` لـ`XITHRONE 500MG 3TAB`، إذا كانا ضمن run المختار، يصلان إلى captured options، مع `best_match` غير موجود. يجب مقارنة row key وtarget key، لا الاسم وحده.

### Acceptance 9 — deterministic replay للمراجعة

شغّل harness مرتين بنفس artifacts وsettings. يجب أن تتطابق:

- قائمة `(item_key, row_key, candidate_method, ranking_tier)` لكل صفحة.
- `C_saved_artifact`, `C_loaded_unique`, `C_display_run`.
- ترتيب options داخل كل بطاقة.

اختلاف checksum أو artifact input يجعل النتيجة `not_comparable` بدل دمج النتائج.

## أقل تغيير مقترح إذا تعذر الاختبار بدون seam

البديل الأول لا يغير production code: patch خاص بالاختبار لـ`_render_item_card` كما في هذا التصميم.

إذا رفض reviewer الاعتماد على private function، يكون أقل تعديل production مقبولًا:

```python
def render_run_candidates(run_dir, app_config=None, *, display_observer=None):
    ...
    visible_options = _limit_candidates_by_source(options, display_limit)
    if display_observer is not None:
        display_observer(item_key, visible_options, run_context)
    _render_item_card(item_key, item, visible_options, run_context, store)
```

الشروط الإلزامية لهذا البديل:

- `display_observer=None` افتراضيًا، ولا يغير السلوك الحالي.
- لا يكتب observer إلى SQLite أو workbook أو `state`؛ يرسل counters إلى الذاكرة/ stdout فقط.
- لا يُستخدم observer لاتخاذ قرار matching أو تغيير options.
- يضاف اختبار يثبت أن callback يرى نفس list التي تصل إلى `_render_item_card`.
- لا تُسمى قيمة callback `C_saved`; تظل `C_display` مستقلة تمامًا.

لا نحتاج هذا التعديل إذا نجح patch الاختباري في قياس boundary الحالي.

## قرار القبول والنتيجة المتوقعة

تُقبل المراجعة فقط إذا كانت الحالة `measured` وجميع Acceptance 1–9 ناجحة. عندها يمكن القول بدقة:

> `C_display` هو عدد المرشحين الذي عرضه مسار Streamlit فعليًا تحت settings محددة، و`C_saved` هو العدد الصريح الموجود في JSONL، مع reconciliation مستقل بينهما.

ولا يجوز القول إن precision تحسنت أو إن recall زاد من هذا القياس وحده؛ ذلك يحتاج labels بشرية منفصلة كما في `19-precision-sampling-report.md`.

إذا فشل أي invariant، فالقرار `blocked`، ويُذكر السبب والـdiff الخام، دون تعديل artifacts أو SQLite أو input workbooks.

## ملفات المراجعة ذات الصلة

- `src/ui/manual_review/streamlit_manual_review_page.py`
- `src/core/manual_review/manual_review_candidate_store.py`
- `src/core/manual_review/manual_review_candidates.py`
- `tools/report_excel_target_candidate_coverage.py`
- `tests/ui/manual_review/test_streamlit_manual_review.py`
- `tests/tools/test_report_excel_target_candidate_coverage.py`
- `docs/approved-manual-match-learning-20260909/19-precision-sampling-report.md`
- `docs/approved-manual-match-learning-20260909/24-gate0-full-replay-results.md`
