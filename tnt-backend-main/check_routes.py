import sys
from app.main import app

print("Total app.routes:", len(app.routes))
v1 = [r.path for r in app.routes if getattr(r, "path", "") and r.path.startswith("/v1")]
auth = [r.path for r in app.routes if getattr(r, "path", "") and r.path.startswith("/auth")]
orders = [r.path for r in app.routes if getattr(r, "path", "") and "/orders" in r.path]
print("v1 routes:", len(v1))
print("auth routes:", len(auth))
print("orders-containing routes:", len(orders))

# Inspect the api_v1_router directly
from app.api.v1 import api_v1_router
print("api_v1_router.routes:", len(api_v1_router.routes))
print("sample api_v1_router paths:", [r.path for r in api_v1_router.routes[:10]])
