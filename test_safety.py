import sys
from src.core.utils.excel import Item
from src.core.matching_models import SearchMatch
from src.core.order_ai_safety import local_match_rejection

item1 = Item("74821", "BETADINE ANTISEPTIC 60 ML SOLN. 10%", 1)
match1 = SearchMatch("q1", 0, 100.0, {"productNameEn": "BETADINE ANTISEPTIC SOLN. 10 % 120 ML", "storeProductId": "123"})
print("Betadine rejection:", local_match_rejection(item1, match1))

item2 = Item("91304", "panthenol 5% care cream 50 gm", 1)
match2 = SearchMatch("q2", 0, 100.0, {"productNameEn": "PANTHENOL CREAM 50 GM COLLEDGE", "storeProductId": "124"})
print("Panthenol rejection:", local_match_rejection(item2, match2))
