# Full Run And Program Audit - 20260514_1252

## Scope

- Run analyzed: `artifacts/order/wardany/20260514_1252`.
- Primary files: `order_item_summary_20260514_1252.csv`, `manual_review_20260514_1252.csv`, `matching_trace_20260514_1252.csv`, `order_ai_trace_20260514_1252.csv`.
- قواعد المراجعة: تم الالتزام بـ `docs/project_guidelines.md`: فصل مشاكل business logic عن Playwright/UI، والتركيز على الأداء والرام والتوسع وعدم كسر الوظائف.
- ملاحظة مهمة: جداول false positive/false negative أدناه مبنية على trace وsummary، وليست اعتمادًا صيدليًا نهائيًا. أي صف بعلامة HIGH/MEDIUM يحتاج مراجعة بشرية قبل الطلب الفعلي، لكن وجوده هنا يعني أن البرنامج أضاع أو قبل مرشحًا يحتاج إصلاحًا أو تحققًا.

## Executive Summary

- إجمالي الأصناف في `order_item_summary`: 300.
- status `no-results`: 151.
- status `matched-only`: 136.
- status `skipped`: 13.
- matched=True: 136; matched=False: 164.
- manual_review rows: 173؛ منها [('no-results', 151), ('skipped', 13), ('matched-only', 9)].
- matching trace rows: 116916; matching candidates: 116616; order_ai rows: 300.
- accepted candidate trace rows: 437؛ rejected/false rows: 116444.
- false-negative suspects from `no-results`: 151 من أصل 151.
- false-positive / unsafe matched suspects: 27 من أصل 136.
- AI API attempts: 411؛ rate limits 429: 112; invalid_json: 15.

## Run-Level Failure Patterns

| Pattern | Evidence | Impact |
|---|---:|---|
| `English name missing requested identity token` | 48685 | identity token / spelling / search ranking |
| `Arabic name missing marker for ML` | 5905 | Arabic marker gate too strict |
| `English name missing requested identity token; Arabic name missing marker for ML` | 4280 | identity token / spelling / search ranking |
| `Candidate missing orderable storeProductId` | 3344 | missing_storeProductId / DOM/API enrichment |
| `Component mismatch: different_brand` | 3294 | component/brand classifier over-rejects |
| `Candidate has unrequested distinguishing token: PLUS` | 1906 | unknown/no detailed rejection |
| `Semantic token conflict: TABLET vs CAPSULE` | 1470 | form equivalence / semantic conflict |
| `Candidate has unrequested numeric token: 1` | 1117 | numeric gate too strict / unit-pack parsing |
| `Synthetic English name missing requested identity token; English name missing requested identity token` | 916 | identity token / spelling / search ranking |
| `Semantic token conflict: CAPSULE vs TABLET` | 714 | form equivalence / semantic conflict |
| `Candidate has unrequested numeric token: 2` | 573 | numeric gate too strict / unit-pack parsing |
| `Candidate has unrequested numeric token: 5` | 557 | numeric gate too strict / unit-pack parsing |
| `Candidate has unrequested numeric token: 10` | 515 | numeric gate too strict / unit-pack parsing |
| `Candidate has unrequested numeric token: 20` | 514 | numeric gate too strict / unit-pack parsing |
| `Semantic token conflict: VIAL vs TABLET` | 506 | form equivalence / semantic conflict |

## False Negative Matching Suspects

كل صف `status=no-results` مذكور هنا. `Best related candidate` هو أقرب مرشح مرتبط بالهوية من `matching_trace` وليس بالضرورة أعلى score مطلقًا، لأن أعلى score أحيانًا يكون دواء مختلفًا بسبب أرقام أو كلمات عامة.

| # | Grade | Code | Requested item | Best related candidate | Store/Product id | Score | Identity | Rejection reason | Root issue |
|---:|---|---|---|---|---|---:|---|---|---|
| 1 | HIGH | `47273` | DEVAROL-S-200.000 I.U 1 AMP | DEVAROL S 200000 I.U / 2 ML SOLUTION FOR I.M INJ. 1 AMP. | `2313003` | 13.024 | 100 `DEVAROL~DEVAROL` ov=1.00 | Candidate has unrequested numeric token: 2, 200000 | numeric gate too strict / unit-pack parsing |
| 2 | HIGH | `80131` | DOLIPRANE 1000 MG 15 TABS | DOLIPRANE NOVALDOL 1 GM 20 TABS | `2625068` | 11.476 | 100 `DOLIPRANE~DOLIPRANE` ov=1.00 | Rejected: overlap=0.680, score=11.476, numeric_match=False, exact_name=False | threshold/scoring rejected likely candidate |
| 3 | MEDIUM | `91733` | CHEMICETRIZINE 5 MG20 TAB | 1 2 3 ONE TWO THREE 20 F.C. TAB | `2437679` | 9.284 | 80 `CHEMICETRIZINE~ONE` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 4 | MEDIUM | `lev` | LEVIASILLS SOOTHING EFFECTIVE RELIEF | LEVA F 30 TABLET | `` | 2.454 | 86 `LEVIASILLS~LEVA` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 5 | HIGH | `57680` | POTASSIUM CHLORIDE 5 ML | POTASSIUM CHLORIDE I.V. 5 ML 5 AMP | `` | 14.607 | 100 `POTASSIUM~POTASSIUM` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 6 | HIGH | `74821` | BETADINE ANTISEPTIC 60 ML SOLN. 10% | BETADINE ANTISEPTIC SOLN. 10 % 60 ML | `` | 14.591 | 100 `BETADINE~BETADINE` ov=0.50 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 7 | HIGH | `28406` | BEBELAC AR MILK | BEBELAC AR MILK 400 GM | `` | 12.554 | 100 `BEBELAC~BEBELAC` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 8 | HIGH | `26979` | IVERZINE LOTION 6O ML | IVERZINE 1 % LOTION 60 ML | `2319808` | 17.773 | 100 `IVERZINE~IVERZINE` ov=1.00 | Candidate has unrequested numeric token: 1 | numeric gate too strict / unit-pack parsing |
| 9 | HIGH | `73328` | BETADINE VAG DOUCHE 120 ML | BETADINE VAGINAL DOUCHE 10 % 120 ML | `1489586` | 16.927 | 100 `BETADINE~BETADINE` ov=1.00 | Candidate has unrequested numeric token: 10 | numeric gate too strict / unit-pack parsing |
| 10 | HIGH | `83061` | CLOSOL 50 ML SPRAY | CLOSOL 10 MG / ML TOPICAL SPRAY 50 ML | `1958955` | 16.208 | 100 `CLOSOL~CLOSOL` ov=1.00 | Candidate has unrequested numeric token: 10 | numeric gate too strict / unit-pack parsing |
| 11 | HIGH | `73173` | CONCOR 5 PLUS 30TAB | CONCOR PLUS 5 / 12.5 MG 30 F.C. TABLETS | `2313532` | 15.734 | 100 `CONCOR~CONCOR` ov=1.00 | Candidate has unrequested numeric token: 12 | numeric gate too strict / unit-pack parsing |
| 12 | HIGH | `74881` | OCTOZINC CAP | OCTOZINC 25 MG 20 CAPS. | `1313189` | 11.329 | 100 `OCTOZINC~OCTOZINC` ov=1.00 | Candidate has unrequested numeric token: 20, 25 | numeric gate too strict / unit-pack parsing |
| 13 | HIGH | `89527` | LIMITLESS B-COMPLEX ODF 30 FILMS | LIMITLESS DIOSMIN COMPLEX 30 FILM COATED TABLETS | `2304401` | 16.242 | 100 `LIMITLESS~LIMITLESS` ov=0.67 | Component mismatch: different_brand | component/brand classifier over-rejects |
| 14 | HIGH | `16763` | AMRIZOLE N SUPP | AMRIZOLE N 5 VAG. SUPP. | `` | 10.667 | 100 `AMRIZOLE~AMRIZOLE` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 15 | HIGH | `adw` | ADWIFLAM 6 AMP | ADWIFLAM 75 MG / 3 ML 6 AMP. | `1425236` | 16.590 | 100 `ADWIFLAM~ADWIFLAM` ov=1.00 | Candidate has unrequested numeric token: 3, 75 | numeric gate too strict / unit-pack parsing |
| 16 | HIGH | `83725` | BEBELAC BEBEJUNIOR 3 MILK 400 GM | BEBELAC 3 (BEBEJUNIOR 1 +) MILK 400 GM | `` | 15.197 | 100 `BEBELAC~BEBELAC` ov=1.00 | Candidate has unrequested numeric token: 1 | numeric gate too strict / unit-pack parsing |
| 17 | HIGH | `73387` | IVYPRONT COUGH 100 ML SYRUP | IVYPRONT 0.84 GM SYRUP 120 ML | `2315006` | 10.134 | 100 `IVYPRONT~IVYPRONT` ov=0.50 | Rejected: overlap=0.740, score=10.134, numeric_match=False, exact_name=False | threshold/scoring rejected likely candidate |
| 18 | HIGH | `79887` | TELFAST DECONGESTANT 60/120MG 10 TABS. | TELFAST DECONGESTANT 60 / 120 MG 10 EXT. REL. TABS | `` | 15.024 | 100 `TELFAST~TELFAST` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 19 | LOW | `54472` | DIVIDO 75 MG 30 TAB | IRBEFUTAL CO 300 / 12.5 MG 30 TAB. | `1945204` | 11.720 | 67 `DIVIDO~CO` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 20 | HIGH | `89588` | REXODIN 10% ANTISEPTIC SOLUTION 60 ML | REXODIN ANTISEPTIC SOLUTION 60 ML | `2476150` | 16.449 | 100 `REXODIN~REXODIN` ov=0.50 | Component mismatch: different_brand | component/brand classifier over-rejects |
| 21 | HIGH | `73214` | GAST-REG SYRUP 125 ML | GAST REG 24 MG / 5 ML 125 ML SUSP. | `` | 9.977 | 100 `GAST~GAST` ov=1.00 | Rejected: overlap=0.800, score=9.977, numeric_match=True, exact_name=False | threshold/scoring rejected likely candidate |
| 22 | LOW | `71903` | NACTALIA 2 MILK 400 G | S 26 GOLD AR MILK 400 GM | `2635006` | 11.329 | 67 `NACTALIA~AR` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 23 | HIGH | `61862` | AMLODIPINE 5MG 30 TAB | AMLODIPINE 5 MG 30 TAB. | `` | 17.500 | 100 `AMLODIPINE~AMLODIPINE` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 24 | HIGH | `74624` | MUCO S.R 20TAB | MUCO S.R 75 MG 20 CAPS. | `` | 0.414 | 100 `MUCO~MUCO` ov=1.00 | Semantic token conflict: TABLET vs CAPSULE | form equivalence / semantic conflict |
| 25 | HIGH | `46822` | CRYPTONAZ SUSP | CRYPTONAZ 100 MG / 5 ML SUSP. 60 ML | `904598` | 12.043 | 100 `CRYPTONAZ~CRYPTONAZ` ov=1.00 | Candidate has unrequested numeric token: 100, 5, 60 | numeric gate too strict / unit-pack parsing |
| 26 | HIGH | `19056` | ZOVIRAX 10% CREAM | ZOVIRAX 5 % TOPICAL CREAM 10 GM | `903662` | 16.111 | 100 `ZOVIRAX~ZOVIRAX` ov=0.50 | Candidate has unrequested numeric token: 5 | numeric gate too strict / unit-pack parsing |
| 27 | HIGH | `73267` | VITACID C EFF 12 TAB | VITACID CALCIUM 12 EFF. TAB. | `2515480` | 18.216 | 100 `VITACID~VITACID` ov=1.00 | Arabic name contains calcium for VITACID C query | unknown/no detailed rejection |
| 28 | HIGH | `74142` | BRISTAFLAM 20TAB | BRISTAFLAM 100 MG 20 F.C.TABS. | `2171211` | 15.896 | 100 `BRISTAFLAM~BRISTAFLAM` ov=1.00 | Candidate has unrequested numeric token: 100 | numeric gate too strict / unit-pack parsing |
| 29 | HIGH | `75635` | GARAMYCIN CREAM 15gm | GARAMYCIN 0.1 % CREAM 15 GM | `2607401` | 17.565 | 100 `GARAMYCIN~GARAMYCIN` ov=1.00 | Candidate has unrequested numeric token: 0, 1 | numeric gate too strict / unit-pack parsing |
| 30 | HIGH | `47650` | T4-THYRO 50MCG TAB | T 4 THYRO 50 MCG 100 TABS. | `` | 14.544 | 100 `THYRO~THYRO` ov=1.00 | Candidate has unrequested numeric token: 100 | numeric gate too strict / unit-pack parsing |
| 31 | HIGH | `2243` | EPIFENAC DROPS | EPIFENAC 0.1 % EYE DROPS 5 ML | `2473716` | 12.415 | 100 `EPIFENAC~EPIFENAC` ov=1.00 | Candidate has unrequested numeric token: 0, 1, 5 | numeric gate too strict / unit-pack parsing |
| 32 | HIGH | `87986` | Omega RX 60 pieces + Omega 30 pieces offer | OMEGA RX JELLY CANDY 60 PCS. + 30 PCS | `902314` | 12.973 | 100 `OMEGA~OMEGA` ov=0.67 | Component mismatch: different_brand | component/brand classifier over-rejects |
| 33 | HIGH | `73632` | MOBITIL 15 MG 3 AMP | MOBITIL 15 MG / 1.5 ML 3 AMP. | `1397647` | 17.222 | 100 `MOBITIL~MOBITIL` ov=1.00 | Candidate has unrequested numeric token: 1, 5 | numeric gate too strict / unit-pack parsing |
| 34 | MEDIUM | `66146` | NACTALIA 1 MILK 400 G | 100 L'ORÉAL PARIS GLYCOLIC BRIGHT DAILY FOAMING CLEANSER ML | `` | 2.230 | 100 `NACTALIA~AL` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 35 | HIGH | `74291` | CLARITINE 20 TAB | CLARITINE 10 MG 20 TAB. | `` | 14.711 | 100 `CLARITINE~CLARITINE` ov=1.00 | Candidate has unrequested numeric token: 10 | numeric gate too strict / unit-pack parsing |
| 36 | HIGH | `73617` | ARCOXIA 90 MG 14 TAB | ARCOXIA 90 MG 14 F.C.TABS. | `` | 14.464 | 100 `ARCOXIA~ARCOXIA` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 37 | HIGH | `ma` | MAALOX LEMON 20 SACHET | MAALOX LEMON 20 ORAL SACHET SUSP. | `` | 16.574 | 100 `MAALOX~MAALOX` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 38 | HIGH | `89684` | HERO VITAMIN D3 + K2 DROPS 10 ML | HERO D 3 + K 2 ORAL DROPS | `2532720` | 10.273 | 100 `HERO~HERO` ov=0.50 | Arabic name missing marker for ML | Arabic marker gate too strict |
| 39 | HIGH | `AT50` | ATROVENT 500 MCG VIAL | ATROVENT 500 MCG / 2 ML 20 UNIT DOSE VIAL. | `2542938` | 16.500 | 100 `ATROVENT~ATROVENT` ov=1.00 | Candidate has unrequested numeric token: 2, 20 | numeric gate too strict / unit-pack parsing |
| 40 | MEDIUM | `85839` | ACHTENON 30 TABS | CONVENTIN XR 300 MG 30 TABS. | `2146223` | 13.124 | 55 `ACHTENON~CONVENTIN` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 41 | LOW | `2779` | METHERGIN 30TAB | AUGMENTIN 625 MG 10 F.C. TAB. + VITACID C 1 GM 12 EFF. TAB | `` | 2.761 | 67 `METHERGIN~AUGMENTIN` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 42 | HIGH | `23265` | TRITACE 1.25MG 14TAB | TRITACE 1.25 MG 14 TAB. | `` | 17.500 | 100 `TRITACE~TRITACE` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 43 | HIGH | `74589` | VISCERALGINE 20 TAB | VISCERALGINE 50 MG 20 F.C.TABS. | `904446` | 16.078 | 100 `VISCERALGINE~VISCERALGINE` ov=1.00 | Candidate has unrequested numeric token: 50 | numeric gate too strict / unit-pack parsing |
| 44 | HIGH | `39985` | TOPMODE FORTE TAB | TOPMODE FORTE 200 MG 10 TAB | `` | 10.364 | 100 `TOPMODE~TOPMODE` ov=1.00 | Candidate has unrequested numeric token: 10, 200 | numeric gate too strict / unit-pack parsing |
| 45 | HIGH | `78192` | NEUROVIT 6 I.M. AMPS. | NEUROVIT 6 I.M. AMPS. | `` | 17.500 | 100 `NEUROVIT~NEUROVIT` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 46 | MEDIUM | `dan` | DANSHIRO MOUTH SPRAY 30ML | DAN OFF HAIR SHAMPOO 250 ML | `2113290` | 3.795 | 100 `DANSHIRO~DAN` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 47 | HIGH | `79694` | MAALOX PLUS FAST 180ML SYRUP | MAALOX PLUS ORAL SUSP. 180 ML | `1405683` | 14.018 | 100 `MAALOX~MAALOX` ov=1.00 | Component mismatch: different_brand | component/brand classifier over-rejects |
| 48 | HIGH | `73069` | UROSOLVINE 12 SACHETS | UROSOLVINE EFF. GRAN. 12 SACHETS | `2424152` | 19.118 | 100 `UROSOLVINE~UROSOLVINE` ov=1.00 | Component mismatch: different_brand | component/brand classifier over-rejects |
| 49 | HIGH | `89426` | ANTODINE 6 AMPOULES * 2 ML | ANTODINE 20 MG / 2 ML 6 I.M. OR I.V. AMP | `` | 12.687 | 100 `ANTODINE~ANTODINE` ov=1.00 | Candidate has unrequested numeric token: 20 | numeric gate too strict / unit-pack parsing |
| 50 | LOW | `76161` | DEVIT-3 1 AMP IMP | 3.5 3.5 ML DR. RASHEL VITAMIN C DAY CREAM FOR SKIN LIGHTENING AND ANTI AGING 50 | `` | 3.258 | 75 `DEVIT~VITAMIN` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 51 | HIGH | `80992` | BISOLVON 8 MG 20 TABS | BISOLVON 8 MG 20 TABS. | `` | 17.500 | 100 `BISOLVON~BISOLVON` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 52 | HIGH | `73363` | AMEBAZOLE 1 GM 2 TAB | AMEBAZOL 1 GM 2 F.C. TABS. | `2681468` | 16.358 | 100 `AMEBAZOLE~AMEBAZOL` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 53 | HIGH | `74272` | CONTROLOC 40MG POWDER FOR I.V. INF. VIAL | CONTROLOC 40 MG POWDER FOR I.V. INF. VIAL | `` | 17.500 | 100 `CONTROLOC~CONTROLOC` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 54 | HIGH | `48041` | KEFENTECH 30 MG 7 PLASTER SHEET. | KEFENTECH 30 MG 7 PLASTER SHEET. | `` | 17.500 | 100 `KEFENTECH~KEFENTECH` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 55 | HIGH | `87435` | TOTACAL CALCIUM 30 TAB | TOTACAL 30 TABS | `2146261` | 16.184 | 100 `TOTACAL~TOTACAL` ov=0.50 | Component mismatch: different_brand | component/brand classifier over-rejects |
| 56 | MEDIUM | `91072` | LICTRILIT 360ML | AZHA VIT C SERUM 30 ML + AZHA ROLL ON RED 60 ML + AZHA WHITENING CREAM 30 G + AZHA BODY LOTION 25 ML | `` | 6.381 | 80 `LICTRILIT~VIT` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 57 | HIGH | `91707` | STOPADOL MIGRAINE 30 F.C. TABS. | STOPADOL NIGHT 30 F.C.TABS | `2282228` | 17.848 | 100 `STOPADOL~STOPADOL` ov=1.00 | Component mismatch: different_modifier | component/brand classifier over-rejects |
| 58 | HIGH | `18115` | GROWTH FORMULA ADULT CHOCOLATE | GROWTH FORMULA WG 400 GRAM POWDER CHOCOLATE | `903132` | 8.699 | 100 `GROWTH~GROWTH` ov=1.00 | Rejected: overlap=0.750, score=8.699, numeric_match=False, exact_name=False | threshold/scoring rejected likely candidate |
| 59 | HIGH | `79639` | PANADOL MIGRAINE 30 TABS | PANADOL MIGRAINE 30 TABS. | `` | 17.500 | 100 `PANADOL~PANADOL` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 60 | HIGH | `18842` | FLUCORAL 2CAPS | FLUCORAL 150 MG 2 CAPS | `2603322` | 17.054 | 100 `FLUCORAL~FLUCORAL` ov=1.00 | Candidate has unrequested numeric token: 150 | numeric gate too strict / unit-pack parsing |
| 61 | HIGH | `73227` | NEUROTON 30 TABS | NEUROTON 30 COATED TAB. | `` | 15.647 | 100 `NEUROTON~NEUROTON` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 62 | HIGH | `73463` | EXFORGE HCT 10 /160 /25 MG MG 14 TAB | EXFORGE HCT 10 / 160 / 25 MG 14 F.C. TAB. | `` | 14.993 | 100 `EXFORGE~EXFORGE` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 63 | HIGH | `73606` | TRITONE 125ML SYRAP | TRITONE 4.8 MG / ML SUSP. 125 ML | `2472093` | 13.857 | 100 `TRITONE~TRITONE` ov=0.50 | Candidate has unrequested numeric token: 4, 8 | numeric gate too strict / unit-pack parsing |
| 64 | HIGH | `67312` | EUTHYROX 25MG 50TAB | EUTHYROX 50 MCG 50 TAB | `` | 9.951 | 100 `EUTHYROX~EUTHYROX` ov=1.00 | Rejected: overlap=0.600, score=9.951, numeric_match=True, exact_name=False | threshold/scoring rejected likely candidate |
| 65 | LOW | `79400` | GASTROTIDIN 3 AMPULES | 3.5 3.5 CLEOPATRA GOAT MILK MAGIC TOUCH SKIN MASSAGE CREAM 125 ML | `` | 6.678 | 75 `GASTROTIDIN~GOAT` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 66 | LOW | `78462` | PHILOZAC 20MG 30-CAP | TEGRETOL CR 200 MG 20 F.C. DIVITAB. | `2435793` | 10.847 | 67 `PHILOZAC~CR` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 67 | HIGH | `67539` | GONAPURE 150 I.U./ML I.M./S.C. 1 VIAL | GONAPURE 150 I.U. / ML I.M. / S.C. VIAL | `` | 15.130 | 100 `GONAPURE~GONAPURE` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 68 | HIGH | `57403` | PANTAZOL40 MG VIAL | PANTAZOL 40 MG POWDER FOR I.V. INF. VIAL | `` | 15.833 | 100 `PANTAZOL~PANTAZOL` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 69 | HIGH | `78142` | BETOLVEX 2 pre-filled AMP | BETOLVEX 1 MG / ML 2 PRE FILLED SYRINGE I.M. | `2274854` | 16.005 | 100 `BETOLVEX~BETOLVEX` ov=1.00 | Candidate has unrequested numeric token: 1 | numeric gate too strict / unit-pack parsing |
| 70 | HIGH | `73321` | B-COM I.M./I.V. 6 AMP. | B COM I.M. / I.V. 6 AMP. | `` | 17.500 | 100 `COM~COM` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 71 | MEDIUM | `65947` | CELEBORG 200 MG 20 CAP | TEGRETOL CR 200 MG 20 F.C. DIVITAB. | `2435793` | 14.767 | 67 `CELEBORG~CR` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 72 | MEDIUM | `80372` | CIALONG 20MG 4TABS | TADALONG 20 MG 4 TABS. | `2312758` | 15.790 | 83 `CIALONG~TADALONG` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 73 | LOW | `88283` | CARTIOJO 30CAPS | L CARNITINE 300 MG / ML SYRUP 30 ML | `901940` | -0.497 | 67 `CARTIOJO~CARNITINE` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 74 | HIGH | `82928` | DEXAZONE 60 TAB | DEXAZONE 0.5 MG 60 TABS | `2313013` | 16.147 | 100 `DEXAZONE~DEXAZONE` ov=1.00 | Candidate has unrequested numeric token: 0, 5 | numeric gate too strict / unit-pack parsing |
| 75 | HIGH | `54471` | THROMBEXX DNA GEL40 G | THROMBEXX DNA 1120 I.U / 100 GM TOPICAL GEL. | `1561607` | 9.618 | 100 `THROMBEXX~THROMBEXX` ov=1.00 | Rejected: overlap=0.740, score=9.618, numeric_match=False, exact_name=False | threshold/scoring rejected likely candidate |
| 76 | HIGH | `22773` | RIRI MILK CEREAL&FRUITS POWDER | RIRI RICE AND FRUITS 200 GM | `2381986` | 1.182 | 100 `RIRI~RIRI` ov=0.67 | Rejected: overlap=0.400, score=1.182, numeric_match=False, exact_name=False | threshold/scoring rejected likely candidate |
| 77 | HIGH | `55146` | CORNETEARS EYE GEL10 GM | CORNETEARS 1000 IU / G AQUEOUS EYE GEL 10 GM | `1659304` | 16.636 | 100 `CORNETEARS~CORNETEARS` ov=1.00 | Candidate has unrequested numeric token: 1000 | numeric gate too strict / unit-pack parsing |
| 78 | HIGH | `73585` | DERMOVATE CREAM 25 GM | DERMOVATE 0.05 % TOP. CREAM 25 GM | `1619484` | 17.118 | 100 `DERMOVATE~DERMOVATE` ov=1.00 | Candidate has unrequested numeric token: 0, 05 | numeric gate too strict / unit-pack parsing |
| 79 | HIGH | `57711` | POLYFRESH EYE DROPS 10 ML | POLYFRESH 2 % EYE DROPS 10 ML | `2144451` | 17.808 | 100 `POLYFRESH~POLYFRESH` ov=1.00 | Candidate has unrequested numeric token: 2 | numeric gate too strict / unit-pack parsing |
| 80 | HIGH | `90448` | orchacortin 1% 5mg ointment | ORCHACORTIN 1 % EYE OINT. 5 GM | `1738871` | 14.624 | 100 `ORCHACORTIN~ORCHACORTIN` ov=0.50 | Component mismatch: different_dosage | component/brand classifier over-rejects |
| 81 | HIGH | `81385` | PRINORELAX 15 MG 30 EXT. R.CAPS | PRINORELAX 15 MG 30 EXT. R.CAPS. | `` | 17.500 | 100 `PRINORELAX~PRINORELAX` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 82 | HIGH | `72944` | SELOKEN ZOC 50 MG 28 TAB | SELOKENZOC 50 MG 28 PROLONGED R.TABS. | `1740222` | 15.633 | 100 `SELOKEN~SELOKENZOC` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 83 | HIGH | `66035` | OROVEX MOUTHWASH CLOVE 250 ML SYRUP | OROVEX CLOVE MOUTH WASH 250 ML | `2488118` | 14.805 | 100 `OROVEX~OROVEX` ov=1.00 | Component mismatch: different_brand | component/brand classifier over-rejects |
| 84 | HIGH | `23233` | SELENIUM-ACE 30 TAB | SELENIUM ACE 30 TABS | `` | 16.772 | 100 `SELENIUM~SELENIUM` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 85 | HIGH | `21386` | ISIS ANISE 20BAGS | ISIS ANISE 12 FILTER BAGS | `2139999` | 10.953 | 100 `ISIS~ISIS` ov=1.00 | Rejected: overlap=0.750, score=10.953, numeric_match=False, exact_name=False | threshold/scoring rejected likely candidate |
| 86 | HIGH | `83084` | CLAVIMOX 642.9 SUSP | CLAVIMOX 642.9 MG / 5 ML PD. FOR ORAL SUSP. 75 ML | `2684107` | 17.969 | 100 `CLAVIMOX~CLAVIMOX` ov=1.00 | Candidate has unrequested numeric token: 5, 75 | numeric gate too strict / unit-pack parsing |
| 87 | HIGH | `73232` | ALL- VENT SYRUP 125 ML | ALL VENT SYRUP 125 ML | `` | 17.500 | 100 `ALL~ALL` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 88 | HIGH | `73843` | LANTUS SOLOSTAR 5 PENS 100UNITS/ML | LANTUS SOLOSTAR 100 I.U. / ML 5 PENS | `` | 13.392 | 100 `LANTUS~LANTUS` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 89 | HIGH | `89823` | pantroglop 40 vial | PANTROGLOB 40 MG POWDER FOR I.V. INF. VIAL | `1872524` | 15.264 | 95 `PANTROGLOP~PANTROGLOB` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 90 | LOW | `87779` | RECORMON 4000 0.3 AMP | 3.2 CHI KERATIN RECONSTRUCTING CONDITIONER 355 ML | `` | 3.005 | 77 `RECORMON~RECONSTRUCTING` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 91 | HIGH | `74069` | SPASMOFREE 3 AMP | SPASMOFREE 5 MG / 2 ML I.V. / I.M. 3 AMP. | `2313135` | 16.200 | 100 `SPASMOFREE~SPASMOFREE` ov=1.00 | Candidate has unrequested numeric token: 2, 5 | numeric gate too strict / unit-pack parsing |
| 92 | HIGH | `74077` | LORNOXICAM 8 MG AMP | LORNOXICAM 8 MG / 2 ML VIAL FOR I.M. / I.V. INJ. | `949345` | 15.400 | 100 `LORNOXICAM~LORNOXICAM` ov=1.00 | Candidate has unrequested numeric token: 2 | numeric gate too strict / unit-pack parsing |
| 93 | HIGH | `73602` | NEUROTON 6 AMP | NEUROTON 6 AMP. | `` | 17.500 | 100 `NEUROTON~NEUROTON` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 94 | HIGH | `48116` | ARIXTRA 2.5MG/0.5ML 10 S.C. PREFILLED SYRINGES | ARIXTRA 2.5 MG / 0.5 ML 10 S.C. PREFILLED SYRINGES | `` | 17.500 | 100 `ARIXTRA~ARIXTRA` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 95 | HIGH | `88163` | arginine+citrulline 1000 60 tab | NOW ARGININE 500 MG CITRULLINE 250 MG 120 CAPS | `2496390` | -4.553 | 100 `ARGININE~ARGININE` ov=1.00 | Semantic token conflict: TABLET vs CAPSULE | form equivalence / semantic conflict |
| 96 | HIGH | `73761` | TRILEPTAL 300MG 50TAB | TRILEPTAL 300 MG 50 F.C.TAB. | `` | 15.100 | 100 `TRILEPTAL~TRILEPTAL` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 97 | HIGH | `21239` | MICONAZ 2% LIQUID SPRAY 60 ML | MICONAZ 2 % LIQUID SPRAY 60 ML | `` | 17.500 | 100 `MICONAZ~MICONAZ` ov=0.67 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 98 | HIGH | `79504` | VIGOTON PLUS 20 TABS | VIGOTON 30 TABS | `2685285` | 11.000 | 100 `VIGOTON~VIGOTON` ov=1.00 | Rejected: overlap=0.500, score=11.000, numeric_match=False, exact_name=False | threshold/scoring rejected likely candidate |
| 99 | HIGH | `80591` | TREXOZOLA 2.5 MG 10 TABS | TREXOZOLA 2.5 MG 10 F.C. TABS. | `` | 15.115 | 100 `TREXOZOLA~TREXOZOLA` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 100 | HIGH | `46744` | DOLO D SUSPENSION 115 ML | DOLO D ORAL SUSP. 115 ML | `` | 15.850 | 100 `DOLO~DOLO` ov=0.50 | Component mismatch: different_brand | component/brand classifier over-rejects |
| 101 | HIGH | `76782` | DOLO-D PLUS 115ML SYRUP | DOLO D PLUS ORAL SUSP. 115 ML | `` | 12.628 | 100 `DOLO~DOLO` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 102 | HIGH | `82651` | NAN 800GM 3 | NAN OPTIPRO STAGE 3 MILK 800 GM | `` | 12.853 | 100 `NAN~NAN` ov=1.00 | Component mismatch: different_brand | component/brand classifier over-rejects |
| 103 | HIGH | `47651` | T4-THYRO 100 MCG 100 TABS | T 4 THYRO 100 MCG 100 TABS. | `` | 17.500 | 100 `THYRO~THYRO` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 104 | MEDIUM | `83813` | WELLINTA SR 150 MG TABS | CHICCO WELL BEING SILICONE BOTTLE 150 ML FOR + BOTTLE 150 ML | `` | 5.195 | 100 `WELLINTA~WELL` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 105 | HIGH | `73505` | NOVORAPID FLEXPEN | NOVORAPID 100 I.U. / ML 1 FLEXPEN | `1661299` | 12.617 | 100 `NOVORAPID~NOVORAPID` ov=1.00 | Candidate has unrequested numeric token: 1, 100 | numeric gate too strict / unit-pack parsing |
| 106 | HIGH | `91111` | QULAPERAFEN SYRUP | QULAPERAFEN SUYRP 100 ML | `2114227` | 6.902 | 100 `QULAPERAFEN~QULAPERAFEN` ov=1.00 | Rejected: overlap=0.500, score=6.902, numeric_match=False, exact_name=False | threshold/scoring rejected likely candidate |
| 107 | HIGH | `73281` | OTRIVIN ADULT DROPS 15 ML | OTRIVIN 0.1 % ADULT NASAL DROPS 15 ML | `2139918` | 17.167 | 100 `OTRIVIN~OTRIVIN` ov=1.00 | Candidate has unrequested numeric token: 0, 1 | numeric gate too strict / unit-pack parsing |
| 108 | LOW | `74091` | DAKTARIN CREAM | CREAM 21 ALOE VERA GEL TO MOISTURIZE THE SKIN 95 % 300 ML | `` | -6.775 | 67 `DAKTARIN~SKIN` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 109 | HIGH | `80483` | PANADOL JOINT 24 TABS | PANADOL COLD FLU DAY 24 F.C. TABS. | `2169070` | 16.208 | 100 `PANADOL~PANADOL` ov=1.00 | Component mismatch: different_modifier | component/brand classifier over-rejects |
| 110 | HIGH | `POT` | POTASSIUM PERMENGANATE | AL AHRAM A POTASSIUM PERMANGANATE 12 PCS | `1868575` | 11.187 | 100 `POTASSIUM~POTASSIUM` ov=0.50 | Component mismatch: different_brand | component/brand classifier over-rejects |
| 111 | HIGH | `78181` | SIMEDILL SYRUP 120ML | SIMEDILL EMULSION 120 ML | `903751` | 14.778 | 100 `SIMEDILL~SIMEDILL` ov=1.00 | Component mismatch: different_brand | component/brand classifier over-rejects |
| 112 | LOW | `73819` | NETLOOK 20MG CAP | ENTRESTO 200 MG 97 / 103 MG 56 F.C.TABS | `2623310` | -1.793 | 57 `NETLOOK~ENTRESTO` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 113 | HIGH | `75875` | MEPACO GREEN TEA 20 TABS | MEPACO GREEN TEA 20 TABLETS | `` | 15.606 | 100 `MEPACO~MEPACO` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 114 | HIGH | `92082` | marshmallow whitening cream | AVUVA VANILLA MARSHMALLOW HAND AND BODY CREAM 200 ML | `2130716` | 8.992 | 100 `MARSHMALLOW~MARSHMALLOW` ov=0.50 | Rejected: overlap=0.667, score=8.992, numeric_match=False, exact_name=False | threshold/scoring rejected likely candidate |
| 115 | HIGH | `80664` | HERO BABY FEH 400 GM | HERO BABY FEH MILK 400 GM | `2558479` | 19.444 | 100 `HERO~HERO` ov=1.00 | Component mismatch: different_brand | component/brand classifier over-rejects |
| 116 | HIGH | `73250` | HEXITOL MOUTHWASH 100 ML | HEXITOL 1.25 MG / ML MOUTH WASH 100 ML | `1458047` | 16.400 | 100 `HEXITOL~HEXITOL` ov=1.00 | Candidate has unrequested numeric token: 1, 25 | numeric gate too strict / unit-pack parsing |
| 117 | HIGH | `87016` | ISOTRETINOIN 20MG 30 SOFT GELATIN CAPS | ISOTRETINOIN 20 MG 30 SOFT GELATIN CAPS | `` | 17.500 | 100 `ISOTRETINOIN~ISOTRETINOIN` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 118 | MEDIUM | `48177` | IMP HYDREA CAPSULES 500 MG 100 CAP | TETRA HYDRO UREA CREAM 75 GM | `2472781` | 3.258 | 89 `HYDREA~HYDRO` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 119 | LOW | `58248` | HALONACE 5 MG 10 TAB | KEPILEPSY 500 MG / 5 ML CONC. SOL. FOR I.V. 5 AMP. | `2635415` | 5.606 | 75 `HALONACE~CONC` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 120 | HIGH | `60073` | LASILACTONE 50MG 30 TAB | LASILACTONE 50 / 20 MG 30 TABS. | `904829` | 17.135 | 100 `LASILACTONE~LASILACTONE` ov=1.00 | Candidate has unrequested numeric token: 20 | numeric gate too strict / unit-pack parsing |
| 121 | LOW | `GTN` | GTN CREAM | ARGENTO CLEAR 200 AZHI BRIGHTENING CREAM 30 G ARGENTO NIGHT CREAM 30 G ARGENTO EYE CONTOUR 15 G | `` | 6.165 | 67 `GTN~ARGENTO` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 122 | LOW | `74137` | GYNODAKTARIN VAGINAL CREAM | CREAM 21 ALOE VERA GEL TO MOISTURIZE THE SKIN 95 % 300 ML | `` | -8.216 | 67 `GYNODAKTARIN~SKIN` ov=0.00 | English name missing requested identity token; Arabic name missing marker for VAGINAL | identity token / spelling / search ranking |
| 123 | LOW | `CYTO` | CYTOTEC 200 MG 14 TABS +++IMP | SEBACLAR PURIFYING CLEANSING GEL 200 ML + SEBACLAR TONIC LOTION 200 ML | `` | 1.429 | 60 `CYTOTEC~TONIC` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 124 | HIGH | `74696` | ANTODINE 20 MG 3 AMP | ANTODINE 20 MG / 2 ML 3 I.M. OR I.V. AMP | `` | 14.071 | 100 `ANTODINE~ANTODINE` ov=1.00 | Candidate has unrequested numeric token: 2 | numeric gate too strict / unit-pack parsing |
| 125 | HIGH | `2944` | ENEMAX 120ML VIAL | ENEMAX ENEMA 120 ML | `1533934` | 14.514 | 100 `ENEMAX~ENEMAX` ov=1.00 | Component mismatch: different_brand | component/brand classifier over-rejects |
| 126 | HIGH | `916` | EPILAT RETARD 20 TAB | EPILAT RETARD 20 MG SR. 20 F.C.TAB. | `` | 14.274 | 100 `EPILAT~EPILAT` ov=1.00 | Component mismatch: different_modifier | component/brand classifier over-rejects |
| 127 | LOW | `89889` | eltroxin 100 | PURITAN’S PRIDE OMEGA 3 FISH OIL 1000 MG 100 TAB | `` | 8.318 | 67 `ELTROXIN~OIL` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 128 | LOW | `26161` | STEROGYL #A# AMP IMP | AL AHRAM A POTASSIUM PERMANGANATE 12 PCS | `1868575` | 5.952 | 67 `STEROGYL~AL` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 129 | HIGH | `90840` | APTAMIL 2 ADVANCE PREMIUM+ MILK 400 GM | APTAMIL 2 ADVANCE MILK 400 GM | `` | 13.751 | 100 `APTAMIL~APTAMIL` ov=1.00 | Candidate missing orderable storeProductId | missing_storeProductId / DOM/API enrichment |
| 130 | HIGH | `73951` | NOVOMIX 30 FLEXPEN | NOVOMIX 30 100 I.U. / ML 1 FLEXPEN | `2697073` | 18.673 | 100 `NOVOMIX~NOVOMIX` ov=1.00 | Candidate has unrequested numeric token: 1, 100 | numeric gate too strict / unit-pack parsing |
| 131 | HIGH | `83661` | MEGAMOX ES 642MG SYRUP | MEGAMOX ES 642.9 MG SUSP. 100 ML | `905187` | 13.289 | 100 `MEGAMOX~MEGAMOX` ov=1.00 | Candidate has unrequested numeric token: 100, 9 | numeric gate too strict / unit-pack parsing |
| 132 | HIGH | `48132` | PROCORLAN 7.5MG TAB | PROCORALAN 7.5 MG 28 F.C. TABS. | `2602255` | 16.122 | 95 `PROCORLAN~PROCORALAN` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 133 | HIGH | `91191` | SANSO D3 PLUS 28 TAB | SANSO D PLUS 4000 I.U + K 2 28 TAB | `2145609` | 15.252 | 100 `SANSO~SANSO` ov=1.00 | Candidate has unrequested numeric token: 2, 4000 | numeric gate too strict / unit-pack parsing |
| 134 | MEDIUM | `18381` | REMERON 30 MG 10 TAB | 1 2 3 ONE TWO THREE 20 F.C. TAB | `2437679` | 7.040 | 80 `REMERON~ONE` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 135 | HIGH | `79566` | HERO BABY NUTRASENSE 1 MILK | HERO BABY NUTRASENSE 1 MILK 400 GM | `2604288` | 19.426 | 100 `HERO~HERO` ov=1.00 | Candidate has unrequested numeric token: 400 | numeric gate too strict / unit-pack parsing |
| 136 | HIGH | `89927` | SODIUM BICARB 500MG BIOMED 30TAB | SODIUM BICARB 500 MG 90 CAPSULES | `` | -3.292 | 100 `SODIUM~SODIUM` ov=0.67 | Semantic token conflict: TABLET vs CAPSULE | form equivalence / semantic conflict |
| 137 | HIGH | `82738` | MONONDEXIN 0.1 EYE DROPS | MONODEXIN 0.1 % EYE DROPS 10 * 0.5 ML SDU | `` | 12.670 | 95 `MONONDEXIN~MONODEXIN` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 138 | LOW | `74414` | ZYLORIC 300 MG 30 TAB | JOYPOX 60 MG 6 TAB + KEMPORIC TAB | `2043935` | 5.931 | 73 `ZYLORIC~KEMPORIC` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 139 | HIGH | `91683` | ZSWEV JOINT 30 TABS | ZSWEV JOINT 30 CAP | `2557141` | 5.324 | 100 `ZSWEV~ZSWEV` ov=1.00 | Semantic token conflict: TABLET vs CAPSULE | form equivalence / semantic conflict |
| 140 | HIGH | `86734` | ZADOGLOBN 20 CAPS | ZADOGLOBIN 20 CAPS | `2199219` | 17.190 | 95 `ZADOGLOBN~ZADOGLOBIN` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 141 | HIGH | `79627` | MECLIZIGO 20 FILM | MECLIZIGO 25 MG 20 ORODISPERSIBLE FILMS | `905217` | 15.236 | 100 `MECLIZIGO~MECLIZIGO` ov=1.00 | Candidate has unrequested numeric token: 25 | numeric gate too strict / unit-pack parsing |
| 142 | HIGH | `21563` | LIGNOCAINE SPRAY | LIGNOCAINE 10 % SPRAY 15 ML | `` | 10.402 | 100 `LIGNOCAINE~LIGNOCAINE` ov=1.00 | Candidate has unrequested numeric token: 10, 15 | numeric gate too strict / unit-pack parsing |
| 143 | MEDIUM | `83227` | LIBRADICLAN 140 MG 7 PLASTER | LIPRADICLAM 140 MG 7 PATCH | `` | 11.374 | 86 `LIBRADICLAN~LIPRADICLAM` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 144 | HIGH | `73733` | LANTUS 100 UNITS 5 CARTIDGES | LANTUS 100 I.U. / ML 5 CARTRIDGES | `1535759` | 16.178 | 100 `LANTUS~LANTUS` ov=0.50 | Component mismatch: different_dosage | component/brand classifier over-rejects |
| 145 | HIGH | `88577` | VITA-DE-VAL 10000 IU 30 SOFT GELATIN CAPS | VITA DE VAL 30 CAPS | `2651235` | 12.611 | 100 `VITA~VITA` ov=1.00 | Rejected: overlap=0.556, score=12.611, numeric_match=True, exact_name=False | threshold/scoring rejected likely candidate |
| 146 | HIGH | `meth` | METHYLTECHNO 1000 MCG O.D.F | METHYLTECHNO 1000 MCG 30 ORODISSOLVABLE FILMS | `2629527` | 15.411 | 100 `METHYLTECHNO~METHYLTECHNO` ov=1.00 | Candidate has unrequested numeric token: 30 | numeric gate too strict / unit-pack parsing |
| 147 | HIGH | `75199` | L-CARNITINE 5 AMP | L CARNITINE 1 GM / 5 ML 5 I.V. AMP. | `2174538` | 16.542 | 100 `CARNITINE~CARNITINE` ov=1.00 | Candidate has unrequested numeric token: 1 | numeric gate too strict / unit-pack parsing |
| 148 | HIGH | `2575` | NORFLEX 3 AMP | NORFLEX 30 MG / ML 3 AMPS. | `` | 13.311 | 100 `NORFLEX~NORFLEX` ov=1.00 | Candidate has unrequested numeric token: 30 | numeric gate too strict / unit-pack parsing |
| 149 | HIGH | `75203` | GYNOZOL VAGINAL CREAM | GYNOZOL 2 % VAGINAL CREAM 40 GM | `` | 10.700 | 100 `GYNOZOL~GYNOZOL` ov=1.00 | Candidate has unrequested numeric token: 2, 40 | numeric gate too strict / unit-pack parsing |
| 150 | LOW | `84408` | FERROSWAB ORAL SOLUTION 20 UNIT | HERO ORS ORAL REHYDRATION SOLUTION 200 ML | `1896063` | 8.376 | 75 `FERROSWAB~HERO` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |
| 151 | MEDIUM | `89715` | PRECOLM CREAM 50MG | CREAM 21 GLYCERIN 99.5 % PURE 125 ML | `` | 3.598 | 86 `PRECOLM~PURE` ov=0.00 | English name missing requested identity token | identity token / spelling / search ranking |

## False Positive / Unsafe Matched Suspects

هذه ليست كلها أخطاء مؤكدة؛ بعضها Arabic-only DOM يحتاج تحقق bilingual. الأخطر هي الصفوف التي يظهر فيها `matched=True` مع `manual_review_required=True` أو `ai_rejected`.

| # | Code | Requested item | Selected product | Winner id | Score | AI status | Why suspicious |
|---:|---|---|---|---|---:|---|---|
| 1 | `73458` | ECTOMETHRIN 5%LOTION 50 ML | اكتومثرين 5 % لوسيون 50 مل | `dom-row-اكتومثرين-5---لوسيون-50-مل` | 14.538462 | `ai_search_accepted` | تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.00 |
| 2 | `73241` | MINALAX 10 TAB | مينالاكس 10 اقراص | `dom-row-مينالاكس-10-اقراص` | 16.428571 | `ai_verified` | تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.00 |
| 3 | `91304` | panthenol 5% care cream 50 gm | PANTHENOL CREAM 50 GM COLLEDGE | `2176170` | 14.887356 | `ai_rejected` | matched=True لكن final_action/manual_review يمنع الاعتماد; AI status متعارض: ai_rejected; تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.50; أرقام مطلوبة غير ظاهرة في المنتج: 5 |
| 4 | `TOUX` | TOUX PROSPERITY SYRUP 120 ML | توكس شراب 120 مل | `dom-row-توكس-شراب-120-مل` | 16.964286 | `ai_verified` | تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.00 |
| 5 | `91686` | PANADOL EXTRA OPTI ZORB 24 F.C. TABS | PANADOL EXTRA 24 F.C. TAB OPTIZORB | `2290018` | 17.629412 | `ai_verified` | تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.33 |
| 6 | `73074` | ZURCAL 40 MG 14 TAB | ZURCAL 40 MG 14 GASTRO RESISTANT TABS. | `1615740` | 15.912857 | `ai_rejected` | matched=True لكن final_action/manual_review يمنع الاعتماد; AI status متعارض: ai_rejected |
| 7 | `73361` | UNICTAM 1500 VIAL | UNICTAM 1.5 GM I.M / I.V. VIAL | `2442786` | 11.609091 | `ai_search_accepted` | أرقام مطلوبة غير ظاهرة في المنتج: 1500 |
| 8 | `59940` | MERIOFERT 150 IU AMP | ميريوفيرت 150 وحده امبول امبول | `dom-row-ميريوفيرت-150-وحده-امبول-امبول` | 16.5 | `ai_rejected` | matched=True لكن final_action/manual_review يمنع الاعتماد; AI status متعارض: ai_rejected; تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.00 |
| 9 | `73558` | HYDROFERRIN DROPS 30 ML | هيدروفيرين 50 مجم / مل قطره 30 مل | `dom-row-هيدروفيرين-50-مجم---مل-قطره-30-مل` | 14.581633 | `ai_search_accepted` | تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.00 |
| 10 | `73931` | BETADERM 0.1% TOPICAL OINT. 15 GM | BETADERM 0.1 % TOPICAL OINT. 15 GM | `2541177` | 20.0 | `ai_verified` | تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.50 |
| 11 | `40019` | BORGASONE OINT | بورجازون 0.1 % مرهم 20 جم | `dom-row-بورجازون-0-1---مرهم-20-جم` | 12.5 | `ai_search_accepted` | تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.00 |
| 12 | `45413` | ABIMOL EXTRA 20 TAB. | ابيمول اكسترا 20 اقراص | `dom-row-ابيمول-اكسترا-20-اقراص` | 16.710526 | `ai_rejected` | matched=True لكن final_action/manual_review يمنع الاعتماد; AI status متعارض: ai_rejected; تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.00 |
| 13 | `64265` | ZURCAL 40 MG 1 VIAL | ZURCAL 40 MG POWDER FOR I.V. INF. VIAL | `2311818` | 14.672727 | `ai_verified` | أرقام مطلوبة غير ظاهرة في المنتج: 1 |
| 14 | `73470` | CLEXANE 80MG 2 SYRINGE | CLEXANE 80 MG / 0.8 ML 2 PREFILLED SYRINGES | `2145568` | 16.11375 | `ai_search_accepted` | تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.50 |
| 15 | `88828` | STAMIGEN 30 CAPS | ستاميجن 30 اقراص | `dom-row-ستاميجن-30-اقراص` | 16.5625 | `ai_rejected` | matched=True لكن final_action/manual_review يمنع الاعتماد; AI status متعارض: ai_rejected; تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.00 |
| 16 | `74000` | TRINUTREX 30 CAP | ترينوتريكس 30 كبسول | `dom-row-ترينوتريكس-30-كبسول` | 16.5625 | `ai_verified` | تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.00 |
| 17 | `73418` | INDOMETACIN 100 MG 10 SUPPS | INDOMETHACIN 100 MG 10 SUPP. B.P. 2014 | `902132` | 15.046984 | `ai_search_accepted` | تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.00 |
| 18 | `61860` | ROSITA HAIR LOTION 250 GM | ROSITA HAIR LOTION 250 ML | `2653544` | 18.2 | `ai_rejected` | matched=True لكن final_action/manual_review يمنع الاعتماد; AI status متعارض: ai_rejected; تحويل/خلط وحدة GM مقابل ML |
| 19 | `59327` | SLIMMER 50 SACHETS | سليمير سويتنير 50 اكياس | `dom-row-سليمير-سويتنير-50-اكياس` | 16.666667 | `ai_verified` | تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.00 |
| 20 | `91448` | CIDOLUT NOR 5MG 30TABS | CIDOLUT NOR 5 MG 30 TAB | `2567736` | 19.493617 | `ai_rejected` | matched=True لكن final_action/manual_review يمنع الاعتماد; AI status متعارض: ai_rejected |
| 21 | `56077` | TEXACORT 0.1 % CREAM 20 GM | TEXACORT 0.1 % TOP. LIPOCREAM 20 GM | `969798` | 14.885714 | `ai_rejected` | matched=True لكن final_action/manual_review يمنع الاعتماد; AI status متعارض: ai_rejected |
| 22 | `92139` | CARCEMIA 400 TAB | كارسيميا 400 مجم 10 اقراص | `dom-row-كارسيميا-400-مجم-10-اقراص` | 14.214286 | `ai_search_accepted` | تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.00 |
| 23 | `77233` | KITADAN ANTI-DANDRUFF SHAMPOO 200ML | KITADAN HAIR SHAMPOO 200 ML | `904773` | 16.460317 | `ai_rejected` | matched=True لكن final_action/manual_review يمنع الاعتماد; AI status متعارض: ai_rejected; qualifier anti-dandruff مفقود |
| 24 | `90130` | MERONEM 1000MG 10 VIAL. | MERONEM 1000 MG I.V.VIAL | `1769304` | 16.988085 | `ai_verified` | أرقام مطلوبة غير ظاهرة في المنتج: 10 |
| 25 | `43798` | MIRAGE 1 GM I.V. VIAL | MIRAGE 1000 MG I.V.VIAL | `2620003` | 17.685271 | `ai_search_accepted` | أرقام مطلوبة غير ظاهرة في المنتج: 1 |
| 26 | `90601` | menzofolic 30tab | MENZOFLIC 30 TABS | `2140662` | 16.239216 | `ai_search_accepted` | تشابه لفظي منخفض أو Arabic-only يحتاج تحقق: overlap=0.00 |
| 27 | `p25` | PULMICORT 0.25 MG 2 ML | PULMICORT 0.25 MG / ML 20 NEBULIZER VIAL SUSP. | `1395823` | 14.34359 | `ai_search_accepted` | أرقام مطلوبة غير ظاهرة في المنتج: 2 |

## Skipped / AI-Blocked Rows

هذه الصفوف لم تظهر كـ `no-results` لكنها انتهت `skipped` بسبب رفض AI review. عمليًا هي مشاكل تشغيل/قرار لأنها تحتاج manual review ولا يوجد سبب matching واضح في `order_item_summary` غير الجملة العامة.

| # | Code | Item | Reason | AI status | Final action |
|---:|---|---|---|---|---|
| 1 | `82905` | MEGAPRAZOLE 40MG I.V VIAL | AI matching requires manual review. | `ai_review_rejected` | `manual_review` |
| 2 | `73595` | LIBRAX 30 TAB | AI matching requires manual review. | `ai_review_rejected` | `manual_review` |
| 3 | `73147` | SOMATROPIN 4 I.U..1.6MG VIAL | AI matching requires manual review. | `ai_review_rejected` | `manual_review` |
| 4 | `59134` | INJECTMOL 1 GM/100ML VIAL FOR I.V. INF. | AI matching requires manual review. | `ai_review_rejected` | `manual_review` |
| 5 | `45178` | ABIMOL SUPP | AI matching requires manual review. | `ai_review_rejected` | `manual_review` |
| 6 | `V100` | VIAGRA 100 MG 4 TAB | AI matching requires manual review. | `ai_review_rejected` | `manual_review` |
| 7 | `40048` | HALOPERIDOL 5 AMP | AI matching requires manual review. | `ai_review_rejected` | `manual_review` |
| 8 | `46895` | MAGNESIUM PLUS TAB | AI matching requires manual review. | `ai_review_rejected` | `manual_review` |
| 9 | `90719` | TRIGASTCARE 120 CAP | AI matching requires manual review. | `ai_review_rejected` | `manual_review` |
| 10 | `87817` | NERKARDOU 5 MG 30 FILM | AI matching requires manual review. | `ai_review_rejected` | `manual_review` |
| 11 | `88233` | ISTIKREMA CREAM | AI matching requires manual review. | `ai_review_rejected` | `manual_review` |
| 12 | `75431` | HERO BABY HA MILK | AI matching requires manual review. | `ai_review_rejected` | `manual_review` |
| 13 | `82150` | MOVELEX PLUS GEL 100GM | AI matching requires manual review. | `ai_review_rejected` | `manual_review` |

## AI Reliability Problems

| Problem | Evidence | Impact | Recommended fix |
|---|---|---|---|
| Provider rate limiting is still frequent | 112 of 411 API-attempt rows are 429 | Slow runs, many manual reviews, wasted fallback attempts | Add run-level provider cooldown honoring `Retry-After`, global semaphore per provider, and skip AI for deterministic no-orderable exact candidates until DOM enrichment is solved. |
| Invalid JSON provider output | 15 `invalid_json` rows | AI search/verify becomes manual review despite useful text | Add stricter response-format config per provider, repair parser for fenced/partial JSON, and provider health quarantine. |
| AI result conflicts with artifact matched fields | 9 rows have `matched=True` but `final_action=manual_review` and `ai_status=ai_rejected` | Users may treat a blocked item as matched | Summary `matched` must represent final actionable status, with separate `deterministic_match_found`. |
| Manual-review hints are not consumed by order/matching flow | `manual_review_hints` appears only in tool/tests, not runtime modules | Human corrections cannot improve future runs | Load hints before matching and short-circuit exact approved corrections. |

## Performance, RAM, And Scalability Problems

| Area | Evidence | Why it hurts | Fix |
|---|---|---|---|
| Artifact size | `match_log_all_20260514_1252.txt` = 63.98 MB | Large disk writes and UI loading overhead | Bound trace detail and write compressed/partitioned diagnostics. |
| Artifact size | `matching_trace_20260514_1252.csv` = 50.60 MB | Large disk writes and UI loading overhead | Bound trace detail and write compressed/partitioned diagnostics. |
| Artifact size | `match_only_summary_20260514_1252.csv` = 18.03 MB | Large disk writes and UI loading overhead | Bound trace detail and write compressed/partitioned diagnostics. |
| Artifact size | `order_ai_trace_20260514_1252.txt` = 0.45 MB | Large disk writes and UI loading overhead | Bound trace detail and write compressed/partitioned diagnostics. |
| Artifact size | `order_ai_trace_20260514_1252.csv` = 0.32 MB | Large disk writes and UI loading overhead | Bound trace detail and write compressed/partitioned diagnostics. |
| Artifact size | `order_item_summary_20260514_1252.txt` = 0.21 MB | Large disk writes and UI loading overhead | Bound trace detail and write compressed/partitioned diagnostics. |
| Artifact size | `match_log_74272_20260514_1252.txt` = 0.13 MB | Large disk writes and UI loading overhead | Bound trace detail and write compressed/partitioned diagnostics. |
| Artifact size | `manual_review_20260514_1252.txt` = 0.12 MB | Large disk writes and UI loading overhead | Bound trace detail and write compressed/partitioned diagnostics. |
| Artifact size | `match_log_88577_20260514_1252.txt` = 0.12 MB | Large disk writes and UI loading overhead | Bound trace detail and write compressed/partitioned diagnostics. |
| Artifact size | `match_log_89684_20260514_1252.txt` = 0.12 MB | Large disk writes and UI loading overhead | Bound trace detail and write compressed/partitioned diagnostics. |
| Detailed match logging | `src/tawreed/tawreed_match_logs.py:37-51` writes per-item TXT, global `match_log_all`, and full `matching_trace` for detailed cases | The latest run produced 67MB `match_log_all` and 53MB `matching_trace`; this is a major IO bottleneck | Add `--trace-level`, cap candidates per item, de-duplicate candidates across query variants, and disable global all-log by default. |
| CSV artifact append | `src/tawreed/tawreed_artifacts.py:49-61` reads header on every append; `:183-196` rewrites whole CSV when schema changes | O(n²)-like IO risk as files grow; schema changes are expensive | Keep per-run schema fixed, open buffered writers, or batch rows in memory per item chunk then flush. |
| XLSX artifact append | `src/tawreed/tawreed_artifacts.py:65-80` loads/saves workbook per append | Very slow and memory-heavy for long runs | Write CSV during run; generate XLSX once at end. |
| Pandas full-load path | `src/core/drug_matching/pipeline.py:59-75` and `:416-421` read full Excel/CSV into DataFrames | RAM grows with input/export size; no streaming | Use column-selective reads and streaming/openpyxl for order items; keep catalog index cached per run. |
| UI artifact loading | `src/ui/streamlit_shared.py:55-60` reads full CSV/XLSX into DataFrame then dict | Opening 50MB+ traces in Streamlit will freeze or spike RAM | Use paged preview, file-size guard, and `nrows`/tail reading. |
| Multiprocessing order workers | `src/cli/cli_order.py:350-356` materializes all items and spawns processes/browsers | High RAM/browser load and Tawreed/API pressure | Use bounded queue workers, shared rate limits, and avoid browser-per-item-worker unless needed. |
| Parallel profile error handling | `src/cli/cli_order.py:74-79` waits futures but does not call `future.result()` | Worker exceptions can be hidden | Iterate futures and re-raise/log each result. |
| Candidate diagnostics retained | `product_matching` builds diagnostics for every query/candidate before decision | Large candidate sets multiply memory and trace size | Keep top-N diagnostics plus rejected reason summary; stream trace rows. |
| Search query explosion | `src/core/product_matching.py:200-208` can emit up to 24 query variants; latest no-results show 13-23 queries | Slow Tawreed searches and duplicated candidates | Stop after high-confidence exact related candidate, cache query results, and remove low-signal generic token queries. |
| DOM row scanning | `src/tawreed/tawreed_products_flow.py:186-189` and `src/tawreed/tawreed_strategy.py:32-34` iterate locators row-by-row | Playwright locator calls are expensive in loops | Extract visible row data once per table and operate on plain objects. |

## Functional Bugs And Design Issues

1. `matched` in order artifacts currently means deterministic match exists, not final accepted match. This creates misleading rows when AI/manual review blocks the item.
2. `no-results` conflates real no result, exact result without `storeProductId`, AI rejection, low confidence, and trace/search failures. Use separate statuses: `candidate_not_orderable`, `ai_blocked`, `search_no_rows`, `manual_review_required`.
3. Missing `storeProductId` is still a dominant false-negative root cause. DOM fallback exists, but many exact candidates still reach trace with blank id, so the fallback/enrichment is incomplete.
4. Numeric safety is over-conservative. It treats formulation concentration, vial volume, pack count, pediatric stage, percentages, and per-ML strengths as unsafe extra numbers.
5. Unit equivalence is incomplete: `200.000 I.U` vs `200000 I.U`, `1500` vs `1.5 GM`, `1 GM` vs `1000 MG`, attached tokens like `30TAB`, and OCR `6O` need one canonical dosage model.
6. Brand/component logic over-rejects products where Tawreed names include category, manufacturer, flavor, or generic ingredient variations.
7. Arabic-only DOM candidates make English lexical checks appear low-overlap; the system needs transliteration-aware comparison or bilingual normalization.
8. Manual review correction import exists but is not connected to matching/order runtime, so corrections do not reduce future false negatives.
9. AI fallback can produce many rate-limited attempts instead of respecting provider cooldown at run scope.
10. Trace files are useful for debugging but currently too large for routine runs and UI inspection.

## Hot Modules Requiring Refactor

| Module | Current size / signal | Problem | Direction |
|---|---|---|---|
| `src/core/product_matching.py` | 855 lines | Query generation, scoring, acceptance, diagnostics, Arabic gates, numeric gates in one module | Split into query generation, scoring, acceptance policy, diagnostics writer. |
| `src/core/drug_matching/trace_log.py` | 1046 lines | In-memory trace rows plus CSV/TXT summary rendering | Stream rows and split renderers. |
| `src/core/drug_matching/ai_steps.py` | 1037 lines | Verify/search/review selection, API handling, DataFrame mutation together | Separate batch selection, AI client calls, result application. |
| `src/core/drug_matching/verifier.py` | 882 lines, `_call_api` ~202 lines | Provider fallback/retry/parsing/rate-limit in one method | Extract provider executor, retry policy, response parser. |
| `src/tawreed/tawreed.py` | 770 lines | Browser session, order flow, search, cart, warehouse operations mixed | Feature modules with clear side-effect boundaries. |
| `src/core/drug_matching/normalizer.py` | 790 lines | Drug parsing and component equivalence rules are dense and hard to audit | Table-driven dosage/form parser with focused tests. |

## Prioritized Fix Plan

1. Fix artifact semantics: `matched` must mean final actionable match; add `deterministic_match_found` and `manual_review_blocked_match`.
2. Add exact-related candidate recovery for missing `storeProductId`: when API has exact candidate with blank id, force DOM enrichment and fail as `candidate_not_orderable` only if DOM also lacks id.
3. Build canonical dosage model: normalize units, percentages, per-ML strengths, pack counts, and OCR before extra-number rejection.
4. Add category-specific numeric policy: topical/eye/nasal/drops/injections/milk/supplements should not treat every extra number as unsafe.
5. De-duplicate candidates across query variants before scoring, diagnostics, trace, and AI search.
6. Integrate manual-review hints into order matching before AI.
7. Reduce query variants and add query-result cache per item/run.
8. Add trace levels: `off`, `summary`, `top-n`, `full`; default to `summary` for production runs.
9. Make artifact writers batch-oriented and generate XLSX after run completion.
10. Add global AI provider cooldown/rate limiter honoring `Retry-After`.
11. Rework Streamlit artifact views to avoid loading large files fully.
12. Re-raise parallel profile exceptions and report worker failures deterministically.

## Validation Needed After Fixes

- Regression fixture from this run containing all HIGH false negatives above.
- Unit tests for numeric equivalence: IU punctuation, percent strengths, per-ML, pack count, stage numbers, decimal strengths.
- Integration smoke with `--match-only --ai` and trace-level summary.
- Performance assertion: trace output bounded by top-N rows per item and no `match_log_all` above configured cap.
- Streamlit test for opening a large run directory without reading 50MB CSV into memory.
