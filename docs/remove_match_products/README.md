# إزالة ميزة "Product Matching" المستقل — مجلد التوثيق

> **الهدف:** حذف `match-products` من CLI و GUI ومن كل البرنامج **دون المساس بأمر `order` إطلاقًا**.

هذا المجلد يحتوي على خطة كاملة جاهزة للتنفيذ، مبنية على تحليل فعلي للكود (سطر بسطر)، وليست اقتراحات نظرية.

## الملفات

| الملف | المحتوى |
|---|---|
| [01-analysis.md](01-analysis.md) | خريطة التبعيات الكاملة: ما يُحذف، ما يُنقل، ما يُمس نهائيًا — مع أرقام الأسطر |
| [02-plan.md](02-plan.md) | خطة التنفيذ خطوة بخطوة (مهام صغيرة قابلة للاختبار والcommit) |
| [03-worktree-guide.md](03-worktree-guide.md) | دليل إنشاء worktree معزول + التنظيف بعد الانتهاء + بيانات GitHub |
| [04-testing-checklist.md](04-testing-checklist.md) | شبكة الأمان: قائمة الاختبارات والتحققات قبل وبعد كل مرحلة |
| [05-rollback-cleanup.md](05-rollback-cleanup.md) | خطة التراجع الكاملة + تنظيف الفروع الراكدة |

## الخلاصة التنفيذية (اقرأ هذا أولًا)

1. **الفكرة سليمة.** يوجد في المشروع نظاما matching منفصلان تمامًا. الحذف آمن بشرط احترام الحدود الموضحة في `01-analysis.md`.

2. **أهم اكتشاف:** `order` يعتمد على جزء من `src/core/drug_matching/` (تحديدًا `normalization/`). لذلك الخطة تتبنى **نطاق الحذف الشامل مع فصل normalization**:
   - `normalization/` (19 ملف) تُنقل إلى `src/core/normalization/` ويُعاد توجيه 6 مستوردين.
   - `pricing.py` يُنقل معها (لا أحد يستخدمه خارج indexing/normalization).
   - باقي `drug_matching/` يُحذف بالكامل (pipeline, indexing, tracing, pipeline_components, config).
   - `ai/` و `verification/` **مجلدات فارغة بالفعل** (لا توجد فيها سوى ملفات `.pyc` قديمة) — حذف مجاني.

3. **مفاجأة لطيفة:** صفحة Manual Review التي تبدو مرتبطة بـ match-products تستخدم في الحقيقة `order --match-only` (وهو يبقى كما قررت). مجلد `artifacts/match-products/` فيها مجرد مسار dummy لملفات مؤقتة — يُعاد تسميته فقط.

4. **القرارات المعتمدة منك:**
   - نطاق الحذف: شامل مع فصل normalization.
   - تاب Results: يُزال match-products من القائمة (الأرشيف القديم يبقى على القرص).
   - `--match-only` داخل order: **يبقى كما هو**.

## طريقة الاستخدام المقترحة

1. ابدأ بـ `03-worktree-guide.md` لإنشاء بيئة العمل المعزولة.
2. نفّذ مهام `02-plan.md` بالترتيب، مع الالتزام بشبكة أمان `04-testing-checklist.md` بعد كل مهمة.
3. لو حدث خلل: خطة التراجع في `05-rollback-cleanup.md`.
