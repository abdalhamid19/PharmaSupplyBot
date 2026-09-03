# نماذج OmniRoute في `opencode.json` — بعد التحديث

> مصدر الملف: `C:\Users\QUANTUM\.config\opencode\opencode.json:1-259`
> النسخ الاحتياطي: `C:\Users\QUANTUM\.config\opencode\opencode.json.bak_20260830`
> تاريخ التحديث: 2026-08-30
> إجمالي النماذج: **81 نموذج** (كان 31، تمت إضافة 54 وحذف 4)

## 1. الإعداد العام

| الحقل | القيمة | السطر |
| :--- | :--- | :--- |
| `$schema` | `https://opencode.ai/config.json` | `C:\Users\QUANTUM\.config\opencode\opencode.json:2` |
| `model` (الافتراضي) | `omniroute/coding-tier-1` | `C:\Users\QUANTUM\.config\opencode\opencode.json:3` |
| `provider.npm` | `@ai-sdk/openai-compatible` | `C:\Users\QUANTUM\.config\opencode\opencode.json:6` |
| `provider.name` | `OmniRoute` | `C:\Users\QUANTUM\.config\opencode\opencode.json:7` |
| `provider.options.baseURL` | `http://localhost:20128/v1` | `C:\Users\QUANTUM\.config\opencode\opencode.json:9` |

## 2. ملخص التغييرات

### محذوفة (4 نماذج) — غير مذكورة في القائمة الجديدة
| Model ID | السبب |
|---|---|
| `blackbox/blackboxai/moonshotai/kimi-k3` | مذكور صراحة للحذف |
| `bb/blackboxai/moonshotai/kimi-k3` | مذكور صراحة للحذف |
| `narorouter/grok-4.5-free` | غير موجود في القائمة الجديدة → حذف تلقائي |
| `opencode api/big-pickle` | غير موجود في القائمة الجديدة → حذف تلقائي |

### مضافة (54 نموذج جديد)

تمت إضافة كل النماذج التالية لأول مرة (لم تكن موجودة في الملف القديم).

## 3. قائمة جميع النماذج الحالية (81)

### 3.1 مجموعة `cl/*` + `trk/*` (17 نموذج) — جديدة كليا
| # | Model ID | السطر |
|---|---|---|
| 1 | `cl/~anthropic/claude-fable-latest` | `C:\Users\QUANTUM\.config\opencode\opencode.json:13` |
| 2 | `cl/openai/gpt-5.6-sol-pro` | `C:\Users\QUANTUM\.config\opencode\opencode.json:16` |
| 3 | `cl/~anthropic/claude-opus-latest` | `C:\Users\QUANTUM\.config\opencode\opencode.json:19` |
| 4 | `cl/anthropic/claude-opus-5-fast` | `C:\Users\QUANTUM\.config\opencode\opencode.json:22` |
| 5 | `cl/anthropic/claude-opus-5` | `C:\Users\QUANTUM\.config\opencode\opencode.json:25` |
| 6 | `cl/openai/gpt-5.6-sol` | `C:\Users\QUANTUM\.config\opencode\opencode.json:28` |
| 7 | `cl/openai/gpt-5.5` | `C:\Users\QUANTUM\.config\opencode\opencode.json:31` |
| 8 | `cl/openai/gpt-5.6-terra` | `C:\Users\QUANTUM\.config\opencode\opencode.json:34` |
| 9 | `cl/~moonshotai/kimi-latest` | `C:\Users\QUANTUM\.config\opencode\opencode.json:37` |
| 10 | `cl/moonshotai/kimi-k3` | `C:\Users\QUANTUM\.config\opencode\opencode.json:40` |
| 11 | `cl/~z-ai/glm-latest` | `C:\Users\QUANTUM\.config\opencode\opencode.json:43` |
| 12 | `cl/z-ai/glm-5.3-flash` | `C:\Users\QUANTUM\.config\opencode\opencode.json:46` |
| 13 | `cl/~x-ai/grok-latest` | `C:\Users\QUANTUM\.config\opencode\opencode.json:49` |
| 14 | `cl/x-ai/grok-4.6` | `C:\Users\QUANTUM\.config\opencode\opencode.json:52` |
| 15 | `cl/google/gemini-3.7-flash` | `C:\Users\QUANTUM\.config\opencode\opencode.json:55` |
| 16 | `cl/minimax/minimax-m3:free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:58` |
| 17 | `trk/z-ai/glm-5.3-free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:61` |

### 3.2 مجموعة `seekai.cc/*` (4) — جديدة
| # | Model ID | السطر |
|---|---|---|
| 18 | `seekai.cc/claude-fable-5` | `C:\Users\QUANTUM\.config\opencode\opencode.json:64` |
| 19 | `seekai.cc/claude-opus-5` | `C:\Users\QUANTUM\.config\opencode\opencode.json:67` |
| 20 | `seekai.cc/gpt-5.6-sol` | `C:\Users\QUANTUM\.config\opencode\opencode.json:70` |
| 21 | `seekai.cc/claude-opus-4-8` | `C:\Users\QUANTUM\.config\opencode\opencode.json:73` |

### 3.3 مجموعة `justwoker.icu/*` (4) — جديدة
| # | Model ID | السطر |
|---|---|---|
| 22 | `justwoker.icu/claude-opus-5-thinking` | `C:\Users\QUANTUM\.config\opencode\opencode.json:76` |
| 23 | `justwoker.icu/claude-opus-5` | `C:\Users\QUANTUM\.config\opencode\opencode.json:79` |
| 24 | `justwoker.icu/claude-opus-4-8-thinking` | `C:\Users\QUANTUM\.config\opencode\opencode.json:82` |
| 25 | `justwoker.icu/claude-opus-4-8` | `C:\Users\QUANTUM\.config\opencode\opencode.json:85` |

### 3.4 مجموعة `tabitoken.com/*` (4) — جديدة
| # | Model ID | السطر |
|---|---|---|
| 26 | `tabitoken.com/claude-opus-5-thinking` | `C:\Users\QUANTUM\.config\opencode\opencode.json:88` |
| 27 | `tabitoken.com/claude-opus-5` | `C:\Users\QUANTUM\.config\opencode\opencode.json:91` |
| 28 | `tabitoken.com/claude-opus-4-8-thinking` | `C:\Users\QUANTUM\.config\opencode\opencode.json:94` |
| 29 | `tabitoken.com/claude-opus-4-8` | `C:\Users\QUANTUM\.config\opencode\opencode.json:97` |

### 3.5 مجموعة `evolink/*` (5) — جديدة
| # | Model ID | السطر |
|---|---|---|
| 30 | `evolink/claude-fable-5` | `C:\Users\QUANTUM\.config\opencode\opencode.json:100` |
| 31 | `evolink/claude-opus-5` | `C:\Users\QUANTUM\.config\opencode\opencode.json:103` |
| 32 | `evolink/gpt-5.6-sol` | `C:\Users\QUANTUM\.config\opencode\opencode.json:106` |
| 33 | `evolink/kimi-k3` | `C:\Users\QUANTUM\.config\opencode\opencode.json:109` |
| 34 | `evolink/grok-4.6` | `C:\Users\QUANTUM\.config\opencode\opencode.json:112` |

### 3.6 مجموعة `orcarouter.ai/*` + `xkiro.com/*` (3) — جديدة
| # | Model ID | السطر |
|---|---|---|
| 35 | `orcarouter.ai/orcarouter/free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:115` |
| 36 | `orcarouter.ai/qwen/qwen3.8-27b-free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:118` |
| 37 | `xkiro.com/qwen/qwen3.8-max:free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:121` |

### 3.7 مجموعة `hf/*` (5) — جديدة
| # | Model ID | السطر |
|---|---|---|
| 38 | `hf/moonshotai/Kimi-K3` | `C:\Users\QUANTUM\.config\opencode\opencode.json:124` |
| 39 | `hf/zai-org/GLM-5.3-Flash` | `C:\Users\QUANTUM\.config\opencode\opencode.json:127` |
| 40 | `hf/zai-org/GLM-5.3-Flash-BF16` | `C:\Users\QUANTUM\.config\opencode\opencode.json:130` |
| 41 | `hf/zai-org/GLM-5.3` | `C:\Users\QUANTUM\.config\opencode\opencode.json:133` |
| 42 | `hf/deepseek-ai/DeepSeek-V4-Flash-0731` | `C:\Users\QUANTUM\.config\opencode\opencode.json:136` |

### 3.8 مجموعة `chat.b.ai/*` (2) — جديدة
| # | Model ID | السطر |
|---|---|---|
| 43 | `chat.b.ai/glm-5.3-flash` | `C:\Users\QUANTUM\.config\opencode\opencode.json:139` |
| 44 | `chat.b.ai/qwen3.8-flash` | `C:\Users\QUANTUM\.config\opencode\opencode.json:142` |

### 3.9 مجموعة `aerolink/*` (4) — جديدة
| # | Model ID | السطر |
|---|---|---|
| 45 | `aerolink/gpt-5.6-sol` | `C:\Users\QUANTUM\.config\opencode\opencode.json:145` |
| 46 | `aerolink/gpt-5.6-terra` | `C:\Users\QUANTUM\.config\opencode\opencode.json:148` |
| 47 | `aerolink/gpt-5.6-luna` | `C:\Users\QUANTUM\.config\opencode\opencode.json:151` |
| 48 | `aerolink/FreeModel` | `C:\Users\QUANTUM\.config\opencode\opencode.json:154` |

### 3.10 مجموعة `aihubmax/*` (6) — جديدة
| # | Model ID | السطر |
|---|---|---|
| 49 | `aihubmax/ox-alpha` | `C:\Users\QUANTUM\.config\opencode\opencode.json:157` |
| 50 | `aihubmax/coding-glm-5.3-free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:160` |
| 51 | `aihubmax/gpt-5.5-free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:163` |
| 52 | `aihubmax/coding-kimi-k3-free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:166` |
| 53 | `aihubmax/gemini-3.7-flash-free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:169` |
| 54 | `aihubmax/coding-minimax-m3-free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:172` |

### 3.11 نماذج OmniRoute الأساسية (11) — محفوظة كما هي
| # | Model ID | السطر |
|---|---|---|
| 55 | `auto` | `C:\Users\QUANTUM\.config\opencode\opencode.json:175` |
| 56 | `auto/coding` | `C:\Users\QUANTUM\.config\opencode\opencode.json:178` |
| 57 | `auto/fast` | `C:\Users\QUANTUM\.config\opencode\opencode.json:181` |
| 58 | `auto/cheap` | `C:\Users\QUANTUM\.config\opencode\opencode.json:184` |
| 59 | `coding-tier-1` | `C:\Users\QUANTUM\.config\opencode\opencode.json:187` |
| 60 | `coding-tier-2` | `C:\Users\QUANTUM\.config\opencode\opencode.json:190` |
| 61 | `coding-tier-3` | `C:\Users\QUANTUM\.config\opencode\opencode.json:193` |
| 62 | `coding-tier-4` | `C:\Users\QUANTUM\.config\opencode\opencode.json:196` |
| 63 | `auto/coding:fast` | `C:\Users\QUANTUM\.config\opencode\opencode.json:199` |
| 64 | `auto/coding:free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:202` |
| 65 | `auto/coding:pro` | `C:\Users\QUANTUM\.config\opencode\opencode.json:205` |

### 3.12 نماذج CometAPI (4) — محفوظة
| # | Model ID | السطر |
|---|---|---|
| 66 | `cometapi/gpt-5.6-sol` | `C:\Users\QUANTUM\.config\opencode\opencode.json:208` |
| 67 | `cometapi/glm-5.3` | `C:\Users\QUANTUM\.config\opencode\opencode.json:211` |
| 68 | `cometapi/grok-4.6` | `C:\Users\QUANTUM\.config\opencode\opencode.json:214` |
| 69 | `cometapi/gemini-3.7-flash-thinking` | `C:\Users\QUANTUM\.config\opencode\opencode.json:217` |

### 3.13 نماذج KC / GMICloud / OpenRouter (5) — محفوظة
| # | Model ID | السطر |
|---|---|---|
| 70 | `openrouter/minimax/minimax-m3:free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:220` |
| 71 | `gmicloud/MiniMaxAI/MiniMax-M3` | `C:\Users\QUANTUM\.config\opencode\opencode.json:223` |
| 72 | `kc/minimax/minimax-m3:free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:226` |
| 73 | `kc/tencent/hy3:free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:229` |
| 74 | `kc/stepfun/step-3.7-flash:free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:232` |

### 3.14 نماذج أخرى (7) — محفوظة (بعد حذف 2)
| # | Model ID | السطر |
|---|---|---|
| 75 | `gc/grok-4.6` | `C:\Users\QUANTUM\.config\opencode\opencode.json:235` |
| 76 | `narorouter/qwen-3.8-max-free` | `C:\Users\QUANTUM\.config\opencode\opencode.json:238` |
| 77 | `morph/morph-v3-large` | `C:\Users\QUANTUM\.config\opencode\opencode.json:241` |
| 78 | `morph/morph-minimax3-428b` | `C:\Users\QUANTUM\.config\opencode\opencode.json:244` |
| 79 | `morph/morph-v3-fast` | `C:\Users\QUANTUM\.config\opencode\opencode.json:247` |
| 80 | `kr/claude-sonnet-4.5` | `C:\Users\QUANTUM\.config\opencode\opencode.json:250` |
| 81 | `inception/mercury-2` | `C:\Users\QUANTUM\.config\opencode\opencode.json:253` |

## 4. التحقق

```powershell
# التحقق من صحة JSON
Get-Content "C:\Users\QUANTUM\.config\opencode\opencode.json" | ConvertFrom-Json | Select-Object -ExpandProperty provider | Select-Object -ExpandProperty omniroute | Select-Object -ExpandProperty models | Get-Member -MemberType NoteProperty | Measure-Object
# النتيجة المتوقعة: 81
```

```powershell
# التأكد من الحذف
Select-String -Path "C:\Users\QUANTUM\.config\opencode\opencode.json" -Pattern "blackbox"
# لا نتائج = تم الحذف بنجاح

Select-String -Path "C:\Users\QUANTUM\.config\opencode\opencode.json" -Pattern "big-pickle|grok-4.5-free"
# لا نتائج (big-pickle و grok-4.5-free تم حذفهما)
```

## 5. الملف الكامل بعد التحديث

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "omniroute/coding-tier-1",
  "provider": {
    "omniroute": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "OmniRoute",
      "options": {
        "baseURL": "http://localhost:20128/v1",
        "apiKey": "sk-fb0a235876e227e5-be2de4-5ca1d8a7"
      },
      "models": {
        "cl/~anthropic/claude-fable-latest": { "name": "cl/~anthropic/claude-fable-latest" },
        "cl/openai/gpt-5.6-sol-pro": { "name": "cl/openai/gpt-5.6-sol-pro" },
        "cl/~anthropic/claude-opus-latest": { "name": "cl/~anthropic/claude-opus-latest" },
        "cl/anthropic/claude-opus-5-fast": { "name": "cl/anthropic/claude-opus-5-fast" },
        "cl/anthropic/claude-opus-5": { "name": "cl/anthropic/claude-opus-5" },
        "cl/openai/gpt-5.6-sol": { "name": "cl/openai/gpt-5.6-sol" },
        "cl/openai/gpt-5.5": { "name": "cl/openai/gpt-5.5" },
        "cl/openai/gpt-5.6-terra": { "name": "cl/openai/gpt-5.6-terra" },
        "cl/~moonshotai/kimi-latest": { "name": "cl/~moonshotai/kimi-latest" },
        "cl/moonshotai/kimi-k3": { "name": "cl/moonshotai/kimi-k3" },
        "cl/~z-ai/glm-latest": { "name": "cl/~z-ai/glm-latest" },
        "cl/z-ai/glm-5.3-flash": { "name": "cl/z-ai/glm-5.3-flash" },
        "cl/~x-ai/grok-latest": { "name": "cl/~x-ai/grok-latest" },
        "cl/x-ai/grok-4.6": { "name": "cl/x-ai/grok-4.6" },
        "cl/google/gemini-3.7-flash": { "name": "cl/google/gemini-3.7-flash" },
        "cl/minimax/minimax-m3:free": { "name": "cl/minimax/minimax-m3:free" },
        "trk/z-ai/glm-5.3-free": { "name": "trk/z-ai/glm-5.3-free" },
        "seekai.cc/claude-fable-5": { "name": "seekai.cc/claude-fable-5" },
        "seekai.cc/claude-opus-5": { "name": "seekai.cc/claude-opus-5" },
        "seekai.cc/gpt-5.6-sol": { "name": "seekai.cc/gpt-5.6-sol" },
        "seekai.cc/claude-opus-4-8": { "name": "seekai.cc/claude-opus-4-8" },
        "justwoker.icu/claude-opus-5-thinking": { "name": "justwoker.icu/claude-opus-5-thinking" },
        "justwoker.icu/claude-opus-5": { "name": "justwoker.icu/claude-opus-5" },
        "justwoker.icu/claude-opus-4-8-thinking": { "name": "justwoker.icu/claude-opus-4-8-thinking" },
        "justwoker.icu/claude-opus-4-8": { "name": "justwoker.icu/claude-opus-4-8" },
        "tabitoken.com/claude-opus-5-thinking": { "name": "tabitoken.com/claude-opus-5-thinking" },
        "tabitoken.com/claude-opus-5": { "name": "tabitoken.com/claude-opus-5" },
        "tabitoken.com/claude-opus-4-8-thinking": { "name": "tabitoken.com/claude-opus-4-8-thinking" },
        "tabitoken.com/claude-opus-4-8": { "name": "tabitoken.com/claude-opus-4-8" },
        "evolink/claude-fable-5": { "name": "evolink/claude-fable-5" },
        "evolink/claude-opus-5": { "name": "evolink/claude-opus-5" },
        "evolink/gpt-5.6-sol": { "name": "evolink/gpt-5.6-sol" },
        "evolink/kimi-k3": { "name": "evolink/kimi-k3" },
        "evolink/grok-4.6": { "name": "evolink/grok-4.6" },
        "orcarouter.ai/orcarouter/free": { "name": "orcarouter.ai/orcarouter/free" },
        "orcarouter.ai/qwen/qwen3.8-27b-free": { "name": "orcarouter.ai/qwen/qwen3.8-27b-free" },
        "xkiro.com/qwen/qwen3.8-max:free": { "name": "xkiro.com/qwen/qwen3.8-max:free" },
        "hf/moonshotai/Kimi-K3": { "name": "hf/moonshotai/Kimi-K3" },
        "hf/zai-org/GLM-5.3-Flash": { "name": "hf/zai-org/GLM-5.3-Flash" },
        "hf/zai-org/GLM-5.3-Flash-BF16": { "name": "hf/zai-org/GLM-5.3-Flash-BF16" },
        "hf/zai-org/GLM-5.3": { "name": "hf/zai-org/GLM-5.3" },
        "hf/deepseek-ai/DeepSeek-V4-Flash-0731": { "name": "hf/deepseek-ai/DeepSeek-V4-Flash-0731" },
        "chat.b.ai/glm-5.3-flash": { "name": "chat.b.ai/glm-5.3-flash" },
        "chat.b.ai/qwen3.8-flash": { "name": "chat.b.ai/qwen3.8-flash" },
        "aerolink/gpt-5.6-sol": { "name": "aerolink/gpt-5.6-sol" },
        "aerolink/gpt-5.6-terra": { "name": "aerolink/gpt-5.6-terra" },
        "aerolink/gpt-5.6-luna": { "name": "aerolink/gpt-5.6-luna" },
        "aerolink/FreeModel": { "name": "aerolink/FreeModel" },
        "aihubmax/ox-alpha": { "name": "aihubmax/ox-alpha" },
        "aihubmax/coding-glm-5.3-free": { "name": "aihubmax/coding-glm-5.3-free" },
        "aihubmax/gpt-5.5-free": { "name": "aihubmax/gpt-5.5-free" },
        "aihubmax/coding-kimi-k3-free": { "name": "aihubmax/coding-kimi-k3-free" },
        "aihubmax/gemini-3.7-flash-free": { "name": "aihubmax/gemini-3.7-flash-free" },
        "aihubmax/coding-minimax-m3-free": { "name": "aihubmax/coding-minimax-m3-free" },
        "auto": { "name": "auto" },
        "auto/coding": { "name": "auto/coding" },
        "auto/fast": { "name": "auto/fast" },
        "auto/cheap": { "name": "auto/cheap" },
        "coding-tier-1": { "name": "coding-tier-1" },
        "coding-tier-2": { "name": "coding-tier-2" },
        "coding-tier-3": { "name": "coding-tier-3" },
        "coding-tier-4": { "name": "coding-tier-4" },
        "auto/coding:fast": { "name": "auto/coding:fast" },
        "auto/coding:free": { "name": "auto/coding:free" },
        "auto/coding:pro": { "name": "auto/coding:pro" },
        "cometapi/gpt-5.6-sol": { "name": "cometapi/gpt-5.6-sol" },
        "cometapi/glm-5.3": { "name": "cometapi/glm-5.3" },
        "cometapi/grok-4.6": { "name": "cometapi/grok-4.6" },
        "cometapi/gemini-3.7-flash-thinking": { "name": "cometapi/gemini-3.7-flash-thinking" },
        "openrouter/minimax/minimax-m3:free": { "name": "openrouter/minimax/minimax-m3:free" },
        "gmicloud/MiniMaxAI/MiniMax-M3": { "name": "gmicloud/MiniMaxAI/MiniMax-M3" },
        "kc/minimax/minimax-m3:free": { "name": "kc/minimax/minimax-m3:free" },
        "kc/tencent/hy3:free": { "name": "kc/tencent/hy3:free" },
        "kc/stepfun/step-3.7-flash:free": { "name": "kc/stepfun/step-3.7-flash:free" },
        "gc/grok-4.6": { "name": "gc/grok-4.6" },
        "narorouter/qwen-3.8-max-free": { "name": "narorouter/qwen-3.8-max-free" },
        "morph/morph-v3-large": { "name": "morph/morph-v3-large" },
        "morph/morph-minimax3-428b": { "name": "morph/morph-minimax3-428b" },
        "morph/morph-v3-fast": { "name": "morph/morph-v3-fast" },
        "kr/claude-sonnet-4.5": { "name": "kr/claude-sonnet-4.5" },
        "inception/mercury-2": { "name": "inception/mercury-2" }
      }
    }
  }
}
```
