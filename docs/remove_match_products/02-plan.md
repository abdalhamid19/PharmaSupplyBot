# 02 — خطة التنفيذ (Implementation Plan)

> **للمنفذ الآلي:** نفّذ المهام بالترتيب. كل مهمة تنتهي باختبار أخضر + commit. استخدم checkboxes للتتبع.
> **المتطلب المسبق:** worktree معزول جاهز (انظر `03-worktree-guide.md`).

**Goal:** حذف ميزة match-products المستقلة (CLI + GUI + محركها) مع الحفاظ الكامل على `order`.

**Architecture:** إزالة على 4 مراحل: (1) نقل normalization المشتركة، (2) قطع الواجهات (CLI/GUI)، (3) حذف المحرك الميت، (4) تنظيف الاختبارات والوثائق والأدوات. كل مرحلة تُركّب على سابقها، والتراجع ممكن بعد أي مرحلة.

**Tech Stack:** Python 3.11+, Typer, Streamlit, pytest.

**Spec:** `docs/remove_match_products/01-analysis.md` — خريطة التبعيات الكاملة (اقرأها قبل البدء).

## Global Constraints

- ممنوع تعديل أي ملف في القائمة الحمراء (01-analysis.md §8).
- `py run.py order --help` يجب أن يعمل بنجاح بعد كل مهمة.
- قسم `matching:` في config.yaml يبقى كما هو.
- كل مهمة = commit مستقل برسالة واضحة.
- لا تعمل على main مباشرة — داخل worktree فقط.

---

### Task 1: نقل `normalization/` إلى `src/core/normalization/`

**Files:**
- Move: `src/core/drug_matching/normalization/*` → `src/core/normalization/`
- Move: `src/core/drug_matching/pricing.py` → `src/core/normalization/pricing.py`
- Modify: `src/core/normalization/normalizer_matching_brand.py:15`
- Modify: `src/core/matching/search_query_templates.py:5`
- Modify: `src/core/matching/matching_confidence.py:7`
- Modify: `src/core/matching/matching_risk.py:39`
- Modify: `src/core/matching/product_matching_acceptance.py:10`
- Modify: `src/core/matching/product_matching_numeric.py:8`
- Modify: `src/core/identity/manufacturer_identity.py:24`

**Interfaces:**
- Produces: `src.core.normalization.normalizer.parse_drug`, `src.core.normalization.normalizer.components_match` (نفس التواقيع، مسار جديد).

- [ ] **Step 1: نقل الملفات بـ git mv (يحفظ التاريخ)**

```powershell
git mv src/core/drug_matching/normalization src/core/normalization
git mv src/core/drug_matching/pricing.py src/core/normalization/pricing.py
```

- [ ] **Step 2: إصلاح الاستيراد العكسي في normalizer_matching_brand.py**

الملف كان داخل حزمة عمق 3 (`src/core/drug_matching/normalization`) ويستخدم `...identity`. العمق الجديد 2 (`src/core/normalization`)، فالاستيراد النسبي يصبح `..identity`:

```python
# src/core/normalization/normalizer_matching_brand.py:15
# قبل:
            from ...identity.manufacturer_identity import manufacturer_conflict
# بعد:
            from ..identity.manufacturer_identity import manufacturer_conflict
```

- [ ] **Step 3: إعادة توجيه المستوردين الستة**

```python
# src/core/matching/search_query_templates.py:5
# قبل: from ..drug_matching.normalization.normalizer import parse_drug
from ..normalization.normalizer import parse_drug

# src/core/matching/matching_confidence.py:7
# قبل: from ..drug_matching.normalization.normalizer import components_match, parse_drug
from ..normalization.normalizer import components_match, parse_drug

# src/core/matching/matching_risk.py:39 (داخل دالة)
# قبل: from ..drug_matching.normalization.normalizer import parse_drug
from ..normalization.normalizer import parse_drug

# src/core/matching/product_matching_acceptance.py:10
# قبل: from ..drug_matching.normalization.normalizer import components_match, parse_drug
from ..normalization.normalizer import components_match, parse_drug

# src/core/matching/product_matching_numeric.py:8
# قبل (مسار معطوب أصلًا): from .drug_matching.normalization.normalizer import components_match, parse_drug
from .normalization.normalizer import components_match, parse_drug

# src/core/identity/manufacturer_identity.py:24
# قبل: from src.core.drug_matching.normalization.normalizer_manufacturer_extraction import (...)
from src.core.normalization.normalizer_manufacturer_extraction import (...)
```

- [ ] **Step 4: التحقق من عدم وجود مراجع متبقية**

Run: `rg -n "drug_matching.normalization" src/`
Expected: لا نتائج.

- [ ] **Step 5: اختبار سريع للـ smoke**

Run:
```powershell
.venv\Scripts\python.exe -c "from src.core.normalization.normalizer import parse_drug, components_match; print('ok')"
.venv\Scripts\python.exe run.py order --help
```
Expected: `ok` + نجاح `order --help`.

- [ ] **Step 6: تشغيل اختبارات normalization**

Run: `.venv\Scripts\python.exe -m pytest tests/core/drug_matching/test_drug_matching_normalizer.py -x -q`
Expected: PASS (المسار القديم يعمل مؤقتًا؟ لا — إن فشل بسبب المسار، حدّث imports في الملف إلى `src.core.normalization...` ثم أعد التشغيل).

- [ ] **Step 7: Commit**

```powershell
git add -A
git commit -m "refactor: move drug_matching/normalization to core/normalization (order-safe)"
```

---

### Task 2: قطع واجهة CLI — حذف أمر `match-products`

**Files:**
- Delete: `src/cli/commands/cli_match_products.py`
- Modify: `src/cli/cli_commands.py:8,14`
- Modify: `src/cli/typer_app.py:251-277` و `:4`
- Modify: `src/cli/commands/__init__.py:6`

- [ ] **Step 1: حذف الملف بـ git rm**

```powershell
git rm src/cli/commands/cli_match_products.py
```

- [ ] **Step 2: تنظيف cli_commands.py**

```python
# src/cli/cli_commands.py — بعد التعديل
"""CLI command runners for Tawreed authentication, ordering, and exports."""

from __future__ import annotations

from .commands.cli_auth import run_auth_command
from .commands.cli_cart_removal import run_remove_cart_command
from .commands.cli_export_products import run_export_products_command
from .commands.cli_order import run_order_command

__all__ = [
    "run_auth_command",
    "run_export_products_command",
    "run_order_command",
    "run_remove_cart_command",
]
```

- [ ] **Step 3: حذف الأمر من typer_app.py**

احذف البلوك من السطر 251 إلى 277 (بما فيه الديكوريتور `@app.command("match-products")` وكل معاملاته و`raise typer.Exit(_run_registered(ctx, "match-products"))`). حدّث docstring السطر 4 بحذف `match-products` من قائمة الأوامر.

- [ ] **Step 4: تحديث docstring في commands/__init__.py**

احذف عبارة "product matching" من وصف الحزمة.

- [ ] **Step 5: التحقق**

Run:
```powershell
.venv\Scripts\python.exe run.py match-products --help
.venv\Scripts\python.exe run.py order --help
.venv\Scripts\python.exe run.py --help
```
Expected: match-products يرفض (Error: No such command) — order و --help يعملان.

- [ ] **Step 6: Commit**

```powershell
git add -A
git commit -m "feat: remove match-products CLI command (order untouched)"
```

---

### Task 3: قطع واجهة GUI — حذف تاب Product Matching

**Files:**
- Delete: `src/ui/views/streamlit_product_matching.py`
- Modify: `src/ui/streamlit_main.py:13, 85-97, 110-116`
- Modify: `src/ui/views/__init__.py:7`
- Modify: `src/ui/views/streamlit_results.py:29`
- Modify: `src/ui/manual_review/streamlit_manual_review_page_saved.py:164`

- [ ] **Step 1: حذف الملف**

```powershell
git rm src/ui/views/streamlit_product_matching.py
```

- [ ] **Step 2: تنظيف streamlit_main.py**

```python
# احذف السطر 13:
from .views.streamlit_product_matching import render_product_matching_tab

# render_main_tabs تصبح:
def render_main_tabs(app_config, default_profile: str | None, config_path) -> None:
    """Render the main Streamlit tabs."""
    tabs = st.tabs(
        _main_tab_labels()
    )
    (
        overview_tab, auth_tab, order_tab,
        prevented_items_tab, remove_cart_tab, results_tab, run_db_tab,
        manual_review_tab
    ) = tabs
    with overview_tab:
        render_overview(app_config, config_path)
    with auth_tab:
        render_auth_tab(app_config, default_profile, config_path)
    with order_tab:
        render_order_tab(app_config, default_profile, config_path)
    with prevented_items_tab:
        render_prevented_items_manager()
    with remove_cart_tab:
        render_remove_cart_tab(app_config, default_profile, config_path)
    with results_tab:
        render_results_tab(default_profile)
    with run_db_tab:
        render_run_db_tab()
    with manual_review_tab:
        render_manual_review_tab(app_config)

# _main_tab_labels تصبح:
def _main_tab_labels() -> list[str]:
    """Return Streamlit main tab labels."""
    return [
        "Overview", "Auth", "Order",
        "Prevented items", "Remove cart items", "Results", "Run DB",
        "Manual Review"
    ]
```

- [ ] **Step 3: إزالة match-products من قائمة Results**

```python
# src/ui/views/streamlit_results.py:29
# قبل: names = ["order", "match-products", "export-products", "remove-cart"]
names = ["order", "export-products", "remove-cart"]
```

- [ ] **Step 4: إعادة تسمية المسار الوهمي في Manual Review**

```python
# src/ui/manual_review/streamlit_manual_review_page_saved.py:164
# قبل: dummy_run_dir = ARTIFACTS_DIR / "match-products" / "manual_research"
dummy_run_dir = ARTIFACTS_DIR / "order" / "manual_research"
```
(الوظيفة الفعلية تستخدم `order --match-only` — انظر 01-analysis.md §5)

- [ ] **Step 5: تحديث docstring في views/__init__.py**

احذف "Product matching" من وصف الحزمة.

- [ ] **Step 6: التحقق — تشغيل Streamlit يدويًا**

```powershell
.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.headless true
```
تحقق: لا crash، التابات 8 بدل 9، تاب Order يعمل.

- [ ] **Step 7: Commit**

```powershell
git add -A
git commit -m "feat: remove Product Matching tab from GUI (order untouched)"
```

---

### Task 4: حذف محرك matching الميت

**Files:**
- Delete: `src/core/drug_matching/` (كل ما تبقى: `__init__.py`, `pipeline.py`, `config/`, `indexing/`, `tracing/`, `pipeline_components/`, `ai/`, `verification/`, `__pycache__/`)

- [ ] **Step 1: تحقق نهائي من عدم وجود مستوردين**

Run:
```powershell
rg -n "MatchPipeline|drug_matching\.(config|pipeline|indexing|tracing|pipeline_components)" src/ --glob "!__pycache__"
rg -n "from src\.core\.drug_matching|from \.\.drug_matching" src/ --glob "!__pycache__"
```
Expected: النتيجة الوحيدة أو لا نتائج (cli_match_products حُذف في Task 2).

- [ ] **Step 2: الحذف**

```powershell
git rm -r src/core/drug_matching
```

- [ ] **Step 3: التحقق**

```powershell
.venv\Scripts\python.exe run.py order --help
.venv\Scripts\python.exe -m pytest tests/ -x -q --ignore=tests/cli --ignore=tests/ui -k "not hypotheses and not solutions"
```
Expected: order --help يعمل؛ الاختبارات تمر (بعض اختبارات cli/ui ستُصلح في Task 5).

- [ ] **Step 4: Commit**

```powershell
git add -A
git commit -m "feat: remove dead drug_matching engine (pipeline/indexing/tracing/config)"
```

---

### Task 5: تنظيف الاختبارات

**Files:**
- Delete: `tests/cli/test_typer_app_match.py`, `tests/ui/views/test_streamlit_product_matching.py`, `tests/core/drug_matching/test_drug_matching_indexer.py`, `tests/core/matching/test_logging_integration.py` (الجزء الخاص بـ drug_matching) — انظر أدناه
- Move: `tests/core/drug_matching/test_drug_matching_normalizer.py` → `tests/core/normalization/`
- Modify: `tests/cli/test_typer_app_compat.py`, `tests/cli/test_summary.py:251`, `tests/cli/test_registry.py:65`, `tests/cli/test_shortcuts.py`, `tests/cli/test_run_logging_e2e.py`, `tests/core/test_logging_audit.py`, واختبارات solutions/hypotheses (إعادة توجيه imports)

- [ ] **Step 1: حذف ملفات الاختبار الخاصة بـ match-products**

```powershell
git rm tests/cli/test_typer_app_match.py tests/ui/views/test_streamlit_product_matching.py tests/core/drug_matching/test_drug_matching_indexer.py
```

- [ ] **Step 2: نقل اختبار normalizer**

```powershell
New-Item -ItemType Directory -Force tests\core\normalization | Out-Null
git mv tests/core/drug_matching/test_drug_matching_normalizer.py tests/core/normalization/test_normalizer.py
Remove-Item -Recurse -Force tests\core\drug_matching -ErrorAction SilentlyContinue
```
ثم داخل `tests/core/normalization/test_normalizer.py` غيّر:
```python
# قبل: from src.core.drug_matching.normalization.normalizer import (...)
from src.core.normalization.normalizer import (...)
```

- [ ] **Step 3: إعادة توجيه اختبارات solutions/hypotheses**

في كل ملف من القائمة (01-analysis.md §3.3) استبدل:
```python
from src.core.drug_matching.normalization.X import Y
# →
from src.core.normalization.X import Y
```

- [ ] **Step 4: تنظيف اختبارات CLI**

- `tests/cli/test_typer_app_compat.py`: احذف البلوك `# ─── match-products ───` كاملًا (test_match_products_accepts_trace_options).
- `tests/cli/test_summary.py:251`: `for cmd in ("auth", "order", "remove-cart", "export-products"):`
- `tests/cli/test_registry.py:65`: `expected = {"auth", "order", "remove-cart", "export-products"}`
- `tests/cli/test_shortcuts.py`: احذف `test_match_products_accepts_x_shortcut_for_excel` و `test_match_products_accepts_n_shortcut_for_limit`.
- `tests/cli/test_run_logging_e2e.py`: احذف `(["match-products", "--help"], 0)` و `"match-products-help"` من قائمة الحالات.

- [ ] **Step 5: تنظيف اختبارات logging**

- `tests/core/test_logging_audit.py`: احذف إدخال `"src.core.drug_matching"` (سطر 187) وبلوك السطر 209 الخاص بمسار `drug_matching/config/config_helpers.py`.
- `tests/core/matching/test_logging_integration.py`: كل الاختبارات تختبر `drug_matching.config.config_helpers.setup_logging` التي حُذفت — احذف الملف كاملًا:
```powershell
git rm tests/core/matching/test_logging_integration.py
```

- [ ] **Step 6: تشغيل الحزمة كاملة**

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q
```
Expected: كلها PASS أو skipped — لا فشل استيراد.

- [ ] **Step 7: Commit**

```powershell
git add -A
git commit -m "test: clean up match-products tests and redirect normalization imports"
```

---

### Task 6: تنظيف الأدوات والوثائق

**Files:**
- Modify: `tools/update_baseline.py:30`, `tools/rule_audit.py:33,83-84`, `tools/phase_validation.py:46-60`, `tools/migrate_artifacts.py:11`
- Modify: `README.md:56` (قسم المثال)
- Modify: `docs/PROJECT_MAP.md`, `docs/audit_logging.md:20,70-71`, `docs/cli_properties.html:169-195`
- Move/Delete: `docs/product_matching_mode.md`

- [ ] **Step 1: تنظيف tools/**

- `tools/update_baseline.py`: احذف سطر `"src/cli/cli_match_products.py",` من القائمة.
- `tools/rule_audit.py`: احذف السطور 33 و 83-84 (إدخالات cli_match_products).
- `tools/phase_validation.py`: احذف بلوك خطوة `match-products --help` (الأسطر 46-60: أمر التشغيل، التحقق، ومسار CSV المرجعي).
- `tools/migrate_artifacts.py:11`: لو "match-products" مجرد إدخال في خريطة ترحيل تاريخية اتركه؛ لو يُنشئ مجلدات جديدة احذفه.

- [ ] **Step 2: تنظيف README.md**

احذف المثال عند السطر 56 (`py run.py match-products --profile wardany ...`) والفقرة المرافقة إن وجدت.

- [ ] **Step 3: تنظيف docs/**

- `docs/PROJECT_MAP.md`: عدّل/احذف المراجع (الأسطر: 47, 235, 237, 288, 300, 315-316, 346, 352-353, 384, 401-402). استبدل أوصاف الأوامر الخمسة بأربعة.
- `docs/audit_logging.md`: احذف صف الجدول (20) وسطري الأخطاء (70-71) الخاصين بـ cli_match_products.
- `docs/cli_properties.html`: احذف القسم `<h3>أمر match-products</h3>` وما بعده حتى القسم التالي.
- `docs/product_matching_mode.md`: انقله للأرشيف:
```powershell
New-Item -ItemType Directory -Force docs\archive | Out-Null
git mv docs/product_matching_mode.md docs/archive/product_matching_mode_REMOVED.md
```
وأضف في أعلى الملف: `> **تم حذف هذه الميزة من البرنامج في <date>. المحتوى محفوظ للمرجع التاريخي.**`

- [ ] **Step 4: Commit**

```powershell
git add -A
git commit -m "docs: remove match-products references from tools, README, and docs"
```

---

### Task 7: التحقق النهائي الشامل (Acceptance)

**Files:** لا تعديلات — تحقق فقط.

- [ ] **Step 1: اختبارات كاملة**

```powershell
.venv\Scripts\python.exe -m pytest tests/ -q
```
Expected: أخضر بالكامل.

- [ ] **Step 2: التحقق من عدم وجود أي إشارة وظيفية متبقية**

```powershell
rg -n "match.products|match_products|MatchPipeline|drug_matching" src/ tools/ --glob "!__pycache__"
```
Expected: لا نتائج (المرجع الوحيد المسموح: مجلد أرشيف artifacts القديم على القرص + docs/archive التاريخية).

- [ ] **Step 3: السيناريوهات الحية**

```powershell
.venv\Scripts\python.exe run.py --help              # الأوامر: auth, order, remove-cart, export-products
.venv\Scripts\python.exe run.py order --help        # يعمل بكل خياراته بما فيها --match-only
.venv\Scripts\python.exe run.py match-products      # يرفض بلطف
.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.headless true
```
Expected: GUI يفتح بـ 8 تابات، order يعمل end-to-end (لو أمكن اختبار حقيقي بسيط).

- [ ] **Step 4: Commit نهائي + دفع**

```powershell
git add -A
git commit -m "chore: final verification for match-products removal"
git push -u origin feature/remove-match-products
```

بعدها: أنشئ PR من `feature/remove-match-products` إلى `main` (انظر 03-worktree-guide.md §4).
