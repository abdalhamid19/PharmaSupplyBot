"""Token tables used by Tawreed product-matching lexical penalties."""

from __future__ import annotations

ALIAS_TO_CANONICAL = {
    "AMP": "AMPOULE",
    "AMPS": "AMPOULE",
    "BAG": "BAGS",
    "CAP": "CAPSULE",
    "CAPS": "CAPSULE",
    "CAPSULES": "CAPSULE",
    "DROP": "DROPS",
    "DRP": "DROPS",
    "FILT": "FILTER",
    "FILTERS": "FILTER",
    "FRUIT": "FRUITS",
    "INJ": "INJECTION",
    "SYP": "SYRUP",
    "SUSP": "SUSPENSION",
    "TAB": "TABLET",
    "TABS": "TABLET",
    "TABLETS": "TABLET",
    "VIT": "VITAMIN",
}
CRITICAL_TOKENS = frozenset(
    {
        "ADULT",
        "ANISE",
        "APPLE",
        "BABY",
        "BAGS",
        "CEREAL",
        "CHAMOMILE",
        "CINNAMON",
        "CLOVE",
        "CREAM",
        "DETOX",
        "DROPS",
        "EYE",
        "FILTER",
        "FORTE",
        "FRUITS",
        "GEL",
        "INJECTION",
        "JUNIOR",
        "KIDS",
        "LEMON",
        "LOTION",
        "MAX",
        "MILK",
        "MINT",
        "OINTMENT",
        "ORANGE",
        "PLUS",
        "POWDER",
        "SHAMPOO",
        "SOAP",
        "SPRAY",
        "STRAWBERRY",
        "SYRUP",
        "TABLET",
        "ULTRA",
        "VANILLA",
        "VIAL",
        "VITAMIN",
    }
)
DISTINGUISHING_TOKENS = frozenset(
    {"ADVANCED", "EXTRA", "FORTE", "MAX", "PLUS", "PRO", "SUPER", "ULTRA"}
)
CONFLICT_GROUPS = (
    frozenset({"ANISE", "CHAMOMILE", "CINNAMON", "CLOVE", "DETOX", "MINT"}),
    frozenset({"APPLE", "BANANA", "CHOCOLATE", "LEMON", "ORANGE", "STRAWBERRY"}),
    frozenset({"CREAM", "GEL", "LOTION", "OINTMENT", "SHAMPOO", "SOAP"}),
    frozenset({"DROPS", "INJECTION", "SYRUP", "VIAL"}),
)
