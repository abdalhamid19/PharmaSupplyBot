# 4 — الأدلة

## 4.1 كتالوج Tawreed (`data/input/tawreed_products.csv`)

| name_en | name_ar | notes |
|---------|---------|-------|
| `AVAZIR 0.3 % EYE OINT. 5 GM` | افازير 0.3 % مرهم للعين 5 جم | المنتج الخاطئ المختار |
| `CO AVAZIR EYE OINT. 5 GM` | كو افازير مرهم للعين 5 جم | التصحيح الصحيح |
| `AVAZIR 0.3 % EYE DROPS 10 ML` | ... | مرفوض بـ different_form |
| `CO AVAZIR EYE SUSP. DROPS 10 ML` | ... | شكل مختلف |

## 4.2 Artifact حي — run `20260713_1038` (match-only)

ملف: `artifacts/order/wardany/20260713_1038/logs/match/match_log_80838_20260713_1038.txt`

| # | product | score | accepted | reason |
|---|---------|-------|----------|--------|
| 1 | CO AVAZIR EYE OINT. 5 GM | **16.800** | False | missing storeProductId |
| 2 | AVAZIR 0.3 % EYE OINT. 5 GM | **15.363** | **True** | safe omission |
| 3 | CO AVAZIR EYE SUSP. DROPS 10 ML | 6.807 | False | unrequested numeric |
| 4 | AVAZIR 0.3 % EYE DROPS 10 ML | 5.164 | False | different_form |

`final_reason`:
`Accepted best candidate because Extra numeric tokens represent safe omission.`

## 4.3 Runs أخرى تؤكد التكرار

| run | status | matched product |
|-----|--------|-----------------|
| 20260712_1107 | added-to-cart | AVAZIR 0.3 % EYE OINT. 5 GM |
| 20260712_1246 | matched-only | AVAZIR 0.3 % EYE OINT. 5 GM |
| 20260713_1038 | matched-only | AVAZIR 0.3 % EYE OINT. 5 GM |
| 20260713_1054 | matched-only | AVAZIR 0.3 % EYE OINT. 5 GM |
| 20260713_1104 | matched-only | AVAZIR 0.3 % EYE OINT. 5 GM |
| 20260713_1126 | added-to-cart | AVAZIR 0.3 % EYE OINT. 5 GM |

## 4.4 إعادة إنتاج حية (قبل الإصلاح)

```text
parse_drug brands: COAVAZIR vs AVAZIR
fuzz.ratio("COAVAZIR","AVAZIR") = 85.714...
len_diff = 2
containment: AVAZIR ⊂ COAVAZIR
components_match → True, "ok"     # BUG
explain_best_product_match(wrong only) → accepted score 15.36
```

## 4.5 بعد الإصلاح

```text
components_match → False, "different_brand"
explain_best_product_match(wrong only) → best_match=None
explain_best_product_match(correct orderable) → CO AVAZIR EYE OINT. 5 GM
```

## 4.6 درجة التداخل (ليست السبب الوحيد)

| pair | overlap |
|------|---------|
| query vs wrong AVAZIR oint | ≈ 0.783 |
| query vs correct CO AVAZIR | ≈ 0.950 |

الصحيح أعلى تداخلاً؛ المشكلة acceptance/orderability + brand leak.
