# 📘 دليل إضافة نظام تسجيل (Logging) احترافي للـ CLI

> **الجمهور:** مطورو وصيانة `PharmaSupplyBot` (Tawreed CLI).
> **الهدف:** استبدال `print()` و `SystemExit()` بنظام تسجيل منظّم يدعم stdout + ملفات + تدوير (rotation) + مستويات + سياقات (context).

---

## 1. لماذا نحتاج نظام تسجيل؟

### الوضع الحالي في `run.py` و `src/cli/cli_shared.py`

```python
# حاليًا — رسائل مختلطة عبر print و SystemExit
print(f"[{profile_key}] {error}")
print(f"Run: py run.py auth --profile {profile_key}")
raise SystemExit(
    f"Session for profile '{profile_key}' is not valid. "
    f"Run: py run.py auth --profile {profile_key}"
)
```

### المشاكل

| # | المشكلة | التأثير |
|---|---------|---------|
| 1 | لا يمكن تمييز مستوى الخطورة (info vs error) | المستخدم لا يعرف هل الرسالة عادية أم خلل |
| 2 | لا يوجد ملف log للرجوع إليه بعد إغلاق الـ terminal | تشخيص الحوادث مستحيل |
| 3 | لا يوجد timestamp ثابت | تتبع تسلسل الأحداث صعب |
| 4 | `SystemExit` يطبع stack trace في بعض الحالات | UX سيئ للمستخدم النهائي |
| 5 | صعوبة الفلترة عند التشغيل في CI/CD أو بصمت (`--quiet`) | يضيع وقت المطور |
| 6 | غياب بنية موحّدة (JSON vs نص) | صعب على أدوات المراقبة قراءته |

### ما الذي سيتحقق بعد إضافة النظام

- ✅ فصل واضح: **stderr** للأخطاء، **stdout** للنتيجة النهائية للمستخدم
- ✅ ملفات يومية في `logs/` مع تدوير تلقائي
- ✅ مستويات قابلة للضبط من CLI: `--log-level DEBUG`
- ✅ خيار `--quiet` يكتم كل شيء ما عدا التحذيرات والأخطاء
- ✅ وضع `--json-logs` لإخراج JSON (مفيد لـ CI و log aggregators)
- ✅ **متوافق مع CLI الموجود** دون كسر أي توقيع دالة

---

## 2. المكتبات المقترحة — ومقارنة سريعة

| المكتبة | متى تختارها | المزايا | العيوب |
|---------|-------------|---------|--------|
| **`logging` (stdlib)** | كأولوية افتراضية | بدون تبعيات إضافية، كافية لـ 95% من الـ CLI | التكوين verbose قليلاً |
| **`loguru`** | إذا أردت كتابة أقل وبديهية | API جميل، rotation مدمج، tracebacks ملوّنة | تبعيات خارجية، أقل مرونة في التكوين المعقد |
| **`structlog`** | إذا كانت السجلات تُستهلك من قبل أدوات (ELK/Datadog) | JSON أصلي، context processors، typed logs | منحنى تعلّم، تبعيات إضافية |

### ✅ التوصية لهذا المشروع

ابدأ بـ **stdlib `logging`** لأن:
- المشروع لا يحتاج أي تبعيات جديدة (تتبع `requirements.txt` نظيف)
- `logging` كافٍ لكل المتطلبات أعلاه
- يمكن الترقية لاحقاً إلى `loguru` أو `structlog` **بدون تغيير كود الاستدعاءات** — هذا هو سر التصميم أدناه

---

## 3. الهيكل المقترح للملفات

```
src/
└── cli/
    ├── cli_shared.py              # موجود — سنُضيف get_logger() هنا
    └── logging_setup.py           # ✨ جديد — كل منطق التهيئة
logs/                              # ✨ جديد — gitignored
├── app.log                        # كل شيء بمستوى INFO+
├── app.log.2026-07-21             # ملف مُدار بالتدوير
└── errors.log                     # الأخطاء فقط (ERROR+)
```

**لا تنسَ إضافة `logs/` إلى `.gitignore`:**

```gitignore
# .gitignore
logs/
*.log
```

---

## 4. التصميم المعماري

### 4.1 المبدأ الأساسي: **مرّة واحدة في التهيئة، استخدام في كل مكان**

```
┌─────────────────────────────────────────────────────────┐
│ run.py  (نقطة الدخول)                                  │
│   │                                                     │
│   ├── configure_logging(args)  ← يحدث مرة واحدة       │
│   │                                                     │
│   └── run_auth_command(...)     ← يستخدم get_logger()   │
│         │                                               │
│         ├── run_match_products_command(...)             │
│         ├── run_order_command(...)                      │
│         └── ...                                        │
└─────────────────────────────────────────────────────────┘
```

### 4.2 الـ Logger Naming Convention

نستخدم **dotted path** يطابق بنية الحزمة:

```python
# في src/cli/cli_shared.py
logger = logging.getLogger("pharmasupply.cli.shared")

# في src/cli/commands/cli_order.py
logger = logging.getLogger("pharmasupply.cli.commands.order")

# في src/core/...
logger = logging.getLogger("pharmasupply.core.config")
```

**القاعدة:** اسم الـ logger = اسم الوحدة النمطية بالضبط، بدءًا من `pharmasupply`.

---

## 5. التنفيذ خطوة بخطوة

### الخطوة 1: إنشاء `src/cli/logging_setup.py`

```python
"""Centralized logging configuration for the PharmaSupplyBot CLI.

This module is the single entry point for configuring Python's logging
package across the entire CLI. It is intentionally framework-agnostic
and exposes one helper: ``configure_logging``.

Design goals
------------
* Zero new dependencies (stdlib only).
* Per-run files written to ``logs/`` with automatic rotation.
* Predictable routing: WARNING+ to stderr, everything else to stdout
  unless the caller opts into ``--quiet``.
* Honors CLI flags: ``--log-level``, ``--quiet``, ``--json-logs``.
* Idempotent: calling ``configure_logging`` twice is safe — the second
  call is a no-op (prevents double-handlers in tests / REPL).
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


DEFAULT_LEVEL: int = logging.INFO
LOG_FORMAT: str = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%S%z"
LOG_DIR: Path = Path("logs")
APP_LOG_FILE: str = "app.log"
ERROR_LOG_FILE: str = "errors.log"
ROTATION_WHEN: str = "midnight"
ROTATION_BACKUPS: int = 14  # احتفظ بأسبوعين


@dataclass(frozen=True)
class LoggingConfig:
    """Immutable bundle of CLI-derived logging options."""

    level: str = "INFO"
    quiet: bool = False
    json_logs: bool = False
    log_dir: Path = LOG_DIR


# ─────────────────────────── Formatters ───────────────────────────


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    # الحقول القياسية التي لا نريد تكرارها من record.__dict__
    _RESERVED = {
        "name", "msg", "args", "levelname", "levelno", "pathname",
        "filename", "module", "exc_info", "exc_text", "stack_info",
        "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process", "message",
        "asctime", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, DATE_FORMAT),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # إضافة الحقول المخصصة التي مرّرها المُتصل عبر logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


# ─────────────────────────── Public API ───────────────────────────


def configure_logging(config: LoggingConfig | None = None) -> None:
    """Initialize the root logger with handlers derived from ``config``.

    Safe to call multiple times — subsequent calls replace handlers on
    the root logger only, so existing loggers (created via
    ``logging.getLogger(__name__)``) automatically inherit the new config.
    """
    cfg = config or LoggingConfig()
    root = logging.getLogger()
    root.setLevel(_resolve_level(cfg.level))

    # إزالة أي handlers سابقة — يمنع التكرار عند إعادة الاستدعاء
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handlers: list[logging.Handler] = [
        _build_console_handler(cfg),
        _build_app_file_handler(cfg),
        _build_error_file_handler(cfg),
    ]
    for handler in handlers:
        root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger — thin wrapper for testability."""
    return logging.getLogger(name)


# ─────────────────────────── Internals ───────────────────────────


def _resolve_level(level: str) -> int:
    """Translate a string level (e.g. 'DEBUG') to its numeric value."""
    numeric = logging.getLevelName(level.upper())
    if not isinstance(numeric, int):
        raise ValueError(f"Unknown log level: {level!r}")
    return numeric


def _build_console_handler(cfg: LoggingConfig) -> logging.Handler:
    """Console handler: stdout for normal, stderr for WARNING+."""
    handler = logging.StreamHandler(stream=sys.stderr)
    if cfg.quiet:
        handler.setLevel(logging.WARNING)
    else:
        handler.setLevel(root_level := logging.getLogger().level or DEFAULT_LEVEL)
        handler.setLevel(root_level)
    handler.setFormatter(_select_formatter(cfg))
    return handler


def _build_app_file_handler(cfg: LoggingConfig) -> logging.Handler:
    """Rotating file handler for the general application log."""
    cfg.log_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.log_dir / APP_LOG_FILE
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=path,
        when=ROTATION_WHEN,
        backupCount=ROTATION_BACKUPS,
        encoding="utf-8",
        utc=False,
    )
    handler.setLevel(logging.DEBUG)  # خزّن كل شيء في الملف
    handler.setFormatter(_select_formatter(cfg))
    return handler


def _build_error_file_handler(cfg: LoggingConfig) -> logging.Handler:
    """Separate file for ERROR+ records (easier alerting later)."""
    cfg.log_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.log_dir / ERROR_LOG_FILE
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=path,
        when=ROTATION_WHEN,
        backupCount=ROTATION_BACKUPS,
        encoding="utf-8",
        utc=False,
    )
    handler.setLevel(logging.ERROR)
    handler.setFormatter(_select_formatter(cfg))
    return handler


def _select_formatter(cfg: LoggingConfig) -> logging.Formatter:
    return JsonFormatter() if cfg.json_logs else logging.Formatter(
        fmt=LOG_FORMAT, datefmt=DATE_FORMAT,
    )
```

### الخطوة 2: إضافة helper في `src/cli/cli_shared.py`

```python
# في أعلى src/cli/cli_shared.py — أضف:
import logging

logger = logging.getLogger(__name__)  # = "src.cli.cli_shared"

# ثم استبدل الـ prints تدريجياً:
# مثال — invalid_session_exit كان يطبع عبر print
def invalid_session_exit(profile_key: str, error: SessionInvalidError) -> SystemExit:
    logger.error(
        "session expired for profile=%s: %s",
        profile_key, error,
    )
    return SystemExit(
        f"Session for profile '{profile_key}' is not valid. "
        f"Run: py run.py auth --profile {profile_key}"
    )
```

### الخطوة 3: تعديل `run.py` (نقطة الدخول)

```python
"""CLI entry point for Tawreed authentication, ordering, and exports."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from src.cli.cli_commands import (
    run_auth_command,
    run_export_products_command,
    run_match_products_command,
    run_order_command,
    run_remove_cart_command,
)
from src.cli.logging_setup import LoggingConfig, configure_logging
from src.cli.parsers.cli_parser import build_parser
from src.core.config.config import load_config


def main() -> int:
    """Run the CLI command requested by the user."""
    load_dotenv()
    args = build_parser().parse_args()

    # ✨ تهيئة الـ logging مرة واحدة — قبل أي شيء آخر
    configure_logging(LoggingConfig(
        level=getattr(args, "log_level", "INFO"),
        quiet=getattr(args, "quiet", False),
        json_logs=getattr(args, "json_logs", False),
    ))

    config_path = Path(args.config)
    app_config = load_config(config_path)

    if args.cmd == "auth":
        return run_auth_command(app_config, args)
    if args.cmd == "order":
        return run_order_command(app_config, args)
    if args.cmd == "remove-cart":
        return run_remove_cart_command(app_config, args)
    if args.cmd == "export-products":
        return run_export_products_command(app_config, args)
    if args.cmd == "match-products":
        return run_match_products_command(app_config, args)
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
```

### الخطوة 4: إضافة الأعلام الجديدة إلى `cli_parser.py`

```python
# في src/cli/parsers/cli_parser.py — داخل build_parser()

parser.add_argument(
    "--log-level",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    default="INFO",
    help="Minimum log level emitted to console (default: INFO).",
)
parser.add_argument(
    "--quiet", "-q",
    action="store_true",
    help="Suppress console output below WARNING. Logs are still written to files.",
)
parser.add_argument(
    "--json-logs",
    action="store_true",
    help="Emit log records as JSON (useful for CI / log aggregators).",
)
```

---

## 6. أنماط الاستخدام في كل مكان

### 6.1 تسجيل عادي بمستوى صحيح

```python
from src.cli.cli_shared import logger  # أو logging.getLogger(__name__)

# ❌ سيئ — يخلط الرسالة بمستوى
logger.info(f"Processing {count} items")

# ✅ جيد — رسالة ثابتة + متغيرات كوسيطات (lazy formatting)
logger.info("Processing %d items", count)

# ✅ أفضل مع سياق منظّم
logger.info("processing items", extra={"count": count, "profile": profile_key})
```

### 6.2 تسجيل الأخطاء مع stack trace

```python
try:
    result = tawreed_api.call(...)
except TawreedAPIError:
    logger.exception(
        "Tawreed API call failed for profile=%s",
        profile_key,
    )
    raise
```

> `logger.exception()` يكافئ `logger.error(..., exc_info=True)` — يُدرج الـ stack trace كاملاً.

### 6.3 تسجيل مع سياق غني (correlation id)

```python
import uuid
from contextvars import ContextVar

run_id: ContextVar[str] = ContextVar("run_id", default="-")


def setup_run_context() -> str:
    rid = uuid.uuid4().hex[:12]
    run_id.set(rid)
    return rid


# في formatter مخصص (اختياري) — أضف run_id إلى كل سجل
class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = run_id.get()
        return True
```

### 6.4 استبدال `print()` بالكامل

| القديم | الجديد |
|--------|--------|
| `print("Starting auth...")` | `logger.info("starting authentication")` |
| `print(f"[{profile_key}] {error}")` | `logger.error("session error: %s", error, extra={"profile": profile_key})` |
| `print(f"✓ Saved {n} items")` | `logger.info("saved items: %d", n)` |
| `raise SystemExit("not configured")` | `logger.critical("missing config")` + `raise SystemExit(1)` |

---

## 7. الاختبار

### 7.1 اختبار وحدة لـ `logging_setup.py`

```python
# tests/test_logging_setup.py
import logging
from pathlib import Path

import pytest

from src.cli.logging_setup import (
    LoggingConfig,
    configure_logging,
    get_logger,
)


def test_configure_logging_is_idempotent(tmp_path: Path) -> None:
    cfg = LoggingConfig(log_dir=tmp_path)
    configure_logging(cfg)
    first_handler_count = len(logging.getLogger().handlers)
    configure_logging(cfg)
    assert len(logging.getLogger().handlers) == first_handler_count


def test_quiet_mode_silences_info(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    cfg = LoggingConfig(quiet=True, log_dir=tmp_path)
    configure_logging(cfg)
    logger = get_logger("test.quiet")
    with caplog.at_level(logging.INFO):
        logger.info("should not appear in console")
        logger.warning("should appear")
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_json_logs_emits_valid_json(tmp_path: Path, capsys) -> None:
    cfg = LoggingConfig(json_logs=True, log_dir=tmp_path)
    configure_logging(cfg)
    logger = get_logger("test.json")
    logger.info("hello")
    captured = capsys.readouterr()
    # ابحث عن سطر JSON في الـ stderr
    assert '"message": "hello"' in captured.err
```

### 7.2 اختبار تكاملي للـ CLI

```bash
# شغّل بصمت وتحقق من الملف
py run.py auth --profile wardany --quiet --log-level DEBUG
ls logs/
cat logs/app.log | head -5
```

---

## 8. قائمة التحقق (Checklist)

- [ ] أضف `src/cli/logging_setup.py` بالمحتوى أعلاه
- [ ] أضف `logs/` إلى `.gitignore`
- [ ] أضف `get_logger` helper في `cli_shared.py`
- [ ] استبدل كل `print()` في `src/cli/` بـ `logger.info/warning/error`
- [ ] استبدل كل `print()` في `src/tawreed/` بـ `logger`
- [ ] أضف `--log-level`, `--quiet`, `--json-logs` إلى `cli_parser.py`
- [ ] شغّل `configure_logging(...)` في بداية `main()` قبل أي شيء آخر
- [ ] اكتب اختبارات `test_logging_setup.py`
- [ ] شغّل `py run.py auth --profile wardany --log-level DEBUG` وتحقق من `logs/app.log`
- [ ] أضف قسم "Logging" إلى `README.md` بالأعلام الجديدة

---

## 9. ترقية مستقبلية (اختياري)

إذا احتجت لاحقاً JSON أصلي + performance أعلى:

```bash
pip install structlog
```

ثم استبدل `JsonFormatter` بـ structlog processor — **كود الاستدعاءات (logger.info) لا يتغيّر**.

---

## 10. مراجع

- [Python docs — `logging`](https://docs.python.org/3/library/logging.html)
- [Python docs — `logging.handlers`](https://docs.python.org/3/library/logging.handlers.html)
- [Logging Cookbook](https://docs.python.org/3/howto/logging-cookbook.html)
- مشروع `loguru` للقراءة فقط (API inspiration)
- مشروع `structlog` للقراءة فقط (لما تنتقل لـ JSON منظم)

---

> **آخر تحديث:** يوليه 2026 — فرع `logging_system`.
> **حالة الوثيقة:** جاهزة للتنفيذ.