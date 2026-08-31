# تقرير: أفضل المهارات (Skills) للاختبار والتخطيط والتنفيذ

> تاريخ التقرير: 2026-08-30
> النطاق: المهارات المتوفرة في هذا المشروع (`.agents/skills/`) وفي المجلد العام (`~/.agents/skills/` و `~/.claude/skills/`)

---

## 1. ملخص تنفيذي

تم فحص المهارات المتاحة وتصنيفها حسب ثلاثة محاور رئيسية: **الاختبار (Testing)**، **التخطيط (Planning)**، **التنفيذ (Implementing)**. النتيجة: أفضل مزيج عمل متكامل هو:

| المرحلة | المهارة الأفضل | السبب |
|---------|----------------|-------|
| التخطيط | `plan` | يستكشف الكود ويصمم خطة تنفيذ قبل كتابة أي كود |
| التنفيذ | `implement` | ينفذ المواصفات/Tickets مع تكامل مباشر مع `tdd` |
| الاختبار | `tdd` + `pytest-testing` | حلقة Red→Green مع مرجع شامل لـ pytest |
| التصحيح | `systematic-debugging` | منهجية منظمة قبل اقتراح أي إصلاح |
| المراجعة | `code-review` | مراجعة وفق معايير المستودع والمواصفات |

---

## 2. مهارات الاختبار (Testing Skills)

### 🥇 tdd (الأفضل للمنهجية)
- **الموقع:** `~/.agents/skills/tdd/`
- **الوصف:** التطوير الموجه بالاختبارات — حلقة **أحمر → أخضر → إعادة هيكلة**.
- **أهم المبادئ:**
  - الاختبارات تتحقق من **السلوك عبر الواجهات العامة** لا تفاصيل التنفيذ.
  - **الـ Seams:** الاختبار يتم فقط عند حدود متفق عليها مسبقاً مع المستخدم.
  - **الشرائح العمودية (Vertical Slices):** اختبار واحد → تنفيذ واحد → تكرار (لا كتابة كل الاختبارات دفعة واحدة).
  - **مضادات الأنماط:** الاختبارات المقيّدة بالتنفيذ (Implementation-coupled)، الاختبارات التوlogyية (Tautological)، والتقطيع الأفقي (Horizontal slicing).
- **متى تستخدمها:** عند بناء ميزات أو إصلاح أخطاء بطريقة test-first.

### 🥈 Pytest Testing (الأفضل للمرجع التقني)
- **الموقع:** `.agents/skills/pytest-testing/` (ضمن هذا المشروع)
- **الإصدار:** 2.1.0
- **الوصف:** مرجع شامل لإطار pytest: fixtures، mocking، الاختبارات المعلمية (Parametrized)، قياس التغطية (Coverage)، والتكامل مع CI/CD.
- **متى تستخدمها:** كمرجع تقني عند كتابة اختبارات Python الفعلية.

### 🥉 webapp-testing
- **الموقع:** `~/.agents/skills/webapp-testing/`
- **الوصف:** اختبار تطبيقات الويب المحلية عبر Playwright — التحقق من الواجهة الأمامية، لقطات الشاشة، وسجلات المتصفح.
- **متى تستخدمها:** لاختبار تطبيقات Streamlit/الويب من طرف إلى طرف.

### مهارات اختبار إضافية
| المهارة | الاستخدام |
|---------|-----------|
| `playwright` | أتمتة المتصفح المتقدمة، تجاوز كاشف البوتات، الاختبار في CI |
| `debugging-streamlit` | تصحيح أخطاء تطبيقات Streamlit مع hot-reload |
| `fixing-streamlit-ci` | تشخيص وإصلاح فشل GitHub Actions CI |
| `systematic-debugging` | منهجية تشخيص إلزامية قبل أي إصلاح |

---

## 3. مهارات التخطيط (Planning Skills)

### 🥇 plan (الأفضل)
- **الموقع:** `~/.agents/skills/plan/`
- **الوصف:** وكيل تخطيط يستكشف قاعدة الكود ويصمم نهج التنفيذ **قبل كتابة الكود**.
- **آلية العمل:**
  1. استكشاف شامل للكود لفهم الأنماط الحالية (عبر وكلاء بحث متوازيين).
  2. تحديد ميزات مشابهة وأساليب معمارية.
  3. موازنة عدةapproaches وبدائلها.
  4. إخراج خطة تنفيذ مكتوبة (ملف خطة).
- **قيد مهم:** وضع القراءة فقط — لا تعديل ملفات إلا ملف الخطة.

### 🥈 to-tickets
- **الموقع:** `~/.agents/skills/to-tickets/`
- **الوصف:** تحويل خطة/مواصفات إلى مجموعة Tickets قابلة للتنفيذ مع تحديد حواف الحجب (Blocking edges) ونشرها في أداة التتبع.

### 🥉 grill-with-docs
- **الموقع:** `~/.agents/skills/grill-with-docs/`
- **الوصف:** مقابلة صارمة لصقل الخطة أو التصميم، مع إنشاء وثائق (ADRs + مسرد مصطلحات) أثناء العمل.

### مهارات تخطيط إضافية
| المهارة | الاستخدام |
|---------|-----------|
| `codebase-design` | مفردات تصميم الوحدات العميقة (seams, interfaces, depth) |
| `improve-codebase-architecture` | فحص الكود بحثاً عن فرص تحسين معمارية |

---

## 4. مهارات التنفيذ (Implementing Skills)

### 🥇 implement (الأفضل)
- **الموقع:** `~/.agents/skills/implement/`
- **الوصف:** تنفيذ العمل بناءً على مواصفات أو Tickets.
- **سير العمل:**
  1. استخدام `/tdd` حيثما أمكن عند الـ seams المتفق عليها.
  2. تشغيل typechecking بانتظام + ملفات اختبار مفردة + مجموعة الاختبارات كاملة في النهاية.
  3. استخدام `/code-review` لمراجعة العمل.
  4. الـ commit إلى الفرع الحالي.

### 🥈 implementing-feature
- **الموقع:** `.agents/skills/implementing-feature/` (ضمن هذا المشروع)
- **الوصف:** تنفيذ ميزة من مواصفات/رابط/Issue على GitHub بأسلوب Streamlit، وإنشاء PR جاهز للدمج.

### 🥉 finalizing-pr
- **الموقع:** `.agents/skills/finalizing-pr/`
- **الوصف:** تبسيط الكود، تشغيل الفحوصات، مراجعة التغييرات، وإنشاء PR عند الجاهزية للدمج.

---

## 5. سير العمل الموصى به (End-to-End)

```
1. plan            → استكشاف الكود وكتابة خطة التنفيذ
2. to-tickets      → (اختياري) تقسيم الخطة إلى Tickets
3. tdd             → تنفيذ كل شريحة: اختبار فاشل → كود ناجح
   └── pytest-testing → مرجع تقني لأدوات pytest
4. implement       → إدارة التنفيذ الكامل (typecheck + tests + review)
5. systematic-debugging → عند مواجهة أي خطأ أو سلوك غير متوقع
6. code-review     → مراجعة نهائية قبل الدمج
7. finalizing-pr   → تجهيز PR للدمج
```

---

## 6. التوصيات الخاصة بهذا المشروع (PharmaSupplyBot)

بما أن المشروع تطبيق Python + Streamlit:

1. **للاختبار:** ابدأ بـ `tdd` للمنهجية، و`pytest-testing` للتفاصيل التقنية، و`webapp-testing` لاختبار واجهة Streamlit.
2. **للتخطيط:** استخدم `plan` قبل أي ميزة جديدة، و`codebase-design` لتحديد الـ seams.
3. **للتنفيذ:** `implement` هو نقطة الدخول، مع `implementing-feature` للميزات الكاملة مع PR.
4. **للتصحيح:** `debugging-streamlit` للواجهة و`systematic-debugging` للمنطق الخلفي.

---

## 7. حالة التثبيت عبر skills.sh (محدثة 2026-08-30)

تم تثبيت أفضل 5 مهارات من [skills.sh](https://skills.sh) في المشروع عبر `npx skills add <owner/repo@skill> -y`:

| المهارة | المصدر على skills.sh | مرات التثبيت عالمياً | الحالة |
|---------|---------------------|----------------------|--------|
| `tdd` | `mattpocock/skills@tdd` | 799K | ✅ مثبتة → `.agents/skills/tdd` |
| `writing-plans` | `obra/superpowers@writing-plans` | 233.8K | ✅ مثبتة → `.agents/skills/writing-plans` |
| `systematic-debugging` | `obra/superpowers@systematic-debugging` | 241.7K | ✅ مثبتة → `.agents/skills/systematic-debugging` |
| `executing-plans` | `obra/superpowers@executing-plans` | 197.8K | ✅ مثبتة → `.agents/skills/executing-plans` |
| `webapp-testing` | `anthropics/skills@webapp-testing` | 145.7K | ✅ مثبتة → `.agents/skills/webapp-testing` |

### أوامر التثبيت المستخدمة
```powershell
npx skills add mattpocock/skills@tdd -y
npx skills add obra/superpowers@writing-plans -y
npx skills add obra/superpowers@systematic-debugging -y
npx skills add obra/superpowers@executing-plans -y
npx skills add anthropics/skills@webapp-testing -y
```

### سير العمل المحدث بالمهارات المثبتة
```
1. writing-plans          → كتابة خطة تنفيذ مفصلة
2. executing-plans        → تنفيذ الخطة خطوة بخطوة
3. tdd                    → حلقة Red→Green لكل ميزة
4. webapp-testing         → اختبار واجهة الويب (Playwright)
5. systematic-debugging   → عند مواجهة أي خطأ
```

*تم إعداد هذا التقرير بناءً على فحص فعلي لملفات SKILL.md في المستودع، وتثبيت فعلي عبر skills.sh CLI.*
