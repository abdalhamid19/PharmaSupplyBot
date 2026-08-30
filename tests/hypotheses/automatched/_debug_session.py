"""Inspect saved Tawreed session state for expired cookies/tokens."""
import json
import time
import datetime

with open(r"state\wardany.json", encoding="utf-8") as f:
    state = json.load(f)

now = time.time()
print("=== COOKIES ===")
for c in state.get("cookies", []):
    exp = c.get("expires", -1)
    exp_s = datetime.datetime.fromtimestamp(exp).isoformat() if exp and exp > 0 else "session"
    expired = "EXPIRED" if (exp and exp > 0 and exp < now) else "ok"
    print(f"{c['name'][:32]:34} {c['domain']:22} {exp_s:27} {expired}")

print("\n=== LOCAL STORAGE ===")
for o in state.get("origins", []):
    for item in o.get("localStorage", []):
        print(f"{o['origin']:28} {item['name']:28} len={len(item['value'])}")
