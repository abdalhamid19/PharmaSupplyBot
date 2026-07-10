# 2 — خريطة الكود المتورّط

كل ملف/وظيفة لها دور في سلسلة المطابقة، من لحظة قراءة الـ Excel حتى عرض الخيارات في صفحة Manual Review.

## 2.1 المسار الأساسي للمطابقة (المسار الجديد عبر API)

```
run.py order  →  CLI  →  TawreedOrderBot  →  require_api_match()
```

| الملف | الوظيفة | الدور |
|------|--------|------|
| `src/tawreed/api/tawreed_api_matching.py` | `require_api_match()` | الحلقة الأساسية: لكل query يبحث ثم يقرر. |
| `src/tawreed/api/tawreed_api_matching.py` | `_manual_review_decision_timed()` | يحمّل الـ saved decision للصنف ويقيس زمن الـ lookup. |
| `src/tawreed/api/tawreed_api_matching.py` | `_api_match_decision()` | يحاول أولاً `manual_review_match` ثم `explain_best_product_match`. |
| `src/tawreed/api/tawreed_api_matching.py` | `_is_saved_manual_review_match()` | يكشف هل المطابقة جاءت من decision محفوظ (reason يبدأ بـ "Approved by saved manual review"). |
| `src/tawreed/api/tawreed_api_matching.py` | `_handle_api_no_match()` | عند فشل كل الـ queries يرفع `no_results_exception("No decisive match found...")`. |
| `src/tawreed/matching/tawreed_search_decision.py` | `decisive_match()` | يقرر هل الـ best_match نهائي أم يجب المتابعة بـ query آخر. |
| `src/tawreed/matching/tawreed_match_logs.py` | `write_match_log()` | يكتب diagnostics مثل `matching_trace_*.csv`، وقد يكتب logs نصية حسب artifact/run setup. |

## 2.2 منطق الـ Saved Correction (القرارات اليدوية المحفوظة)

| الملف | الوظيفة | الدور |
|------|--------|------|
| `src/core/manual_review/manual_review_runtime.py` | `saved_manual_review_decision()` | يرجع decision من cache أو من DB. |
| `src/core/manual_review/manual_review_runtime.py` | `manual_review_queries()` | **يضع `correct_query` في مقدمة قائمة البحث** — هذا هو المفترض أن يُصلح المشكلة. |
| `src/core/manual_review/manual_review_runtime.py` | `manual_review_match()` | يفرض مطابقة بالـ store_product_id المحفوظ أو بالاسم المُطابق تماماً (score 999). |
| `src/core/manual_review/manual_review_helpers.py` | `_preferred_queries()` | يعيد `[correct_query]` إن وُجد، وإلا `[correct_product_name, correct_product_name_ar]`. |
| `src/core/manual_review/manual_review_helpers.py` | `_manual_review_id_match()` | يبحث عن candidate بـ store_product_id مطابق، ويُسقط التحقق (للتوافق مع الإصدارات السابقة). |
| `src/core/manual_review/manual_review_helpers.py` | `_manual_review_name_match()` | يفرض مطابقة بالاسم الإنجليزي أو العربي بالضبط. |
| `src/core/manual_review/manual_review_store.py` | `ManualReviewStore.lookup()` / `upsert()` | CockroachDB persistence للقرارات. |
| `src/core/manual_review/manual_review_hints.py` | `hint_key()` | مفتاح البحث: `(clean_code.upper(), clean_name.upper())` مع تطبيع يحذف كل ما ليس حرفاً إنجليزياً/عربياً/رقماً. |

## 2.3 خوارزمية التسجيل (Scoring) والرفض الدلالي — **موضع الخلل الأساسي**

| الملف | الوظيفة | الدور |
|------|--------|------|
| `src/core/matching/product_matching.py` | `explain_best_product_match()` | يبني `MatchDecision` لكل الـ results. |
| `src/core/matching/product_matching.py` | `is_decisive_product_match()` | اختبار سريع: تطابق اسمي حاسم أم لا. |
| `src/core/matching/product_matching_acceptance.py` | `_check_rejections()` | يحسب الـ compatibility_rejection_reason ومنطق الـ manufacturer_conflict. |
| `src/core/matching/matching_penalties.py` | `compatibility_rejection_reason()` | **مصدر رسالة "Semantic token conflict: CREAM vs GEL, GEL vs CREAM".** |
| `src/core/matching/matching_penalties.py` | `_token_details()` / `_semantic_conflicts()` | يحسب الـ conflicts بين tokens الـ query والـ candidate. |
| `src/core/matching/matching_penalties.py` | `penalty_breakdown()` | يحسب الـ semantic_penalty = `-semantic_weight × len(conflicts)`. |
| `src/core/matching_types.py` | `CONFLICT_GROUPS` | المجموعة الثالثة: `{CREAM, GEL, LOTION, OINTMENT, SHAMPOO, SOAP}` — أي عضوين مختلفين فيها يمكن أن يُعتبرا "متضادين". |
| `src/core/matching_types.py` | `CRITICAL_TOKENS` | `CREAM` و`GEL` مُدرجَين كـ tokens حرجة (يحققان penalties إضافية). |

## 2.4 عرض الخيارات في صفحة Manual Review

| الملف | الوظيفة | الدور |
|------|--------|------|
| `src/ui/manual_review/streamlit_manual_review_page.py` | `render_run_candidates()` | يحمّل الـ candidates من ملف JSONL ويبني بطاقات المراجعة. |
| `src/ui/manual_review/streamlit_manual_review_page.py` | `_render_form_ui()` / `_build_radio_opts()` | يبني قائمة الـ radio بالخيارات. |
| `src/core/manual_review/manual_review_candidate_store.py` | `load_review_candidates()` | **يقرأ من ملف JSONL محفوظ أثناء التشغيل الأصلي فقط** — لا يعيد البحث. |
| `src/core/manual_review/manual_review_candidates.py` | `review_candidate_options()` | يأخذ `decision.diagnostics[:5]` فقط. |
| `src/tawreed/order/tawreed_order_summary_build.py` | `_save_review_candidates_if_available()` | **يكتب** ملف JSONL من نتائج الـ run مرة واحدة (أثناء التشغيل). |

## 2.5 ملاحظة على الفجوة المفاهيمية

هناك **مساران منفصلان تماماً**:

1. **مسار "التشغيل الحيّ"** (`require_api_match`) — يستخدم `manual_review_queries()` و
   `manual_review_match()` ويعيد البحث فعلياً على Tawreed، فيستطيع أن يجد المنتج الصحيح
   لو نجح التصحيح.

2. **مسار "عرض المراجعة اليدوية"** (`render_run_candidates`) — يعرض فقط ما حُفظ سابقاً في
   `manual_review_candidates_*.jsonl`، **دون أي re-search**. هذا هو سبب "الخيارات تظهر كلها غلط".

هذه الفجوة هي مفتاح فهم العرض 3 (الخيارات الخاطئة) وتفصّل في `03_ROOT_CAUSE.md` و`05_HYPOTHESES_DISPROVED.md`.
