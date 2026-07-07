# Broadcast System Plan

## Backend
- [ ] Add `Broadcast` model to `app/modules/admin/model.py`
- [ ] Add `POST /admin/broadcasts` — fans out push + optionally SMS for critical, persists history
- [ ] Add `GET /admin/broadcasts` — list real broadcast history
- [ ] Add broadcast schemas

## Frontend (tnt-admin)
- [ ] Add `getBroadcasts()` and `sendBroadcast()` to `adminApi`
- [ ] Replace hardcoded `sentList` with real fetch on mount
- [ ] Add severity selector (info/warning/critical)
- [ ] Add audience filter (all/faculty/vendor_customers)

## Acceptance
- Sending a broadcast creates a real backend record
- Reload shows real data, not hardcoded
- "critical" severity also calls the SMS path
