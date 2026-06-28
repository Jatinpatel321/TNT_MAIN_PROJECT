"""Standalone dev server for vendor module — bypasses ML deps not available on Python 3.15."""
import sys
import os

# Add current dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Stub out all missing ML/deps
import types
for mod_name in ['numpy', 'joblib', 'scipy', 'pandas', 'sklearn', 'xgboost', 'lightgbm']:
    if mod_name not in sys.modules:
        stub = types.ModuleType(mod_name)
        stub.__file__ = '<stub>'
        stub.__package__ = mod_name
        sys.modules[mod_name] = stub

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Minimal config
from app.core.config import settings
from app.core.logging_setup import configure_logging
from app.core.startup_checks import validate_production_settings
from app.database.init_db import init_db

configure_logging(settings.LOG_JSON)
validate_production_settings(settings.APP_ENV, settings.CORS_ORIGINS)
try:
    init_db()
except Exception as e:
    print(f"Warning: DB init issue (OK if tables exist): {e}")

app = FastAPI(title="TNT Vendor Dev")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include only vendor auth router + health
from fastapi import APIRouter as APIRouterCls
from app.modules.vendors.auth_router import router as vendor_auth_router
from app.modules.vendors.router import router as vendors_router
from app.modules.auth.router import router as auth_router

# Wrap all routes under /v1 prefix to match frontend expectations
v1_router = APIRouterCls(prefix="/v1")
v1_router.include_router(vendor_auth_router)
v1_router.include_router(vendors_router)
v1_router.include_router(auth_router)
app.include_router(v1_router)

# Also keep direct routes for backward compat
app.include_router(vendor_auth_router)
app.include_router(vendors_router)
app.include_router(auth_router)

@app.get("/health")
def health():
    return {"status": "ok", "db": "connected"}

@app.get("/")
def root():
    return {"app": "TNT Vendor Dev", "status": "running"}


# ─── Permissions stub (for dev — all permissions granted) ───────────────────
_PERMISSIONS_MODULES = [
    {"module": "dashboard", "actions": ["view_dashboard", "view_analytics"], "description": "Dashboard access"},
    {"module": "orders", "actions": ["view_orders", "accept_orders", "prepare_orders", "complete_orders"], "description": "Order management"},
    {"module": "menu", "actions": ["view_menu", "edit_menu", "manage_items"], "description": "Menu management"},
    {"module": "staff", "actions": ["view_staff", "manage_staff"], "description": "Staff management"},
    {"module": "slots", "actions": ["view_slots", "manage_slots"], "description": "Slot management"},
    {"module": "promotions", "actions": ["view_promotions", "manage_promotions"], "description": "Promotions management"},
    {"module": "settlements", "actions": ["view_settlements"], "description": "Settlement access"},
    {"module": "analytics", "actions": ["view_analytics", "view_reports"], "description": "Analytics access"},
]
_DEFAULT_ROLES = {
    "owner": [a for m in _PERMISSIONS_MODULES for a in m["actions"]],
    "manager": ["view_dashboard", "view_analytics", "view_orders", "accept_orders", "prepare_orders", "complete_orders", "view_menu", "edit_menu", "view_slots", "view_staff"],
    "staff": ["view_dashboard", "view_orders", "accept_orders", "prepare_orders", "complete_orders"],
}


@app.get("/v1/vendors/profile/permissions")
def get_permissions():
    return {
        "permissions": _PERMISSIONS_MODULES,
        "roles": _DEFAULT_ROLES,
    }


# Also mount without /v1 prefix as fallback
@app.get("/vendors/profile/permissions")
def get_permissions_direct():
    return get_permissions()

port = int(os.getenv("PORT", "8000"))
print(f"\n{'='*50}")
print(f"TNT Vendor Dev Server")
print(f"{'='*50}")
print(f"Server: http://0.0.0.0:{port}")
print(f"Login:  POST /vendor/login")
print(f"Health: GET  /health")
print(f"\nVENDOR LOGIN CREDENTIALS:")
print(f"  vendor_id=1  password=vendor123  (Campus Cafe)")
print(f"  vendor_id=2  password=vendor123  (Burger Hub)")
print(f"  vendor_id=3  password=vendor123  (Spice Corner)")
print(f"  vendor_id=4  password=vendor123  (Green Bowl)")
print(f"  vendor_id=5  password=vendor123  (Pizza Station)")
print(f"  vendor_id=6  password=vendor123  (Xerox Point)")
print(f"  vendor_id=7  password=vendor123  (Print Hub)")
print(f"  vendor_id=8  password=vendor123  (Campus Stationery)")
print(f"\nSTAFF LOGIN CREDENTIALS:")
print(f"  staff_phone=+919800100001  password=staff123  (Campus Cafe Manager)")
print(f"  staff_phone=+919800100002  password=staff123  (Campus Cafe Staff)")
print(f"{'='*50}\n")

uvicorn.run(app, host="0.0.0.0", port=port)
