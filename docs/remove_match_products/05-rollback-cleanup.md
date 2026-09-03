# 05 — التراجع والتنظيف (Rollback & Cleanup)

> كل سيناريوهات الفشل المحتملة + طريقة الخروج منها بدون فقدان عمل.

## 1. مستويات التراجع (من الأخف للأثقل)

### 1.1 تراجع عن تعديل غير معتمد (قبل commit)

```powershell
git restore <file>            # ملف واحد
git restore .                 # كل التعديلات غير المرحّلة
git clean -fd                 # حذف الملفات الجديدة غير المتتبعة (احذر!)
```

### 1.2 تراجع عن آخر commit مع إبقاء التعديلات

```powershell
git reset --soft HEAD~1       # التعديلات تعود للـ staging
git reset HEAD~1              # التعديلات تعود للـ working directory
```

### 1.3 تراجع عن آخر commit بالكامل (خطر — يفقد التعديلات)

```powershell
git reset --hard HEAD~1
```

### 1.4 التراجع عن عدة commits (بعد دفعها للـ remote)

```powershell
git revert <commit-sha>..HEAD # أنشئ commits عكسية — آمن بعد push
git push
```
> لا تستخدم `git push --force` على فرع مشترك أبدًا.

### 1.5 إلغاء الميزة بالكامل والعودة لنقطة الصفر

```powershell
cd C:\pc\py\pyreview\PharmaSupplyBot   # المشروع الأصلي
git worktree remove --force ../PharmaSupplyBot-remove-mmp
git branch -D feature/remove-match-products
```
main لم يُمس إطلاقًا — هذا جوهر فوائد الـ worktree.

## 2. سيناريوهات فشل محددة → حلول محددة

### السيناريو A: كسرت استيرادات normalization بعد النقل

**الأعراض:** `ModuleNotFoundError: No module named 'src.core.normalization'` أو عكسه.

**التشخيص:**
```powershell
rg -n "normalization" src/ --glob "!__pycache__" -l
.venv\Scripts\python.exe -c "import src.core.normalization"
```

**الحل:** راجع Task 1 Step 3 — أكثر خطأ شائع هو نسيان أحد المستوردين الستة أو خطأ في `normalizer_matching_brand.py:15` (`..identity` مقابل `...identity`).

### السيناريو B: order توقف عن العمل بعد حذف drug_matching

**الأعراض:** `order --help` يفشل أو `ModuleNotFoundError` في `src.core.matching.*`

**التشخيص:** واحد من ملفات المنطقة الحمراء استُدعي بالخطأ:
```powershell
git log --oneline -5
rg -n "drug_matching" src/core/matching/ src/tawreed/
```

**الحل:** لو وُجدت مراجع لـ drug_matching في src/core/matching — تراجع عن Task 4 (`git revert <sha>`) وأعد فحص التبعيات: يعني أن ملفًا في matching كان يستورد من الحزمة المحذوفة وتخطاه التحليل.

### السيناريو C: pytest يفشل بعد Task 5

**الأعراض:** collection errors أو import errors في الاختبارات.

**الحل:** 
```powershell
.venv\Scripts\python.exe -m pytest tests/ --co -q 2>&1 | Select-String "ERROR"
```
كل ERROR = ملف اختبار لا يزال يستورد مسارًا قديمًا. صححه أو احذفه (لو كان اختبار match-products فُوّت في القائمة).

### السيناريو D: Streamlit crash بعد Task 3

**الأعراض:** صفحة فارغة أو خطأ TabError/ImportError.

**التشخيص الشائع:** عدم تطابق عدد التابات في unpack — راجع Task 3 Step 2: عدد المتغيرات في الـ tuple يجب أن يساوي عدد عناصر `_main_tab_labels()` (8 = 8).

### السيناريو E: تعارض أثناء rebase مع main

```powershell
git rebase --abort   # إلغاء آمن — تعود لما قبل الـ rebase
# أو حل التعارض يدويًا ثم:
git rebase --continue
```

## 3. التنظيف الدوري (بعد دمج الـ PR)

### 3.1 على GitHub

- احذف الفرع البعيد من صفحة الـ PR (زر Delete branch) أو:
```powershell
git push origin --delete feature/remove-match-products
```

### 3.2 محليًا

```powershell
git worktree remove ../PharmaSupplyBot-remove-mmp
git branch -d feature/remove-match-products   # -d ينجح فقط لو مدمج
git fetch --prune
git worktree prune
```

### 3.3 فحص الفروع الراكدة (شهرًا)

```powershell
# فروع مدمجة يمكن حذفها
git branch --merged origin/main

# worktrees المتبقية
git worktree list
```

## 4. أرشيف artifacts القديم (قرار مستقبلي)

`artifacts/match-products/` يبقى على القرص بعد الحذف (قرارك: إزالة من قائمة Results فقط). لاحقًا لو أردت:

```powershell
# أرشفته (مثال) — لا تحذفه في هذا الـ PR
Compress-Archive -Path artifacts\match-products -DestinationPath artifacts\archive_match_products_2026.zip
Remove-Item -Recurse artifacts\match-products
```
> هذا قرار منفصل وليس جزءًا من الخطة الحالية — لا تدمجه في نفس الـ PR.

## 5. ما بعد الدمج (Post-merge)

- [ ] راقب أول تشغيل حقيقي لـ `order` بعد الدمج
- [ ] راقب صفحة Manual Review (زر Search)
- [ ] حذف worktree والفرع المحلي (§3.2)
- [ ] حدّث `docs/PROJECT_MAP.md` في main إذا لزم (لو تغيرت هيكلة docs)
