# Vendor Module Phase A — Inventory Automation (Implementation Status)

## What the audit found (from code reads)
- **Menu & Inventory models exist**:
  - `app/modules/menu/model.py`
    - `MenuItem.available_quantity`
    - `Inventory.current_stock`, `low_stock_threshold`, `auto_disable`
- **Inventory endpoints exist**:
  - `app/modules/menu/router.py` under `/menu/.../inventory/...`
  - Includes low-stock alerts: `GET /menu/inventory/alerts/low-stock`
- **Order placement already deducts inventory**:
  - `app/modules/orders/checkout_service.py`
    - `_validate_order_items_for_vendor(...)` checks `MenuItem.available_quantity` and `Inventory.current_stock`
    - `_deduct_inventory_for_order(...)` deducts from `MenuItem.available_quantity` and `Inventory.current_stock`
    - Auto-disable happens when stock reaches 0

## Gap analysis for the requested spec
Requested (from user):
- Auto stock deduction on order completion
- Auto stock deduction on accepted/prepared orders where appropriate
- Low-stock detection
- Out-of-stock detection
- Auto disable unavailable products
- Auto enable workflow
- Inventory alert notifications

Actual implementation in code:
- ✅ Stock is deducted at **checkout / order placement** time (not at accepted/prepared/completed).
- ✅ Low/out-of-stock checks exist.
- ✅ Auto-disable exists (`Inventory.auto_disable` + `MenuItem.is_available` updates).
- ❌ No dedicated stock deduction logic on:
  - `vendor accept` (CONFIRMED)
  - `vendor prepare` (PREPARING)
  - `vendor ready` (READY)
  - `order completion / picked` (PICKED)
- ❌ No automatic stock “auto-enable” workflow unless vendor manually restocks (restock endpoint exists).
- ❌ No inventory alert push integration on stock crossing thresholds (only vendor can pull low-stock alerts via API).

## Implementation plan (next steps)
1. Add an inventory reservation + commit flow aligned with the order lifecycle.
   - Reserve inventory when vendor accepts / confirms (or when status becomes CONFIRMED).
   - Commit (deduct) when order becomes PICKED (pickup confirmed) OR READY depending on business choice.
2. Add low/out-of-stock detection events and push notifications using existing notification/FCM layers.
3. Ensure invalid transitions are blocked by existing order state machine.

## Blockers
- Web search is unavailable (ripgrep missing), but direct file reads succeeded for the inventory and order checkout modules.
- Tests could not be executed due to shell command parsing issues with `&&` separators.

## Current status
- No code changes have been applied yet in this phase.

