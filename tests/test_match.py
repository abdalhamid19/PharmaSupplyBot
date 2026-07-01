import sys
from src.core.utils.excel import Item
from src.core.matching.product_matching import explain_best_product_match

item = Item("1", "BETADINE ANTISEPTIC 60 ML SOLN. 10%", 1)
candidates = [
    {"productNameEn": "BETADINE ANTISEPTIC SOLN. 10 % 120 ML", "productName": "بيتادين 120مللى محلول مطهر 10%", "storeProductId": "s1", "salePrice": 100, "availableQuantity": 10}
]

search_results = [("BETADINE ANTISEPTIC 60 ML SOLN. 10%", candidates)]
decision = explain_best_product_match(item, search_results)

print("Best Match:", bool(decision.best_match))
print("Final Reason:", decision.final_reason)
for d in decision.diagnostics:
    print(d.candidate["productNameEn"], "-> Accepted:", d.accepted, "AccReason:", d.accepted_reason, "RejReason:", d.rejection_reason)
