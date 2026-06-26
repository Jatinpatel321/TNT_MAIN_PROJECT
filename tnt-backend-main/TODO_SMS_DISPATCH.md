# SMS Dispatch Fix Plan

## Root Causes of All 20 Test Failures

1. **Missing `StationeryService` import** — `User` model has `relationship("StationeryService")` but `app.modules.stationery.service_model` is never imported, so SQLAlchemy fails mapper config when `Notification(...)` is called.

2. **Wrong patch target in test** — Tests patch `app.modules.notifications.model.Notification` but `notify_user` imports it as a local name in `service.py`, so the patch misses. Must target `app.modules.notifications.service.Notification`.

3. **Slot cancel test mock missing `max_orders`** — `mock_slot` has no `max_orders` attribute, so `_update_slot_status` crashes with `TypeError: '<=' not supported between instances of 'MagicMock' and 'int'`.

## Fix Plan

- [ ] Add StationeryService import to test_sms_dispatch.py
- [ ] Fix patch target from model.Notification to service.Notification
- [ ] Fix slot mock attributes in cancel_slot test
- [ ] Run tests to verify 20/20 pass
