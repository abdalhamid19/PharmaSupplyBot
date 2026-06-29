# Matching Trace Audit: wardany 20260513_2352

Source: `artifacts/order/wardany/20260513_2352/matching_trace_20260513_2352.csv`.

## Summary

| Metric | Count |
|---|---:|
| Total rows | 12,710 |
| Matching rows | 12,660 |
| Order AI rows | 50 |
| Unique matching items | 35 |
| Accepted matching rows | 51 |
| Accepted unique candidate groups | 29 |
| Rejected matching rows | 12,608 |
| Items with no deterministic accepted candidate | 17 |

## Error Categories

| Category | Count | Why it matters |
|---|---:|---|
| Accepted candidate has blank `candidate_id` | 9 | Cannot be trusted for real cart insertion. |
| Accepted item has multiple accepted candidate groups | 17 | Final winner can be ambiguous by supplier/id/name. |
| Accepted candidate later disagrees with AI status | 4 | Deterministic matching accepted a candidate that AI rejected or marked low confidence. |
| Accepted by fuzzy/non-exact rule | 15 | Needs stricter review when strength, pack size, or variant tokens differ. |
| Items with no deterministic accepted candidate | 17 | Potential false negatives or safe rejections requiring manual review. |

## Accepted Candidate Problems

Each row below is a unique accepted candidate group, not every repeated query row.

| Code | Item | Candidate id | Candidate | Score | Rule | Queries | Trace issue |
|---|---|---:|---|---:|---|---|---|
| `21058` | MIDODRINE 2.5 mg 20 TAB | 2127225 | MIDODRINE 2.5 MG 20 TAB. | 20.000 | exact_normalized_name_match | MIDODRINE 2.5 mg 20 TAB | multiple accepted candidates for item |
| `21058` | MIDODRINE 2.5 mg 20 TAB | 2530689 | MIDODRINE 2.5 MG 20 TAB. | 20.000 | exact_normalized_name_match | MIDODRINE 2.5 mg 20 TAB | multiple accepted candidates for item |
| `21058` | MIDODRINE 2.5 mg 20 TAB | 2673124 | MIDODRINE 2.5 MG 20 TAB. | 20.000 | exact_normalized_name_match | MIDODRINE 2.5 mg 20 TAB | multiple accepted candidates for item |
| `21058` | MIDODRINE 2.5 mg 20 TAB | 2693629 | MIDODRINE 2.5 MG 20 TAB. | 20.000 | exact_normalized_name_match | MIDODRINE 2.5 mg 20 TAB | multiple accepted candidates for item |
| `21058` | MIDODRINE 2.5 mg 20 TAB | 2695415 | MIDODRINE 2.5 MG 20 TAB. | 20.000 | exact_normalized_name_match | MIDODRINE 2.5 mg 20 TAB | multiple accepted candidates for item |
| `32158` | SUPRAX 100MG SYRUP 30ML | 1396786 | SUPRAX 100 MG / 5 ML SUSP. 30 ML | 13.926 | strong_score_with_good_overlap | SUPRAX 100MG SYRUP 30ML; SUPRAX 100 MG SYRUP 30 ML; SUPRAX 100 MG SYRUP | accepted by strong_score_with_good_overlap; missing important token(s): 30ML; extra numeric token(s): 100, 30, 5 |
| `47273` | DEVAROL-S-200.000 I.U 1 AMP | 2096264 | DEVAROL S 200000 I.U / 2 ML SOLUTION FOR I.M INJ. 1 AMP. | 13.024 | high_token_overlap | DEVAROL-S-200.000 I.U 1 AMP; DEVAROL S 200 000 I U 1 AMP; DEVAROL S 200 000 | accepted by high_token_overlap; extra numeric token(s): 2, 200000 |
| `61862` | AMLODIPINE 5MG 30 TAB | <blank> | AMLODIPINE 5 MG 30 TAB. | 17.500 | exact_normalized_name_match | AMLODIPINE 5MG 30 TAB | missing candidate_id; missing important token(s): 5MG; extra numeric token(s): 5 |
| `71903` | NACTALIA 2 MILK 400 G | <blank> | NACTALIA 2 MILK 400 GM | 16.904 | high_token_overlap | NACTALIA 2 MILK 400 G; NACTALIA 2 MILK 400; NACTALIA 2 MILK | missing candidate_id; accepted by high_token_overlap |
| `73241` | MINALAX 10 TAB | <blank> | MINALAX 10 TAB. | 17.500 | exact_normalized_name_match | MINALAX 10 TAB | missing candidate_id |
| `73253` | MOOV MASSAGE CREAM 40 GM | <blank> | MOOV MASSAGE CREAM 40 GM | 17.500 | exact_normalized_name_match | MOOV MASSAGE CREAM 40 GM | missing candidate_id; multiple accepted candidates for item |
| `73253` | MOOV MASSAGE CREAM 40 GM | 2562986 | MOOV MASSAGE CREAM 40 GM | 20.000 | exact_normalized_name_match | MOOV MASSAGE CREAM 40 GM | multiple accepted candidates for item |
| `73253` | MOOV MASSAGE CREAM 40 GM | <blank> | MOOV UP CREAM MASSAGE 40 GM | 16.029 | high_token_overlap | MOOV MASSAGE CREAM 40 GM | missing candidate_id; multiple accepted candidates for item; accepted by high_token_overlap |
| `73564` | CLEAREST 14 CAP | <blank> | CLEAREST 14 CAPS. | 16.539 | high_token_overlap | CLEAREST 14 CAP; CLEAREST 14; CLEAREST | missing candidate_id; accepted by high_token_overlap |
| `74881` | OCTOZINC CAP | 1313189 | OCTOZINC 25 MG 20 CAPS. | 11.329 | high_token_overlap | OCTOZINC CAP; OCTOZINC | accepted by high_token_overlap; extra numeric token(s): 20, 25; AI did not approve final item: ai_rejected |
| `78379` | NESTOGEN 3 MILK 200GM | 2630924 | NESTOGEN 3 MILK 200 GM | 20.000 | exact_normalized_name_match | NESTOGEN 3 MILK 200GM | multiple accepted candidates for item; extra numeric token(s): 200 |
| `78379` | NESTOGEN 3 MILK 200GM | 2695428 | NESTOGEN 3 MILK 200 GM | 20.000 | exact_normalized_name_match | NESTOGEN 3 MILK 200GM | multiple accepted candidates for item; extra numeric token(s): 200 |
| `89883` | JEPARILON 10 MG 10 CHEW. TABS | 1521391 | JEPARILON 10 MG 10 CHEW. TABS | 20.000 | exact_normalized_name_match | JEPARILON 10 MG 10 CHEW. TABS | multiple accepted candidates for item |
| `89883` | JEPARILON 10 MG 10 CHEW. TABS | <blank> | JEPARILON 10 MG 20 CHEW. TABS | 15.321 | high_token_overlap | JEPARILON 10 MG 10 CHEW. TABS | missing candidate_id; multiple accepted candidates for item; accepted by high_token_overlap; extra numeric token(s): 20 |
| `91304` | panthenol 5% care cream 50 gm | 2490314 | PANTHENOL 5 % APU CREAM | 13.811 | strong_score_with_good_overlap | panthenol 5% care cream | multiple accepted candidates for item; accepted by strong_score_with_good_overlap; missing important token(s): CARE; AI did not approve final item: ai_rejected |
| `91304` | panthenol 5% care cream 50 gm | 2176170 | PANTHENOL CREAM 50 GM COLLEDGE | 14.887 | strong_score_with_good_overlap | panthenol 5% care cream 50 gm; PANTHENOL 5 CARE CREAM 50 GM; panthenol 5% care cream | multiple accepted candidates for item; accepted by strong_score_with_good_overlap; missing important token(s): CARE; AI did not approve final item: ai_rejected |
| `91304` | panthenol 5% care cream 50 gm | <blank> | PANTHENOL CREAM 50 GM DREAM | 12.585 | strong_score_with_good_overlap | panthenol 5% care cream 50 gm; PANTHENOL 5 CARE CREAM 50 GM | missing candidate_id; multiple accepted candidates for item; accepted by strong_score_with_good_overlap; missing important token(s): CARE; AI did not approve final item: ai_rejected |
| `91686` | PANADOL EXTRA OPTI ZORB 24 F.C. TABS | 2319620 | PANADOL EXTRA 24 F.C. TAB | 16.768 | strong_score_with_good_overlap | PANADOL EXTRA OPTI ZORB 24 F.C. TABS; PANADOL EXTRA OPTI ZORB 24 F C TABS; PANADOL EXTRA OPTI ZORB | multiple accepted candidates for item; accepted by strong_score_with_good_overlap; missing important token(s): OPTI, ZORB |
| `91686` | PANADOL EXTRA OPTI ZORB 24 F.C. TABS | 2290018 | PANADOL EXTRA 24 F.C. TAB OPTIZORB | 17.629 | high_token_overlap | PANADOL EXTRA OPTI ZORB 24 F.C. TABS; PANADOL EXTRA OPTI ZORB 24 F C TABS; PANADOL EXTRA OPTI ZORB | multiple accepted candidates for item; accepted by high_token_overlap |
| `91733` | CHEMICETRIZINE 5 MG20 TAB | <blank> | CHEMICETRIZINE 5 MG 20 TABS | 16.926 | high_token_overlap | CHEMICETRIZINE 5 MG20 TAB; CHEMICETRIZINE 5 MG 20 TAB; CHEMICETRIZINE 5 MG 20 | missing candidate_id; accepted by high_token_overlap; missing important token(s): MG20; extra numeric token(s): 20 |
| `91763` | NORIGYNCIN 50/5MG I.M. AMP | 2341067 | NORIGYNCIN 50 / 5 MG I.M. AMP | 20.000 | exact_normalized_name_match | NORIGYNCIN 50/5MG I.M. AMP | missing important token(s): 5MG; extra numeric token(s): 5 |
| `91823` | Awadist 1000 mg Tab | 2468546 | AWADIST 1000 MG 20 F.C. TABS. | 16.530 | high_token_overlap | Awadist 1000 mg Tab; Awadist 1000 mg; Awadist 1000 | accepted by high_token_overlap; extra numeric token(s): 20 |
| `CONG` | CONGESTAL 20 TAB | 2064107 | CONGESTAL 20 TABS. | 19.048 | high_token_overlap | CONGESTAL 20 TAB; CONGESTAL 20; CONGESTAL | accepted by high_token_overlap |

## Items With No Deterministic Accepted Candidate

Top 3 rejected candidates per item. These are the main places to inspect for false negatives.

| Code | Item | AI status in trace | Rank | Candidate id | Candidate | Score | Rejection reason | Query |
|---|---|---|---:|---:|---|---:|---|---|
| `19056` | ZOVIRAX 10% CREAM | ai_rejected | 1 | 903662 | ZOVIRAX 5 % TOPICAL CREAM 10 GM | 16.111 | Component mismatch: different_dosage | ZOVIRAX 10% CREAM |
| `19056` | ZOVIRAX 10% CREAM | ai_rejected | 2 | 903662 | ZOVIRAX 5 % TOPICAL CREAM 10 GM | 16.111 | Component mismatch: different_dosage | ZOVIRAX 10 CREAM |
| `19056` | ZOVIRAX 10% CREAM | ai_rejected | 3 | 903662 | ZOVIRAX 5 % TOPICAL CREAM 10 GM | 16.111 | Component mismatch: different_dosage | ZOVIRAX 10% |
| `26979` | IVERZINE LOTION 6O ML | ai_low_confidence | 1 | 2319808 | IVERZINE 1 % LOTION 60 ML | 17.773 | Component mismatch: different_dosage | IVERZINE LOTION 6O ML |
| `26979` | IVERZINE LOTION 6O ML | ai_low_confidence | 2 | 2319808 | IVERZINE 1 % LOTION 60 ML | 17.773 | Component mismatch: different_dosage | IVERZINE LOTION 60 ML |
| `26979` | IVERZINE LOTION 6O ML | ai_low_confidence | 3 | 2319808 | IVERZINE 1 % LOTION 60 ML | 17.773 | Component mismatch: different_dosage | IVERZINE LOTION 6O |
| `27457` | EPOETIN 4000 IU VIAL | ai_review_rejected | 1 | <blank> | EPOETIN SEDICO 4000 I.U. / ML VIAL. | 15.822 | Component mismatch: different_brand | EPOETIN 4000 IU VIAL |
| `27457` | EPOETIN 4000 IU VIAL | ai_review_rejected | 2 | <blank> | EPOETIN SEDICO 4000 I.U. / ML VIAL. | 15.822 | Component mismatch: different_brand | EPOETIN 4000 IU |
| `27457` | EPOETIN 4000 IU VIAL | ai_review_rejected | 3 | <blank> | EPOETIN SEDICO 4000 I.U. / ML VIAL. | 15.822 | Component mismatch: different_brand | EPOETIN 4000 |
| `54472` | DIVIDO 75 MG 30 TAB | ai_rejected | 1 | 2406835 | ASPIRIN CHEMIPHARM 75 MG 30 CHEW.TABS | 13.599 | English name missing requested identity token | 75 MG |
| `54472` | DIVIDO 75 MG 30 TAB | ai_rejected | 2 | 2406835 | ASPIRIN CHEMIPHARM 75 MG 30 CHEW.TABS | 13.599 | English name missing requested identity token | 75 MG |
| `54472` | DIVIDO 75 MG 30 TAB | ai_rejected | 3 | 2406835 | ASPIRIN CHEMIPHARM 75 MG 30 CHEW.TABS | 13.599 | English name missing requested identity token | 75 MG |
| `73173` | CONCOR 5 PLUS 30TAB | ai_low_confidence | 1 | 2313532 | CONCOR PLUS 5 / 12.5 MG 30 F.C. TABLETS | 15.734 | Component mismatch: different_brand | CONCOR 5 PLUS 30TAB |
| `73173` | CONCOR 5 PLUS 30TAB | ai_low_confidence | 2 | 2313532 | CONCOR PLUS 5 / 12.5 MG 30 F.C. TABLETS | 15.734 | Component mismatch: different_brand | CONCOR 5 PLUS 30 TAB |
| `73173` | CONCOR 5 PLUS 30TAB | ai_low_confidence | 3 | 2313532 | CONCOR PLUS 5 / 12.5 MG 30 F.C. TABLETS | 15.734 | Component mismatch: different_brand | CONCOR 5 PLUS 30 |
| `73214` | GAST-REG SYRUP 125 ML | ai_rejected | 1 | 2142553 | APIDONE SYRUP 125 ML | 15.459 | English name missing requested identity token | REG SYRUP |
| `73214` | GAST-REG SYRUP 125 ML | ai_rejected | 2 | 2142553 | APIDONE SYRUP 125 ML | 15.459 | English name missing requested identity token | REG SYRUP |
| `73214` | GAST-REG SYRUP 125 ML | ai_rejected | 3 | 2142553 | APIDONE SYRUP 125 ML | 15.459 | English name missing requested identity token | SYRUP 125 |
| `73267` | VITACID C EFF 12 TAB | ai_low_confidence | 1 | 2515480 | VITACID CALCIUM 12 EFF. TAB. | 18.216 | Arabic name contains calcium for VITACID C query | VITACID C EFF 12 TAB |
| `73267` | VITACID C EFF 12 TAB | ai_low_confidence | 2 | 2515480 | VITACID CALCIUM 12 EFF. TAB. | 18.216 | Arabic name contains calcium for VITACID C query | VITACID C EFF 12 |
| `73267` | VITACID C EFF 12 TAB | ai_low_confidence | 3 | 2515480 | VITACID CALCIUM 12 EFF. TAB. | 18.216 | Arabic name contains calcium for VITACID C query | VITACID C EFF |
| `73387` | IVYPRONT COUGH 100 ML SYRUP | ai_rejected | 1 | 2499723 | APPEGREEK SYRUP 100 ML | 13.637 | English name missing requested identity token | SYRUP |
| `73387` | IVYPRONT COUGH 100 ML SYRUP | ai_rejected | 2 | 2499723 | APPEGREEK SYRUP 100 ML | 13.637 | English name missing requested identity token | SYRUP |
| `73387` | IVYPRONT COUGH 100 ML SYRUP | ai_rejected | 3 | 901681 | EPICOPHYLLINE 2.5 G / 100 ML SYRUP 125 ML | 13.496 | English name missing requested identity token | ML SYRUP |
| `73458` | ECTOMETHRIN 5%LOTION 50 ML | ai_search_accepted | 1 | 2474951 | ECTOMETHRIN 5 % LOTION 50 ML | 20.000 | Component mismatch: different_dosage | ECTOMETHRIN 5%LOTION 50 ML |
| `73458` | ECTOMETHRIN 5%LOTION 50 ML | ai_search_accepted | 2 | 2474951 | ECTOMETHRIN 5 % LOTION 50 ML | 20.000 | Component mismatch: different_dosage | ECTOMETHRIN 5 LOTION 50 ML |
| `73458` | ECTOMETHRIN 5%LOTION 50 ML | ai_search_accepted | 3 | 2474951 | ECTOMETHRIN 5 % LOTION 50 ML | 20.000 | Component mismatch: different_dosage | ECTOMETHRIN 5 LOTION 50 |
| `73571` | PRISOLINE DROPS | ai_search_accepted | 1 | 2621859 | PRISOLINE EYE / NASAL DROPS 15 ML | 12.261 | Component mismatch: different_modifier | PRISOLINE DROPS |
| `73571` | PRISOLINE DROPS | ai_search_accepted | 2 | 2621859 | PRISOLINE EYE / NASAL DROPS 15 ML | 12.261 | Component mismatch: different_modifier | PRISOLINE |
| `73571` | PRISOLINE DROPS | ai_search_accepted | 3 | 2621859 | PRISOLINE EYE / NASAL DROPS 15 ML | 12.261 | Component mismatch: different_modifier | PRISOLINE DROPS |
| `74624` | MUCO S.R 20TAB | ai_rejected | 1 | 2313009 | DECANCIT S.R 20 F.C.TAB | 17.678 | English name missing requested identity token | R 20 |
| `74624` | MUCO S.R 20TAB | ai_rejected | 2 | 2313009 | DECANCIT S.R 20 F.C.TAB | 17.678 | English name missing requested identity token | R 20 |
| `74624` | MUCO S.R 20TAB | ai_rejected | 3 | 2313009 | DECANCIT S.R 20 F.C.TAB | 17.678 | English name missing requested identity token | R 20 |
| `80131` | DOLIPRANE 1000 MG 15 TABS | ai_rejected | 1 | 2673371 | CETAL 1000 MG 15 TABS | 15.096 | English name missing requested identity token | 15 TABS |
| `80131` | DOLIPRANE 1000 MG 15 TABS | ai_rejected | 2 | 2673371 | CETAL 1000 MG 15 TABS | 15.096 | English name missing requested identity token | 15 TABS |
| `80131` | DOLIPRANE 1000 MG 15 TABS | ai_rejected | 3 | 2673371 | CETAL 1000 MG 15 TABS | 15.096 | English name missing requested identity token | 15 TABS |
| `83725` | BEBELAC BEBEJUNIOR 3 MILK 400 GM | ai_rejected | 1 | <blank> | BEBELAC 3 (BEBEJUNIOR 1 +) MILK 400 GM | 15.197 | Component mismatch: different_brand | BEBELAC BEBEJUNIOR 3 MILK 400 GM |
| `83725` | BEBELAC BEBEJUNIOR 3 MILK 400 GM | ai_rejected | 2 | <blank> | BEBELAC 3 (BEBEJUNIOR 1 +) MILK 400 GM | 15.197 | Component mismatch: different_brand | BEBELAC BEBEJUNIOR 3 MILK |
| `83725` | BEBELAC BEBEJUNIOR 3 MILK 400 GM | ai_rejected | 3 | <blank> | BEBELAC 3 (BEBEJUNIOR 1 +) MILK 400 GM | 15.197 | Component mismatch: different_brand | BEBELAC BEBEJUNIOR 3 |
| `89527` | LIMITLESS B-COMPLEX ODF 30 FILMS | ai_rejected | 1 | 2304401 | LIMITLESS DIOSMIN COMPLEX 30 FILM COATED TABLETS | 16.242 | Component mismatch: different_brand | LIMITLESS B-COMPLEX ODF 30 FILMS |
| `89527` | LIMITLESS B-COMPLEX ODF 30 FILMS | ai_rejected | 2 | 2304401 | LIMITLESS DIOSMIN COMPLEX 30 FILM COATED TABLETS | 16.242 | Component mismatch: different_brand | LIMITLESS B COMPLEX ODF 30 FILMS |
| `89527` | LIMITLESS B-COMPLEX ODF 30 FILMS | ai_rejected | 3 | 2304401 | LIMITLESS DIOSMIN COMPLEX 30 FILM COATED TABLETS | 16.242 | Component mismatch: different_brand | LIMITLESS B-COMPLEX ODF 30 |
| `89588` | REXODIN 10% ANTISEPTIC SOLUTION 60 ML | ai_rejected | 1 | 2476150 | REXODIN ANTISEPTIC SOLUTION 60 ML | 16.449 | Component mismatch: different_brand | REXODIN 10% ANTISEPTIC SOLUTION 60 ML |
| `89588` | REXODIN 10% ANTISEPTIC SOLUTION 60 ML | ai_rejected | 2 | 2476150 | REXODIN ANTISEPTIC SOLUTION 60 ML | 16.449 | Component mismatch: different_brand | REXODIN 10 ANTISEPTIC SOLUTION 60 ML |
| `89588` | REXODIN 10% ANTISEPTIC SOLUTION 60 ML | ai_rejected | 3 | 2476150 | REXODIN ANTISEPTIC SOLUTION 60 ML | 16.449 | Component mismatch: different_brand | REXODIN 10% ANTISEPTIC SOLUTION |
| `TOUX` | TOUX PROSPERITY SYRUP 120 ML | ai_rejected | 1 | 2468081 | APPE RAISE SYRUP 120 ML | 15.329 | English name missing requested identity token | SYRUP 120 |
| `TOUX` | TOUX PROSPERITY SYRUP 120 ML | ai_rejected | 2 | 2468081 | APPE RAISE SYRUP 120 ML | 15.329 | English name missing requested identity token | SYRUP 120 |
| `TOUX` | TOUX PROSPERITY SYRUP 120 ML | ai_rejected | 3 | 2468081 | APPE RAISE SYRUP 120 ML | 15.329 | English name missing requested identity token | SYRUP 120 |
| `lev` | LEVIASILLS SOOTHING EFFECTIVE RELIEF | ai_rejected | 1 | 2130600 | CAREFREE DUO EFFECT DAILY INTIMATE WASH WITH VITAMIN E AND COTTON EXTRACT 200 ML | 6.493 | English name missing requested identity token | EFFECTIVE RELIEF |
| `lev` | LEVIASILLS SOOTHING EFFECTIVE RELIEF | ai_rejected | 2 | 2130600 | CAREFREE DUO EFFECT DAILY INTIMATE WASH WITH VITAMIN E AND COTTON EXTRACT 200 ML | 6.493 | English name missing requested identity token | EFFECTIVE RELIEF |
| `lev` | LEVIASILLS SOOTHING EFFECTIVE RELIEF | ai_rejected | 3 | 2130600 | CAREFREE DUO EFFECT DAILY INTIMATE WASH WITH VITAMIN E AND COTTON EXTRACT 200 ML | 6.493 | English name missing requested identity token | EFFECTIVE RELIEF |

## Rejection Reason Totals

| Rejection reason | Count |
|---|---:|
| English name missing requested identity token | 4,648 |
| Component mismatch: different_brand | 1,174 |
| English name missing requested identity token; Arabic name missing marker for ML | 1,024 |
| Component mismatch: different_modifier | 534 |
| English name missing requested identity token; Arabic name missing marker for EFF | 433 |
| Component mismatch: different_dosage | 406 |
| Arabic name missing marker for ML | 252 |
| Arabic name missing marker for LOTION | 165 |
| Semantic token conflict: TABLET vs CAPSULE | 163 |
| Rejected: overlap=0.667, score=8.405, numeric_match=False, exact_name=False | 141 |
| Synthetic English name missing requested identity token; English name missing requested identity token | 129 |
| Rejected: overlap=0.450, score=10.505, numeric_match=True, exact_name=False | 129 |
| Rejected: overlap=0.450, score=10.337, numeric_match=True, exact_name=False | 129 |
| Rejected: overlap=0.283, score=5.292, numeric_match=False, exact_name=False | 129 |
| Rejected: overlap=0.800, score=9.977, numeric_match=True, exact_name=False | 123 |
| Rejected: overlap=0.740, score=5.013, numeric_match=False, exact_name=False | 123 |
| Arabic name missing marker for LOTION; Arabic name missing marker for ML | 120 |
| Arabic name missing marker for EFF | 114 |
| English name missing requested identity token; Arabic name missing marker for LOTION; Arabic name missing marker for ML | 93 |
| Semantic token conflict: TABLET vs SYRUP | 91 |
| Rejected: overlap=0.833, score=11.561, numeric_match=True, exact_name=False | 83 |
| Candidate has unrequested distinguishing token: PLUS | 77 |
| Rejected: overlap=0.517, score=7.911, numeric_match=False, exact_name=False | 75 |
| Rejected: overlap=0.283, score=5.691, numeric_match=False, exact_name=False | 75 |
| Rejected: overlap=0.283, score=4.846, numeric_match=False, exact_name=False | 75 |
| Rejected: overlap=0.283, score=2.976, numeric_match=False, exact_name=False | 75 |
| Rejected: overlap=0.283, score=2.974, numeric_match=False, exact_name=False | 75 |
| Rejected: overlap=0.567, score=5.886, numeric_match=False, exact_name=False | 74 |
| Rejected: overlap=0.540, score=8.511, numeric_match=True, exact_name=False | 72 |
| Arabic name contains calcium for VITACID C query | 72 |
| Rejected: overlap=0.450, score=10.284, numeric_match=True, exact_name=False | 67 |
| Rejected: overlap=0.667, score=11.722, numeric_match=True, exact_name=False | 67 |
| Rejected: overlap=0.450, score=13.767, numeric_match=True, exact_name=False | 66 |
| Rejected: overlap=0.450, score=11.531, numeric_match=True, exact_name=False | 66 |
| English name missing requested identity token; Arabic name missing marker for LOTION | 61 |
| Rejected: overlap=0.680, score=11.476, numeric_match=False, exact_name=False | 57 |
| Rejected: overlap=0.740, score=10.170, numeric_match=True, exact_name=False | 57 |
| Rejected: overlap=0.680, score=9.476, numeric_match=False, exact_name=False | 57 |
| Rejected: overlap=0.480, score=3.809, numeric_match=False, exact_name=False | 57 |
| Rejected: overlap=0.740, score=10.134, numeric_match=False, exact_name=False | 57 |
| Semantic token conflict: VIAL vs TABLET | 49 |
| Rejected: overlap=0.667, score=11.577, numeric_match=True, exact_name=False | 37 |
| Rejected: overlap=0.333, score=4.640, numeric_match=False, exact_name=False | 37 |
| Rejected: overlap=0.567, score=4.006, numeric_match=False, exact_name=False | 37 |
| Rejected: overlap=0.567, score=3.233, numeric_match=False, exact_name=False | 37 |
| Rejected: overlap=0.333, score=1.367, numeric_match=False, exact_name=False | 37 |
| Rejected: overlap=0.733, score=10.992, numeric_match=True, exact_name=False | 36 |
| Rejected: overlap=0.500, score=7.545, numeric_match=False, exact_name=False | 36 |
| Rejected: overlap=0.250, score=3.242, numeric_match=False, exact_name=False | 35 |
| Rejected: overlap=0.250, score=3.081, numeric_match=False, exact_name=False | 35 |
| Rejected: overlap=0.250, score=3.000, numeric_match=False, exact_name=False | 35 |
| Rejected: overlap=0.250, score=2.894, numeric_match=False, exact_name=False | 35 |
| Semantic token conflict: VIAL vs CAPSULE | 32 |
| Candidate has unrequested distinguishing token: MAX | 24 |
| Rejected: overlap=0.500, score=14.091, numeric_match=True, exact_name=False | 24 |
| Rejected: overlap=0.500, score=13.769, numeric_match=True, exact_name=False | 24 |
| Rejected: overlap=0.500, score=11.609, numeric_match=True, exact_name=False | 24 |
| Rejected: overlap=0.567, score=8.156, numeric_match=False, exact_name=False | 24 |
| Rejected: overlap=0.333, score=6.048, numeric_match=False, exact_name=False | 24 |
| Rejected: overlap=0.740, score=11.228, numeric_match=True, exact_name=False | 16 |
| Rejected: overlap=0.540, score=9.673, numeric_match=True, exact_name=False | 16 |
| Rejected: overlap=0.500, score=11.591, numeric_match=True, exact_name=False | 16 |
| Rejected: overlap=0.500, score=11.278, numeric_match=True, exact_name=False | 16 |
| Rejected: overlap=0.450, score=13.056, numeric_match=True, exact_name=False | 14 |
| Rejected: overlap=0.333, score=12.497, numeric_match=True, exact_name=False | 14 |
| Rejected: overlap=0.333, score=6.576, numeric_match=False, exact_name=False | 14 |
| Rejected: overlap=0.283, score=5.610, numeric_match=False, exact_name=False | 14 |
| Semantic token conflict: TABLET vs DROPS | 13 |
| Rejected: overlap=0.450, score=10.930, numeric_match=True, exact_name=False | 12 |
| Rejected: overlap=0.283, score=5.067, numeric_match=False, exact_name=False | 12 |
| Rejected: overlap=0.167, score=3.667, numeric_match=False, exact_name=False | 12 |
| Rejected: overlap=0.283, score=2.521, numeric_match=False, exact_name=False | 12 |
| Rejected: overlap=0.250, score=5.462, numeric_match=False, exact_name=False | 10 |
| Rejected: overlap=0.250, score=5.344, numeric_match=False, exact_name=False | 10 |
| Rejected: overlap=0.250, score=5.222, numeric_match=False, exact_name=False | 10 |
| Rejected: overlap=0.250, score=5.208, numeric_match=False, exact_name=False | 10 |
| Rejected: overlap=0.250, score=5.206, numeric_match=False, exact_name=False | 10 |
| Rejected: overlap=0.250, score=5.167, numeric_match=False, exact_name=False | 10 |
| Rejected: overlap=0.250, score=5.143, numeric_match=False, exact_name=False | 10 |
| Rejected: overlap=0.250, score=5.097, numeric_match=False, exact_name=False | 10 |
| Rejected: overlap=0.250, score=5.090, numeric_match=False, exact_name=False | 10 |
| Rejected: overlap=0.250, score=4.778, numeric_match=False, exact_name=False | 10 |
| Rejected: overlap=0.500, score=13.857, numeric_match=True, exact_name=False | 10 |
| Rejected: overlap=0.567, score=5.469, numeric_match=False, exact_name=False | 10 |
| Synthetic English name missing requested identity token; English name missing requested identity token; Arabic name missing marker for LOTION; Arabic name missing marker for ML | 9 |
| Rejected: overlap=0.500, score=13.453, numeric_match=True, exact_name=False | 9 |
| Rejected: overlap=0.680, score=10.622, numeric_match=True, exact_name=False | 8 |
| Rejected: overlap=0.680, score=10.607, numeric_match=True, exact_name=False | 8 |
| Rejected: overlap=0.740, score=11.253, numeric_match=True, exact_name=False | 7 |
| Rejected: overlap=0.540, score=9.962, numeric_match=True, exact_name=False | 7 |
| Rejected: overlap=0.540, score=9.820, numeric_match=True, exact_name=False | 7 |
| Rejected: overlap=0.820, score=9.381, numeric_match=True, exact_name=False | 7 |
| Rejected: overlap=0.540, score=9.039, numeric_match=True, exact_name=False | 7 |
| Rejected: overlap=0.500, score=8.953, numeric_match=True, exact_name=False | 7 |
| Rejected: overlap=0.283, score=4.838, numeric_match=False, exact_name=False | 6 |
| Rejected: overlap=0.250, score=4.467, numeric_match=False, exact_name=False | 4 |
| Rejected: overlap=0.250, score=2.192, numeric_match=False, exact_name=False | 4 |
| Rejected: overlap=0.480, score=7.493, numeric_match=False, exact_name=False | 4 |
| Rejected: overlap=0.340, score=3.813, numeric_match=False, exact_name=False | 4 |
| Rejected: overlap=0.200, score=2.774, numeric_match=False, exact_name=False | 4 |
| Rejected: overlap=0.340, score=0.633, numeric_match=False, exact_name=False | 4 |
| Rejected: overlap=0.340, score=0.584, numeric_match=False, exact_name=False | 4 |
| Rejected: overlap=0.340, score=0.506, numeric_match=False, exact_name=False | 4 |
| Rejected: overlap=0.283, score=5.178, numeric_match=False, exact_name=False | 4 |
| Rejected: overlap=0.500, score=5.988, numeric_match=False, exact_name=False | 4 |
| Rejected: overlap=0.500, score=5.909, numeric_match=False, exact_name=False | 4 |
| Rejected: overlap=0.500, score=5.321, numeric_match=False, exact_name=False | 4 |
| Rejected: overlap=0.588, score=6.277, numeric_match=False, exact_name=False | 3 |
| Rejected: overlap=0.675, score=10.546, numeric_match=False, exact_name=False | 3 |
| Rejected: overlap=0.425, score=4.879, numeric_match=False, exact_name=False | 3 |
| Component mismatch: different_weight | 3 |
| Rejected: overlap=0.783, score=10.100, numeric_match=True, exact_name=False | 3 |
| Rejected: overlap=0.763, score=10.482, numeric_match=False, exact_name=False | 3 |
| Rejected: overlap=0.250, score=9.403, numeric_match=True, exact_name=False | 3 |
| Rejected: overlap=0.500, score=8.286, numeric_match=False, exact_name=False | 3 |
| Rejected: overlap=0.500, score=8.188, numeric_match=False, exact_name=False | 3 |
| Rejected: overlap=0.338, score=7.994, numeric_match=True, exact_name=False | 3 |
| Rejected: overlap=0.338, score=7.155, numeric_match=False, exact_name=False | 3 |
| Rejected: overlap=0.740, score=11.071, numeric_match=True, exact_name=False | 3 |
| Rejected: overlap=0.667, score=10.407, numeric_match=True, exact_name=False | 3 |
| Rejected: overlap=0.250, score=4.311, numeric_match=False, exact_name=False | 2 |
| Rejected: overlap=0.250, score=4.270, numeric_match=False, exact_name=False | 2 |
| Rejected: overlap=0.250, score=2.000, numeric_match=False, exact_name=False | 2 |
| Rejected: overlap=0.250, score=1.833, numeric_match=False, exact_name=False | 2 |
| Rejected: overlap=0.250, score=1.790, numeric_match=False, exact_name=False | 2 |
| Rejected: overlap=0.783, score=11.717, numeric_match=True, exact_name=False | 2 |
| Rejected: overlap=0.300, score=0.848, numeric_match=False, exact_name=False | 2 |
| Rejected: overlap=0.450, score=10.171, numeric_match=True, exact_name=False | 2 |
| Rejected: overlap=0.283, score=4.816, numeric_match=False, exact_name=False | 2 |
| Rejected: overlap=0.283, score=4.774, numeric_match=False, exact_name=False | 2 |
| Rejected: overlap=0.283, score=4.753, numeric_match=False, exact_name=False | 2 |
| Rejected: overlap=0.250, score=3.444, numeric_match=False, exact_name=False | 2 |
| Semantic token conflict: VIAL vs DROPS | 2 |
| Rejected: overlap=0.783, score=11.004, numeric_match=True, exact_name=False | 1 |
| Rejected: overlap=0.740, score=11.465, numeric_match=False, exact_name=False | 1 |
| Rejected: overlap=0.600, score=10.345, numeric_match=False, exact_name=False | 1 |
| Rejected: overlap=0.250, score=3.212, numeric_match=False, exact_name=False | 1 |
| Rejected: overlap=0.540, score=9.668, numeric_match=False, exact_name=False | 1 |

## Concrete Fix List

1. Do not allow an ordering-capable match when `candidate_id` is blank. Keep it as diagnostic/manual-review only.
2. Add a tie-break report for items with more than one accepted candidate id or candidate name.
3. Treat `exact_normalized_name_match` as safer than `high_token_overlap`; fuzzy accepted rows with extra/missing numeric tokens need review.
4. Fix false negatives where parsing rejects likely valid products, especially ECTOMETHRIN, IVERZINE `6O` vs `60`, CONCOR PLUS, EPOETIN, and Bebelac/Bebejunior.
5. Add regression tests from this trace for blank ids, multiple accepted ids, tokenized OPTIZORB, PANTHENOL 5%, JEPARILON 10 vs 20, and SUPRAX syrup/suspension equivalence.

