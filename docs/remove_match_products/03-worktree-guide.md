# 03 — دليل Worktree (بيئة العمل المعزولة)

> العمل داخل worktree يعطيك: عزلًا تامًا عن main، إمكانية تشغيل نسختين جنبًا إلى جنب، وحذفًا نظيفًا بعد الدمج.

## 1. إنشاء الـ worktree

### 1.1 من داخل المشروع (PowerShell)

```powershell
# أولًا: تأكد أن أحدث main موجود محليًا
git fetch origin
git worktree add -b feature/remove-match-products ../PharmaSupplyBot-remove-mmp origin/main
```

- `feature/remove-match-products` = اسم الفرع الجديد
- `../PharmaSupplyBot-remove-mmp` = المجلد الجديد (خارج المشروع الحالي، بنفس مستواه)
- `origin/main` = نقطة التفرع

### 1.2 التحقق من نقطة التفرع

```powershell
git -C ../PharmaSupplyBot-remove-mmp log --oneline -3
# يجب أن يكون آخر commit هو آخر commit في origin/main
```

### 1.3 الدخول والتأكد من وجود نسخة الكود

```powershell
cd ../PharmaSupplyBot-remove-mmp
ls
# يجب أن ترى: run.py, streamlit_app.py, src/, tests/, docs/, requirements.txt ...
git status
# Should show: On branch feature/remove-match-products
```

### 1.4 تجهيز البيئة داخل المجلد الجديد (مهم في Windows)

الـ worktree لا يشارك `.venv` ولا `.env` — أنشئهما محليًا:

```powershell
# البيئة الافتراضية
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# ملف البيئة — انسخه من المشروع الأصلي
Copy-Item ..\PharmaSupplyBot\.env .env
Copy-Item ..\PharmaSupplyBot\config.yaml state\config.yaml -ErrorAction SilentlyContinue
```

> **ملاحظة:** لو `.env` فيه بيانات حساسة، تأكد أن `.gitignore` يمنع رفعه (موجود أصلًا في المشروع).

### 1.5 ابدأ العمل

كل مهام `02-plan.md` تُنفّذ من داخل `../PharmaSupplyBot-remove-mmp`.

## 2. قواعد ذهبية أثناء العمل

- لا تعدّل شيئًا في المجلد الأصلي `C:\pc\py\pyreview\PharmaSupplyBot` أثناء وجود الميزة.
- commit صغير بعد كل مهمة ناجحة (الخطة تحدد رسائل الـ commit جاهزة).
- دفع دوري إلى GitHub: `git push -u origin feature/remove-match-products` — لا تنتظر النهاية.
- لو ظهر تعارض مع main تحدّث أثناء عملك:
  ```powershell
  git fetch origin
  git rebase origin/main
  ```

## 3. التنظيف بعد الانتهاء من العمل

### 3.1 ادفع كل عملك إلى GitHub أولًا

```powershell
git push -u origin feature/remove-match-products
git log origin/main..HEAD --oneline   # راجع كل الـ commits قبل الدمج
```

### 3.2 بعد دمج الـ PR على GitHub، احذف الـ worktree

```powershell
cd C:\pc\py\pyreview\PharmaSupplyBot
git worktree remove ../PharmaSupplyBot-remove-mmp
# لو كان فيه ملفات غير متتبعة عالقة:
git worktree remove --force ../PharmaSupplyBot-remove-mmp
```

### 3.3 نظّف الفروع الراكدة دوريًا

```powershell
# حذف الفرع المحلي بعد الدمج
git branch -d feature/remove-match-products

# حذف مرجع الفرع البعيد بعد حذفه على GitHub
git fetch --prune
git worktree prune

# عرض الفروع المدمجة لتحديد الراكدة
git branch --merged origin/main
```

## 4. إنشاء الـ PR على GitHub

بعد الـ push النهائي (Task 7):

```powershell
gh auth status   # تأكد أنك مسجل
gh pr create --base main --head feature/remove-match-products --title "Remove standalone match-products (CLI + GUI + engine)" --body "See docs/remove_match_products/ for full plan and analysis. Order untouched: run.py order and --match-only verified."
```

بيانات الحساب للـ push (استخدم Personal Access Token — GitHub لا يقبل كلمة المرور):

- **Username:** `abdalhamid19`
- **Email:** `abdalhamid.mahrous@gmail.com`

لو لم يكن الـ remote مضبوطًا:
```powershell
git remote -v   # تحقق أولًا
git remote set-url origin https://github.com/abdalhamid19/PharmaSupplyBot.git
# أو مع token مباشرة (تجنّب حفظ token في الملفات!)
```

> **أمان:** لا تكتب الـ token في أي ملف داخل المشروع. استخدم Git Credential Manager (المدمج في Git for Windows) أو `gh auth login`.
