import json

with open("routes_dump.json") as f:
    routes = json.load(f)

suspects = [
    "/v1/cart", "/v1/complaints", "/v1/groups", "/v1/notifications",
    "/v1/search", "/v1/slots", "/v1/vendors", "/v1/admin/calendar-events",
    "/v1/vendors/business-hours", "/v1/vendors/dashboard", "/v1/vendors/demand-dashboard",
]

all_paths = [r["path"] for r in routes]

print("=== Routes matching suspect prefixes ===")
for p in all_paths:
    for s in suspects:
        if p == s or p.startswith(s + "/") or p == s + "/":
            # only print exact-ish
            if p.replace("/v1", "") in [x.replace("/v1", "") for x in suspects] or p in suspects:
                print(f"  {p}  {json.dumps(sorted(r['methods'])) if False else ''}")
                break
print()

print("=== Exact suspect path presence ===")
for s in suspects:
    present = s in all_paths
    print(f"  {'YES ' if present else 'NO  '} {s}")

print()
print("=== All /v1/cart* ===")
for p in all_paths:
    if p.startswith("/v1/cart"):
        print("  ", p)
print("=== All /v1/groups* ===")
for p in all_paths:
    if p.startswith("/v1/groups"):
        print("  ", p)
print("=== All /v1/notifications* ===")
for p in all_paths:
    if p.startswith("/v1/notifications"):
        print("  ", p)
print("=== All /v1/search* ===")
for p in all_paths:
    if p.startswith("/v1/search"):
        print("  ", p)
print("=== All /v1/slots* ===")
for p in all_paths:
    if p.startswith("/v1/slots"):
        print("  ", p)
