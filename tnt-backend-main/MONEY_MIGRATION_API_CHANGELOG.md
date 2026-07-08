# Money Migration — API Contract Changelog

Canonical unit for every monetary field, across every request and response
body in this API, is now **Indian Rupees (₹)** as a decimal number (e.g.
`73.5`, `0.5`, `9999.99`). Paise only ever exists at the Razorpay HTTP
boundary (`app/core/money.py::to_paise`/`from_paise`) and never appears in
any TNT-owned request/response body.

No API versioning was introduced (no `/v2` prefix). This is a pre-launch,
single-deployment system — backend and all 3 frontends (`tnt-user-frontend`,
`tnt-vendor-frontend`, `tnt-admin`) are migrated and released together, so
there are no independent external API consumers to preserve backward
compatibility for. Versioning would add maintenance overhead without a
corresponding consumer to protect.

## Breaking change: value semantics

Every monetary field in every endpoint changed from **integer paise** to
**decimal rupees**. A client reading `total_amount: 7350` before this
migration must now read `total_amount: 73.50`. This is a silent-looking but
fully breaking change — any external consumer doing `amount / 100` client-side
must remove that division.

## Breaking change: renamed fields

Fields with a stale `_paise` suffix were renamed to drop the suffix (value
semantics also changed to rupees, per above):

| Endpoint area | Old field | New field |
|---|---|---|
| Vouchers (`/rewards/vouchers*`) | `min_order_amount_paise` | `min_order_amount` |
| Vouchers | `max_discount_amount_paise` | `max_discount_amount` |
| Voucher redemptions | `discount_amount_paise` | `discount_amount` |
| Printer cost matrix (`/admin/printers*`) | `price_per_page_paise` | `price_per_page` |
| AI / recommendations (`smart_engine`, `dataset_builder`) | `price_paise` | `price` |
| Admin analytics trends (`/v1/admin/analytics/trends`) | `amount_paise` | `amount` |
| Admin analytics trends | `refund_amount_paise` | `refund_amount` |
| Vendor analytics (internal, no external consumer found) | `total_revenue_paise` | `total_revenue` |

## Breaking change: request body types widened

Menu/stationery price fields accepted `int` (whole paise) and now accept
`float`/decimal rupees — a client sending `8000` meaning ₹80.00 must now send
`80.00`:

- `POST /menu` / menu update — `price`
- `POST /stationery/services` — `price_per_unit`, `price_per_page`
- Admin print-cost-matrix upsert — `price_per_page`
- Admin ledger-adjustment — `amount`

## Removed: cash payment

`TransactionType.CASH_ORDER` and all cash-order fields/endpoints were
removed — see the cash-removal migration (`20260707_0040`). Any client
branch on a `payment_method` or transaction-type value of `"cash"` will no
longer see that value; the platform is online-prepaid only (Razorpay/UPI).

## Non-breaking: internal serialization fixes

Two internal correctness fixes changed *how* values are encoded on the wire
but not their meaning, so no client code changes are needed unless a client
was working around the bugs:
- Routes with a loose `-> dict[str, Any]` return annotation and no
  `response_model` used to serialize `Decimal` money fields as a **JSON
  string** (e.g. `"120.00"`) instead of a number, because Pydantic's default
  encoder stringifies `Decimal` — this bypassed a global
  `ENCODERS_BY_TYPE[Decimal] = float` override in `app/main.py`. All ~55
  affected response sites across `orders`, `payments`, `menu`, `stationery`,
  `vendors`, `recommendations`, `admin`, `fraud`, `group_cart` now explicitly
  `float(...)`-wrap Decimal values so every client always receives a JSON
  number.
- Audit-log writes containing a money field used to hard-crash
  (`TypeError: Decimal not JSON serializable`) on entity mutations (e.g.
  creating a menu item). Fixed; no client-visible change (this was an
  internal 500 on write, not a response-shape change).

## OpenAPI schema

No static OpenAPI file is checked into the repo — the schema is generated
live by FastAPI (`app.openapi()`) directly from the current route/Pydantic
definitions, so it is always in sync with the code above; there is no
separate regeneration step. Verified it still builds cleanly after this
migration (835 paths). Pre-existing duplicate-operation-ID warnings from
routes registered under both legacy and `/v1` paths are unrelated to this
migration and were not touched.
