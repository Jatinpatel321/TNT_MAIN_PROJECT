import requests
import json

BASE = "http://localhost:8000"

# Test 1: Admin analytics
print("=== GET /v1/admin/analytics ===")
r = requests.get(f"{BASE}/v1/admin/analytics")
print(f"  Status: {r.status_code}")
print(f"  Body: {r.text[:200]}")

print()

# Test 2: Admin vendors
print("=== GET /v1/admin/vendors ===")
r = requests.get(f"{BASE}/v1/admin/vendors")
print(f"  Status: {r.status_code}")
print(f"  Body: {r.text[:200]}")

print()

# Test 3: Admin orders
print("=== GET /v1/admin/orders ===")
r = requests.get(f"{BASE}/v1/admin/orders")
print(f"  Status: {r.status_code}")
print(f"  Body: {r.text[:200]}")

print()

# Test 4: Admin conflicts
print("=== GET /v1/admin/conflicts ===")
r = requests.get(f"{BASE}/v1/admin/conflicts")
print(f"  Status: {r.status_code}")
print(f"  Body: {r.text[:200]}")

print()

# Test 5: AI signals/rush-hour
print("=== GET /v1/ai/signals/rush-hour ===")
r = requests.get(f"{BASE}/v1/ai/signals/rush-hour")
print(f"  Status: {r.status_code}")
print(f"  Body: {r.text[:200]}")

print()

# Test 6: AI vendor-ranking
print("=== GET /v1/ai/vendor-ranking ===")
r = requests.get(f"{BASE}/v1/ai/vendor-ranking")
print(f"  Status: {r.status_code}")
print(f"  Body: {r.text[:200]}")

print()

# Test 7: Complaints
print("=== GET /v1/complaints/ ===")
r = requests.get(f"{BASE}/v1/complaints/")
print(f"  Status: {r.status_code}")
print(f"  Body: {r.text[:200]}")

print()

# Test all v1/ routes to check for matches
print("=== OpenAPI spec - checking for route collisions ===")
r = requests.get(f"{BASE}/openapi.json")
spec = r.json()
paths = list(spec.get("paths", {}).keys())

# Look for potential 405 issues - same path with wrong method
from collections import defaultdict
path_to_methods = defaultdict(set)
for path, methods in spec.get("paths", {}).items():
    for method in methods:
        path_to_methods[path].add(method.upper())

# Find paths used by dashboard frontend
dashboard_paths = [
    "/v1/admin/analytics",
    "/v1/admin/vendors",
    "/v1/admin/orders",
    "/v1/admin/conflicts",
    "/v1/ai/signals/rush-hour",
    "/v1/ai/vendor-ranking",
    "/v1/complaints/",
    "/v1/ai/demand-planning",
]
for p in dashboard_paths:
    if p in path_to_methods:
        print(f"  {p}: {path_to_methods[p]}")
    else:
        print(f"  {p}: NOT FOUND")
