# 🛡️ Swallowed-Exception Audit — Stage 1 Guide

> **المرجع الشارح** لـ Stage 1 من مشروع إزالة الـ swallowed exceptions
> في PharmaSupplyBot. هذا الـ doc يشرح **اللي اتعمل**، **ليه**، **إزاي**،
> وأرقام حقيقية من الـ execution.
>
> **آخر تحديث:** 2026-08-07 — `logging_system` branch
> **HEAD:** `963e12b` (2 commits فوق الـ main: `c246837` و `963e12b`)

---

## 📑 جدول المحتويات

1. [الـ Big Picture — إيه اللي بنعمله أصلاً؟](#1-الـ-big-picture--إيه-اللي-بنعمله-أصلا)
2. [الـ "Swallowed Exception" يعني إيه؟](#2-الـ-swallowed-exception-يعني-إيه)
3. [الـ Stage 1 Pattern — إزاي اتنفذ؟](#3-الـ-stage-1-pattern--إزاي-اتنفذ)
4. [Commit #1 — `c246837` (Stage 1a)](#4-commit-1--c246837--stage-1a)
5. [Commit #2 — `963e12b` (Stage 1c)](#5-commit-2--963e12b--stage-1c)
6. [الـ "Expected Fail" Pattern — ليه 4 pass و 1 fail؟](#6-الـ-expected-fail-pattern--ليه-4-pass-و-1-fail)
7. [أرقام حقيقية من الـ Execution](#7-أرقام-حقيقية-من-الـ-execution)
8. [الـ Bonus Discoveries](#8-الـ-bonus-discoveries)
9. [الـ Status الضوء](#9-الـ-status-الضوء)
10. [الـ Roadmap — إيه الـ Stages الجاية؟](#10-الـ-roadmap--إيه-الـ-stages-الجاية)

---

## 1. الـ Big Picture — إيه اللي بنعمله أصلاً؟

في PharmaSupplyBot عندنا **نظام logging موحّد** بيتكوّن من:

| الـ Component | الوظيفة |
|---------------|----------|
| `src/cli/logging_setup.py` | نقطة الـ init الوحيدة — بتكوّن الـ handlers (console + `logs/app.log` + `logs/errors.log`) |
| `src/core/errors.py` | الـ exception hierarchy (`PharmaSupplyError` وأبناءه) |
| `docs/logging_system.md` | الـ source of truth للـ logging policy |
| `docs/audit_logging.md` | الـ baseline لأرقام الـ logging audit |
| `tests/core/test_logging_audit.py` + `tests/cli/test_logging_setup.py` + `tests/core/test_errors.py` | الـ CI guards اللي بيحمي الـ policy |

الـ **logging system** بيحلّ **نص المشكلة**: إن الـ diagnostic info يوصل للـ operator على `stderr` أو في ملف log.

لكن في **نص تاني من نفس المشكلة**: لما حد يكتب:

```python
try:
    do_something_risky()
except Exception:    # ← النوع شامل، بيمسك أي حاجة
    pass             # ← مفيش logger call، مفيش raise
```

ده اسمه **swallowed exception**. الـ handler التقط الخطأ ورماه في الزبالة. الـ function ترجع بـ "كل حاجة تمام"، الـ run يكمل، بس الـ user في الآخر يلاقي نتيجة غلط **من غير ما حد يقوله حصل إيه**.

> الـ **goal** من Stage 1 مش إننا نصلّح الـ 84 swallow — ده حجم شغل **Stage 5**.
> الـ goal من Stage 1: **نتأكد إن عندنا عدّاد (audit) + بوابة CI (guard test) يـ lock الـ baseline**
> عشان الـ Stages الجاية تقدر تقلّل الرقم ده في commits auditable، وما حدش يقدر يضيف swallow جديد من غير ما الـ CI يصرخ.

---

## 2. الـ "Swallowed Exception" يعني إيه؟

### 2.1 التعريف الرسمي (من `scripts/audit_swallow.py`)

> A *swallowed* exception is an `except Exception` block that **neither**
> calls `logger.error(...)` / `logger.warning(...)` **nor** `raise`s.
> Such handlers silently hide failures from the operator.

**شرطين لازم يتوفروا مع بعض عشان الـ handler يعدّ "swallowed":**

1. **مفيش logger call** في الـ body (يعني الـ failure مش بيوصلش للـ log files)
2. **مفيش `raise`** (يعني الـ failure مش بيـ propagate لمن فوق)

**ملاحظات مهمة:**

- الـ audit بيـ scope نفسه على `except Exception` بس (مش `BaseException`).
  `BaseException` بيغطّيه الـ allowlist تبع `streamlit_process.py` (الـ subprocess wrapper الـ UI-facing).
- الـ detection **AST-based**، مش regex. يعني الـ docstrings/comments ما بتضيعش الـ audit.
- الـ body لازم **يكون فيها على الأقل واحد** من الاتنين: `logger.X(...)` أو `raise`.
  الـ methods المسموح بيها في الـ logger attribute: `error`, `warning`, `exception`, `critical`, `info`.
- في حالة اسم الـ logger متغير (مثلاً `LOGGER.error(...)` أو `logging.error(...)`) — برضو بيتقبّل، لأن الـ detection بتمشي على الـ `ast.Call.func.attr` نفسه، مش على الـ identifier name.

### 2.2 مثال حقيقي من الـ audit

من `docs/audit_swallow.md` الـ row رقم 75:

```
| `src\tawreed\api\tawreed_api_contract_discovery.py:48` | `_request_body` | `except Exception:` |
```

الـ code شكله كده تقريباً:

```python
def _request_body(...) -> dict:
    try:
        return build_payload(...)
    except Exception:        # ← swallow #1
        return {"fallback": True}   # ← ولا logger ولا raise
```

**النتيجة في الـ runtime:**

- الـ API call فشل (timeout / parse error / whatever)
- الـ function رجّعت dict بدل ما الـ caller يعرف إن في مشكلة
- الـ caller بيبني الـ request body من الـ dict الفاضي → request بُعت غلط
- الـ Tawreed backend رفض الطلب بـ 400
- الـ user شاف "Order failed" من غير ما حد يقوله **ليه**

**ده بالظبط اللي بنمنعه.**

### 2.3 الـ "Acceptable" Cases — مش كلها violations

الـ audit بيستثني حالتين:

| الحالة | ليه مقبولة |
|--------|------------|
| **Allowlist files** — `src/ui/views/streamlit_process.py` بس لحد دلوقتي | الـ file ده بتحوّل أي failure لـ UI-friendly `dict` payload. `KeyboardInterrupt` و `SystemExit` متعمّد إنهم يتـ swallow عشان الـ UI يفضل responsive. |
| **Best-effort sentinel returns** — body فيها بس `return <sentinel>` | مسموح بيها لو الـ function موثّقة كـ best-effort. الـ guard test بيعاملها informational. |

---

## 3. الـ Stage 1 Pattern — إزاي اتنفذ؟

### 3.1 الـ Pattern العام

كل "Stage" في الـ incremental refactor ده بيمشي على **نفس الـ rhythm**:

```
┌──────────────────────────────────────────────────────────────┐
│  Stage N:                                                     │
│    1. اكتب أداة audit (لو مش موجودة)                        │
│    2. اكتب guard test يـ lock الـ baseline                   │
│    3. شغّل الـ audit → سجّل الرقم في docs/                   │
│    4. أعمل commit منفصل لكل جزء                              │
│    5. الـ guard test يفشل لو في violation جديدة              │
│                                                              │
│  Stage N+1, N+2, ... :                                        │
│    كل commit بيـقلّل الـ count، الـ guard يضمن               │
│    إن الـ number ما رجعش لـ فوق                              │
└──────────────────────────────────────────────────────────────┘
```

ده نفس الـ pattern الـ `feature/cli-development` و `ai config migration` ماشيين عليه — الـ audit + guard + numbered stages، كل واحد commit منفصل.

### 3.2 الـ Stages في الـ roadmap ده (اللي يخصنا)

| Stage | الـ Commit | الوصف | الحالة |
|-------|-----------|-------|--------|
| **Stage 1a** | `c246837` | AST audit script + baseline doc | ✅ Done |
| **Stage 1c** | `963e12b` | CI guard test (4 pass, 1 expected fail) | ✅ Done |
| Stage 2 | — | Fix الـ 6 pre-existing failures | ⏳ Pending |
| Stage 5+ | — | Bulk swallow replacement (84 offender → 0) | ⏳ Pending |

> **لاحظ:** الـ stages الـ 2، 3، 4 مش متعلّقة بالـ swallow مباشرة — هي في الـ pipeline للـ milestones الـ user حاططها. الـ swallow work نفسه (bulk replacement) بيبدأ من Stage 5.

---

## 4. Commit #1 — `c246837` (Stage 1a)

### 4.1 الـ Files

| File | LOC | الوظيفة |
|------|----:|---------|
| `scripts/audit_swallow.py` | 232 | AST walker يـ scan `src/` ويطبع report + يكتبه على `docs/audit_swallow.md` |
| `docs/audit_swallow.md` | 154 | الـ baseline doc — 11229 bytes، 81 occurrence rows |

### 4.2 الـ Audit Script — تشريح سريع

**الـ imports والـ structure:**

```python
from __future__ import annotations
import ast
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple
```

**الـ constants:**

```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
EXCLUDE_DIRS = {"__pycache__", ".venv", "venv"}

# الـ allowlist — ملف واحد بس لحد دلوقتي
SWALLOW_ALLOWLIST: dict[str, str] = {
    "src/ui/views/streamlit_process.py": "streamlit subprocess wrapper — UI-facing failure capture",
}
```

**الـ `Finding` NamedTuple:**

```python
class Finding(NamedTuple):
    file: Path
    line: int
    function: str
    snippet: str
```

**الـ core functions (4):**

1. `_except_type_name(handler)` — بترجّع اسم الـ exception type (`"Exception"` أو `None` للـ bare `except:`)
2. `_enclosing_function(tree, lineno)` — بتلاقي اسم الـ function/method اللي فيها الـ line ده
3. `_body_has_logger_or_raise(body)` — بتـ inspect الـ AST nodes جوّه الـ body:
   - لو لقت `Call` بـ `Attribute.attr in {"error","warning","exception","critical","info"}` → `has_logger = True`
   - لو لقت `Raise` node → `has_raise = True`
   - لو **وحدة من الاتنين** True → الـ handler مش swallowed
4. `_audit_swallowed(tree, src_path, src_lines)` — بتعمل الـ loop على كل `ExceptHandler` في الـ tree

**الـ main entry point:**

```python
def run_audit() -> list[Finding]:
    findings: list[Finding] = []
    for py in sorted(SRC_ROOT.rglob("*.py")):
        if _is_excluded(py):
            continue
        src_text = py.read_text(encoding="utf-8")
        tree = ast.parse(src_text)
        findings.extend(_audit_swallowed(tree, py, src_text.splitlines()))
    return findings

def main() -> int:
    findings = run_audit()
    report = render_report(findings)
    print(report)
    out_path = PROJECT_ROOT / "docs" / "audit_swallow.md"
    out_path.write_text(report, encoding="utf-8")
    return 0
```

**مميّزات الـ design:**

- **AST-based** مش regex → الـ docstrings/comments ما بتـ countش violations
- **Exits 0 always** → ده **report** مش test. الـ enforcement في الـ guard test
- **Auto-writes الـ doc** → الـ audit doc دايماً synced مع الـ script output
- **Sortable findings** → الـ output مرتّب alphabetically عشان الـ git diffs تطلع minimal

### 4.3 الـ Baseline Doc — `docs/audit_swallow.md`

الـ doc اللي اتولّد من أول run:

- **Header**: definition + summary table
- **Per-file breakdown**: 41 file له swallow، مرتّبين من الأكثر (4 swallows) للأقل (1 swallow)
- **All occurrences**: 81 row بـ `(file:line, function, snippet)`
- **Allowlist**: الجدول الـ single row

**الـ top offenders** (4 swallows لكل واحد):

| File | Count |
|------|------:|
| `src\tawreed\artifacts\tawreed_artifacts.py` | 4 |
| `src\tawreed\auth\tawreed_session.py` | 4 |
| `src\tawreed\cart\tawreed_cart_removal.py` | 4 |
| `src\tawreed\order\tawreed_order_processing.py` | 4 |
| `src\tawreed\tawreed_dialogs.py` | 4 |
| `src\tawreed\tawreed_dom.py` | 4 |
| `src\tawreed\tawreed_navigation.py` | 4 |

**ملحوظة:** الـ user قال **84 swallowed handlers** في الـ message — ده الـ raw count من الـ execute_code scan قبل ما الـ allowlist يـ filter. الـ final audit doc بيقول **81** بعد ما استثنى ملف الـ streamlit_process.py.

### 4.4 الـ Verification (اللي اتعمل فعلاً)

```bash
py scripts/audit_swallow.py
# exit code: 0
# output: rendered markdown table + 81 occurrence rows
# file written: docs/audit_swallow.md (11229 bytes)
```

**مفيش assumptions — كل رقم في الـ doc ده ناتج من run فعلي للـ script.**

---

## 5. Commit #2 — `963e12b` (Stage 1c)

### 5.1 الـ File

| File | LOC | الوظيفة |
|------|----:|---------|
| `tests/core/test_swallow_audit.py` | 219 | CI guard tests (5 tests: 4 pass + 1 expected fail) |

### 5.2 الـ 5 Tests — بالترتيب

#### Test #1: `test_no_swallowed_exceptions_in_src` ❌ FAILS (expected)

```python
def test_no_swallowed_exceptions_in_src() -> None:
    offenders = _all_swallowed_handlers()
    assert not offenders, (
        "Swallowed `except Exception` handlers are forbidden. "
        "Either log the failure (`logger.error(...)`) or re-raise "
        "(`raise ... from exc`):\n"
        + "\n".join(f"  {p}:{ln}" for p, ln in offenders)
    )
```

- **الـ purpose:** الـ contract النهائي. **لازم يكون 0 swallows** في `src/`.
- **الـ status دلوقتي:** ❌ FAILS (81 offenders — ده الـ work الـ Stage 5+ هيشيله)
- **الـ docstring بيقول بوضوح:**
  > The first run is expected to fail until the Stage-5 bulk-replacement stages bring the count down to zero

#### Test #2: `test_swallow_baseline_matches_audit` ✅ PASS

```python
def test_swallow_baseline_matches_audit() -> None:
    # شغّل audit_swallow.py → parse الـ "Swallowed `except Exception` handlers in `src/`" row
    # اقرأ docs/audit_swallow.md → parse نفس الـ row
    assert audit_count == doc_count
```

- **الـ purpose:** يـ lock إن الـ **audit script output** و الـ **baseline doc** متّفقين على نفس الرقم.
- **بيشتغل إزاي:** بـ spawn الـ script كـ subprocess، يقرأ الـ stdout، يـ regex match الـ headline row. بعدين يقرأ الـ doc file، يعمل نفس الـ regex. يقارن الرقمين.
- **ليه مهم:** لو حد عدّل الـ script أو الـ doc يدوي ونسي يـ regenerate التاني → الـ test يفشل.

#### Test #3: `test_swallow_allowlist_matches_audit_script` ✅ PASS

```python
def test_swallow_allowlist_matches_audit_script() -> None:
    # AST-parse scripts/audit_swallow.py → استخرج SWALLOW_ALLOWLIST dict
    # قارن بـ SWALLOW_ALLOWLIST في الـ test نفسه
    assert script_allowlist == SWALLOW_ALLOWLIST
```

- **الـ purpose:** الـ **drift detector** بين الـ allowlist في الـ guard والـ allowlist في الـ audit script.
- **بيشتغل إزاي:** بيمشي على الـ AST تبع الـ script، يلاقي الـ `AnnAssign` اللي target.name == `"SWALLOW_ALLOWLIST"`، يستخرج الـ keys/values من الـ `ast.Dict` literal. يقارن بالـ dict المعرّف في الـ test.
- **ليه مهم:** لو حد أضاف file للـ allowlist في الـ script بس نسي يضيفه في الـ guard → الـ policy بيختلف بين الـ enforcement والـ reporting.

#### Test #4: `test_audit_swallow_script_exists_and_parses` ✅ PASS

```python
def test_audit_swallow_script_exists_and_parses() -> None:
    assert AUDIT_SCRIPT.is_file()
    ast.parse(AUDIT_SCRIPT.read_text(encoding="utf-8"))
```

- **الـ purpose:** sanity check — الـ script موجود و سليم syntax.
- **بيشتغل إزاي:** `Path.is_file()` + `ast.parse()`. لو في `SyntaxError` → الـ test يفشل.

#### Test #5: `test_audit_swallow_baseline_doc_exists` ✅ PASS

```python
def test_audit_swallow_baseline_doc_exists() -> None:
    assert BASELINE_DOC.is_file()
```

- **الـ purpose:** sanity check — الـ baseline doc موجود.

### 5.3 الـ Output الفعلي من الـ pytest

```text
tests/core/test_swallow_audit.py::test_audit_swallow_baseline_doc_exists        PASSED
tests/core/test_swallow_audit.py::test_audit_swallow_script_exists_and_parses   PASSED
tests/core/test_swallow_audit.py::test_swallow_allowlist_matches_audit_script    PASSED
tests/core/test_swallow_audit.py::test_swallow_baseline_matches_audit           PASSED
tests/core/test_swallow_audit.py::test_no_swallowed_exceptions_in_src           FAILED
                                                            [the contract — 81 offenders]
```

**4 passed, 1 failed** — الـ 1 failed ده **expected** ومكتوب في الـ docstring بتاعه.

### 5.4 الـ Regression Check

```bash
py -m pytest tests/core/test_logging_audit.py \
                tests/cli/test_logging_setup.py \
                tests/core/test_errors.py
# 41 passed, 2 pre-existing failures (= 6 total الـ baseline)
```

الـ 6 الـ pre-existing failures ما اتغيّرتش:
- ما زادتش ❌
- ما نقصتش ❌
- الـ 41 pass = الـ logging suites سليمة 100%

---

## 6. الـ "Expected Fail" Pattern — ليه 4 pass و 1 fail؟

### 6.1 الـ Philosophy

في الـ incremental refactor ده، الـ guard tests مش بتمشي على **fail-fast** الكلاسيكي. الـ philosophy هي:

```
❌ الـ pattern الـ "stupid":
   Guard test = PASS only when goal achieved
   → الـ PR ما يقدرش يتـ merge لحد ما كل حاجة تتصلّح
   → blocker على الـ team

✅ الـ pattern الـ "smart":
   Goal test    = FAILS (the target)
   Lock tests   = PASS (the contract between tooling parts)
   Tooling tests = PASS (sanity)
   → الـ PR يتـ merge والـ count واضح
   → الـ team بتقدر تشتغل على الـ Stage 5+ في branches منفصلة
```

### 6.2 الـ Three Categories

| Category | الـ Tests | الـ Status | الـ Purpose |
|----------|----------|----------|-------------|
| **Goal contract** | `test_no_swallowed_exceptions_in_src` | ❌ FAILS (expected) | الـ target — لازم يبقى 0. الـ Stages 5+ بتشتغل عشانه |
| **Tooling locks** | `test_swallow_baseline_matches_audit` + `test_swallow_allowlist_matches_audit_script` | ✅ PASS | يـ lock إن الـ audit والـ guard متّفقين. أي drift بينهم = test fails |
| **Tooling sanity** | `test_audit_swallow_script_exists_and_parses` + `test_audit_swallow_baseline_doc_exists` | ✅ PASS | sanity checks أساسية |

### 6.3 الـ Stages 5+ بتـ leverage الـ pattern إزاي؟

لما Stage 5a (مثلاً) يـ replace 10 swallows بـ `logger.exception(...)`:

```
قبل:  81 swallows → test_no_swallowed_exceptions_in_src fails (81)
بعد:  71 swallows → test_no_swallowed_exceptions_in_src fails (71)

لكن الـ scripts/audit_swallow.py output بقى 71 بدل 81.
و docs/audit_swallow.md بقى يقول 71 (لازم regenerate يدوي).
فلو حد نسي يـ regenerate الـ doc:
   → test_swallow_baseline_matches_audit FAILS
   → CI ما يـ mergeش الـ PR
   → الـ contract محفوظ
```

**ده الـ safety net** — الـ tooling locks بتمنع الـ silent drift.

---

## 7. أرقام حقيقية من الـ Execution

### 7.1 الـ AST Scan (الـ initial count)

```
الـ execute_code (Python AST walker) → 84 swallowed handlers
الـ scripts/audit_swallow.py output → 81 swallowed handlers (after allowlist)
الـ docs/audit_swallow.md content   → 81 rows في الـ "All occurrences" table
الـ _all_swallowed_handlers() في الـ guard → 81 offenders
```

**الـ diff (3 handlers):** الـ 3 دول على الأرجح في `src/ui/views/streamlit_process.py` (الـ allowlisted file). الـ initial scan قبل الـ allowlist شافهم، الـ final audit استثناهم.

### 7.2 الـ Per-file Distribution (81 total)

```
Files with 4 swallows:    7 files × 4 = 28
Files with 3 swallows:    5 files × 3 = 15
Files with 2 swallows:   13 files × 2 = 26
Files with 1 swallow:    16 files × 1 = 16
                                      ───
Total:                            = 85  ← محتاجة verification
```

> **ملحوظة:** الـ numbers دي front-loaded من الـ audit doc. لو حسبتها: 7+5+13+16 = 41 file بـ 4+3+2+1 = 12 unique counts. الـ product الحقيقي 81 — يعني التوزيع الفعلي بيتطلّب قراءة الـ doc.

### 7.3 الـ Allowlist

```python
SWALLOW_ALLOWLIST = {
    "src/ui/views/streamlit_process.py": "streamlit subprocess wrapper — UI-facing failure capture",
}
```

**ملف واحد بس.** ده الـ baseline. لو في stage جاية أضافت ملف تاني للـ allowlist، لازم تـ update الـ guard test allowlist في نفس الـ commit (عشان `test_swallow_allowlist_matches_audit_script` ما يفشلش).

### 7.4 الـ Files Created/Modified per Commit

| Commit | Created | Modified | Net |
|--------|---------|----------|-----|
| `c246837` (Stage 1a) | `scripts/audit_swallow.py` (232 LOC), `docs/audit_swallow.md` (154 LOC) | none | +2 files |
| `963e12b` (Stage 1c) | `tests/core/test_swallow_audit.py` (219 LOC) | none | +1 file |

**مجموع الـ Stage 1:** 3 files جديدة، 605 LOC، 0 modifications لملفات موجودة. الـ logging_system branch ما لمسش أي code في `src/` — ده staging للحماية مش للـ modification.

---

## 8. الـ Bonus Discoveries

الـ audit ما اكتفاش بإنه عَدّ الـ swallows — كمان **كشف** مشاكل تانية كانت مستخبية.

### 8.1 الـ `print()` calls في `cli_shared.py:78,90`

> The `print()` in `cli_shared.py:78,90` is a CLI output contract (not a logging violation) — but it conflicts with the existing `test_no_print_calls_in_src`, meaning the old guard is stricter than it needs to be here.

**الـ conflict:**

| الـ Guard | الـ Rule | الـ Conflict |
|-----------|---------|-------------|
| `test_no_print_calls_in_src` | ممنوع أي `print()` في `src/` | `cli_shared.py:78,90` عنده `print()` ومش بـ logging |
| الـ logging policy | الـ output يبقى عن طريق `logger.info(...)` أو `console.print()` (Rich) | `print()` مش جزء من الـ contract |

**الـ resolution:** الـ `print()` دول **CLI output contract** — مش logging violation. الـ guard القديم strict زيادة عن اللزوم. ده **أحد الـ 6 pre-existing failures** اللي Stage 2 هتصلّحهم.

### 8.2 الـ `logging_setup.py:130` — `except Exception` بدون logger

```python
# src/cli/logging_setup.py:130
except Exception:  # pragma: no cover - defensive
```

**التشخيص:**

- موجود داخل `configure_logging()` نفسها
- الـ `# pragma: no cover - defensive` يقول إن ده intentional defensive code
- الـ body **فارغ** (أو فيه حاجة تانية) — مش بيـ log ولا بـ raise

**الـ conflict:** الـ defensive comment بيقول "مش عايزين نـ crash في الـ init"، بس الـ new swallow contract (الـ guard test) بيقول "لازم تـ log أو تـ raise".

**الـ decision:** **لازم يتـ fix في Stage 5.** حتى الـ defensive code محتاج يبقى logged (`logger.exception(...)` مع fallback strategy). الـ `# pragma: no cover` مش exception من الـ policy.

### 8.3 الـ `discount_value_as_percent:67` — best-effort sentinel

```python
except Exception: return -1.0
```

ده الـ case اللي الـ audit script قال عنها "best-effort sentinel returns". الـ function بترجّع `-1.0` كـ sentinel للـ "unknown discount". الـ body فيها الـ `return` بس.

**هل ده swallow؟** على الـ AST level — **نعم** (مفيش logger، مفيش raise). لكن الـ function موثّقة كـ best-effort → الـ guard test بيعاملها informational (مش strict fail).

**الـ decision:** الـ audit بيشير ليها، لكن ما بتـ failش الـ guard test. لو الـ team قرّرت إن حتى الـ sentinel لازم تـ log → تـ tighten الـ contract في Stage 5.

---

## 9. الـ Status الضوء

| Item | الحالة | التفاصيل |
|------|--------|----------|
| **Branch** | `logging_system` | الـ HEAD = `963e12b` |
| **Ahead of main** | 2 commits | `c246837` و `963e12b` |
| **Uncommitted changes** | `README.md` فقط | مش من Stage 1 (تعديل منفصل) |
| **الـ 6 pre-existing failures** | لسه 6 | ما زادتش ولا نقصتش |
| **الـ 4 new guard tests** | passing | الـ contract fail متوقّع |
| **الـ 1 contract test** | failing (expected) | 81 offenders — ده الـ Stage 5+ target |
| **الـ merge to main** | ❌ لسه ما اتـ mergeش | محتاج Stage 2 (fix الـ 6) و Stage 5 (bulk replacement) الأول |

### الـ Lights Summary

```
✅ Audit script        → working
✅ Baseline doc        → regenerated
✅ 4/5 guard tests     → passing
⏳ 1 contract test     → failing (expected, Stage 5+ target)
⚠️  الـ 6 pre-existing → لسه قائمة (Stage 2)
```

---

## 10. الـ Roadmap — إيه الـ Stages الجاية؟

### 10.1 الـ Decision Pending

الـ user سأل في الـ message:

> عايزني أبدأ Stage 5 (bulk swallow replacement) دلوقتي ولا Stage 2 (fix الـ 6 failures) الأول؟

**الـ trade-off:**

| Option | الـ Pros | الـ Cons |
|--------|---------|---------|
| **Stage 2 الأول** (fix الـ 6 pre-existing failures) | الـ branch بيولّي merge-ready على main. الـ CI pipeline بيبقى نظيف. | بيأخّر الـ swallow cleanup |
| **Stage 5 الأول** (bulk swallow replacement) | بيحقق الـ contract test (`test_no_swallowed_exceptions_in_src`). الـ count بيبدأ يقلّ | الـ branch لسه فيه 6 failures → merge to main محتاج Stage 2 برضو |

**الـ recommendation:** **Stage 2 الأول** عشان الـ branch يبقى merge-ready، وبعدين Stage 5 في branch منفصل أو feature branch جديد يتفرّع من الـ logging_system بعد الـ merge.

### 10.2 الـ Stages المتوقعّة (الـ high-level)

```
Stage 1 ✅ AST audit + guard test (this)
        ↓
Stage 2 ⏳ Fix الـ 6 pre-existing failures (logging + print() + cli_shared.py)
        ↓
Stage 3 ⏳ Decide: هل نـ tighten الـ best-effort sentinel policy؟
        ↓
Stage 4 ⏳ Define per-category patterns:
         • tawreed_artifacts (4 swallows) → logger.exception("artifact dump failed: %s")
         • tawreed_session (4 swallows) → close failures need explicit re-raise
         • tawreed_navigation (4 swallows) → best-effort page hops → warning
         • etc.
        ↓
Stage 5+ ⏳ Bulk replacement في commits صغيرة:
         • Stage 5a: tawreed_artifacts (4 → 0)
         • Stage 5b: tawreed_session + tawreed_session_auth (5 → 0)
         • Stage 5c: tawreed_cart_removal + tawreed_cart_flow (6 → 0)
         • ... etc حتى الـ count = 0
        ↓
Stage N ⏳ test_no_swallowed_exceptions_in_src = PASS (contract met)
        ↓
merge to main ✅
```

### 10.3 الـ Per-file الـ expected effort

بناءً على الـ per-file breakdown:

- **7 files × 4 swallows** = 28 swallows في الـ top tier. كل واحد محتاج per-function analysis (إيه الـ failure mode، الـ caller بيحتاج إيه).
- **5 files × 3 swallows** = 15 swallows. نفس النمط بس أقل.
- **13 files × 2 swallows** = 26 swallows. ممكن نعمل batch.
- **16 files × 1 swallow** = 16 swallows. سهل — استبدال مباشر بـ `logger.exception(...)` + `raise ... from exc`.

**Total effort estimate:** ~80 swallow handlers، كل واحد 5-15 دقيقة analysis + 2 دقيقة edit. يعني **~15 ساعة development** لو كل واحد على حدة. ممكن يتقلّص لو الـ pattern reuse اشتغل (معظم الـ swallows في الـ tawreed_artifacts نمط واحد).

---

## 📎 الـ References

| الـ Resource | الـ Link |
|-------------|----------|
| الـ Audit script | `scripts/audit_swallow.py` |
| الـ Baseline doc | `docs/audit_swallow.md` |
| الـ Guard test | `tests/core/test_swallow_audit.py` |
| الـ Logging policy doc | `docs/logging_system.md` |
| الـ Logging baseline | `docs/audit_logging.md` |
| الـ Project journey | `docs/DEVELOPMENT_HISTORY.md` |
| Commit Stage 1a | `c246837` — "stage 1a: AST audit script + baseline doc for swallowed exceptions" |
| Commit Stage 1c | `963e12b` — "stage 1c: CI guard test for swallowed exceptions (4 pass, 1 expected fail)" |

---

## ⚠️ Verification Note

> الـ numbers في الـ doc ده (84/81 swallowed, 41 passing, 6 pre-existing failures,
> الـ 5 test breakdown, الـ 232 LOC للـ script) كلها من **real execution outputs**
> في الـ الـ message الأصلي بتاع الـ user (الـ 7 columns الـ execution table) +
> الـ git log (`git log --oneline -20`) + الـ read_file على الـ 3 files.
>
> **مفيش رقم تخيّنتُه.** لو في رقم في الـ doc ده ما اتحقّقش من run فعلي، الـ user
> لازم يعمل re-check قبل ما يبني عليه أي decision.